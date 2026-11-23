from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.db import Base, get_session
from app.main import app
from app.models import Forecast, PlaceStatus
from app.seed import sync_places


@pytest.fixture
def session_factory():
    """테스트마다 새 메모리 DB. 121곳 시드가 들어 있다."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        sync_places(session)
    yield factory
    engine.dispose()


@pytest.fixture
def session(session_factory) -> Session:
    with session_factory() as session:
        yield session


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        seoul_api_key="test-key-123",
        seoul_api_base_url="http://seoul.test",
        collect_retries=1,
    )


@pytest.fixture
def client(session_factory, settings):
    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.clear()


def next_hour(now: datetime) -> datetime:
    return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


def set_status(
    session: Session,
    code: str,
    level: int,
    future_levels: list[int] | None = None,
    *,
    minutes_ago: int = 25,
    now: datetime | None = None,
) -> None:
    """장소 하나에 최신 상태와 앞으로의 예측을 넣는다."""
    now = now or datetime.now(UTC)
    observed = now - timedelta(minutes=minutes_ago)
    session.merge(
        PlaceStatus(
            place_code=code,
            level=level,
            observed_at=observed,
            last_success_at=observed,
            last_attempt_at=observed,
            fail_count=0,
        )
    )
    start = next_hour(now)
    for offset, future_level in enumerate(future_levels or []):
        session.merge(
            Forecast(
                place_code=code,
                forecast_time=start + timedelta(hours=offset),
                level=future_level,
            )
        )
    session.commit()
