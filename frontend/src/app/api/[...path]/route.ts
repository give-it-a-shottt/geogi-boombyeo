import { BACKEND_TIMEOUT_MS, BACKEND_URL } from "@/lib/backend";
import { relayGet } from "@/lib/relay";

// 브라우저 → 같은 주소(/api/...) → 여기서 백엔드로 전달.
// 브라우저가 백엔드 주소를 몰라도 되고, 다른 출처 요청(CORS) 설정도 필요 없다.
// 읽기(GET)만, 화면이 쓰는 경로만 전달한다(lib/relay.ts의 허용 목록).

export async function GET(request: Request, context: RouteContext<"/api/[...path]">) {
  const { path } = await context.params;
  return relayGet(request, path, { backendUrl: BACKEND_URL, timeoutMs: BACKEND_TIMEOUT_MS });
}
