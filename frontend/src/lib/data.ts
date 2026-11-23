import { cacheLife } from "next/cache";

import { BACKEND_TIMEOUT_MS, BACKEND_URL } from "./backend";
import type { HomeResponse, PlaceDetailResponse } from "./types";

// 서버 컴포넌트가 쓰는 데이터 함수. 결과를 1분 동안 캐시하고 뒤에서 다시 만든다.
// 실패하면 null을 돌려주고, 그 실패는 몇 초만 기억해서 곧 다시 시도하게 한다.

// 성공한 결과는 'crowd'(1분, next.config.ts), 실패는 'seconds'(곧 다시 시도) 수명으로 캐시한다.
// cacheLife는 Next 문서 권장대로 캐시되는 함수 안에서 직접 부른다.

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${BACKEND_URL}${path}`, {
      signal: AbortSignal.timeout(BACKEND_TIMEOUT_MS),
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export async function getHome(): Promise<HomeResponse | null> {
  "use cache";
  const data = await getJson<HomeResponse>("/api/home");
  if (data) {
    cacheLife("crowd");
  } else {
    cacheLife("seconds");
  }
  return data;
}

export async function getPlaceDetail(code: string): Promise<PlaceDetailResponse | null> {
  "use cache";
  const data = await getJson<PlaceDetailResponse>(`/api/places/${encodeURIComponent(code)}`);
  if (data) {
    cacheLife("crowd");
  } else {
    cacheLife("seconds");
  }
  return data;
}
