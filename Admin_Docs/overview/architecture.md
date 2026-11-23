# 전체 구조

## 한눈에 보기 (코드 몰라도 OK)
상태: [통과]

무엇을: 프로그램이 세 개다. **수집 워커**가 5분마다 서울시 API에서 121곳의 혼잡도를 받아 DB에 넣고, **조회 API**가 DB의 값을 화면이 쓰기 좋은 모양(답 한 줄, 순위, 근처 대안)으로 바꿔 주고, **웹 화면**이 그 값을 보여 준다.
비유: 워커는 5분마다 시세를 적어 오는 직원, DB는 장부, 조회 API는 장부를 읽어 주는 창구, 화면은 전광판이다. 손님(브라우저)은 서울시에 직접 묻지 않고 전광판만 본다.

왜: 서울시 API는 한 번에 한 곳만 알려 주고 과거 값을 주지 않는다. 그래서 우리가 주기적으로 모아 쌓아 두고, 화면은 우리 DB만 읽게 했다. 사용자가 몰려도 서울시 API 호출 수는 늘지 않는다.

## 개발자 상세

```
서울시 API ──(5분마다 121번 호출)──▶ 수집 워커 ──▶ DB ◀── 조회 API ◀── Next 서버 ◀── 브라우저
(citydata_ppltn)                  python -m app.worker    (Postgres)   FastAPI     (페이지 · /api 중계)
```

| 흐름 | 경로 |
|---|---|
| 페이지 열기 | 브라우저 → Next 서버 컴포넌트 → `frontend/src/lib/data.ts`(use cache, 1분) → 조회 API → DB |
| 화면 안에서 불러오기(검색, 근처 대안, 전체 목록) | 브라우저 → `/api/*` → `frontend/src/app/api/[...path]/route.ts` → `src/lib/relay.ts`(중계, 허용된 경로만) → 조회 API → DB |
| 수집 | `app/worker.py` → `app/collector/service.py` → `app/collector/client.py` → 서울시 API |
| 장소 넣기 | `python -m app.seed` — 121곳 시드를 DB에 맞춘다. 도커 구성에서는 조회 API가 뜨기 직전에 실행하고, 워커도 시작할 때 한 번 더 한다(여러 번 해도 결과는 같다) |

### 폴더

```
backend/
  app/
    config.py        환경변수 설정 (SEOUL_API_KEY, DATABASE_URL 등)
    db.py            DB 연결, 세션, UTC 시각 타입
    models.py        테이블 4개
    levels.py        혼잡도 4단계, 분류 표기 이름
    timeutil.py      시각 변환과 "오후 4시" 같은 말 만들기
    seed.py          121곳 시드를 DB에 맞추기 (python -m app.seed)
    seed_data/places.json 121곳 (scripts/build_seed.py가 만든다)
    collector/       서울시 API 호출 · 해석(client.py), 저장(service.py)
    worker.py        수집 워커 실행 파일
    services/        답 한 줄(answer.py), 거리(geo.py), 검색(search.py), 조회 조립(places.py)
    schemas.py       API 응답 모양
    api.py           조회 API 라우터
    main.py          FastAPI 앱
    demo.py          화면 확인용 가짜 데이터 (로컬 SQLite 전용)
  alembic/           테이블 구조 변경 기록
  scripts/build_seed.py  서울시 공식 파일 → 시드
  data/raw/          서울시 공식 파일 2개 (목록 xlsx, 영역 zip)
  tests/
frontend/
  src/app/           주소별 페이지 (page.tsx, place/[code], search, about, not-found, api 중계, sitemap, robots)
  src/proxy.ts       없는 장소 코드를 404로 돌림
  src/components/    화면 조각 (AnswerHero, PlaceRow, ForecastChart, NearbyLauncher 등)
  src/app/actions.ts 서버 동작: "다시 시도"가 혼잡도 캐시를 비운다
  src/lib/           데이터 함수(data.ts), 중계(relay.ts), 응답 타입(types.ts), 시각 문구(time.ts), 장소 목록(places.ts)
  src/data/places.json  121곳 코드 · 이름 (build_seed.py가 함께 만든다)
```

### 의존 방향 (백엔드)
`api.py` → `services/places.py` → `services/answer.py · geo.py · search.py` → `models.py` → `db.py`. 라우터는 입력 검증과 404/422만 맡고, 계산은 services에 있다. `collector/`는 조회 쪽 코드를 쓰지 않는다.

### 상태를 두는 곳 (프론트)
- 서버 데이터: 서버 컴포넌트에서 `data.ts`로 읽고 Next가 캐시한다. 전역 상태 라이브러리는 쓰지 않는다.
- 화면 상태(그래프/표 전환, 시트 열림, 검색어, 분류 칩): 각 클라이언트 컴포넌트의 `useState`.
- 최근 검색: 브라우저 `localStorage` (서버에 보내지 않는다).

최종 수정: 2026-11-23 · 관련: F-001, F-002, F-003, D-001, D-006, D-007
