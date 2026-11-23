import { WarningCircleIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import type { ReactNode } from "react";

import { clockText } from "@/lib/time";

import { RetryButton } from "./actions";
import ui from "./ui.module.css";

/** 데이터 출처 표시(공공누리 1유형 의무). 홈 · 장소 상세 · 정보 화면에 모두 둔다. */
export function Footer() {
  return (
    <footer className={ui.footer}>
      <p>데이터 출처: 서울 실시간 도시데이터 (서울특별시, 공공누리 1유형)</p>
      <p>혼잡도는 약 25분 늦게 들어오고, 예측은 추정치예요.</p>
      <p>
        <Link href="/about">서비스 소개와 데이터 출처</Link>
      </p>
      <p>© 2026 거기붐벼?</p>
    </footer>
  );
}

/** 화면 아래에 고정되는 버튼 바. 버튼은 children으로 받는다. */
export function BottomBar({ children }: { children: ReactNode }) {
  return <div className={ui.bottomBar}>{children}</div>;
}

/** 하단 버튼 바가 내용을 가리지 않게 넣는 여백 */
export function BottomSpace() {
  return <div className={ui.bottomSpace} aria-hidden="true" />;
}

export function Band() {
  return <div className={ui.band} aria-hidden="true" />;
}

/** 데이터 지연 안내: 장소별로 판정한다(CMN_01_001). */
export function StaleNotice({ observedAt }: { observedAt: string }) {
  return (
    <div className={ui.notice} role="status">
      <WarningCircleIcon size={20} aria-hidden="true" />
      <p className={ui.noticeText}>
        <strong>업데이트가 늦어지고 있어요</strong>
        마지막으로 확인한 시각은 {clockText(observedAt)}이에요.
      </p>
      <RetryButton />
    </div>
  );
}

/** 불러오기 실패 화면 */
export function LoadError({ title = "불러오지 못했어요" }: { title?: string }) {
  return (
    <div className={ui.empty}>
      <p className={ui.emptyTitle}>{title}</p>
      <p className={ui.emptyBody}>잠시 뒤에 다시 시도해 주세요.</p>
      <RetryButton className={`${ui.button} ${ui.l} ${ui.secondary}`} />
    </div>
  );
}

/** 로딩 스켈레톤: 답 영역 + 목록 */
export function PageSkeleton() {
  return (
    <div className={ui.skeletonStack} aria-busy="true" aria-label="불러오는 중">
      <div className={ui.skeleton} style={{ width: 120, height: 22 }} />
      <div className={ui.skeleton} style={{ width: "80%", height: 42 }} />
      <div className={ui.skeleton} style={{ width: "60%", height: 42 }} />
      <div className={ui.skeleton} style={{ width: 160, height: 24 }} />
      <div className={ui.skeleton} style={{ height: 136, marginTop: 24 }} />
      <div className={ui.skeleton} style={{ height: 56 }} />
      <div className={ui.skeleton} style={{ height: 56 }} />
    </div>
  );
}
