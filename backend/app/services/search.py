"""장소 검색. 121곳뿐이라 DB 검색 대신 메모리에서 찾는다.

공식 이름이 길거나 낯설어서('홍대 관광특구', 'DDP(동대문디자인플라자)')
사람들이 실제로 부르는 이름을 별칭 사전으로 둔다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

# 부르는 이름 → 공식 장소 이름들 (앞에 있을수록 먼저 보여 준다)
ALIASES: dict[str, list[str]] = {
    "홍대": ["홍대 관광특구", "홍대입구역(2호선)", "연남동"],
    "연트럴파크": ["연남동"],
    "명동": ["명동 관광특구"],
    "동대문": ["동대문 관광특구", "DDP(동대문디자인플라자)", "동대문역"],
    "ddp": ["DDP(동대문디자인플라자)"],
    "이태원": ["이태원 관광특구", "이태원역", "이태원 앤틱가구거리"],
    "경리단길": ["해방촌·경리단길"],
    "해방촌": ["해방촌·경리단길"],
    "잠실": ["잠실 관광특구", "잠실역", "잠실롯데타워·석촌호수"],
    "롯데월드": ["잠실 관광특구", "잠실롯데타워·석촌호수"],
    "롯데타워": ["잠실롯데타워·석촌호수"],
    "석촌호수": ["잠실롯데타워·석촌호수"],
    "송리단길": ["송리단길·호수단길"],
    "코엑스": ["강남 MICE 관광특구"],
    "삼성역": ["강남 MICE 관광특구"],
    "강남": ["강남역", "강남 MICE 관광특구", "신논현역·논현역"],
    "종로": ["종로·청계 관광특구", "인사동", "익선동"],
    "청계천": ["종로·청계 관광특구"],
    "광화문": ["광화문광장", "광화문·덕수궁"],
    "덕수궁": ["광화문·덕수궁", "덕수궁길·정동길"],
    "정동길": ["덕수궁길·정동길"],
    "시청": ["광화문·덕수궁", "시의회 앞"],
    "창덕궁": ["창덕궁·종묘"],
    "종묘": ["창덕궁·종묘"],
    "북촌": ["북촌한옥마을"],
    "성수": ["성수카페거리", "서울숲공원", "뚝섬역"],
    "성수동": ["성수카페거리", "서울숲공원"],
    "서울숲": ["서울숲공원"],
    "가로수길": ["가로수길"],
    "신사": ["가로수길"],
    "압구정": ["압구정로데오거리"],
    "청담": ["청담동 명품거리"],
    "더현대": ["여의도"],
    "ifc": ["여의도"],
    "타임스퀘어": ["영등포 타임스퀘어"],
    "영등포": ["영등포 타임스퀘어"],
    "용리단길": ["용리단길"],
    "신용산": ["용리단길", "용산역"],
    "국립중앙박물관": ["국립중앙박물관·용산가족공원"],
    "국중박": ["국립중앙박물관·용산가족공원"],
    "남산": ["남산공원"],
    "남산타워": ["남산공원"],
    "한강": ["여의도한강공원", "반포한강공원", "뚝섬한강공원", "망원한강공원"],
    "여의도한강": ["여의도한강공원"],
    "반포": ["반포한강공원"],
    "세빛섬": ["반포한강공원"],
    "뚝섬": ["뚝섬한강공원", "뚝섬역"],
    "망원": ["망원한강공원"],
    "하늘공원": ["월드컵공원"],
    "상암": ["DMC(디지털미디어시티)", "월드컵공원"],
    "dmc": ["DMC(디지털미디어시티)"],
    "건대": ["건대입구역"],
    "이대": ["신촌·이대역"],
    "신촌": ["신촌·이대역", "신촌 스타광장"],
    "대학로": ["혜화역"],
    "혜화": ["혜화역"],
    "고터": ["고속터미널역"],
    "고속터미널": ["고속터미널역"],
    "이수": ["총신대입구(이수)역"],
    "서울대공원": ["서울대공원"],
    "어대공": ["어린이대공원"],
    "올공": ["올림픽공원"],
    "남대문": ["남대문시장", "숭례문"],
    "광장시장": ["광장(전통)시장"],
    "경동시장": ["청량리 제기동 일대 전통시장"],
    "청량리": ["청량리 제기동 일대 전통시장"],
    "노량진": ["노량진"],
    "김포공항": ["김포공항"],
    "마곡": ["서울식물원·마곡나루역"],
    "서울식물원": ["서울식물원·마곡나루역"],
    "목동": ["오목교역·목동운동장"],
    "고척": ["고척돔"],
    "잠실야구장": ["잠실종합운동장"],
    "종합운동장": ["잠실종합운동장"],
}

MAX_RESULTS = 10
SUGGESTION_COUNT = 3
MAX_QUERY_LENGTH = 50
_NOISE = re.compile(r"[\s·\-_.,()/]+")


def normalize(text: str) -> str:
    """띄어쓰기·가운뎃점·괄호를 없애고 소문자로."""
    return _NOISE.sub("", text).lower()


@dataclass(frozen=True)
class SearchablePlace:
    code: str
    name: str
    eng_name: str


@dataclass(frozen=True)
class SearchResult:
    codes: list[str]
    # codes가 비었을 때만 채운다: "혹시 이곳인가요?" 후보
    suggestions: list[str]


def search_places(query: str, places: list[SearchablePlace]) -> SearchResult:
    q = normalize(query[:MAX_QUERY_LENGTH])
    if not q:
        return SearchResult(codes=[], suggestions=[])

    by_name = {place.name: place.code for place in places}
    ranked: dict[str, int] = {}

    def offer(code: str, rank: int) -> None:
        ranked[code] = min(rank, ranked.get(code, rank))

    for alias, names in ALIASES.items():
        key = normalize(alias)
        if key == q or (len(q) >= 2 and key.startswith(q)):
            for order, name in enumerate(names):
                if name in by_name:
                    offer(by_name[name], (0 if key == q else 3) * 10 + order)

    for place in places:
        name = normalize(place.name)
        if name == q:
            offer(place.code, 0)
        elif name.startswith(q):
            offer(place.code, 10)
        elif q in name:
            offer(place.code, 20)
        elif len(q) >= 3 and q in normalize(place.eng_name):
            offer(place.code, 40)

    if ranked:
        order = {place.code: index for index, place in enumerate(places)}
        codes = sorted(ranked, key=lambda code: (ranked[code], order[code]))
        return SearchResult(codes=codes[:MAX_RESULTS], suggestions=[])

    # 결과 없음 → 글자가 가장 비슷한 장소를 후보로.
    def similarity(place: SearchablePlace) -> float:
        best = SequenceMatcher(None, q, normalize(place.name)).ratio()
        for alias, names in ALIASES.items():
            if place.name in names:
                best = max(best, SequenceMatcher(None, q, normalize(alias)).ratio())
        return best

    scored = sorted(places, key=similarity, reverse=True)
    return SearchResult(codes=[], suggestions=[p.code for p in scored[:SUGGESTION_COUNT]])
