import type { Metadata } from "next";
import { Suspense } from "react";

import { SearchScreen } from "@/components/SearchScreen";
import ui from "@/components/ui.module.css";

export const metadata: Metadata = {
  title: "장소 검색",
  description: "서울 주요 121곳을 이름이나 별칭으로 찾아 지금 혼잡도를 확인하세요.",
  alternates: { canonical: "/search" },
};

/** 검색 (SRC_01_001 · 결과 없음 SRC_01_002) */
export default function SearchPage() {
  return (
    <main className={ui.grow}>
      <Suspense fallback={null}>
        <SearchScreen />
      </Suspense>
    </main>
  );
}
