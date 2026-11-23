"""조회 API. 읽기만 한다 — 화면은 서울시 API가 아니라 우리 DB의 값만 본다."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.levels import CATEGORY_LABELS
from app.models import PlaceStatus
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
from app.services.search import MAX_QUERY_LENGTH
from app.timeutil import now_utc

router = APIRouter(prefix="/api")

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
Latitude = Annotated[float, Query(ge=-90, le=90)]
Longitude = Annotated[float, Query(ge=-180, le=180)]


def _views(session: Session, settings: Settings) -> tuple[list[PlaceView], datetime]:
    now = now_utc()
    return service.load_views(session, now, settings.stale_after_minutes), now


@router.get("/health", response_model=HealthResponse)
def health(session: SessionDep, settings: SettingsDep) -> HealthResponse:
    views, _now = _views(session, settings)
    last = session.scalar(select(func.max(PlaceStatus.last_success_at)))
    return HealthResponse(
        status="ok",
        place_count=len(views),
        fresh_count=sum(view.fresh for view in views),
        last_success_at=last,
    )


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
        raise HTTPException(status_code=404, detail="없는 장소예요")
    return result


@router.get("/places/{code}/nearby", response_model=NearbyResponse)
def nearby_from_place(code: str, session: SessionDep, settings: SettingsDep) -> NearbyResponse:
    views, now = _views(session, settings)
    base = next((view for view in views if view.place.code == code), None)
    if base is None:
        raise HTTPException(status_code=404, detail="없는 장소예요")
    return service.nearby_from_place(views, now, base)


@router.get("/nearby", response_model=NearbyResponse)
def nearby_from_location(
    lat: Latitude, lng: Longitude, session: SessionDep, settings: SettingsDep
) -> NearbyResponse:
    views, now = _views(session, settings)
    return service.nearby_from_location(views, now, lat, lng)


@router.get("/search", response_model=SearchResponse)
def search(
    q: Annotated[str, Query(min_length=1, max_length=MAX_QUERY_LENGTH)],
    session: SessionDep,
    settings: SettingsDep,
) -> SearchResponse:
    views, now = _views(session, settings)
    return service.search(views, now, q.strip())
