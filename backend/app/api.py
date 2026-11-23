"""조회 API. 읽기만 한다 — 화면은 서울시 API가 아니라 우리 DB의 값만 본다.

라우터는 입력 검증과 404/422만 맡고, 계산과 DB 읽기는 services/places.py가 한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.levels import CATEGORY_LABELS
from app.schemas import (
    HealthResponse,
    HomeResponse,
    NearbyResponse,
    PlaceDetailResponse,
    PlaceListResponse,
    SearchResponse,
)
from app.services import places as service
from app.services.places import PlaceView
from app.timeutil import now_utc

router = APIRouter(prefix="/api")

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
# allow_inf_nan=False: "nan"·"inf"는 범위 비교에 걸리지 않으므로 따로 막는다.
Latitude = Annotated[float, Query(ge=-90, le=90, allow_inf_nan=False)]
Longitude = Annotated[float, Query(ge=-180, le=180, allow_inf_nan=False)]

PLACE_NOT_FOUND = "없는 장소예요"


def _views(session: Session, settings: Settings) -> tuple[list[PlaceView], datetime]:
    now = now_utc()
    return service.load_views(session, now, settings.stale_after_minutes), now


@router.get("/health", response_model=HealthResponse)
def health(session: SessionDep, settings: SettingsDep) -> HealthResponse:
    views, _now = _views(session, settings)
    return service.health(session, views)


@router.get("/home", response_model=HomeResponse)
def home(session: SessionDep, settings: SettingsDep) -> HomeResponse:
    views, now = _views(session, settings)
    return service.home(views, now)


@router.get("/places", response_model=PlaceListResponse)
def list_places(
    session: SessionDep,
    settings: SettingsDep,
    category: Annotated[str | None, Query(max_length=30)] = None,
) -> PlaceListResponse:
    if category is not None and category not in CATEGORY_LABELS:
        raise HTTPException(status_code=422, detail="없는 분류예요")
    views, now = _views(session, settings)
    return service.list_places(views, now, category)


@router.get("/places/{code}", response_model=PlaceDetailResponse)
def place_detail(code: str, session: SessionDep, settings: SettingsDep) -> PlaceDetailResponse:
    views, now = _views(session, settings)
    result = service.detail(views, now, code)
    if result is None:
        raise HTTPException(status_code=404, detail=PLACE_NOT_FOUND)
    return result


@router.get("/places/{code}/nearby", response_model=NearbyResponse)
def nearby_from_place(code: str, session: SessionDep, settings: SettingsDep) -> NearbyResponse:
    views, now = _views(session, settings)
    base = service.find_view(views, code)
    if base is None:
        raise HTTPException(status_code=404, detail=PLACE_NOT_FOUND)
    return service.nearby_from_place(views, now, base)


@router.get("/nearby", response_model=NearbyResponse)
def nearby_from_location(
    lat: Latitude, lng: Longitude, session: SessionDep, settings: SettingsDep
) -> NearbyResponse:
    views, now = _views(session, settings)
    return service.nearby_from_location(views, now, lat, lng)


@router.get("/search", response_model=SearchResponse)
def search(
    q: Annotated[str, Query(min_length=1, max_length=service.MAX_QUERY_LENGTH)],
    session: SessionDep,
    settings: SettingsDep,
) -> SearchResponse:
    query = q.strip()
    # 띄어쓰기나 기호만 있는 검색어는 빈 값과 같다.
    if not service.is_searchable(query):
        raise HTTPException(status_code=422, detail="검색어를 입력해 주세요")
    views, now = _views(session, settings)
    return service.search(views, now, query)
