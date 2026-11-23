"""화면 확인용 가짜 데이터를 121곳에 넣는다. 실제 값이 아니다.

인증키가 없거나 체험용(sample) 키만 있을 때 화면을 보려고 쓴다.
운영 DB에는 실행하지 않는다 — 실제 수집 값이 가짜로 덮인다.
실행: uv run python -m app.demo
"""

from __future__ import annotations

import random
import sys
from datetime import timedelta

from sqlalchemy import select

from app.collector.client import ForecastPoint, Observation
from app.collector.service import store_observation
from app.config import get_settings
from app.db import get_session_factory
from app.models import Place
from app.seed import sync_places
from app.timeutil import now_utc

FORECAST_HOURS = 12


def demo_observation(place: Place, now) -> Observation:
    rng = random.Random(place.code)  # 장소마다 늘 같은 모양
    level = rng.choices([1, 2, 3, 4], weights=[35, 30, 22, 13])[0]
    first = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    forecasts = []
    current = level
    for hour in range(FORECAST_HOURS):
        current = min(4, max(1, current + rng.choice([-1, -1, 0, 0, 0, 1])))
        forecasts.append(ForecastPoint(first + timedelta(hours=hour), current, None, None))
    observed = (now - timedelta(minutes=25)).replace(second=0, microsecond=0)
    return Observation(place.code, level, None, None, observed, forecasts)


def main() -> None:
    if not get_settings().sqlalchemy_url.startswith("sqlite"):
        sys.exit("가짜 데이터는 로컬 SQLite에만 넣어요. DATABASE_URL을 확인해 주세요.")
    now = now_utc()
    with get_session_factory()() as session:
        sync_places(session)
        places = list(session.scalars(select(Place)))
        for place in places:
            store_observation(session, demo_observation(place, now), now)
    print(f"가짜 데이터 {len(places)}곳 입력")


if __name__ == "__main__":
    main()
