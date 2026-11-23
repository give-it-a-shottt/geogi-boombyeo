import type { Metadata } from "next";
import Link from "next/link";

import { MainGnb } from "@/components/Gnb";
import ui from "@/components/ui.module.css";

export const metadata: Metadata = { title: "없는 페이지" };

/** 없는 장소 · 없는 주소 (ERR_01_001) */
export default function NotFound() {
  return (
    <>
      <MainGnb />
      <main className={`${ui.grow} ${ui.empty}`}>
        <p className={ui.emptyCode} aria-hidden="true">
          404
        </p>
        <h1 className={ui.emptyTitle}>찾는 장소가 없어요</h1>
        <p className={ui.emptyBody}>주소가 바뀌었거나, 서울 주요 121곳에 없는 장소예요.</p>
        <Link href="/" className={`${ui.button} ${ui.l} ${ui.primary}`}>
          홈으로 가기
        </Link>
      </main>
    </>
  );
}
