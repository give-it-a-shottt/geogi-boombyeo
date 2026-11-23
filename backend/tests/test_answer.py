"""답 한 줄 규칙. 디자인 md '답 한 줄 문구 규칙' 표의 줄마다 테스트가 있다."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services.answer import (
    build_answer,
    relaxed_hours,
    relaxed_until_text,
    topic_particle,
)
from app.timeutil import KST, format_hour


def at(hour: int, day: int = 23) -> datetime:
    return datetime(2026, 11, day, hour, 0, tzinfo=KST)


NOW = datetime(2026, 11, 23, 15, 5, tzinfo=KST)


def future(levels: list[int], first_hour: int = 16) -> list[tuple[datetime, int]]:
    start = at(first_hour)
    return [(start + timedelta(hours=i), level) for i, level in enumerate(levels)]


def test_calm_later_with_end_says_both_times():
    # 그래프와 어긋나지 않게 여유가 끝나는 시각까지 말한다.
    answer = build_answer(3, future([1, 1, 2, 2, 1, 1]), NOW)
    assert answer.lines == ("오후 4시부터 6시까지", "여유로울 거예요")
    assert (answer.recommend_start, answer.recommend_end) == (0, 2)
    assert answer.recommend_tag == "오후 4~6시"


def test_calm_later_without_end():
    answer = build_answer(3, future([3, 1, 1, 1]), NOW)
    assert answer.lines == ("오후 5시부터", "여유로울 거예요")
    assert (answer.recommend_start, answer.recommend_end) == (1, 4)
    assert answer.recommend_tag == "오후 5시부터"


def test_calm_later_crossing_period_names_both_periods():
    answer = build_answer(4, future([4, 1, 1, 1, 1, 2], first_hour=17), NOW)
    assert answer.lines == ("오후 6시부터 밤 10시까지", "여유로울 거예요")
    assert answer.recommend_tag == "오후 6시~밤 10시"


def test_calm_now_tells_until_when():
    answer = build_answer(1, future([1, 1, 2, 3]), NOW)
    assert answer.kind == "calm_now"
    assert answer.lines == ("지금 가도", "여유로워요")
    assert answer.detail == "오후 6시까지 여유로울 거예요"
    assert answer.recommend_tag is None


def test_calm_all_day():
    answer = build_answer(1, future([1] * 11), NOW)
    assert answer.lines == ("오늘은 계속", "여유로울 거예요")


def test_least_busy_when_never_calm():
    answer = build_answer(4, future([4, 3, 2, 2, 3]), NOW)
    assert answer.lines == ("오후 6시가", "그나마 덜 붐벼요")
    assert (answer.recommend_start, answer.recommend_end) == (2, 4)
    assert answer.recommend_tag == "오후 6시"


def test_least_busy_at_midnight_uses_right_particle():
    answer = build_answer(
        3, future([3, 3, 2], first_hour=22), datetime(2026, 11, 23, 21, 5, tzinfo=KST)
    )
    assert answer.lines == ("자정이", "그나마 덜 붐벼요")


def test_same_level_all_day():
    assert build_answer(4, future([4] * 11), NOW).lines == ("오늘은 계속", "붐벼요")
    assert build_answer(2, future([2] * 11), NOW).lines == ("오늘은 계속", "보통일 거예요")


def test_now_is_best_when_it_only_gets_busier():
    answer = build_answer(2, future([2, 3, 4, 3]), NOW)
    assert answer.lines == ("지금이", "그나마 덜 붐벼요")
    assert answer.recommend_start is None


def test_no_forecast_says_only_now():
    assert build_answer(3, [], NOW).lines == ("지금은", "약간 붐벼요")


def test_tomorrow_morning_gets_prefix():
    now = datetime(2026, 11, 23, 21, 5, tzinfo=KST)
    hours = [(at(22) + timedelta(hours=i), 4) for i in range(11)]
    hours[-1] = (hours[-1][0], 1)  # 다음 날 오전 8시
    answer = build_answer(4, hours, now)
    assert answer.lines == ("내일 오전 8시부터", "여유로울 거예요")


def test_dawn_has_no_tomorrow_prefix():
    now = datetime(2026, 11, 23, 21, 5, tzinfo=KST)
    hours = [(at(22), 3), (at(23), 3), (at(0, day=24), 3), (at(1, day=24), 1)]
    assert build_answer(3, hours, now).lines == ("새벽 1시부터", "여유로울 거예요")


@pytest.mark.parametrize(
    ("hour", "text"),
    [
        (0, "자정"),
        (3, "새벽 3시"),
        (9, "오전 9시"),
        (12, "낮 12시"),
        (16, "오후 4시"),
        (20, "오후 8시"),
        (22, "밤 10시"),
    ],
)
def test_format_hour_never_uses_24h(hour, text):
    assert format_hour(at(hour)) == text


def test_relaxed_until_text():
    assert relaxed_until_text(future([1, 1, 3]), NOW) == "오후 6시까지 여유로울 거예요"
    assert relaxed_until_text(future([1] * 6), NOW) == "오늘은 계속 여유로울 거예요"
    # 예측이 몇 시간뿐이면 "오늘은 계속"이라고 단정하지 않는다.
    assert relaxed_until_text(future([1, 1, 1]), NOW) == "지금 여유로워요"
    assert relaxed_until_text([], NOW) == "지금 여유로워요"


def test_relaxed_hours_for_ranking():
    assert relaxed_hours(1, future([1, 1, 3])) == 2
    assert relaxed_hours(1, future([1, 1, 1])) == 3
    assert relaxed_hours(2, future([1, 1, 1])) == 0


@pytest.mark.parametrize(
    ("name", "particle"),
    [
        ("경복궁", "은"),
        ("서촌", "은"),
        ("여의도", "는"),
        ("홍대입구역(2호선)", "은"),
        ("DDP(동대문디자인플라자)", "는"),
        ("노들섬", "은"),
        ("가로수길", "은"),
        ("아차산", "은"),
        ("고척돔", "은"),
        ("여의서로", "는"),
    ],
)
def test_topic_particle(name, particle):
    assert topic_particle(name) == particle
