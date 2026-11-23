"""시각 다루기. 저장은 UTC, 말로 바꿀 때는 한국 시간."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def now_utc() -> datetime:
    return datetime.now(UTC)


def parse_seoul_time(text: str) -> datetime:
    """서울시 API의 '2026-11-23 15:05'(한국 시간)를 UTC 시각으로."""
    return datetime.strptime(text.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=KST).astimezone(UTC)


def local_hour(moment: datetime) -> int:
    """한국 시간의 시(0 ~ 23)."""
    return moment.astimezone(KST).hour


def period_of(hour: int) -> str:
    """시간대 말. 디자인 md의 '시간대 말' 줄과 같다."""
    if hour == 0:
        return "자정"
    if hour < 6:
        return "새벽"
    if hour < 12:
        return "오전"
    if hour == 12:
        return "낮"
    if hour < 21:
        return "오후"
    return "밤"


def hour_number(hour: int) -> int:
    return hour if hour <= 12 else hour - 12


def format_hour(moment: datetime, *, with_period: bool = True) -> str:
    """'오후 4시', '밤 10시', '자정'. '16시'처럼 쓰지 않는다."""
    hour = moment.astimezone(KST).hour
    if hour == 0:
        return "자정"
    if not with_period:
        return f"{hour_number(hour)}시"
    return f"{period_of(hour)} {hour_number(hour)}시"


def short_hour(moment: datetime) -> str:
    """그래프 가로축용 짧은 표기: '6시', '자정'."""
    return format_hour(moment, with_period=False)


def same_period(a: datetime, b: datetime) -> bool:
    ha, hb = a.astimezone(KST).hour, b.astimezone(KST).hour
    return ha != 0 and hb != 0 and period_of(ha) == period_of(hb)


def is_next_day_daytime(moment: datetime, now: datetime) -> bool:
    """내일 아침 6시 이후인가. 자정·새벽은 '내일'을 붙이지 않아도 뜻이 통한다."""
    local, local_now = moment.astimezone(KST), now.astimezone(KST)
    return local.date() > local_now.date() and local.hour >= 6
