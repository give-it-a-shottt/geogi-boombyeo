import type { NextConfig } from "next";

// 모든 응답에 붙이는 보안 헤더. 로그인이 없는 서비스라 기본적인 것만 둔다.
const SECURITY_HEADERS = [
  // 브라우저가 파일 종류를 멋대로 추측하지 않게 한다.
  { key: "X-Content-Type-Options", value: "nosniff" },
  // 다른 사이트로 나갈 때 주소의 경로·쿼리를 넘기지 않는다.
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // 다른 사이트가 이 화면을 틀(iframe) 안에 넣지 못하게 한다.
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
];

const nextConfig: NextConfig = {
  // 데이터 함수에 'use cache'를 붙여 페이지를 미리 만들어 두고, 수명이 지나면 뒤에서 다시 만든다.
  cacheComponents: true,
  partialPrefetching: true,
  cacheLife: {
    // 혼잡도 데이터용. 수집이 5분 주기라 1분마다 다시 만들면 충분하다.
    // expire가 5분 이상이어야 빌드 때 미리 만들어진다.
    crowd: {
      stale: 60,
      revalidate: 60,
      expire: 3600,
    },
  },
  // 도커 이미지에 필요한 파일만 담는다.
  output: "standalone",
  // "X-Powered-By: Next.js" 헤더를 내보내지 않는다.
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
};

export default nextConfig;
