"""조회 로직: DB에서 읽은 값을 화면이 바로 쓸 모양으로 바꾼다.

장소가 121곳뿐이라 요청마다 전체를 3번의 쿼리로 읽는다(장소·상태·예측).
장소마다 따로 쿼리하지 않는다.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.levels import BUSY_FROM, CATEGORY_LABELS, LEVEL_NAMES, RELAXED, category_label
from app.models import Forecast, Place, PlaceStatus
from app.schemas import (
    AnswerInfo,
    CategoryCount,
    HomeAnswer,
    HomeResponse,
    NearbyResponse,
    PlaceCard,
    PlaceDetailResponse,
    PlaceInfo,
    PlaceListResponse,
    Recommend,
    SearchResponse,
    StatusInfo,
    TimelinePoint,
)
from app.services.answer import (
    build_answer,
    relaxed_hours,
    relaxed_until_text,
    topic_particle,
)
from app.services.geo import NEARBY_COUNT, NEARBY_LIMIT_KM, distance_km
from app.services.search import SearchablePlace, search_places
from app.timeutil import format_hour, short_hour

TOP_COUNT = 5
# 그래프는 '지금' 1칸 + 예측 11칸 = 12칸
TIMELINE_FUTURE = 11
AXIS_LABEL_EVERY_HOURS = 3


@dataclass
class PlaceView:
    place: Place
    status: PlaceStatus | None
    fresh: bool
    future: list[tuple[datetime, int]] = field(default_factory=list)

    @property
    def level(self) -> int | None:
        return self.status.level if self.status else None


def load_views(session: Session, now: datetime, stale_after_minutes: int) -> list[PlaceView]:
    """모든 장소의 최신 상태와 앞으로의 예측을 읽는다."""
    places = list(session.scalars(select(Place).order_by(Place.name)))
    statuses = {status.place_code: status for status in session.scalars(select(PlaceStatus))}
    futures: dict[str, list[tuple[datetime, int]]] = defaultdict(list)
    rows = session.execute(
        select(Forecast.place_code, Forecast.forecast_time, Forecast.level)
        .where(Forecast.forecast_time > now)
        .order_by(Forecast.forecast_time)
    )
    for code, moment, level in rows:
        if len(futures[code]) < TIMELINE_FUTURE:
            futures[code].append((moment, level))

    oldest_fresh = now - timedelta(minutes=stale_after_minutes)
    views = []
    for place in places:
        status = statuses.get(place.code)
        has_value = status is not None and status.level is not None
        fresh = bool(has_value and status.observed_at and status.observed_at >= oldest_fresh)
        views.append(
            PlaceView(
                place=place,
                status=status if has_value else None,
                fresh=fresh,
                # 오래된 관측에 붙어 있던 예측은 믿을 수 없어서 쓰지 않는다.
                future=futures.get(place.code, []) if fresh else [],
            )
        )
    return views


def rank_key(view: PlaceView) -> tuple:
    """여유 순: 지금 단계가 낮을수록, 여유가 오래 이어질수록 앞."""
    return (view.level, -relaxed_hours(view.level, view.future), view.place.name)


def to_card(view: PlaceView, now: datetime, distance: float | None = None) -> PlaceCard:
    level = view.level
    calm_text = None
    if view.fresh and level == RELAXED:
        calm_text = relaxed_until_text(view.future, now)
    return PlaceCard(
        code=view.place.code,
        name=view.place.name,
        category=view.place.category,
        category_label=category_label(view.place.category),
        level=level,
        level_label=LEVEL_NAMES[level] if level else None,
        observed_at=view.status.observed_at if view.status else None,
        stale=not view.fresh,
        calm_text=calm_text,
        distance_km=None if distance is None else round(distance, 1),
    )


def home(views: list[PlaceView], now: datetime) -> HomeResponse:
    ranked = sorted((view for view in views if view.fresh), key=rank_key)
    top = [to_card(view, now) for view in ranked[:TOP_COUNT]]
    answer = None
    if ranked:
        best = ranked[0]
        label = "지금 여유로운 곳은" if best.level == RELAXED else "지금 그나마 덜 붐비는 곳은"
        answer = HomeAnswer(label=label, place=top[0])
    return HomeResponse(answer=answer, top=top, place_count=len(views))


def list_places(views: list[PlaceView], now: datetime, category: str | None) -> PlaceListResponse:
    counts: dict[str, int] = defaultdict(int)
    for view in views:
        counts[view.place.category] += 1
    categories = [
        CategoryCount(value=value, label=label, count=counts[value])
        for value, label in CATEGORY_LABELS.items()
        if counts[value]
    ]
    chosen = [view for view in views if category is None or view.place.category == category]
    fresh = sorted((view for view in chosen if view.fresh), key=rank_key)
    # 값이 없거나 오래된 장소는 순위를 매길 수 없어서 맨 뒤에 이름순으로 둔다.
    rest = [view for view in chosen if not view.fresh]
    return PlaceListResponse(
        places=[to_card(view, now) for view in fresh + rest], categories=categories
    )


def alternatives(
    views: list[PlaceView],
    now: datetime,
    *,
    base: PlaceView,
    origin_lat: float,
    origin_lng: float,
) -> list[PlaceCard]:
    """근처의 덜 붐비는 곳. 출발점에서 5km 안, 가까운 순 3곳.

    기준 장소보다 단계가 낮은 곳만 고른다(기준이 이미 여유면 다른 여유인 곳).
    거리가 100m 단위로 같으면 같은 분류를 먼저 둔다.
    """
    base_level = base.level or BUSY_FROM
    found = []
    for view in views:
        if view.place.code == base.place.code or not view.fresh or view.level is None:
            continue
        calmer = view.level < base_level or (base_level == RELAXED and view.level == RELAXED)
        if not calmer:
            continue
        distance = distance_km(origin_lat, origin_lng, view.place.lat, view.place.lng)
        if distance <= NEARBY_LIMIT_KM:
            found.append((view, distance))
    found.sort(
        key=lambda item: (
            round(item[1], 1),
            item[0].place.category != base.place.category,
            item[1],
        )
    )
    return [to_card(view, now, distance) for view, distance in found[:NEARBY_COUNT]]


def nearby_from_place(views: list[PlaceView], now: datetime, base: PlaceView) -> NearbyResponse:
    cards = alternatives(
        views, now, base=base, origin_lat=base.place.lat, origin_lng=base.place.lng
    )
    return NearbyResponse(origin="place", base=to_card(base, now), alternatives=cards)


def nearby_from_location(
    views: list[PlaceView], now: datetime, lat: float, lng: float
) -> NearbyResponse:
    """내 위치에서 가장 가까운 지원 장소를 기준으로 삼는다. 5km 안에 없으면 base가 없다."""
    nearest: tuple[PlaceView, float] | None = None
    for view in views:
        distance = distance_km(lat, lng, view.place.lat, view.place.lng)
        if distance <= NEARBY_LIMIT_KM and (nearest is None or distance < nearest[1]):
            nearest = (view, distance)
    if nearest is None:
        return NearbyResponse(origin="location", base=None, alternatives=[])
    base, base_distance = nearest
    cards = alternatives(views, now, base=base, origin_lat=lat, origin_lng=lng)
    return NearbyResponse(
        origin="location", base=to_card(base, now, base_distance), alternatives=cards
    )


def directions_url(name: str) -> str:
    """네이버 지도 웹 검색 주소. 지도 API를 부르지 않는다."""
    return f"https://map.naver.com/p/search/{quote(name, safe='')}"


def detail(views: list[PlaceView], now: datetime, code: str) -> PlaceDetailResponse | None:
    view = next((item for item in views if item.place.code == code), None)
    if view is None:
        return None
    place = view.place
    info = PlaceInfo(
        code=place.code,
        name=place.name,
        eng_name=place.eng_name,
        category=place.category,
        category_label=category_label(place.category),
        lat=place.lat,
        lng=place.lng,
    )
    if view.status is None or view.level is None:
        return PlaceDetailResponse(
            place=info,
            status=None,
            answer=None,
            timeline=[],
            recommend=None,
            nearby_top=None,
            primary_action="directions",
            directions_url=directions_url(place.name),
        )

    level = view.level
    status = view.status
    answer = build_answer(level, view.future, now)
    timeline = [
        TimelinePoint(
            time=status.observed_at,
            level=level,
            level_label=LEVEL_NAMES[level],
            is_now=True,
            axis_label="지금",
            full_label="지금",
        )
    ]
    for moment, future_level in view.future:
        local_hour = short_hour(moment)
        show_axis = local_hour == "자정" or int(local_hour[:-1]) % AXIS_LABEL_EVERY_HOURS == 0
        timeline.append(
            TimelinePoint(
                time=moment,
                level=future_level,
                level_label=LEVEL_NAMES[future_level],
                is_now=False,
                axis_label=local_hour if show_axis else "",
                full_label=format_hour(moment),
            )
        )
    recommend = None
    if answer.recommend_start is not None and answer.recommend_tag:
        # timeline은 맨 앞에 '지금'이 있어서 예측 색인에 1을 더한다.
        recommend = Recommend(
            start_index=answer.recommend_start + 1,
            end_index=(answer.recommend_end or answer.recommend_start + 1) + 1,
            tag=answer.recommend_tag,
        )
    near = alternatives(views, now, base=view, origin_lat=place.lat, origin_lng=place.lng)
    return PlaceDetailResponse(
        place=info,
        status=StatusInfo(
            level=level,
            level_label=LEVEL_NAMES[level],
            observed_at=status.observed_at,
            stale=not view.fresh,
            ppltn_min=status.ppltn_min,
            ppltn_max=status.ppltn_max,
        ),
        answer=AnswerInfo(
            kind=answer.kind,
            label=f"{place.name}{topic_particle(place.name)}",
            lines=list(answer.lines),
            detail=answer.detail,
        ),
        timeline=timeline,
        recommend=recommend,
        nearby_top=near[0] if near else None,
        primary_action="nearby" if level >= BUSY_FROM else "directions",
        directions_url=directions_url(place.name),
    )


def search(views: list[PlaceView], now: datetime, query: str) -> SearchResponse:
    by_code = {view.place.code: view for view in views}
    result = search_places(
        query,
        [SearchablePlace(v.place.code, v.place.name, v.place.eng_name) for v in views],
    )
    return SearchResponse(
        query=query,
        results=[to_card(by_code[code], now) for code in result.codes],
        suggestions=[to_card(by_code[code], now) for code in result.suggestions],
    )
