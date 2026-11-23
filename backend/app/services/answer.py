"""답 한 줄 만들기. DB도 시계도 쓰지 않는 순수 함수라서 규칙마다 테스트한다.

규칙의 출처는 디자인 md의 '답 한 줄 문구 규칙' 표다.
가장 큰 글자는 항상 "언제 가면 되는지"를 말하고, 단정하지 않는다("~ㄹ 거예요").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.levels import RELAXED
from app.timeutil import (
    format_hour,
    hour_number,
    is_next_day_daytime,
    local_hour,
    period_of,
    same_period,
)

NOW_PHRASE = {1: "여유로워요", 2: "보통이에요", 3: "약간 붐벼요", 4: "붐벼요"}
ALL_DAY_PHRASE = {1: "여유로울 거예요", 2: "보통일 거예요", 3: "붐벼요", 4: "붐벼요"}
# 예측이 이만큼(시간)은 있어야 "오늘은 계속"이라고 말한다. 한두 시간만 보고 단정하지 않는다.
MIN_HOURS_FOR_ALL_DAY = 6


@dataclass(frozen=True)
class Answer:
    kind: str
    # 큰 글자 두 줄. 화면은 이 줄바꿈 그대로 보여 준다.
    lines: tuple[str, str]
    # 큰 글자 아래 설명 한 줄 (없을 수 있음)
    detail: str | None = None
    # 그래프에서 강조할 구간: future의 [start, end) 색인과 꼬리표 글자
    recommend_start: int | None = None
    recommend_end: int | None = None
    recommend_tag: str | None = None


def _hour(moment: datetime, now: datetime) -> str:
    text = format_hour(moment)
    return f"내일 {text}" if is_next_day_daytime(moment, now) else text


def _subject(time_text: str) -> str:
    """'오후 4시가', '자정이' — 받침에 맞춘 조사."""
    return f"{time_text}이" if time_text.endswith("자정") else f"{time_text}가"


def _first_index(levels: list[int], predicate, start: int = 0) -> int | None:
    for index in range(start, len(levels)):
        if predicate(levels[index]):
            return index
    return None


def _first_busy(levels: list[int], start: int = 0) -> int | None:
    """start부터 처음으로 여유가 아닌 칸. 없으면 None."""
    return _first_index(levels, lambda level: level > RELAXED, start)


def _range_tag(start: datetime, end: datetime | None) -> str:
    """그래프 꼬리표: '오후 4~6시', '오후 4시~밤 9시', '오후 4시부터'."""
    if end is None:
        return f"{format_hour(start)}부터"
    if same_period(start, end):
        start_hour, end_hour = local_hour(start), local_hour(end)
        return f"{period_of(start_hour)} {hour_number(start_hour)}~{hour_number(end_hour)}시"
    return f"{format_hour(start)}~{format_hour(end)}"


def relaxed_until_text(future: list[tuple[datetime, int]], now: datetime) -> str:
    """지금 여유인 장소의 둘째 줄: 여유가 언제까지 이어지는지."""
    busy = _first_busy([level for _, level in future])
    if busy is not None:
        return f"{_hour(future[busy][0], now)}까지 여유로울 거예요"
    if len(future) >= MIN_HOURS_FOR_ALL_DAY:
        return "오늘은 계속 여유로울 거예요"
    return "지금 여유로워요"


def relaxed_hours(now_level: int | None, future: list[tuple[datetime, int]]) -> int:
    """여유가 앞으로 몇 칸(시간) 이어지는지. 순위를 매길 때 쓴다."""
    if now_level != RELAXED:
        return 0
    busy = _first_busy([level for _, level in future])
    return len(future) if busy is None else busy


def build_answer(now_level: int, future: list[tuple[datetime, int]], now: datetime) -> Answer:
    """지금 단계와 앞으로의 예측(시간 순)으로 답 한 줄을 만든다.

    future에는 now보다 뒤의 예측만 넣는다.
    """
    if not future:
        return Answer(kind="no_forecast", lines=("지금은", NOW_PHRASE[now_level]))

    times = [moment for moment, _ in future]
    levels = [level for _, level in future]
    enough_for_all_day = len(future) >= MIN_HOURS_FOR_ALL_DAY

    if now_level == RELAXED:
        busy = _first_busy(levels)
        if busy is not None:
            return Answer(
                kind="calm_now",
                lines=("지금 가도", "여유로워요"),
                detail=f"{_hour(times[busy], now)}까지 여유로울 거예요",
            )
        if enough_for_all_day:
            return Answer(kind="calm_all", lines=("오늘은 계속", ALL_DAY_PHRASE[RELAXED]))
        return Answer(kind="calm_now", lines=("지금 가도", "여유로워요"))

    calm = _first_index(levels, lambda level: level == RELAXED)
    if calm is not None:
        busy_again = _first_busy(levels, calm + 1)
        start = times[calm]
        if busy_again is None:
            return Answer(
                kind="calm_later",
                lines=(f"{_hour(start, now)}부터", "여유로울 거예요"),
                recommend_start=calm,
                recommend_end=len(levels),
                recommend_tag=_range_tag(start, None),
            )
        end = times[busy_again]
        # 같은 시간대면 끝 시각의 "오후"를 줄이고, 다르면 온전히("내일"까지) 말한다.
        if same_period(start, end):
            end_text = format_hour(end, with_period=False)
        else:
            end_text = _hour(end, now)
        return Answer(
            kind="calm_later",
            lines=(f"{_hour(start, now)}부터 {end_text}까지", "여유로울 거예요"),
            recommend_start=calm,
            recommend_end=busy_again,
            recommend_tag=_range_tag(start, end),
        )

    lowest = min(levels)
    if lowest < now_level:
        best = levels.index(lowest)
        change = _first_index(levels, lambda level: level != lowest, best + 1)
        return Answer(
            kind="least_busy",
            lines=(_subject(_hour(times[best], now)), "그나마 덜 붐벼요"),
            recommend_start=best,
            recommend_end=len(levels) if change is None else change,
            recommend_tag=format_hour(times[best]),
        )
    if all(level == now_level for level in levels):
        if enough_for_all_day:
            return Answer(kind="same_all", lines=("오늘은 계속", ALL_DAY_PHRASE[now_level]))
        return Answer(kind="no_forecast", lines=("지금은", NOW_PHRASE[now_level]))
    # 앞으로 더 붐비기만 한다 → 지금이 가장 낫다.
    return Answer(kind="least_busy_now", lines=("지금이", "그나마 덜 붐벼요"))


# 영문자로 끝나는 이름(DDP, DMC)은 글자를 읽는 소리의 받침으로 조사를 고른다.
# 받침이 있는 글자는 엘·엠·엔·알뿐이다.
_LETTERS_WITH_FINAL_CONSONANT = "LMNR"
_DIGITS_WITH_FINAL_CONSONANT = "013678"
_HANGUL_FIRST, _HANGUL_LAST = "가", "힣"
_FINAL_CONSONANT_CYCLE = 28


def topic_particle(name: str) -> str:
    """'경복궁은', '여의도는', 'DDP(동대문디자인플라자)는' — 장소 이름 뒤 조사.

    괄호 안은 빼고 마지막 글자의 받침을 본다.
    """
    base = name.split("(")[0].strip() or name
    last = base[-1]
    if _HANGUL_FIRST <= last <= _HANGUL_LAST:
        has_final = (ord(last) - ord(_HANGUL_FIRST)) % _FINAL_CONSONANT_CYCLE != 0
        return "은" if has_final else "는"
    if last.isdigit():
        return "은" if last in _DIGITS_WITH_FINAL_CONSONANT else "는"
    if last.isascii() and last.isalpha():
        return "은" if last.upper() in _LETTERS_WITH_FINAL_CONSONANT else "는"
    return "은(는)"
