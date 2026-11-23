"""답 한 줄의 경계: 예측이 짧을 때, 구간의 끝이 자정이거나 다음 날일 때."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.services.answer import build_answer
from app.timeutil import KST


def hours_from(first: datetime, levels: list[int]) -> list[tuple[datetime, int]]:
    return [(first + timedelta(hours=i), level) for i, level in enumerate(levels)]


AFTERNOON = datetime(2026, 11, 23, 15, 5, tzinfo=KST)
NIGHT = datetime(2026, 11, 23, 21, 5, tzinfo=KST)


def test_short_forecast_does_not_claim_all_day():
    one_hour = hours_from(datetime(2026, 11, 23, 16, tzinfo=KST), [1])
    calm = build_answer(1, one_hour, AFTERNOON)
    assert (calm.kind, calm.lines, calm.detail) == ("calm_now", ("지금 가도", "여유로워요"), None)

    busy = build_answer(4, hours_from(datetime(2026, 11, 23, 16, tzinfo=KST), [4, 4]), AFTERNOON)
    assert (busy.kind, busy.lines) == ("no_forecast", ("지금은", "붐벼요"))


def test_six_hours_is_enough_to_say_all_day():
    six = hours_from(datetime(2026, 11, 23, 16, tzinfo=KST), [1] * 6)
    assert build_answer(1, six, AFTERNOON).lines == ("오늘은 계속", "여유로울 거예요")


def test_range_ending_at_midnight():
    # 밤 10시·11시 여유, 자정에 보통
    future = hours_from(datetime(2026, 11, 23, 22, tzinfo=KST), [1, 1, 2])
    answer = build_answer(3, future, NIGHT)
    assert answer.lines == ("밤 10시부터 자정까지", "여유로울 거예요")
    assert answer.recommend_tag == "밤 10시~자정"


def test_range_ending_next_morning_says_tomorrow():
    # 밤 10시부터 여유, 다음 날 오전 7시에 보통
    future = hours_from(datetime(2026, 11, 23, 22, tzinfo=KST), [1] * 9 + [2])
    answer = build_answer(3, future, NIGHT)
    assert answer.lines == ("밤 10시부터 내일 오전 7시까지", "여유로울 거예요")
    assert (answer.recommend_start, answer.recommend_end) == (0, 9)


def test_calm_now_until_tomorrow_morning():
    future = hours_from(datetime(2026, 11, 23, 22, tzinfo=KST), [1] * 9 + [2])
    assert build_answer(1, future, NIGHT).detail == "내일 오전 7시까지 여유로울 거예요"
