"""서울 실시간 도시데이터(실시간 인구) API 호출과 응답 해석.

주의: 인증키가 주소 경로에 들어간다. 그래서 요청 주소나 httpx 예외 원문을
로그·DB에 남기지 않고, 여기서 만든 짧은 메시지만 밖으로 내보낸다.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote

import httpx

from app.levels import LEVEL_BY_NAME
from app.timeutil import parse_seoul_time

# httpx는 INFO 로그에 요청 주소를 통째로 찍는다. 주소에 인증키가 있으므로
# 이 모듈을 쓰는 모든 프로세스(워커·테스트·스크립트)에서 항상 끈다.
for _name in ("httpx", "httpcore"):
    logging.getLogger(_name).setLevel(logging.WARNING)

SERVICE = "citydata_ppltn"
RESULT_KEY = "SeoulRtd.citydata_ppltn"
# 서울시 API 주소의 "시작 행/끝 행". 장소 하나를 물으면 1줄만 오므로 값은 형식상 필요할 뿐이다.
ROW_RANGE = "1/5"
BACKOFF_SECONDS = 0.5
_XML_CODE = re.compile(r"<CODE>([^<]+)</CODE>")
_XML_SCAN_LENGTH = 500


class SeoulApiError(Exception):
    """수집 실패. 메시지에는 인증키나 주소를 넣지 않는다."""


@dataclass(frozen=True)
class ForecastPoint:
    time: datetime
    level: int
    ppltn_min: int | None
    ppltn_max: int | None


@dataclass(frozen=True)
class Observation:
    code: str
    level: int
    ppltn_min: int | None
    ppltn_max: int | None
    observed_at: datetime
    forecasts: list[ForecastPoint] = field(default_factory=list)


def _to_int(value) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        # OverflowError: "1e999"처럼 너무 큰 수
        return None


def _level(name) -> int:
    level = LEVEL_BY_NAME.get(str(name).strip())
    if level is None:
        raise SeoulApiError("알 수 없는 혼잡도 단계")
    return level


def _error_code(data: dict) -> str:
    result = data.get("RESULT")
    if isinstance(result, dict):
        code = result.get("RESULT.CODE") or result.get("CODE")
        if isinstance(code, str) and code:
            return code
    return "응답 형식 다름"


def parse_response(data: object, expected_code: str) -> Observation:
    """응답 JSON을 Observation으로. 모양이 조금이라도 다르면 SeoulApiError.

    밖에서 온 값이라 모양을 믿지 않는다. 예상 밖의 모양은 여기서 SeoulApiError로 바꾼다.
    그래도 빠져나가는 예외는 service._fetch_all이 한 번 더 받아 그 장소만의 실패로 끝낸다.
    """
    if not isinstance(data, dict):
        raise SeoulApiError("응답 형식 다름")
    rows = data.get(RESULT_KEY)
    if not rows:
        raise SeoulApiError(f"서울시 API 오류 {_error_code(data)}")
    if not isinstance(rows, list) or not isinstance(rows[0], dict):
        raise SeoulApiError("응답 형식 다름")
    row = rows[0]
    # 다른 장소의 값이 돌아오는 경우가 있다(예: 체험용 sample 키는 항상 한 장소만 준다).
    if row.get("AREA_CD") != expected_code:
        raise SeoulApiError("요청한 장소와 다른 장소의 응답")
    try:
        observed_at = parse_seoul_time(row["PPLTN_TIME"])
        level = _level(row["AREA_CONGEST_LVL"])
        forecasts = []
        if row.get("FCST_YN") == "Y":
            for item in row.get("FCST_PPLTN") or []:
                forecasts.append(
                    ForecastPoint(
                        time=parse_seoul_time(item["FCST_TIME"]),
                        level=_level(item["FCST_CONGEST_LVL"]),
                        ppltn_min=_to_int(item.get("FCST_PPLTN_MIN")),
                        ppltn_max=_to_int(item.get("FCST_PPLTN_MAX")),
                    )
                )
    except (KeyError, ValueError, TypeError, AttributeError, OverflowError) as exc:
        # 값이 없거나(null), 문자열이 아니거나, 목록 안이 사전이 아니거나, 범위를 벗어난 경우
        raise SeoulApiError("응답에 필요한 값이 없음") from exc
    forecasts.sort(key=lambda point: point.time)
    return Observation(
        code=expected_code,
        level=level,
        ppltn_min=_to_int(row.get("AREA_PPLTN_MIN")),
        ppltn_max=_to_int(row.get("AREA_PPLTN_MAX")),
        observed_at=observed_at,
        forecasts=forecasts,
    )


def _decode(response: httpx.Response) -> object:
    """본문을 JSON으로. 인증키 오류는 상태 200에 XML로 온다."""
    try:
        return response.json()
    except ValueError:
        match = _XML_CODE.search(response.text[:_XML_SCAN_LENGTH])
        code = match.group(1) if match else "JSON 아님"
        raise SeoulApiError(f"서울시 API 오류 {code}") from None


async def fetch_place(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    api_key: str,
    code: str,
    name: str,
    retries: int,
    backoff_seconds: float = BACKOFF_SECONDS,
) -> Observation:
    """장소 하나의 실시간 인구를 가져온다. 일시적 실패는 retries번 다시 시도한다."""
    url = f"{base_url}/{quote(api_key, safe='')}/json/{SERVICE}/{ROW_RANGE}/{quote(name, safe='')}"
    last_error = "알 수 없는 오류"
    for attempt in range(retries + 1):
        if attempt:
            await asyncio.sleep(backoff_seconds * attempt)
        try:
            response = await client.get(url)
        except httpx.TimeoutException:
            last_error = "응답 시간 초과"
            continue
        except httpx.HTTPError as exc:
            # 예외 원문에는 주소(인증키)가 들어 있어서 종류 이름만 남긴다.
            last_error = f"연결 실패 {type(exc).__name__}"
            continue
        if response.status_code >= 500:
            last_error = f"서울시 API 상태 {response.status_code}"
            continue
        if response.status_code != 200:
            raise SeoulApiError(f"서울시 API 상태 {response.status_code}")
        # 형식·인증 오류는 다시 시도해도 같으므로 바로 실패로 둔다.
        return parse_response(_decode(response), code)
    raise SeoulApiError(last_error)
