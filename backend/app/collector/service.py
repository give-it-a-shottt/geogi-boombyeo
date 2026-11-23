"""수집 한 바퀴: 121곳을 가져와 DB에 넣는다."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

import httpx
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.collector.client import Observation, SeoulApiError, fetch_place
from app.config import Settings
from app.models import LAST_ERROR_MAX_LENGTH, Forecast, Place, PlaceStatus, Snapshot
from app.timeutil import now_utc

logger = logging.getLogger(__name__)

SAVE_FAILED = "저장 실패"


@dataclass(frozen=True)
class CollectResult:
    total: int
    succeeded: int
    failed: int


def _get_status(session: Session, code: str, now: datetime) -> PlaceStatus:
    status = session.get(PlaceStatus, code)
    if status is None:
        status = PlaceStatus(place_code=code, last_attempt_at=now, fail_count=0)
        session.add(status)
    return status


def store_observation(session: Session, obs: Observation, now: datetime) -> None:
    """관측 하나를 저장한다: 원본 기록 추가, 예측 교체, 최신 상태 갱신. 한 트랜잭션."""
    already = session.scalar(
        select(Snapshot.id).where(
            Snapshot.place_code == obs.code, Snapshot.observed_at == obs.observed_at
        )
    )
    if already is None:
        session.add(
            Snapshot(
                place_code=obs.code,
                observed_at=obs.observed_at,
                collected_at=now,
                level=obs.level,
                ppltn_min=obs.ppltn_min,
                ppltn_max=obs.ppltn_max,
            )
        )

    session.execute(delete(Forecast).where(Forecast.place_code == obs.code))
    seen: set[datetime] = set()
    for point in obs.forecasts:
        if point.time in seen:
            continue
        seen.add(point.time)
        session.add(
            Forecast(
                place_code=obs.code,
                forecast_time=point.time,
                level=point.level,
                ppltn_min=point.ppltn_min,
                ppltn_max=point.ppltn_max,
            )
        )

    status = _get_status(session, obs.code, now)
    status.level = obs.level
    status.ppltn_min = obs.ppltn_min
    status.ppltn_max = obs.ppltn_max
    status.observed_at = obs.observed_at
    status.last_success_at = now
    status.last_attempt_at = now
    status.fail_count = 0
    status.last_error = None
    session.commit()


def record_failure(session: Session, code: str, message: str, now: datetime) -> None:
    """실패를 적는다. 마지막으로 성공한 값은 지우지 않는다(오래되면 화면이 '지연'으로 보여 준다)."""
    status = _get_status(session, code, now)
    status.last_attempt_at = now
    status.fail_count += 1
    status.last_error = message[:LAST_ERROR_MAX_LENGTH]
    session.commit()


async def _fetch_all(
    http: httpx.AsyncClient, settings: Settings, places: list[tuple[str, str]]
) -> list[Observation | SeoulApiError]:
    """모든 장소를 동시에(한 번에 collect_concurrency개씩) 가져온다. 예외를 던지지 않는다."""
    semaphore = asyncio.Semaphore(settings.collect_concurrency)

    async def fetch(code: str, name: str) -> Observation | SeoulApiError:
        async with semaphore:
            try:
                return await fetch_place(
                    http,
                    base_url=settings.seoul_api_base_url,
                    api_key=settings.seoul_api_key.get_secret_value(),
                    code=code,
                    name=name,
                    retries=settings.collect_retries,
                )
            except SeoulApiError as exc:
                return exc
            except Exception as exc:
                # 예상하지 못한 오류도 이 장소만의 실패로 끝낸다. 여기서 예외가 새면
                # gather가 깨져 121곳 전부가 저장되지 않는다.
                # 예외 원문에는 주소(인증키)가 들어 있을 수 있어 종류 이름만 남긴다.
                return SeoulApiError(f"처리 실패 {type(exc).__name__}")

    return await asyncio.gather(*(fetch(code, name) for code, name in places))


def _save(session: Session, code: str, result: Observation | SeoulApiError, now: datetime) -> bool:
    """결과 하나를 저장하고 성공 여부를 돌려준다. 저장 실패도 이 장소만의 실패로 끝낸다."""
    try:
        if isinstance(result, SeoulApiError):
            record_failure(session, code, str(result), now)
            return False
        store_observation(session, result, now)
        return True
    except SQLAlchemyError:
        session.rollback()
        logger.exception("저장 실패 %s", code)
    try:
        # 저장하지 못했다는 사실도 장소별 기록에 남긴다. 이것마저 안 되면 로그만 남는다.
        record_failure(session, code, SAVE_FAILED, now)
    except SQLAlchemyError:
        session.rollback()
        logger.exception("실패 기록도 저장하지 못함 %s", code)
    return False


async def collect_once(
    settings: Settings,
    session_factory: sessionmaker[Session],
    client: httpx.AsyncClient | None = None,
) -> CollectResult:
    """모든 장소를 한 번 수집한다. 장소 하나의 실패가 다른 장소를 막지 않는다."""
    with session_factory() as session:
        places = [(p.code, p.name) for p in session.scalars(select(Place).order_by(Place.code))]

    if client is None:
        async with httpx.AsyncClient(timeout=settings.collect_timeout_seconds) as http:
            results = await _fetch_all(http, settings, places)
    else:
        results = await _fetch_all(client, settings, places)

    now = now_utc()
    with session_factory() as session:
        succeeded = sum(
            _save(session, code, result, now)
            for (code, _name), result in zip(places, results, strict=True)
        )

    outcome = CollectResult(total=len(places), succeeded=succeeded, failed=len(places) - succeeded)
    logger.info(
        "수집 끝: 전체 %d, 성공 %d, 실패 %d", outcome.total, outcome.succeeded, outcome.failed
    )
    return outcome
