import type { NextConfig } from "next";

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
};

export default nextConfig;
