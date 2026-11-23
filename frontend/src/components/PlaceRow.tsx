import { CaretRightIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";

import { distanceText } from "@/lib/time";
import type { PlaceCard } from "@/lib/types";

import { CrowdBadge } from "./Crowd";
import styles from "./PlaceRow.module.css";

/**
 * 장소 목록 한 줄. 목록마다 따로 만들지 않고 이 컴포넌트 하나를 쓴다.
 * - TOP 5: rank + second="calm" (여유가 끝나는 시각)
 * - 121곳 · 검색 결과: second="category"
 * - 근처 대안: second="category" + 거리
 */
export function PlaceRow({
  place,
  rank,
  second = "category",
  onNavigate,
}: {
  place: PlaceCard;
  rank?: number;
  second?: "category" | "calm" | "none";
  onNavigate?: () => void;
}) {
  const secondText =
    second === "calm" ? (place.calm_text ?? place.category_label) : place.category_label;
  const showSecond = second !== "none";
  return (
    <li>
      <Link
        href={`/place/${place.code}`}
        className={`${styles.row} ${showSecond ? styles.two : ""}`}
        onNavigate={onNavigate}
      >
        {rank ? <span className={styles.rank}>{rank}</span> : null}
        <span className={styles.text}>
          <span className={styles.name}>{place.name}</span>
          {showSecond ? <span className={styles.second}>{secondText}</span> : null}
        </span>
        {place.distance_km !== null ? (
          <span className={styles.meta}>{distanceText(place.distance_km)}</span>
        ) : null}
        <CrowdBadge level={place.stale ? null : place.level} label={place.level_label} />
        <CaretRightIcon size={24} className={styles.caret} aria-hidden="true" />
      </Link>
    </li>
  );
}
