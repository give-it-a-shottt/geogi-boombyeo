import { BACKEND_TIMEOUT_MS, BACKEND_URL } from "@/lib/backend";

// 브라우저 → 같은 주소(/api/...) → 여기서 백엔드로 전달.
// 브라우저가 백엔드 주소를 몰라도 되고, 다른 출처 요청(CORS) 설정도 필요 없다.
// 읽기(GET)만 전달한다. 전달 대상은 고정된 백엔드 주소의 /api/ 아래뿐이다.

const SAFE_SEGMENT = /^[\w.\-~%가-힣]+$/;

export async function GET(request: Request, context: RouteContext<"/api/[...path]">) {
  const { path } = await context.params;
  if (path.some((segment) => segment === "." || segment === ".." || !SAFE_SEGMENT.test(segment))) {
    return Response.json({ detail: "잘못된 주소예요" }, { status: 400 });
  }

  const target = new URL(`${BACKEND_URL}/api/${path.map(encodeURIComponent).join("/")}`);
  target.search = new URL(request.url).search;

  try {
    const upstream = await fetch(target, {
      headers: { accept: "application/json" },
      signal: AbortSignal.timeout(BACKEND_TIMEOUT_MS),
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
    return Response.json({ detail: "서버에 연결하지 못했어요" }, { status: 502 });
  }
}
