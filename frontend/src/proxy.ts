import { NextResponse, type NextRequest } from "next/server";

import { findKnownPlace } from "@/lib/places";

// 121곳에 없는 장소 코드는 실제 404 상태로 응답한다.
// 장소 페이지는 껍데기를 먼저 보내는 방식이라, 페이지 안에서 notFound()를 불러도
// 상태 코드는 이미 200으로 나간 뒤다. 그래서 페이지에 닿기 전에 여기서 거른다.
const MISSING_PATH = "/_missing/place";

export function proxy(request: NextRequest) {
  const code = request.nextUrl.pathname.split("/")[2] ?? "";
  // 코드는 영문 · 숫자뿐이라 주소 해석(decode)이 필요 없다. 그대로 목록과 비교한다.
  if (findKnownPlace(code)) return NextResponse.next();
  // 존재하지 않는 주소로 돌리면 Next가 not-found 화면을 404로 내보낸다.
  return NextResponse.rewrite(new URL(MISSING_PATH, request.url));
}

export const config = {
  matcher: "/place/:code",
};
