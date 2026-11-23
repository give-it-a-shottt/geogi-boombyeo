# T-007 도커로 띄우면 sitemap 주소가 localhost로 굳음

## 한눈에 보기 (코드 몰라도 OK)
무슨 문제였나: 검색엔진에 알려 주는 주소 목록(sitemap)과 공유 주소에 실제 사이트 주소 대신 `localhost`가 들어갈 뻔했다. 사이트 주소를 "실행할 때" 넣게 해 두었는데, 이 파일들은 "빌드할 때" 미리 만들어지기 때문이다.
어떻게 해결했나: 사이트 주소를 빌드할 때 받도록 바꿨다.

## 개발자 상세
- 증상(리뷰 R4의 [추정]을 빌드 결과로 확인): `next build` 결과에서 `/sitemap.xml`, `/robots.txt`는 정적(○)이다. `SITE_URL` 없이 빌드하면 기본값 `http://localhost:3000`이 들어가고, 실행할 때 환경변수를 줘도 바뀌지 않는다.
- 원인: 백엔드 주소(BACKEND_URL)는 요청마다 읽는 코드에서만 쓰여 실행 때 넣어도 되지만, SITE_URL은 미리 만들어지는 페이지에서 쓰인다. 두 값의 성격이 다른데 같은 방식으로 넣었다.
- 해결: `frontend/Dockerfile`에 `ARG SITE_URL`, `docker-compose.yml`의 web에 `build.args`. `frontend/src/lib/backend.ts`에 두 값의 차이를 주석으로 적음.
- 확인: `SITE_URL=https://example.test`로 빌드하면 sitemap의 주소 124개가 모두 그 주소로 나온다.
- 남은 일: 실제 공개 주소가 정해지면 `.env`의 SITE_URL을 넣고 다시 빌드한다(Q-006).
- 관련: F-003 (1차 리뷰 R4 [주의]), D-006, D-007

최종 수정: 2026-11-23
