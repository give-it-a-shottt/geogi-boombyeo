import assert from "node:assert/strict";
import { test } from "node:test";

import { agoText, clockText, distanceText } from "./time.ts";

test("clockText는 한국 시간으로 말한다", () => {
  assert.equal(clockText("2026-11-23T06:05:00Z"), "오후 3시 5분");
  assert.equal(clockText("2026-11-23T03:00:00Z"), "낮 12시");
  assert.equal(clockText("2026-11-23T15:10:00Z"), "밤 12시 10분");
  assert.equal(clockText("2026-11-23T13:00:00Z"), "밤 10시");
});

test("agoText는 분 · 시간 · 일 단위로 바뀐다", () => {
  const now = new Date("2026-11-23T06:30:00Z");
  assert.equal(agoText("2026-11-23T06:05:00Z", now), "25분 전 기준");
  assert.equal(agoText("2026-11-23T06:29:50Z", now), "방금 기준");
  assert.equal(agoText("2026-11-23T03:30:00Z", now), "3시간 전 기준");
  assert.equal(agoText("2026-11-21T06:30:00Z", now), "2일 전 기준");
  // 서버 시계가 조금 앞서 있어도 음수가 나오지 않는다.
  assert.equal(agoText("2026-11-23T06:31:00Z", now), "방금 기준");
});

test("distanceText는 1km 아래를 m로 쓴다", () => {
  assert.equal(distanceText(0.8), "800m");
  assert.equal(distanceText(0), "100m");
  assert.equal(distanceText(1.24), "1.2km");
});
