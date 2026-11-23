"""수집의 실패 경로: 이상한 응답, 예상 못 한 예외, 저장 실패, 워커 종료 코드."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app import worker
from app.collector import service
from app.collector.client import SeoulApiError, fetch_place, parse_response
from app.collector.service import SAVE_FAILED, collect_once
from app.models import Place, PlaceStatus, Snapshot
from tests.test_collector import CODE, NAME, payload

KEY = "test-key-123"  # conftest의 settings 값과 같다


def with_row(**changes) -> dict:
    data = payload()
    data["SeoulRtd.citydata_ppltn"][0].update(changes)
    return data


@pytest.mark.parametrize(
    "data",
    [
        [],  # 사전이 아니라 목록
        "문자열",
        None,
        {"SeoulRtd.citydata_ppltn": {"AREA_CD": CODE}},  # 목록이 아니라 사전
        {"SeoulRtd.citydata_ppltn": ["문자열"]},  # 목록 안이 사전이 아님
        {"SeoulRtd.citydata_ppltn": [], "RESULT": "문자열"},  # RESULT가 사전이 아님
        {"RESULT": {"RESULT.CODE": None}},
        with_row(PPLTN_TIME=None),  # 시각이 null
        with_row(PPLTN_TIME=20261123),  # 시각이 숫자
        with_row(FCST_PPLTN="문자열"),  # 예측이 목록이 아님
        with_row(FCST_PPLTN=[None]),  # 예측 칸이 null
    ],
)
def test_parse_turns_any_odd_shape_into_seoul_api_error(data):
    # SeoulApiError가 아닌 예외가 나가면 수집 한 바퀴 전체가 멈춘다.
    with pytest.raises(SeoulApiError):
        parse_response(data, CODE)


def run_fetch(handler, retries: int):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await fetch_place(
                http,
                base_url="http://seoul.test",
                api_key=KEY,
                code=CODE,
                name=NAME,
                retries=retries,
                backoff_seconds=0,
            )

    return asyncio.run(run())


def test_fetch_does_not_retry_on_4xx():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(404)

    with pytest.raises(SeoulApiError, match="상태 404"):
        run_fetch(handler, retries=2)
    assert len(calls) == 1


def test_fetch_gives_up_when_5xx_continues():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(502)

    with pytest.raises(SeoulApiError, match="상태 502"):
        run_fetch(handler, retries=2)
    assert len(calls) == 3  # 처음 1번 + 재시도 2번


def collect(session_factory, settings, handler):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await collect_once(settings, session_factory, client=http)

    return asyncio.run(run())


def place_names(session_factory) -> dict[str, str]:
    with session_factory() as session:
        return {place.name: place.code for place in session.scalars(select(Place))}


def test_odd_response_and_unexpected_error_fail_only_that_place(session_factory, settings):
    names = place_names(session_factory)

    def handler(request: httpx.Request) -> httpx.Response:
        code = names[request.url.path.rsplit("/", 1)[-1]]
        if code == "POI001":
            return httpx.Response(200, json={"SeoulRtd.citydata_ppltn": {"AREA_CD": code}})
        if code == "POI002":
            return httpx.Response(200, json=with_row(AREA_CD=code, PPLTN_TIME=None))
        if code == "POI003":
            # httpx 오류가 아닌 예외. 메시지에 주소(인증키)가 들어 있다고 가정한다.
            raise RuntimeError(f"boom http://seoul.test/{KEY}/json")
        if code == "POI004":
            raise httpx.ConnectError(f"failed http://seoul.test/{KEY}/json", request=request)
        return httpx.Response(200, json=payload(code=code))

    result = collect(session_factory, settings, handler)

    assert (result.total, result.succeeded, result.failed) == (121, 117, 4)
    with session_factory() as session:
        errors = {
            code: session.get(PlaceStatus, code).last_error
            for code in ("POI001", "POI002", "POI003", "POI004")
        }
        assert errors == {
            "POI001": "응답 형식 다름",
            "POI002": "응답에 필요한 값이 없음",
            "POI003": "처리 실패 RuntimeError",
            "POI004": "연결 실패 ConnectError",
        }
        # 인증키와 주소가 DB의 실패 사유에 남지 않는다.
        stored = session.scalars(select(PlaceStatus.last_error)).all()
        assert not any(KEY in (text or "") or "seoul.test" in (text or "") for text in stored)
        assert session.get(PlaceStatus, "POI005").level == 3


def test_save_failure_is_recorded_for_that_place_only(session_factory, settings, monkeypatch):
    names = place_names(session_factory)
    real_store = service.store_observation

    def flaky_store(session, obs, now):
        if obs.code == "POI001":
            raise OperationalError("insert", {}, Exception("db down"))
        real_store(session, obs, now)

    monkeypatch.setattr(service, "store_observation", flaky_store)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload(code=names[request.url.path.rsplit("/", 1)[-1]]))

    result = collect(session_factory, settings, handler)

    assert (result.succeeded, result.failed) == (120, 1)
    with session_factory() as session:
        failed = session.get(PlaceStatus, "POI001")
        assert failed.last_error == SAVE_FAILED and failed.fail_count == 1
        assert failed.level is None
        assert session.scalar(select(func.count()).select_from(Snapshot)) == 120


class FakeSettings:
    def __init__(self, key: str):
        from pydantic import SecretStr

        self.seoul_api_key = SecretStr(key)
        self.collect_interval_seconds = 300


def test_worker_exits_with_1_when_key_is_missing(monkeypatch):
    monkeypatch.setattr(worker, "get_settings", lambda: FakeSettings(""))
    assert asyncio.run(worker.run(once=True)) == 1


def test_worker_once_returns_0_and_1(session_factory, monkeypatch):
    monkeypatch.setattr(worker, "get_settings", lambda: FakeSettings(KEY))
    monkeypatch.setattr(worker, "get_session_factory", lambda: session_factory)

    async def ok(settings, factory):
        return None

    async def boom(settings, factory):
        raise RuntimeError("한 바퀴 실패")

    monkeypatch.setattr(worker, "collect_once", ok)
    assert asyncio.run(worker.run(once=True)) == 0
    monkeypatch.setattr(worker, "collect_once", boom)
    assert asyncio.run(worker.run(once=True)) == 1


def test_worker_keeps_running_after_a_failed_round(session_factory, monkeypatch):
    monkeypatch.setattr(worker, "get_settings", lambda: FakeSettings(KEY))
    monkeypatch.setattr(worker, "get_session_factory", lambda: session_factory)
    rounds = []

    async def flaky(settings, factory):
        rounds.append(datetime.now(UTC))
        if len(rounds) == 1:
            raise RuntimeError("첫 바퀴 실패")
        raise asyncio.CancelledError  # 두 번째 바퀴까지 왔으면 루프를 끝낸다

    async def no_sleep(seconds):
        return None

    monkeypatch.setattr(worker, "collect_once", flaky)
    monkeypatch.setattr(worker.asyncio, "sleep", no_sleep)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(worker.run(once=False))
    assert len(rounds) == 2
