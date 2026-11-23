"""121곳 시드를 DB에 맞춘다."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Place

SEED_PATH = Path(__file__).resolve().parent / "seed" / "places.json"


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
