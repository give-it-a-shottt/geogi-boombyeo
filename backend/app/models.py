"""테이블 4개.

- places        : 서울 주요 121곳 (시드)
- snapshots     : 5분마다 쌓는 혼잡도 원본 (시계열). 나중에 요일·시간대 패턴을 만든다.
- forecasts     : 장소별 최신 예측만 (수집할 때마다 갈아 끼움)
- place_status  : 장소별 최신 상태 한 줄. 화면은 이 표만 읽는다.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UTCDateTime

# 실패 사유를 저장하는 열의 길이. 수집 쪽이 이 길이에 맞춰 자른다.
LAST_ERROR_MAX_LENGTH = 200


class Place(Base):
    __tablename__ = "places"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    category: Mapped[str] = mapped_column(String(30), index=True)
    eng_name: Mapped[str] = mapped_column(String(200), default="")
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)


class Snapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = (
        UniqueConstraint("place_code", "observed_at", name="uq_snapshots_place_observed"),
        CheckConstraint("level BETWEEN 1 AND 4", name="ck_snapshots_level"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    place_code: Mapped[str] = mapped_column(ForeignKey("places.code", ondelete="CASCADE"))
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime)
    collected_at: Mapped[datetime] = mapped_column(UTCDateTime)
    level: Mapped[int] = mapped_column(Integer)
    ppltn_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ppltn_max: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (CheckConstraint("level BETWEEN 1 AND 4", name="ck_forecasts_level"),)

    place_code: Mapped[str] = mapped_column(
        ForeignKey("places.code", ondelete="CASCADE"), primary_key=True
    )
    forecast_time: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True)
    level: Mapped[int] = mapped_column(Integer)
    ppltn_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ppltn_max: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PlaceStatus(Base):
    __tablename__ = "place_status"
    __table_args__ = (
        CheckConstraint("level IS NULL OR level BETWEEN 1 AND 4", name="ck_place_status_level"),
    )

    place_code: Mapped[str] = mapped_column(
        ForeignKey("places.code", ondelete="CASCADE"), primary_key=True
    )
    # 한 번도 수집에 성공하지 못한 장소는 level·observed_at이 비어 있다.
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ppltn_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ppltn_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_attempt_at: Mapped[datetime] = mapped_column(UTCDateTime)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(LAST_ERROR_MAX_LENGTH), nullable=True)
