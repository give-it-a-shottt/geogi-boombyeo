import type { Metadata, Viewport } from "next";

import "pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css";
import "./globals.css";

import { SITE_URL } from "@/lib/backend";

const DESCRIPTION =
  "서울 주요 121곳이 지금 붐비는지, 몇 시에 가면 덜 붐비는지 한 문장으로 알려 드려요.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "거기붐벼? 서울 덜 붐비는 시간과 장소", template: "%s | 거기붐벼?" },
  description: DESCRIPTION,
  openGraph: {
    type: "website",
    siteName: "거기붐벼?",
    locale: "ko_KR",
    title: "거기붐벼? 서울 덜 붐비는 시간과 장소",
    description: DESCRIPTION,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko">
      <body>
        <div className="page">{children}</div>
      </body>
    </html>
  );
}
