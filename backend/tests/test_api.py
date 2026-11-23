"""조회 API: 응답 모양과 순위·근처·검색 규칙."""

from __future__ import annotations

from tests.conftest import set_status

SEOUL_FOREST = "POI111"  # 아래 fixture에서 실제 코드를 찾아 쓴다


def code_of(client, name: str) -> str:
    places = client.get("/api/places").json()["places"]
    return next(place["code"] for place in places if place["name"] == name)


def test_home_is_empty_before_first_collection(client):
    body = client.get("/api/home").json()
    assert body == {"answer": None, "top": [], "place_count": 121}


def test_home_ranks_by_level_then_how_long_calm_lasts(client, session):
    forest, seochon, gyeongbok = (code_of(client, n) for n in ("서울숲공원", "서촌", "경복궁"))
    set_status(session, seochon, 1, [1, 2, 2])  # 여유가 1시간 이어짐
    set_status(session, forest, 1, [1, 1, 1, 1, 3])  # 여유가 4시간 이어짐
    set_status(session, gyeongbok, 3, [1, 1, 2])

    body = client.get("/api/home").json()
    assert [place["name"] for place in body["top"]] == ["서울숲공원", "서촌", "경복궁"]
    assert body["answer"]["label"] == "지금 여유로운 곳은"
    assert body["answer"]["place"]["name"] == "서울숲공원"
    assert body["top"][0]["calm_text"].endswith("까지 여유로울 거예요")
    assert body["top"][2]["calm_text"] is None


def test_home_label_changes_when_nothing_is_calm(client, session):
    set_status(session, code_of(client, "경복궁"), 3, [3, 3])
    assert client.get("/api/home").json()["answer"]["label"] == "지금 그나마 덜 붐비는 곳은"


def test_stale_place_is_left_out_of_top_and_flagged(client, session):
    fresh, old = code_of(client, "서촌"), code_of(client, "경복궁")
    set_status(session, fresh, 2, [2])
    set_status(session, old, 1, [1], minutes_ago=180)

    body = client.get("/api/home").json()
    assert [place["name"] for place in body["top"]] == ["서촌"]

    detail = client.get(f"/api/places/{old}").json()
    assert detail["status"]["stale"] is True
    # 오래된 관측에 붙은 예측은 쓰지 않는다.
    assert detail["answer"]["kind"] == "no_forecast"
    assert len(detail["timeline"]) == 1


def test_detail_shape_for_busy_place(client, session):
    code = code_of(client, "경복궁")
    set_status(session, code, 3, [1, 1, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1])

    body = client.get(f"/api/places/{code}").json()
    assert body["place"]["category_label"] == "고궁"
    assert body["status"]["level_label"] == "약간 붐빔" and body["status"]["stale"] is False
    assert body["answer"]["label"] == "경복궁은"
    assert body["answer"]["lines"][1] == "여유로울 거예요"
    # 지금 1칸 + 예측 11칸
    assert len(body["timeline"]) == 12
    assert body["timeline"][0]["is_now"] and body["timeline"][0]["axis_label"] == "지금"
    assert body["recommend"]["start_index"] == 1 and body["recommend"]["end_index"] == 3
    assert body["primary_action"] == "nearby"
    assert body["directions_url"].startswith("https://map.naver.com/p/search/")


def test_detail_primary_action_is_directions_when_calm(client, session):
    code = code_of(client, "서촌")
    set_status(session, code, 2, [2, 2])
    assert client.get(f"/api/places/{code}").json()["primary_action"] == "directions"


def test_detail_without_any_data_and_unknown_place(client):
    code = code_of(client, "경복궁")
    body = client.get(f"/api/places/{code}").json()
    assert body["status"] is None and body["answer"] is None and body["timeline"] == []

    missing = client.get("/api/places/POI999")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "없는 장소예요"}
    assert client.get("/api/places/POI999/nearby").status_code == 404


def test_nearby_from_place_picks_calmer_places_within_5km_nearest_first(client, session):
    base = code_of(client, "경복궁")
    seochon, gwanghwamun, insadong = (code_of(client, n) for n in ("서촌", "광화문광장", "인사동"))
    far = code_of(client, "서울대공원")
    set_status(session, base, 3, [3])
    set_status(session, seochon, 1, [1])
    set_status(session, gwanghwamun, 2, [2])
    set_status(session, insadong, 4, [4])  # 더 붐비는 곳은 제외
    set_status(session, far, 1, [1])  # 5km 밖은 제외

    body = client.get(f"/api/places/{base}/nearby").json()
    names = [place["name"] for place in body["alternatives"]]
    assert set(names) == {"서촌", "광화문광장"}
    distances = [place["distance_km"] for place in body["alternatives"]]
    assert distances == sorted(distances) and max(distances) <= 5
    assert body["origin"] == "place" and body["base"]["name"] == "경복궁"


def test_nearby_returns_empty_list_when_nothing_is_calmer(client, session):
    base = code_of(client, "경복궁")
    set_status(session, base, 3, [3])
    assert client.get(f"/api/places/{base}/nearby").json()["alternatives"] == []


def test_nearby_from_location(client, session):
    set_status(session, code_of(client, "경복궁"), 4, [4])
    set_status(session, code_of(client, "서촌"), 1, [1])

    # 경복궁 근처 좌표
    body = client.get("/api/nearby", params={"lat": 37.5796, "lng": 126.9770}).json()
    assert body["origin"] == "location"
    assert body["base"]["name"] == "경복궁" and body["base"]["distance_km"] < 1
    assert [place["name"] for place in body["alternatives"]] == ["서촌"]

    # 서울 밖(부산)에서는 기준 장소가 없다.
    busan = client.get("/api/nearby", params={"lat": 35.1796, "lng": 129.0756}).json()
    assert busan == {"origin": "location", "base": None, "alternatives": []}


def test_nearby_validates_coordinates(client):
    assert client.get("/api/nearby", params={"lat": 91, "lng": 127}).status_code == 422
    assert client.get("/api/nearby").status_code == 422


def test_places_list_filter_and_order(client, session):
    set_status(session, code_of(client, "서울숲공원"), 2, [2])
    set_status(session, code_of(client, "남산공원"), 1, [1])

    body = client.get("/api/places", params={"category": "공원"}).json()
    assert len(body["places"]) == 33
    assert [place["name"] for place in body["places"][:2]] == ["남산공원", "서울숲공원"]
    assert body["places"][2]["level"] is None and body["places"][2]["stale"] is True
    labels = {item["label"]: item["count"] for item in body["categories"]}
    assert labels == {"고궁": 5, "공원": 33, "관광지": 7, "번화가": 28, "역 주변": 48}

    assert client.get("/api/places", params={"category": "없는분류"}).status_code == 422


def test_search_by_name_alias_and_suggestion(client):
    def names(q: str, key: str = "results") -> list[str]:
        return [place["name"] for place in client.get("/api/search", params={"q": q}).json()[key]]

    assert names("경복궁") == ["경복궁"]
    assert names("홍대")[:2] == ["홍대 관광특구", "홍대입구역(2호선)"]
    assert "DDP(동대문디자인플라자)" in names("ddp")
    assert "광화문·덕수궁" in names("광화문 덕수궁")
    assert names("서울 숲")[0] == "서울숲공원"

    assert names("경북궁") == []
    assert "경복궁" in names("경북궁", "suggestions")
    assert len(names("경북궁", "suggestions")) == 3

    assert client.get("/api/search", params={"q": ""}).status_code == 422
    assert client.get("/api/search", params={"q": "가" * 51}).status_code == 422


def test_health(client, session):
    set_status(session, code_of(client, "서촌"), 1, [1])
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["place_count"] == 121 and body["fresh_count"] == 1
