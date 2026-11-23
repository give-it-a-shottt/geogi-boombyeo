# 화면과 서버가 주고받는 요청

## 한눈에 보기 (코드 몰라도 OK)
상태: [통과]

무엇을: 요청은 7개이고 전부 읽기(GET)다. 홈, 장소 목록, 장소 상세, 근처 대안 2가지(장소 기준 · 내 위치 기준), 검색, 상태 확인.
왜: 로그인도 저장할 것도 없는 서비스라 쓰기 요청이 없다. "답 한 줄" 같은 계산은 서버가 끝내서 화면은 받은 글자를 그대로 보여 준다.

## 개발자 상세

- 백엔드: `backend/app/api.py`, 응답 모양: `backend/app/schemas.py`, 프론트 타입: `frontend/src/lib/types.ts`
- 브라우저는 같은 주소의 `/api/*`로 부르고, Next의 `frontend/src/app/api/[...path]/route.ts`가 백엔드로 넘긴다(GET만). 넘기는 경로는 아래 표의 7개 모양뿐이다(`frontend/src/lib/relay.ts`의 허용 목록). 그 밖의 경로는 백엔드를 부르지 않고 404.
- 오류 형식: `{"detail": "메시지"}` (입력 형식이 틀린 422는 FastAPI 기본 형식으로 `detail`이 배열). 중계 실패는 502 `{"detail": "서버에 연결하지 못했어요"}`.
- API 문서 화면(`/api/docs`, `/api/openapi.json`)은 기본으로 꺼져 있다. 개발할 때만 환경변수 `ENABLE_DOCS=true`로 켠다.
- 시각은 ISO 8601 UTC 문자열.

### 공통 조각: PlaceCard (목록 한 줄)
| 필드 | 타입 | 설명 |
|---|---|---|
| code, name | 문자 | |
| category, category_label | 문자 | 원본 분류 / 화면 표기(고궁 · 공원 · 관광지 · 번화가 · 역 주변) |
| level, level_label | 1 ~ 4 또는 null / 문자 또는 null | 한 번도 수집되지 않았으면 null |
| observed_at | 시각 또는 null | |
| stale | 불리언 | 값이 없거나 60분보다 오래됨 |
| calm_text | 문자 또는 null | 지금 여유인 곳만: "밤 10시까지 여유로울 거예요" |
| distance_km | 수 또는 null | 근처 대안 응답에서만(alternatives와, 내 위치 기준일 때의 base), 소수 첫째 자리 |

### 요청 목록
| 요청 | 입력 | 응답 | 오류 |
|---|---|---|---|
| `GET /api/health` | - | `{status: "ok", place_count, fresh_count, last_success_at}` | - |
| `GET /api/home` | - | `{answer: {label, place: PlaceCard} \| null, top: PlaceCard[] (최대 5), place_count}` | - |
| `GET /api/places` | `category`(선택, 원본 분류명) | `{places: PlaceCard[], categories: [{value, label, count}]}` | 없는 분류 422 |
| `GET /api/places/{code}` | 장소 코드 | 아래 "장소 상세" | 없는 코드 404 |
| `GET /api/places/{code}/nearby` | 장소 코드 | `{origin: "place", base: PlaceCard, alternatives: PlaceCard[] (최대 3)}` | 없는 코드 404 |
| `GET /api/nearby` | `lat`(-90 ~ 90), `lng`(-180 ~ 180) 필수 | `{origin: "location", base: PlaceCard \| null, alternatives}` — 5km 안에 장소가 없으면 base가 null | 범위 밖 · 누락 · nan · inf 422 |
| `GET /api/search` | `q` 필수 (1 ~ 50자) | `{query, results: PlaceCard[] (최대 10), suggestions: PlaceCard[] (결과 없을 때만 3개)}` | 빈 값 · 51자 이상 422. 띄어쓰기나 기호만 있는 값도 422 `{"detail": "검색어를 입력해 주세요"}` |

### 장소 상세 `GET /api/places/{code}`
| 필드 | 설명 |
|---|---|
| place | `{code, name, eng_name, category, category_label, lat, lng}` |
| status | `{level, level_label, observed_at, stale, ppltn_min, ppltn_max}` 또는 null(수집된 적 없음) |
| answer | `{kind, label, lines: [두 줄], detail \| null}` 또는 null. label은 "경복궁은" |
| timeline | `[{time, level, level_label, is_now, axis_label, full_label}]` — 맨 앞이 지금, 뒤로 예측 최대 11개. 예측이 없으면 1개, 수집된 적이 없으면 빈 목록 |
| recommend | `{start_index, end_index, tag}` 또는 null — timeline의 [start, end) 구간과 꼬리표("오후 4~6시"). 항상 timeline 범위 안이다 |
| nearby_top | PlaceCard 또는 null — 가장 가까운 대안 1곳 |
| primary_action | `"directions"`(여유 · 보통) 또는 `"nearby"`(약간 붐빔 · 붐빔) |
| directions_url | 네이버 지도 검색 주소 |

`answer.kind` 값: `calm_now`(지금 여유) · `calm_all`(계속 여유) · `calm_later`(나중에 여유) · `least_busy`(그나마 덜 붐비는 시각) · `least_busy_now`(지금이 그나마 나음) · `same_all`(계속 같은 단계) · `no_forecast`(예측 없음)

### 규칙
- 여유 순 정렬: 지금 단계가 낮은 순 → 여유가 오래 이어지는 순 → 이름순. 지연된 장소는 TOP 5에서 빼고, 목록에서는 맨 뒤에 둔다.
- 근처 대안: 출발점에서 5km 안, 기준 장소보다 단계가 낮은 곳(기준이 여유면 다른 여유인 곳), 가까운 순 3곳. 거리가 100m 단위로 같으면 같은 분류 먼저(Q-003).
- 근처 대안에는 값이 없거나 지연된 장소를 넣지 않는다(Q-005). 기준 장소의 값이 없으면 "약간 붐빔"으로 보고 그보다 덜 붐비는 곳을 찾는다.
- 지연된 장소는 예측을 쓰지 않는다(`answer.kind = no_forecast`, timeline 1개).
- "오늘은 계속 ~"(`calm_all`, `same_all`)은 예측이 6시간 이상 있을 때만 말한다. 그보다 짧으면 지금 상태만 말한다.

최종 수정: 2026-11-23 · 관련: F-002, F-003, D-004, D-007
