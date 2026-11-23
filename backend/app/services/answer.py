"""답 한 줄 만들기. DB도 시계도 쓰지 않는 순수 함수라서 규칙마다 테스트한다.

규칙의 출처는 디자인 md의 '답 한 줄 문구 규칙' 표다.
가장 큰 글자는 항상 "언제 가면 되는지"를 말하고, 단정하지 않는다("~ㄹ 거예요").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.levels import RELAXED
from app.timeutil import KST, format_hour, hour_number, is_next_day_daytime, same_period

NOW_PHRASE = {1: "여유로워요", 2: "보통이에요", 3: "약간 붐벼요", 4: "붐벼요"}
ALL_DAY_PHRASE = {1: "여유로울 거예요", 2: "보통일 거예요", 3: "붐벼요", 4: "붐벼요"}


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


def _range_tag(start: datetime, end: datetime | None) -> str:
    """그래프 꼬리표: '오후 4~6시', '오후 4시~밤 9시', '오후 4시부터'."""
    if end is None:
        return f"{format_hour(start)}부터"
    if same_period(start, end):
        return f"{format_hour(start)[:-1]}~{hour_number(end.astimezone(KST).hour)}시"
    return f"{format_hour(start)}~{format_hour(end)}"


def relaxed_until_text(future: list[tuple[datetime, int]], now: datetime) -> str:
    """지금 여유인 장소의 둘째 줄: 여유가 언제까지 이어지는지."""
    if not future:
        return "지금 여유로워요"
    busy = _first_index([level for _, level in future], lambda level: level > RELAXED)
    if busy is None:
        return "오늘은 계속 여유로울 거예요"
    return f"{_hour(future[busy][0], now)}까지 여유로울 거예요"


def relaxed_hours(now_level: int | None, future: list[tuple[datetime, int]]) -> int:
    """여유가 앞으로 몇 칸(시간) 이어지는지. 순위를 매길 때 쓴다."""
    if now_level != RELAXED:
        return 0
    busy = _first_index([level for _, level in future], lambda level: level > RELAXED)
    return len(future) if busy is None else busy


def build_answer(now_level: int, future: list[tuple[datetime, int]], now: datetime) -> Answer:
    """지금 단계와 앞으로의 예측(시간 순)으로 답 한 줄을 만든다.

    future에는 now보다 뒤의 예측만 넣는다.
    """
    if not future:
        return Answer(kind="no_forecast", lines=("지금은", NOW_PHRASE[now_level]))

    times = [moment for moment, _ in future]
    levels = [level for _, level in future]

    if now_level == RELAXED:
        busy = _first_index(levels, lambda level: level > RELAXED)
        if busy is None:
            return Answer(kind="calm_all", lines=("오늘은 계속", ALL_DAY_PHRASE[1]))
        return Answer(
            kind="calm_now",
            lines=("지금 가도", "여유로워요"),
            detail=f"{_hour(times[busy], now)}까지 여유로울 거예요",
        )

    calm = _first_index(levels, lambda level: level == RELAXED)
    if calm is not None:
        busy_again = _first_index(levels, lambda level: level > RELAXED, calm + 1)
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
        end_text = format_hour(end, with_period=not same_period(start, end))
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
        return Answer(kind="same_all", lines=("오늘은 계속", ALL_DAY_PHRASE[now_level]))
    # 앞으로 더 붐비기만 한다 → 지금이 가장 낫다.
    return Answer(kind="least_busy_now", lines=("지금이", "그나마 덜 붐벼요"))


# 영문자로 끝나는 이름(DDP, DMC)은 글자를 읽는 소리의 받침으로 조사를 고른다.
# 받침이 있는 글자는 엘·엠·엔·알뿐이다.
_LETTERS_WITH_FINAL_CONSONANT = "LMNR"


def topic_particle(name: str) -> str:
    """'경복궁은', '여의도는', 'DDP(동대문디자인플라자)는' — 장소 이름 뒤 조사.

    괄호 안은 빼고 마지막 글자의 받침을 본다.
    """
    base = name.split("(")[0].strip() or name
    last = base[-1]
    if "가" <= last <= "힣":
        return "은" if (ord(last) - ord("가")) % 28 else "는"
    if last.isdigit():
        return "은" if last in "013678" else "는"
    if last.isascii() and last.isalpha():
        return "은" if last.upper() in _LETTERS_WITH_FINAL_CONSONANT else "는"
    return "은(는)"
