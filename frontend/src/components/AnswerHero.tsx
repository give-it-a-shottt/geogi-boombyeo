import { CaretRightIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import type { ReactNode } from "react";

import styles from "./AnswerHero.module.css";

/**
 * 홈과 장소 상세의 첫 구역. 가장 큰 글자로 답을 말한다.
 * href가 있으면 답 줄 전체가 그 주소로 가는 링크가 된다(홈).
 */
export function AnswerHero({
  label,
  lines,
  detail,
  href,
  children,
}: {
  label: string;
  lines: string[];
  detail?: string | null;
  href?: string;
  children?: ReactNode;
}) {
  const answer = lines.map((line) => <span key={line}>{line}</span>);
  return (
    <section className={styles.hero}>
      <div>
        <p className={styles.label}>{label}</p>
        {href ? (
          <h2 className={styles.answer}>
            <Link href={href} className={styles.answerLink}>
              <span>{answer}</span>
              <CaretRightIcon size={24} aria-hidden="true" />
            </Link>
          </h2>
        ) : (
          <h2 className={styles.answer}>{answer}</h2>
        )}
      </div>
      {detail ? <p className={styles.detail}>{detail}</p> : null}
      {children}
    </section>
  );
}

export { styles as heroStyles };
