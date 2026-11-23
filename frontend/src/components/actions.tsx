"use client";

import { ShareNetworkIcon } from "@phosphor-icons/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { refreshCrowdData } from "@/app/actions";

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

/**
 * 다시 시도: 서버의 혼잡도 캐시를 비운 뒤 화면을 다시 불러온다.
 * router.refresh()만 부르면 서버가 캐시해 둔 같은 결과가 다시 나온다.
 */
export function RetryButton({ className = ui.textButton }: { className?: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function retry() {
    startTransition(async () => {
      try {
        await refreshCrowdData();
      } catch {
        // 캐시를 비우지 못해도 화면은 다시 불러와 본다.
      }
      router.refresh();
    });
  }

  return (
    <button type="button" className={className} disabled={pending} onClick={retry}>
      {pending ? "불러오는 중" : "다시 시도"}
    </button>
  );
}
