# 배포 안내 — geogi-boombyeo.shop

도메인은 이름표다. 이름표를 서버에 붙이고, 서버에서 서비스를 켜면 끝난다.

```
깃허브(공장)                서버(가게)                      도메인(주소)
코드를 올리면 자동으로  →  완성된 이미지를 내려받아 켠다  ←  geogi-boombyeo.shop 이 서버를 가리킨다
이미지를 만들어 둔다
```

서버 메모리가 1GB라서 서버에서는 빌드하지 않는다. 빌드는 깃허브 Actions가 하고(`.github/workflows/build.yml`), 서버는 내려받아 켜기만 한다.

> ③ ~ ④는 아직 실제 서버에서 끝까지 돌려 보지 않았다. 막히는 곳이 있으면 그 화면이나 오류 글자를 그대로 알려 주면 된다.

## ① 서버 준비 (네이버 클라우드, `my-server`)

**방화벽(ACG)** 에서 들어오는 문을 연다.

| 포트 | 용도 | 허용 대상 |
| ---- | ---- | --------- |
| 22 | 서버에 접속(SSH) | 내 IP만 |
| 80 | http (인증서 발급과 https로 넘기기에 필요) | 전체 `0.0.0.0/0` |
| 443 | https | 전체 `0.0.0.0/0` |

3000, 8000, 5432는 열지 않는다. 밖에서 닿을 필요가 없다.

**서버 안에서 한 번만** 해 두는 것:

```bash
# 예비 메모리(스왑) 1GB — 메모리가 잠깐 모자라도 프로그램이 죽지 않게 한다
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 도커 설치
curl -fsSL https://get.docker.com | sudo sh
docker --version
```

(쓸모없이 200MB를 쓰던 `fwupd`는 이미 꺼 두었다 — Admin_Docs/troubleshooting/T-008)

## ② 도메인을 서버에 연결 (가비아)

1. 네이버 클라우드 콘솔에서 `my-server`의 **공인 IP**를 확인한다.
2. 가비아 → **My가비아 → 도메인 → `geogi-boombyeo.shop`의 DNS 관리(설정)**
3. 레코드를 2개 추가하고 저장한다.

   | 타입 | 호스트 | 값 | TTL |
   | ---- | ------ | -- | --- |
   | A | `@` | 서버의 공인 IP | 600 |
   | A | `www` | 서버의 공인 IP | 600 |

4. 몇 분 ~ 길면 몇 시간 뒤, 서버에서 아래를 쳐서 공인 IP가 나오면 연결된 것이다.

   ```bash
   getent hosts geogi-boombyeo.shop
   ```

## ③ 서버에서 켜기

```bash
# 코드 받기 (설정 파일과 도커 구성이 들어 있다. 빌드는 하지 않는다)
git clone https://github.com/give-it-a-shottt/geogi-boombyeo.git
cd geogi-boombyeo

# 설정 파일 만들기
cp .env.example .env
nano .env        # 저장: Ctrl+O, Enter / 나가기: Ctrl+X
```

`.env`에 넣을 값 (이 파일은 서버에만 두고 git에 올리지 않는다)

| 이름 | 값 |
| ---- | -- |
| `SEOUL_API_KEY` | 서울 열린데이터광장 인증키 |
| `POSTGRES_PASSWORD` | 새로 정한 긴 비밀번호 (영문 · 숫자만 쓴다. 기호가 들어가면 접속 주소가 깨질 수 있다) |
| `SITE_DOMAIN` | `geogi-boombyeo.shop` |
| `SITE_URL` | `https://geogi-boombyeo.shop` |
| 나머지 | 그대로 둔다 |

```bash
# 완성된 이미지 내려받기 → 켜기
docker compose --profile https pull
docker compose --profile https up -d --no-build

# 상태 보기: 다섯 개(db, api, worker, web, caddy)가 모두 Up / healthy 인지
docker compose --profile https ps

# 수집이 도는지 보기: "수집 끝: 전체 121, 성공 121, 실패 0" 이 5분마다 찍힌다 (나가기: Ctrl+C)
docker compose logs -f worker
```

`pull`에서 `denied`나 `unauthorized`가 나오면 깃허브의 이미지가 비공개 상태다. 깃허브 → 내 프로필 → **Packages** → `geogi-boombyeo-backend`, `geogi-boombyeo-web` 각각 → **Package settings → Change visibility → Public** 으로 바꾼다.

## ④ 확인

- 브라우저에서 `https://geogi-boombyeo.shop` — 주소창에 자물쇠가 보이고 홈이 뜬다.
- `http://geogi-boombyeo.shop`으로 들어가도 https로 넘어간다.
- 휴대폰에서 홈의 **"지금 있는 곳, 붐비나요?"** — 위치 허용을 묻는 창이 뜬다 (https여야만 뜬다).
- `https://geogi-boombyeo.shop/sitemap.xml` — 주소가 전부 `https://geogi-boombyeo.shop/...`로 나온다.
- 서버에서 `free -h` — `available`이 100Mi 아래로 떨어지지 않는지 본다.

## 코드를 고친 뒤 다시 올리기

1. PC에서 `git push` → 깃허브 Actions가 검사하고 새 이미지를 만든다 (저장소의 **Actions** 탭에서 초록색 체크 확인, 몇 분).
2. 서버에서:

   ```bash
   cd geogi-boombyeo
   git pull
   docker compose --profile https pull
   docker compose --profile https up -d --no-build
   docker image prune -f      # 안 쓰는 옛 이미지 지우기 (디스크가 10GB라 가끔 해 준다)
   ```

## 자주 쓰는 명령

```bash
docker compose --profile https ps            # 상태
docker compose logs --tail 100 api           # 조회 API 로그
docker compose logs --tail 100 caddy         # HTTPS 문지기 로그 (인증서 발급이 안 될 때)
docker compose --profile https down          # 끄기 (데이터는 남는다)
df -h /                                      # 디스크 남은 양
```

주의

- `docker compose down -v`의 `-v`는 **쌓인 수집 기록과 인증서를 지운다.** 붙이지 않는다.
- 인증서는 Caddy가 알아서 받아 오고 갱신한다. ②가 끝나기 전(도메인이 서버를 가리키기 전)에 켜면 발급에 실패하니, ②의 확인을 한 뒤에 켠다.
- 주소(`SITE_URL`)는 이미지를 만들 때 정해진다. 주소를 바꾸려면 깃허브 저장소 Settings → Variables에 `SITE_URL`을 넣고 Actions를 다시 돌린다.

## 배포한 뒤

- 서울 열린데이터광장 **활용사례(갤러리)** 에 `https://geogi-boombyeo.shop`으로 등록 신청
- 네이버 서치어드바이저 · 구글 서치 콘솔에 사이트를 등록하고 `sitemap.xml` 제출 (검색 유입을 원할 때)
