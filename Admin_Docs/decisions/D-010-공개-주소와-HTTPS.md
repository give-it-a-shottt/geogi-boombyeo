# D-010 공개 주소는 geogi-boombyeo.shop, HTTPS는 Caddy가 맡는다

## 한눈에 보기 (코드 몰라도 OK)
상태: [통과]

무엇을: 서비스의 공개 주소를 `geogi-boombyeo.shop`으로 정했다. 가비아에서 샀고, 이유는 가격이 싸서다. (사용자 확인, 2026-11-23)
주소창의 자물쇠(HTTPS)는 서버 맨 앞에 Caddy라는 프로그램을 두어 맡긴다. 인증서를 무료로 받아 오고 알아서 갱신한다.
왜: 홈의 "지금 있는 곳, 붐비나요?"가 쓰는 브라우저 위치 기능은 https 주소에서만 동작한다. 그래서 배포할 때 HTTPS는 선택이 아니다.

## 개발자 상세

| 후보 | 장점 | 단점 |
|---|---|---|
| A. nginx + certbot | 가장 널리 쓰임 | 인증서 발급 · 갱신을 따로 설정해야 함 |
| B. Caddy (선택) | 설정 4줄. 인증서 발급 · 갱신 · http → https 넘기기가 기본 | nginx보다 자료가 적음 |
| C. 네이버 클라우드 로드밸런서 + 인증서 | 관리형 | 서버 한 대짜리에는 비용이 큼 |

결정: B.
- `docker-compose.yml`의 `caddy` 서비스(프로필 `https`)와 `deploy/Caddyfile`. 실제 서버에서만 `docker compose --profile https up -d --build`로 켠다.
- 밖으로 여는 포트는 80 · 443뿐이다. web은 `127.0.0.1:3000`에만 열려 Caddy를 거치지 않고는 닿지 않는다.
- 도메인은 `.env`의 `SITE_DOMAIN`(Caddy용, `geogi-boombyeo.shop`)과 `SITE_URL`(sitemap · 공유 주소용, `https://geogi-boombyeo.shop`, 빌드할 때 정해짐 — T-007)에 넣는다.
- `www.`를 붙여 들어오면 붙이지 않은 주소로 보낸다.

확인(2026-11-23): 실제 서버에서 인증서가 발급되어 https로 열리고, http와 www 주소가 본 주소로 넘어간다. 절차는 레포 루트의 DEPLOY.md.
바꿔야 하는 조건: 서버를 여러 대로 늘리면 C. `.shop`은 갱신 가격이 올라가므로 1년 뒤 주소를 바꿀 수 있다 — 그때는 두 값을 바꾸고 다시 빌드한다.

출발한 질문: Q-006

최종 수정: 2026-11-23 · 관련: F-003, D-007, T-007
