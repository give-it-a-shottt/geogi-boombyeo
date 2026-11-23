import "server-only";

// 서버에서만 쓰는 값. 브라우저 코드에서 가져오면 빌드가 실패한다(server-only).

// 백엔드 주소: 실행할 때 환경변수로 받는다. 브라우저에는 내보내지 않는다(NEXT_PUBLIC_ 아님).
export const BACKEND_URL = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export const BACKEND_TIMEOUT_MS = 5000;

// 사이트 주소: sitemap · robots · 공유 주소에 쓴다. 이 페이지들은 빌드할 때 만들어지므로
// 빌드할 때 환경변수로 넣어야 한다(Dockerfile의 ARG SITE_URL).
export const SITE_URL = (process.env.SITE_URL ?? "http://localhost:3000").replace(/\/+$/, "");
