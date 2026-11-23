# 배포 안내 — geogi-boombyeo.shop

도메인은 이름표다. 이름표가 가리킬 서버를 만들고, 이름표를 서버에 붙이고, 서버에서 서비스를 켜면 끝난다.

```
① 서버 만들기 → ② 도메인을 서버에 연결 → ③ 서버에 코드 올리고 켜기 → ④ 확인
 (네이버 클라우드)      (가비아 DNS)           (docker compose)
```

> 이 문서의 ③은 아직 실제 서버에서 돌려 보지 않았다. 처음 할 때 막히는 곳이 있으면 그 화면이나 오류 글자를 그대로 알려 주면 된다.

## ① 서버 만들기 (네이버 클라우드)

1. 콘솔에서 **Server** 를 만든다.
   - 운영체제: Ubuntu 22.04 또는 24.04
   - 크기: **메모리 2GB 이상**을 권한다. 1GB짜리는 프론트를 빌드하다가 메모리가 모자라 멈출 수 있다.
2. **공인 IP**를 만들어 그 서버에 붙인다. 이 숫자(예: `223.130.xxx.xxx`)가 ②에서 필요하다.
3. 방화벽(**ACG**)에서 들어오는 문을 연다.

   | 포트 | 용도 | 허용 대상 |
   | ---- | ---- | --------- |
   | 22 | 서버에 접속(SSH) | 내 IP만 |
   | 80 | http (인증서 발급과 https로 넘기기에 필요) | 전체 |
   | 443 | https | 전체 |

   그 밖의 포트(3000, 8000, 5432)는 열지 않는다. 밖에서 닿을 필요가 없다.

## ② 도메인을 서버에 연결 (가비아)

1. 가비아에 로그인 → **My가비아 → 도메인 → DNS 관리(DNS 설정)** → `geogi-boombyeo.shop`의 **설정**
2. 레코드를 2개 추가한다.

   | 타입 | 호스트 | 값 | TTL |
   | ---- | ------ | -- | --- |
   | A | `@` | ①의 공인 IP | 600 |
   | A | `www` | ①의 공인 IP | 600 |

3. 저장한 뒤 몇 분 ~ 길면 몇 시간 기다린다. 내 PC에서 아래를 쳐서 공인 IP가 나오면 연결된 것이다.

   ```bash
   nslookup geogi-boombyeo.shop
   ```

여기까지 해도 브라우저에는 아직 아무것도 안 뜬다. 서버에서 서비스를 켜야 한다.

## ③ 서버에 코드 올리고 켜기

서버에 접속해서(SSH) 아래를 순서대로 한다.

```bash
# 도커 설치 (처음 한 번)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # 그다음 접속을 끊었다가 다시 들어온다

# 코드 받기
git clone https://github.com/give-it-a-shottt/geogi-boombyeo.git
cd geogi-boombyeo

# 설정 파일 만들기
cp .env.example .env
nano .env
```

`.env`에 넣을 값 (이 파일은 서버에만 두고 git에 올리지 않는다)

| 이름 | 값 |
| ---- | -- |
| `SEOUL_API_KEY` | 서울 열린데이터광장 인증키 |
| `POSTGRES_PASSWORD` | 새로 정한 긴 비밀번호 (영문 · 숫자만 쓰면 안전하다) |
| `SITE_DOMAIN` | `geogi-boombyeo.shop` |
| `SITE_URL` | `https://geogi-boombyeo.shop` |
| `DATABASE_URL` | 그대로 둔다 (도커로 띄울 때는 도커 구성이 자기 값을 쓴다) |

```bash
# 켜기 (처음에는 빌드하느라 몇 분 걸린다)
docker compose --profile https up -d --build

# 상태 보기: 다섯 개(db, api, worker, web, caddy)가 모두 running / healthy 인지
docker compose --profile https ps

# 수집이 도는지 보기: "수집 끝: 전체 121, 성공 121, 실패 0" 이 5분마다 찍힌다
docker compose logs -f worker
```

## ④ 확인

- 브라우저에서 `https://geogi-boombyeo.shop` — 주소창에 자물쇠가 보이고 홈이 뜬다.
- `http://geogi-boombyeo.shop`으로 들어가도 https로 넘어간다.
- 휴대폰에서 홈의 **"지금 있는 곳, 붐비나요?"** — 위치 허용을 묻는 창이 뜬다 (https여야만 뜬다).
- `https://geogi-boombyeo.shop/sitemap.xml` — 주소가 전부 `https://geogi-boombyeo.shop/...`로 나온다.

## 자주 하는 일

```bash
# 코드를 고친 뒤 다시 올리기
git pull && docker compose --profile https up -d --build

# 끄기 (데이터는 남는다)
docker compose --profile https down

# 로그 보기
docker compose logs --tail 100 api
docker compose logs --tail 100 caddy
```

주의

- `docker compose down -v`의 `-v`는 **쌓인 수집 기록과 인증서를 지운다.** 붙이지 않는다.
- 주소(`SITE_URL`)를 바꾸면 `--build`로 다시 빌드해야 sitemap과 공유 주소에 반영된다.
- 인증서는 Caddy가 알아서 받아 오고 갱신한다. ②가 끝나기 전(도메인이 서버를 가리키기 전)에 켜면 발급에 실패하니, `nslookup`으로 연결을 확인한 뒤에 켠다.

## 배포한 뒤

- 서울 열린데이터광장 **활용사례(갤러리)** 에 `https://geogi-boombyeo.shop`으로 등록 신청
- 네이버 서치어드바이저 · 구글 서치 콘솔에 사이트를 등록하고 `sitemap.xml` 제출 (검색 유입을 원할 때)
