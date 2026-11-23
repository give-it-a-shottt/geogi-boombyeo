"use client";

import { ShareNetworkIcon } from "@phosphor-icons/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import gnb from "./Gnb.module.css";
import ui from "./ui.module.css";

/** 공유: 기기 공유 창을 열고, 없으면 주소를 복사한다. */
export function ShareButton({ title }: { title: string }) {
  const [message, setMessage] = useState("");

  async function share() {
    const url = window.location.href;
    try {
      if (navigator.share) {
        await navigator.share({ title, url });
        return;
      }
      await navigator.clipboard.writeText(url);
      setMessage("주소를 복사했어요");
    } catch (error) {
      // 공유 창을 그냥 닫은 경우는 실패가 아니다.
      if (error instanceof DOMException && error.name === "AbortError") return;
      setMessage("공유하지 못했어요");
    }
  }

  return (
    <>
      <button type="button" className={gnb.iconButton} aria-label="공유" onClick={share}>
        <ShareNetworkIcon size={24} aria-hidden="true" />
      </button>
      <span className="srOnly" role="status">
        {message}
      </span>
    </>
  );
}

/** 다시 시도: 서버 데이터를 다시 불러온다. */
export function RetryButton({ className = ui.textButton }: { className?: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <button
      type="button"
      className={className}
      disabled={pending}
      onClick={() => startTransition(() => router.refresh())}
    >
      {pending ? "불러오는 중" : "다시 시도"}
    </button>
  );
}
