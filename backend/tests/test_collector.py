"""수집: 응답 해석, 실패 처리, 저장."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import func, select

from app.collector.client import SeoulApiError, fetch_place, parse_response
from app.collector.service import collect_once, record_failure, store_observation
from app.models import Forecast, Place, PlaceStatus, Snapshot

CODE, NAME = "POI009", "광화문·덕수궁"


def payload(
    code: str = CODE,
    level: str = "약간 붐빔",
    time: str = "2026-11-23 15:05",
    forecast: bool = True,
) -> dict:
    row = {
        "AREA_NM": NAME,
        "AREA_CD": code,
        "AREA_CONGEST_LVL": level,
        "AREA_PPLTN_MIN": "22000",
        "AREA_PPLTN_MAX": "24000",
        "PPLTN_TIME": time,
        "FCST_YN": "Y" if forecast else "N",
    }
    if forecast:
        row["FCST_PPLTN"] = [
            {
                "FCST_TIME": "2026-11-23 17:00",
                "FCST_CONGEST_LVL": "보통",
                "FCST_PPLTN_MIN": "100",
                "FCST_PPLTN_MAX": "200",
            },
            {
                "FCST_TIME": "2026-11-23 16:00",
                "FCST_CONGEST_LVL": "여유",
                "FCST_PPLTN_MIN": "100",
                "FCST_PPLTN_MAX": "200",
            },
        ]
    return {
        "SeoulRtd.citydata_ppltn": [row],
        "RESULT": {"RESULT.CODE": "INFO-000", "RESULT.MESSAGE": "정상"},
    }


def test_parse_normal_response_converts_time_and_sorts_forecast():
    obs = parse_response(payload(), CODE)
    assert obs.level == 3
    assert (obs.ppltn_min, obs.ppltn_max) == (22000, 24000)
    # 한국 시간 15:05 = UTC 06:05
    assert obs.observed_at == datetime(2026, 11, 23, 6, 5, tzinfo=UTC)
    assert [point.level for point in obs.forecasts] == [1, 2]


def test_parse_without_forecast():
    assert parse_response(payload(forecast=False), CODE).forecasts == []


def test_parse_rejects_other_place():
    # 체험용 키는 어떤 장소를 물어도 한 장소만 돌려준다. 다른 장소 값으로 저장되면 안 된다.
    with pytest.raises(SeoulApiError, match="다른 장소"):
        parse_response(payload(code="POI009"), "POI001")


def test_parse_error_result_and_bad_values():
    with pytest.raises(SeoulApiError, match="INFO-200"):
        parse_response({"RESULT": {"RESULT.CODE": "INFO-200"}}, CODE)
    with pytest.raises(SeoulApiError, match="혼잡도"):
        parse_response(payload(level="매우 붐빔"), CODE)
    broken = payload()
    del broken["SeoulRtd.citydata_ppltn"][0]["PPLTN_TIME"]
    with pytest.raises(SeoulApiError, match="필요한 값"):
        parse_response(broken, CODE)


def fetch(handler, **kwargs):
    kwargs.setdefault("retries", 0)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await fetch_place(
                http,
                base_url="http://seoul.test",
                api_key="secret-key",
                code=CODE,
                name=NAME,
                backoff_seconds=0,
                **kwargs,
            )

    return asyncio.run(run())


def test_fetch_retries_on_server_error_then_succeeds():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=payload())

    assert fetch(handler, retries=2).level == 3
    assert len(calls) == 2
    assert calls[0].startswith("/secret-key/json/citydata_ppltn/1/5/")


def test_fetch_gives_up_after_retries_without_leaking_key():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("failed http://seoul.test/secret-key/json", request=request)

    with pytest.raises(SeoulApiError) as error:
        fetch(handler, retries=1)
    assert "secret-key" not in str(error.value)
    assert "seoul.test" not in str(error.value)


def test_fetch_reports_invalid_key_sent_as_xml():
    def handler(request: httpx.Request) -> httpx.Response:
        body = "<RESULT><CODE>INFO-100</CODE><MESSAGE>x</MESSAGE></RESULT>"
        return httpx.Response(200, text=body)

    with pytest.raises(SeoulApiError, match="INFO-100"):
        fetch(handler)


def test_fetch_timeout_becomes_short_message():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(SeoulApiError, match="응답 시간 초과"):
        fetch(handler, retries=0)


def count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_store_observation_is_idempotent_and_replaces_forecast(session):
    now = datetime(2026, 11, 23, 6, 30, tzinfo=UTC)
    store_observation(session, parse_response(payload(), CODE), now)
    store_observation(session, parse_response(payload(), CODE), now)
    assert count(session, Snapshot) == 1  # 같은 관측 시각은 한 번만 쌓는다
    assert count(session, Forecast) == 2

    later = parse_response(payload(level="붐빔", time="2026-11-23 15:10", forecast=False), CODE)
    store_observation(session, later, now)
    assert count(session, Snapshot) == 2
    assert count(session, Forecast) == 0  # 예측은 최신 것으로 갈아 끼운다
    status = session.get(PlaceStatus, CODE)
    assert status.level == 4 and status.fail_count == 0


def test_failure_keeps_last_good_value(session):
    now = datetime(2026, 11, 23, 6, 30, tzinfo=UTC)
    store_observation(session, parse_response(payload(), CODE), now)
    record_failure(session, CODE, "응답 시간 초과", now)
    record_failure(session, CODE, "응답 시간 초과", now)
    status = session.get(PlaceStatus, CODE)
    assert status.level == 3
    assert status.fail_count == 2 and status.last_error == "응답 시간 초과"

    record_failure(session, "POI001", "x" * 500, now)
    never = session.get(PlaceStatus, "POI001")
    assert never.level is None and len(never.last_error) == 200


def test_collect_once_one_place_failing_does_not_stop_others(session_factory, settings, caplog):
    with session_factory() as session:
        names = {place.name: place.code for place in session.scalars(select(Place))}

    def handler(request: httpx.Request) -> httpx.Response:
        name = request.url.path.rsplit("/", 1)[-1]
        code = names[name]
        if code == "POI001":
            return httpx.Response(500)
        if code == "POI002":
            return httpx.Response(200, json=payload(code="POI009"))  # 다른 장소 응답
        return httpx.Response(200, json=payload(code=code))

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await collect_once(settings, session_factory, client=http)

    with caplog.at_level(logging.DEBUG):
        result = asyncio.run(run())

    assert (result.total, result.succeeded, result.failed) == (121, 119, 2)
    with session_factory() as session:
        assert count(session, Snapshot) == 119
        assert session.get(PlaceStatus, "POI001").level is None
        assert session.get(PlaceStatus, "POI002").last_error == "요청한 장소와 다른 장소의 응답"
        assert session.get(PlaceStatus, "POI003").level == 3
    # 인증키가 로그에 남지 않는다.
    assert settings.seoul_api_key.get_secret_value() not in caplog.text
    # 설정 객체를 통째로 찍어도 키가 보이지 않는다(SecretStr).
    assert "test-key-123" not in repr(settings)
