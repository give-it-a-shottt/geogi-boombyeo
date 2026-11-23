"use client";

import { MainGnb } from "@/components/Gnb";
import ui from "@/components/ui.module.css";

/** 예상하지 못한 오류. 자세한 내용은 화면에 보여 주지 않는다. */
export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <>
      <MainGnb />
      <main className={`${ui.grow} ${ui.empty}`}>
        <h1 className={ui.emptyTitle}>문제가 생겼어요</h1>
        <p className={ui.emptyBody}>잠시 뒤에 다시 시도해 주세요.</p>
        <button type="button" className={`${ui.button} ${ui.l} ${ui.secondary}`} onClick={reset}>
          다시 시도
        </button>
      </main>
    </>
  );
}
