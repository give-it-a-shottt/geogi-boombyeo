"""시드 데이터, 별칭 사전, 마이그레이션이 서로 맞는지."""

from __future__ import annotations

import json
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.db import Base
from app.levels import CATEGORY_LABELS
from app.seed import load_seed, sync_places
from app.services.geo import distance_km
from app.services.search import ALIASES


def test_seed_has_121_places_inside_seoul_area():
    places = load_seed()
    assert len(places) == 121
    assert len({place["code"] for place in places}) == 121
    assert len({place["name"] for place in places}) == 121
    for place in places:
        assert place["category"] in CATEGORY_LABELS
        # 서울과 그 주변(서울대공원은 과천)
        assert 37.40 < place["lat"] < 37.70 and 126.75 < place["lng"] < 127.20


def test_frontend_place_list_matches_seed():
    """프론트가 들고 있는 장소 목록(코드·이름)이 시드와 같아야 한다."""
    path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "data" / "places.json"
    front = json.loads(path.read_text(encoding="utf-8"))
    seed = [{"code": place["code"], "name": place["name"]} for place in load_seed()]
    assert front == seed


def test_every_alias_points_to_a_real_place():
    names = {place["name"] for place in load_seed()}
    for alias, targets in ALIASES.items():
        for target in targets:
            assert target in names, f"별칭 '{alias}'의 대상 '{target}'이 시드에 없음"


def test_sync_places_can_run_twice(session):
    assert sync_places(session) == 121
    assert sync_places(session) == 121


def test_distance_gyeongbokgung_to_city_hall_is_about_1_5km():
    assert 1.2 < distance_km(37.5796, 126.9770, 37.5663, 126.9779) < 1.7


def test_migration_creates_the_same_tables_as_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")

    engine = create_engine(url)
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert diff == []
