// 브라우저의 /api/... 요청을 백엔드로 넘기는 중계.
// 다른 모듈을 가져오지 않는 순수 함수로 두어 가짜 fetch로 테스트한다.

const PLACE_CODE = "[A-Za-z0-9]{1,10}";

// 화면이 실제로 쓰는 경로만 통과시킨다. 백엔드에 다른 GET 경로(문서 화면, 나중에
// 생길 내부용 경로)가 있어도 이 목록에 없으면 인터넷에서 닿지 않는다.
const ALLOWED_PATHS: RegExp[] = [
  /^home$/,
  /^health$/,
  /^places$/,
  new RegExp(`^places/${PLACE_CODE}$`),
  new RegExp(`^places/${PLACE_CODE}/nearby$`),
  /^nearby$/,
  /^search$/,
];

export interface RelayOptions {
  backendUrl: string;
  timeoutMs: number;
  fetchImpl?: typeof fetch;
}

export function isAllowedPath(segments: string[]): boolean {
  const path = segments.join("/");
  return ALLOWED_PATHS.some((pattern) => pattern.test(path));
}

function json(detail: string, status: number): Response {
  return Response.json({ detail }, { status, headers: { "cache-control": "no-store" } });
}

/** GET 요청 하나를 백엔드의 /api/ 아래 같은 경로로 넘기고 상태 코드와 본문을 그대로 돌려준다. */
export async function relayGet(
  request: Request,
  segments: string[],
  { backendUrl, timeoutMs, fetchImpl = fetch }: RelayOptions,
): Promise<Response> {
  if (!isAllowedPath(segments)) {
    return json("없는 주소예요", 404);
  }

  // 넘길 곳은 고정된 백엔드 주소의 /api/ 아래뿐이다. 쿼리는 그대로 전달하고 검증은 백엔드가 한다.
  const target = new URL(`${backendUrl}/api/${segments.map(encodeURIComponent).join("/")}`);
  target.search = new URL(request.url).search;

  try {
    const upstream = await fetchImpl(target, {
      headers: { accept: "application/json" },
      // 브라우저가 요청을 취소하면(검색어를 바꾸는 등) 백엔드 호출도 같이 멈춘다.
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(timeoutMs)]),
      cache: "no-store",
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/json",
        "cache-control": "no-store",
      },
    });
  } catch {
    // 백엔드 주소나 내부 오류 내용은 밖으로 내보내지 않는다.
    return json("서버에 연결하지 못했어요", 502);
  }
}
