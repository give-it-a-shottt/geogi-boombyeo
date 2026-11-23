"""혼잡도 4단계와 분류 표기."""

from __future__ import annotations

LEVEL_BY_NAME: dict[str, int] = {"여유": 1, "보통": 2, "약간 붐빔": 3, "붐빔": 4}
LEVEL_NAMES: dict[int, str] = {level: name for name, level in LEVEL_BY_NAME.items()}

RELAXED = 1
# 이 단계부터는 "근처 덜 붐비는 곳"이 주 버튼이다.
BUSY_FROM = 3

# 데이터의 분류명(행정 용어) → 화면에 적는 쉬운 말
CATEGORY_LABELS: dict[str, str] = {
    "고궁·문화유산": "고궁",
    "공원": "공원",
    "관광특구": "관광지",
    "발달상권": "번화가",
    "인구밀집지역": "역 주변",
}


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category)
