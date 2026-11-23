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
from app.collector.client import SeoulApiError, _to_int, fetch_place, parse_response
from app.collector.service import FETCH_TIMED_OUT, SAVE_FAILED, collect_once
from app.models import Forecast, Place, PlaceStatus, Snapshot
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
        with_row(PPLTN_TIME="99999-01-01 00:00"),  # 범위를 벗어난 연도
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


def test_too_large_number_becomes_none_not_an_exception():
    assert _to_int("1e999") is None
    assert parse_response(with_row(AREA_PPLTN_MIN="1e999"), CODE).ppltn_min is None


def ok_handler(names):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload(code=names[request.url.path.rsplit("/", 1)[-1]]))

    return handler


def rows_for(session, model, code: str) -> int:
    return session.scalar(select(func.count()).select_from(model).where(model.place_code == code))


@pytest.mark.parametrize(
    "error",
    [
        OperationalError("insert", {}, Exception("db down")),  # DB 오류
        RuntimeError("DB 오류가 아닌 예외"),  # 그 밖의 예외도 같은 길로 처리한다
    ],
)
def test_save_failure_rolls_back_and_is_recorded(session_factory, settings, monkeypatch, error):
    names = place_names(session_factory)
    real_store = service.store_observation

    def half_written_store(session, obs, now):
        if obs.code != "POI001":
            return real_store(session, obs, now)
        # 스냅샷과 예측을 DB로 내보낸 뒤(commit 전) 실패한다 = 반쯤 쓴 상태.
        session.add(
            Snapshot(place_code=obs.code, observed_at=obs.observed_at, collected_at=now, level=1)
        )
        session.add(Forecast(place_code=obs.code, forecast_time=now, level=1))
        session.flush()
        raise error

    monkeypatch.setattr(service, "store_observation", half_written_store)

    result = collect(session_factory, settings, ok_handler(names))

    assert (result.succeeded, result.failed) == (120, 1)
    with session_factory() as session:
        # 반쯤 쓴 것이 남지 않는다(롤백).
        assert rows_for(session, Snapshot, "POI001") == 0
        assert rows_for(session, Forecast, "POI001") == 0
        failed = session.get(PlaceStatus, "POI001")
        assert failed.level is None and failed.observed_at is None
        assert failed.last_error == SAVE_FAILED and failed.fail_count == 1
        # 다른 장소는 정상 저장된다.
        assert session.scalar(select(func.count()).select_from(Snapshot)) == 120
        assert session.get(PlaceStatus, "POI002").level == 3


def test_round_finishes_even_when_failure_cannot_be_recorded(
    session_factory, settings, monkeypatch
):
    names = place_names(session_factory)
    real_store, real_record = service.store_observation, service.record_failure

    def broken_store(session, obs, now):
        if obs.code == "POI001":
            raise OperationalError("insert", {}, Exception("db down"))
        real_store(session, obs, now)

    def broken_record(session, code, message, now):
        if code == "POI001":
            raise OperationalError("update", {}, Exception("db down"))
        real_record(session, code, message, now)

    monkeypatch.setattr(service, "store_observation", broken_store)
    monkeypatch.setattr(service, "record_failure", broken_record)

    result = collect(session_factory, settings, ok_handler(names))

    # 실패 기록조차 못 남겨도(로그만 남음) 나머지 120곳은 저장된다.
    assert (result.succeeded, result.failed) == (120, 1)
    with session_factory() as session:
        assert session.get(PlaceStatus, "POI001") is None
        assert session.scalar(select(func.count()).select_from(Snapshot)) == 120


def test_place_that_never_finishes_does_not_hold_the_round(session_factory, settings):
    names = place_names(session_factory)
    # 한도를 아주 짧게: 0.02초 × 3 × (재시도 0 + 1) = 0.06초
    settings.collect_timeout_seconds = 0.02
    settings.collect_retries = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        code = names[request.url.path.rsplit("/", 1)[-1]]
        if code == "POI001":
            await asyncio.sleep(30)  # 끝나지 않는 응답
        return httpx.Response(200, json=payload(code=code))

    started = datetime.now(UTC)
    result = collect(session_factory, settings, handler)
    elapsed = (datetime.now(UTC) - started).total_seconds()

    assert elapsed < 10
    assert (result.succeeded, result.failed) == (120, 1)
    with session_factory() as session:
        assert session.get(PlaceStatus, "POI001").last_error == FETCH_TIMED_OUT


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
