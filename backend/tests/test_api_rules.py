"""조회 API의 경계 규칙: 상한, 지연, 값 없는 장소, 잘못된 입력."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app
from app.models import PlaceStatus
from tests.conftest import FIXED_NOW, set_status


def code_of(client, name: str) -> str:
    places = client.get("/api/places").json()["places"]
    return next(place["code"] for place in places if place["name"] == name)


# 경복궁에서 5km 안에 있는 곳들
NEAR_GYEONGBOK = ["서촌", "광화문광장", "인사동", "북촌한옥마을", "익선동", "창덕궁·종묘"]


def test_top_is_capped_at_five(client, session):
    for name in NEAR_GYEONGBOK:
        set_status(session, code_of(client, name), 1, [1] * 6)
    assert len(client.get("/api/home").json()["top"]) == 5


def test_ties_are_broken_by_fewer_people_not_by_name(client, session):
    # 네 곳 모두 지금 여유이고 12시간 내내 여유 → 앞의 두 기준이 전부 같다.
    all_calm = [1] * 11
    set_status(session, code_of(client, "경복궁"), 1, all_calm, people=9000)
    set_status(session, code_of(client, "서촌"), 1, all_calm, people=1500)
    set_status(session, code_of(client, "인사동"), 1, all_calm, people=4000)
    set_status(session, code_of(client, "익선동"), 1, all_calm)  # 추정 인구 없음

    body = client.get("/api/home").json()
    # 이름순(경복궁 · 서촌 · 익선동 · 인사동)이 아니라 사람이 적은 순. 인구를 모르는 곳은 맨 뒤.
    assert [place["name"] for place in body["top"]] == ["서촌", "인사동", "경복궁", "익선동"]
    assert body["answer"]["place"]["name"] == "서촌"

    # 장소 목록도 같은 순서다(같은 정렬 함수를 쓴다).
    listed = client.get("/api/places").json()["places"]
    assert [place["name"] for place in listed[:4]] == ["서촌", "인사동", "경복궁", "익선동"]


def test_zero_people_is_a_real_value_and_equal_people_fall_back_to_name(client, session):
    all_calm = [1] * 11
    set_status(session, code_of(client, "인사동"), 1, all_calm, people=2000)
    set_status(session, code_of(client, "서촌"), 1, all_calm, people=2000)
    set_status(session, code_of(client, "경복궁"), 1, all_calm, people=0)
    set_status(session, code_of(client, "익선동"), 1, all_calm)  # 추정 인구 없음

    names = [place["name"] for place in client.get("/api/home").json()["top"]]
    # 0명은 "값 없음"이 아니라 가장 적은 값이라 맨 앞. 인구가 같으면 이름순. 값이 없으면 맨 뒤.
    assert names == ["경복궁", "서촌", "인사동", "익선동"]


def test_people_only_matters_when_level_and_calm_hours_are_equal(client, session):
    # 사람이 훨씬 적어도 단계가 높으면 뒤, 여유가 짧으면 뒤.
    set_status(session, code_of(client, "경복궁"), 1, [1] * 11, people=9000)
    set_status(session, code_of(client, "서촌"), 1, [1, 2, 2], people=100)
    set_status(session, code_of(client, "인사동"), 2, [2] * 11, people=50)

    names = [place["name"] for place in client.get("/api/home").json()["top"]]
    assert names == ["경복궁", "서촌", "인사동"]


def test_nearby_is_capped_at_three_and_sorted_by_distance(client, session):
    base = code_of(client, "경복궁")
    set_status(session, base, 4, [4])
    for name in NEAR_GYEONGBOK:
        set_status(session, code_of(client, name), 1, [1])

    places = client.get(f"/api/places/{base}/nearby").json()["alternatives"]
    assert len(places) == 3
    assert [p["distance_km"] for p in places] == sorted(p["distance_km"] for p in places)


def test_nearby_for_calm_base_offers_other_calm_places_only(client, session):
    base = code_of(client, "경복궁")
    set_status(session, base, 1, [1])
    set_status(session, code_of(client, "서촌"), 1, [1])
    set_status(session, code_of(client, "인사동"), 2, [2])

    names = [p["name"] for p in client.get(f"/api/places/{base}/nearby").json()["alternatives"]]
    assert names == ["서촌"]


def test_stale_place_is_not_offered_as_alternative(client, session):
    base = code_of(client, "경복궁")
    set_status(session, base, 4, [4])
    set_status(session, code_of(client, "서촌"), 1, [1], minutes_ago=180)
    set_status(session, code_of(client, "인사동"), 1, [1])

    names = [p["name"] for p in client.get(f"/api/places/{base}/nearby").json()["alternatives"]]
    assert names == ["인사동"]


def test_stale_boundary_is_60_minutes(client, session):
    just_fresh, just_stale = code_of(client, "서촌"), code_of(client, "인사동")
    set_status(session, just_fresh, 1, [1], minutes_ago=60)
    set_status(session, just_stale, 1, [1], minutes_ago=61)

    assert client.get(f"/api/places/{just_fresh}").json()["status"]["stale"] is False
    assert client.get(f"/api/places/{just_stale}").json()["status"]["stale"] is True


def test_place_that_only_ever_failed_does_not_break_any_endpoint(client, session):
    # 첫 수집부터 실패한 장소: place_status 줄은 있지만 level이 비어 있다.
    code = code_of(client, "경복궁")
    session.add(
        PlaceStatus(
            place_code=code,
            last_attempt_at=FIXED_NOW - timedelta(minutes=1),
            fail_count=3,
            last_error="응답 시간 초과",
        )
    )
    session.commit()
    set_status(session, code_of(client, "서촌"), 1, [1])

    assert [p["name"] for p in client.get("/api/home").json()["top"]] == ["서촌"]
    detail = client.get(f"/api/places/{code}").json()
    assert detail["status"] is None and detail["timeline"] == []
    nearby = client.get(f"/api/places/{code}/nearby").json()
    assert nearby["base"]["level"] is None
    assert [p["name"] for p in nearby["alternatives"]] == ["서촌"]
    assert client.get("/api/places").status_code == 200


def test_detail_text_for_busy_place_at_fixed_time(client, session):
    # 지금은 한국 시간 15:20 → 예측은 16시부터. 16~17시 여유, 18시 보통.
    code = code_of(client, "경복궁")
    set_status(session, code, 3, [1, 1, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1])

    body = client.get(f"/api/places/{code}").json()
    assert body["answer"]["lines"] == ["오후 4시부터 6시까지", "여유로울 거예요"]
    assert body["recommend"] == {"start_index": 1, "end_index": 3, "tag": "오후 4~6시"}
    labels = [point["axis_label"] for point in body["timeline"]]
    assert labels == ["지금", "", "", "6시", "", "", "9시", "", "", "자정", "", ""]


def test_blank_or_symbol_only_query_is_422(client):
    for q in ("   ", "·", "( )", "-_."):
        response = client.get("/api/search", params={"q": q})
        assert response.status_code == 422, q
        assert response.json() == {"detail": "검색어를 입력해 주세요"}


def test_nan_and_infinite_coordinates_are_422(client):
    for lat, lng in (("nan", "127"), ("37.5", "nan"), ("inf", "127"), ("37.5", "-inf")):
        response = client.get("/api/nearby", params={"lat": lat, "lng": lng})
        assert response.status_code == 422, (lat, lng)


def test_docs_are_off_unless_enabled(client, monkeypatch):
    # 기본값: 문서 화면이 없다(프론트의 /api 중계를 타고 밖에 보이지 않게).
    assert client.get("/api/docs").status_code == 404
    assert client.get("/api/openapi.json").status_code == 404

    get_settings.cache_clear()
    monkeypatch.setenv("ENABLE_DOCS", "true")
    try:
        assert Settings(_env_file=None).enable_docs is True
        with_docs = TestClient(create_app())
        assert with_docs.get("/api/openapi.json").status_code == 200
    finally:
        get_settings.cache_clear()
