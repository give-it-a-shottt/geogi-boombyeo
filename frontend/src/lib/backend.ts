// 서버에서만 쓰는 백엔드 주소. 브라우저에는 내보내지 않는다(NEXT_PUBLIC_ 아님).
export const BACKEND_URL = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export const BACKEND_TIMEOUT_MS = 5000;

export const SITE_URL = (process.env.SITE_URL ?? "http://localhost:3000").replace(/\/+$/, "");
