"""API 응답 모양. Admin_Docs/overview/api-list.md와 같아야 한다."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class PlaceCard(BaseModel):
    """목록 한 줄에 필요한 값."""

    code: str
    name: str
    category: str
    category_label: str
    # 한 번도 수집되지 않은 장소는 level이 없다.
    level: int | None
    level_label: str | None
    observed_at: datetime | None
    stale: bool
    # 지금 여유인 장소만: "밤 10시까지 여유로울 거예요"
    calm_text: str | None = None
    distance_km: float | None = None


class HomeAnswer(BaseModel):
    label: str
    place: PlaceCard


class HomeResponse(BaseModel):
    answer: HomeAnswer | None
    top: list[PlaceCard]
    place_count: int


class CategoryCount(BaseModel):
    value: str
    label: str
    count: int


class PlaceListResponse(BaseModel):
    places: list[PlaceCard]
    categories: list[CategoryCount]


class PlaceInfo(BaseModel):
    code: str
    name: str
    eng_name: str
    category: str
    category_label: str
    lat: float
    lng: float


class StatusInfo(BaseModel):
    level: int
    level_label: str
    observed_at: datetime
    stale: bool
    ppltn_min: int | None
    ppltn_max: int | None


class AnswerInfo(BaseModel):
    kind: str
    label: str
    lines: list[str]
    detail: str | None


class TimelinePoint(BaseModel):
    time: datetime
    level: int
    level_label: str
    is_now: bool
    # 그래프 가로축 글자("지금", "6시", "자정")와 표에 쓰는 글자("오후 6시")
    axis_label: str
    full_label: str


class Recommend(BaseModel):
    # timeline의 [start_index, end_index) 구간
    start_index: int
    end_index: int
    tag: str


class PlaceDetailResponse(BaseModel):
    place: PlaceInfo
    status: StatusInfo | None
    answer: AnswerInfo | None
    timeline: list[TimelinePoint]
    recommend: Recommend | None
    nearby_top: PlaceCard | None
    primary_action: Literal["directions", "nearby"]
    directions_url: str


class NearbyResponse(BaseModel):
    origin: Literal["place", "location"]
    base: PlaceCard | None
    alternatives: list[PlaceCard]


class SearchResponse(BaseModel):
    query: str
    results: list[PlaceCard]
    suggestions: list[PlaceCard]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    place_count: int
    fresh_count: int
    last_success_at: datetime | None
