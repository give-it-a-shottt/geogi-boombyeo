# 거기붐벼?

**https://geogi-boombyeo.shop**

서울 주요 121곳이 지금 붐비는지, **몇 시에 가면 덜 붐비는지**, 근처에 덜 붐비는 곳이 어디인지 한 문장으로 알려 주는 모바일 웹.

- 데이터: [서울 실시간 도시데이터](https://data.seoul.go.kr/dataList/OA-21285/A/1/datasetView.do) (서울특별시, 공공누리 제1유형)
- 구조와 설계 이유: [Admin_Docs/START_HERE.md](Admin_Docs/START_HERE.md)
- 디자인 기준: [geogi-boombyeo-design.md](geogi-boombyeo-design.md)

## 구성

| 폴더 | 내용 |
| ---- | ---- |
| `backend/` | 수집 워커(5분마다 121곳 수집)와 조회 API — Python 3.13, FastAPI, SQLAlchemy, Alembic |
| `frontend/` | 화면 — Next.js 16 (App Router, Cache Components), TypeScript, CSS Modules |
| `Admin_Docs/` | 구조 · 결정 · 기능 · 리뷰 기록 |

화면은 서울시 API를 직접 부르지 않는다. 워커가 모아 DB에 넣은 값만 읽는다.

## 준비

1. `.env.example`을 `.env`로 복사한다.
2. `.env`의 `SEOUL_API_KEY`에 서울 열린데이터광장 일반 인증키를 넣는다. 도커로 띄울 때는 `POSTGRES_PASSWORD`도 정한다.

`.env`는 git에 올리지 않는다.

## 로컬에서 실행 (도커 없이, SQLite)

```bash
# 1) 백엔드
cd backend
uv sync
uv run alembic upgrade head          # 테이블 만들기
uv run python -m app.seed            # 121곳 넣기
uv run python -m app.worker --once   # 한 번 수집 (계속 수집하려면 --once를 뺀다)
uv run uvicorn app.main:app --port 8000

# 2) 프론트 (다른 터미널)
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

인증키가 아직 없으면 `uv run python -m app.demo`로 화면 확인용 가짜 데이터를 넣을 수 있다 (로컬 SQLite 전용).

## 도커로 실행 (Postgres)

```bash
docker compose up -d --build         # http://localhost:3000
```

사이트 주소(`SITE_URL`)는 sitemap과 공유 주소에 들어가고 **빌드할 때** 정해진다. 주소를 바꾸면 `--build`로 다시 빌드한다.
API 문서 화면(`/api/docs`)은 기본으로 꺼져 있다. 로컬에서 보려면 백엔드를 `ENABLE_DOCS=true`로 띄우고 `http://localhost:8000/api/docs`를 연다.

실제 서버에 올리는 방법(도메인 연결, HTTPS)은 [DEPLOY.md](DEPLOY.md). main에 올리면 깃허브 Actions가 검사하고 도커 이미지를 만들어 둔다(`.github/workflows/build.yml`).

## 확인

```bash
cd backend  && uv run pytest && uv run ruff check .
cd frontend && npm test && npm run typecheck && npm run lint && npm run build
```

## 장소 목록 갱신

서울시가 장소를 추가하면 `backend/data/raw/`의 두 파일을 새로 받아 넣고 아래를 실행한다.

```bash
cd backend && uv run --with openpyxl --with pyshp python scripts/build_seed.py
```

백엔드 시드(`backend/app/seed_data/places.json`)와 프론트 장소 목록(`frontend/src/data/places.json`)이 함께 만들어진다.
