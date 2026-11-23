"""121곳 시드를 DB에 맞춘다.

조회 API와 워커가 뜨기 전에 한 번 실행한다: python -m app.seed
(워커도 시작할 때 같은 일을 한다. 여러 번 실행해도 결과는 같다.)
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session_factory
from app.models import Place

SEED_PATH = Path(__file__).resolve().parent / "seed_data" / "places.json"


def load_seed() -> list[dict]:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def sync_places(session: Session) -> int:
    """시드에 있는 장소를 넣거나 고친다. 시드에서 빠진 장소는 지우지 않는다(쌓인 기록 보호)."""
    existing = {place.code: place for place in session.scalars(select(Place))}
    for row in load_seed():
        place = existing.get(row["code"])
        if place is None:
            session.add(Place(**row))
        else:
            for key, value in row.items():
                setattr(place, key, value)
    session.commit()
    return session.scalar(select(func.count()).select_from(Place)) or 0


def main() -> None:
    with get_session_factory()() as session:
        print(f"장소 {sync_places(session)}곳 준비됨")


if __name__ == "__main__":
    main()
