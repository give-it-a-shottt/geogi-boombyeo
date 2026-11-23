"use client";

import { InfoIcon } from "@phosphor-icons/react";
import { useEffect, useId, useState } from "react";

import { agoText, clockText } from "@/lib/time";

import styles from "./AnswerHero.module.css";

const TICK_MS = 30_000;

/**
 * "25분 전 기준" + 정보 버튼.
 * 페이지는 미리 만들어 두기 때문에 "몇 분 전"은 브라우저에서 계산한다.
 * 계산 전(서버가 만든 HTML)에는 시각 그대로 "오후 3시 5분 기준"을 보여 준다.
 */
export function BasisTime({ observedAt }: { observedAt: string }) {
  const [now, setNow] = useState<Date | null>(null);
  const [open, setOpen] = useState(false);
  const tipId = useId();

  useEffect(() => {
    const tick = () => setNow(new Date());
    tick();
    const timer = setInterval(tick, TICK_MS);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className={styles.basisWrap}>
      <span className={styles.basis}>
        <time dateTime={observedAt}>
          {now ? agoText(observedAt, now) : `${clockText(observedAt)} 기준`}
        </time>
        <button
          type="button"
          className={styles.infoButton}
          aria-label="기준 시각 설명"
          aria-expanded={open}
          aria-controls={tipId}
          onClick={() => setOpen((value) => !value)}
        >
          <InfoIcon size={16} aria-hidden="true" />
        </button>
      </span>
      <p id={tipId} className={styles.tip} hidden={!open}>
        혼잡도는 약 25분 늦게 들어와요. 앞으로의 혼잡도는 추정치예요.
      </p>
    </div>
  );
}
