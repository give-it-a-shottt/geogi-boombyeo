# 화면 목록과 주소

## 한눈에 보기 (코드 몰라도 OK)
상태: [통과]

무엇을: 주소는 5종류다. 홈(`/`), 장소 상세(`/place/장소코드`, 121개), 검색(`/search`), 서비스 소개(`/about`), 없는 주소(404). 근처 대안은 주소가 따로 없고 홈과 상세 위에 뜨는 시트다.
왜: 장소마다 주소가 있어야 검색엔진에 "경복궁 혼잡도" 같은 페이지가 따로 잡힌다. 그래서 121곳을 미리 만들어 둔다.

## 개발자 상세

화면 ID는 `geogi-boombyeo-design.md`의 IA 표와 같다. 화면 모양(디자인)은 그 문서가 기준이고, 여기는 주소와 파일만 적는다.

| 화면 ID | 주소 | 파일 | 데이터 | 만드는 방식 |
|---|---|---|---|---|
| HOM_01_001 홈 | `/` | `src/app/page.tsx` | `getHome()` → `GET /api/home`. 전체 목록은 누를 때 `GET /api/places` | 미리 만들고 1분마다 갱신 |
| PLC_01_001 장소 상세 | `/place/[code]` | `src/app/place/[code]/page.tsx` | `getPlaceDetail(code)` → `GET /api/places/{code}` | 121곳 미리 만들고 1분마다 갱신 |
| PLC_01_003 예측 없음 | (같은 주소) | 같은 파일 — `timeline`이 1개일 때 | | |
| CMN_01_001 데이터 지연 | (같은 주소) | 같은 파일 — `status.stale`일 때 `StaleNotice` | | |
| PLC_01_002 근처 대안 시트 | (주소 없음) | `src/components/NearbyLauncher.tsx` | 상세: `GET /api/places/{code}/nearby` / 홈: 위치 허용 후 `GET /api/nearby?lat&lng` | 브라우저에서 요청 |
| SRC_01_001 검색 · SRC_01_002 결과 없음 | `/search` (`?from=location`이면 위치 실패 안내) | `src/app/search/page.tsx`, `src/components/SearchScreen.tsx` | `GET /api/search?q=` (입력 200ms 뒤) | 틀은 미리 만들고 결과는 브라우저에서 |
| INF_01_001 서비스 소개 · 데이터 출처 | `/about` | `src/app/about/page.tsx` | 없음 | 미리 만듦 |
| ERR_01_001 없는 장소 | 없는 주소 전부 | `src/app/not-found.tsx` | 없음 | 상태 코드 404 |
| (오류) | - | `src/app/error.tsx` | - | 예상 못 한 오류 |

그 밖의 주소: `/sitemap.xml`(`src/app/sitemap.ts`, 홈 · 검색 · 소개 + 121곳), `/robots.txt`(`src/app/robots.ts`, `/api/` 제외), `/api/*`(`src/app/api/[...path]/route.ts` → `src/lib/relay.ts`, 백엔드 중계. 화면이 쓰는 경로만 통과).

sitemap · robots · 공유 주소에 들어가는 사이트 주소(SITE_URL)는 빌드할 때 정해진다. 실행할 때 바꿔도 반영되지 않는다.

### 다시 시도
홈 · 상세의 "다시 시도"(`src/components/actions.tsx`의 `RetryButton`)는 서버 동작 `refreshCrowdData`(`src/app/actions.ts`)로 혼잡도 캐시를 비운 뒤 화면을 다시 불러온다. 근처 대안 시트는 시트 안의 "다시 시도"가 요청을 다시 보낸다. 전체 목록은 같은 버튼을 다시 누르고, 검색은 입력하면 다시 검색된다.

### 이동
- 홈 답 한 줄 · TOP 5 · 전체 목록 · 검색 결과 · 근처 대안의 줄 → `/place/{code}`
- 홈 하단 버튼 → 위치 허용: 근처 대안 시트 / 위치 거부 · 실패: `/search?from=location`
- 상세 하단: 길찾기 → 네이버 지도(새 탭) / 근처 덜 붐비는 곳 → 시트 (약간 붐빔 · 붐빔일 때만)
- 헤더: 홈 = 검색(`/search`) · 정보(`/about`), 서브 화면 = 뒤로(`/`)

### 없는 장소 코드가 404가 되는 길
`src/proxy.ts`가 `/place/:code` 요청을 먼저 받는다. 코드가 `src/data/places.json`에 없으면 존재하지 않는 내부 주소로 돌려서 `not-found.tsx`가 404로 나가게 한다(D-006).

최종 수정: 2026-11-23 · 관련: F-003, D-006
