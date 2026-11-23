import { PersonIcon } from "@phosphor-icons/react/ssr";

import type { Level } from "@/lib/types";

import styles from "./ui.module.css";

const LEVEL_CLASS: Record<Level, string> = {
  1: styles.level1,
  2: styles.level2,
  3: styles.level3,
  4: styles.level4,
};

/** 혼잡도 배지. 색만으로 단계를 말하지 않도록 글자를 항상 함께 보여 준다. */
export function CrowdBadge({
  level,
  label,
  size = "s",
}: {
  level: Level | null;
  label: string | null;
  size?: "s" | "m";
}) {
  const sizeClass = size === "m" ? styles.badgeM : styles.badgeS;
  if (level === null || label === null) {
    return <span className={`${styles.badge} ${sizeClass} ${styles.badgeNone}`}>확인 중</span>;
  }
  return <span className={`${styles.badge} ${sizeClass} ${LEVEL_CLASS[level]}`}>{label}</span>;
}

/** 사람 미터: 4칸 중 단계만큼 채운다. 옆의 배지 글자가 같은 정보를 주므로 화면 낭독기에는 숨긴다. */
export function PersonMeter({ level, size = 24 }: { level: Level; size?: number }) {
  return (
    <span className={styles.meter} aria-hidden="true">
      {[1, 2, 3, 4].map((step) =>
        step <= level ? (
          <PersonIcon key={step} size={size} weight="fill" />
        ) : (
          <PersonIcon key={step} size={size} weight="regular" className={styles.meterEmpty} />
        ),
      )}
    </span>
  );
}
