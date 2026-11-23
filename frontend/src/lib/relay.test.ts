import assert from "node:assert/strict";
import { test } from "node:test";

import { isAllowedPath, relayGet } from "./relay.ts";

const OPTIONS = { backendUrl: "http://backend.test:8000", timeoutMs: 1000 };

function fakeFetch(respond: (url: URL) => Response | Promise<Response>) {
  const calls: URL[] = [];
  const fetchImpl = (async (input: URL) => {
    calls.push(input);
    return respond(input);
  }) as unknown as typeof fetch;
  return { calls, fetchImpl };
}

test("화면이 쓰는 경로만 통과한다", () => {
  for (const path of ["home", "health", "places", "places/POI009", "places/POI009/nearby", "nearby", "search"]) {
    assert.equal(isAllowedPath(path.split("/")), true, path);
  }
  for (const path of ["docs", "openapi.json", "places/POI009/extra", "admin", "places/..", "places/%2e%2e", ""]) {
    assert.equal(isAllowedPath(path.split("/")), false, path);
  }
});

test("허용되지 않은 경로는 백엔드를 부르지 않고 404", async () => {
  const { calls, fetchImpl } = fakeFetch(() => new Response("{}"));
  const response = await relayGet(new Request("http://site.test/api/docs"), ["docs"], {
    ...OPTIONS,
    fetchImpl,
  });
  assert.equal(response.status, 404);
  assert.deepEqual(await response.json(), { detail: "없는 주소예요" });
  assert.equal(calls.length, 0);
});

test("경로와 쿼리를 백엔드의 /api 아래로 그대로 넘긴다", async () => {
  const { calls, fetchImpl } = fakeFetch(() => Response.json({ ok: true }));
  const request = new Request("http://site.test/api/nearby?lat=37.58&lng=126.977");
  const response = await relayGet(request, ["nearby"], { ...OPTIONS, fetchImpl });
  assert.equal(response.status, 200);
  assert.equal(calls[0].href, "http://backend.test:8000/api/nearby?lat=37.58&lng=126.977");
  assert.equal(response.headers.get("cache-control"), "no-store");
});

test("백엔드의 상태 코드와 본문을 그대로 돌려준다", async () => {
  for (const status of [404, 422, 500]) {
    const { fetchImpl } = fakeFetch(() => Response.json({ detail: "x" }, { status }));
    const response = await relayGet(new Request("http://site.test/api/places/POI999"), ["places", "POI999"], {
      ...OPTIONS,
      fetchImpl,
    });
    assert.equal(response.status, status);
    assert.deepEqual(await response.json(), { detail: "x" });
  }
});

test("백엔드에 연결하지 못하면 내부 정보 없이 502", async () => {
  const { fetchImpl } = fakeFetch(() => {
    throw new Error("connect ECONNREFUSED http://backend.test:8000");
  });
  const response = await relayGet(new Request("http://site.test/api/home"), ["home"], {
    ...OPTIONS,
    fetchImpl,
  });
  assert.equal(response.status, 502);
  const body = await response.text();
  assert.equal(body.includes("backend.test"), false);
  assert.deepEqual(JSON.parse(body), { detail: "서버에 연결하지 못했어요" });
});
