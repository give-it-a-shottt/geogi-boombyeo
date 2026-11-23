"use server";

import { updateTag } from "next/cache";

import { CROWD_TAG } from "@/lib/cache-tags";

// 누구나 부를 수 있는 동작이라, 연달아 눌러 캐시를 계속 비우지 못하게 간격을 둔다.
const MIN_INTERVAL_MS = 5000;
let lastClearedAt = 0;

/**
 * "다시 시도": 혼잡도 캐시를 비워 다음 화면이 백엔드에서 새 값을 읽게 한다.
 * router.refresh()만으로는 서버의 "use cache" 결과가 그대로 다시 나온다.
 */
export async function refreshCrowdData(): Promise<void> {
  const now = Date.now();
  if (now - lastClearedAt < MIN_INTERVAL_MS) return;
  lastClearedAt = now;
  updateTag(CROWD_TAG);
}
