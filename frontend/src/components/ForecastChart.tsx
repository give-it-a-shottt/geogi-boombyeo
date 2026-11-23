"use client";

import { useState } from "react";

import type { Level, Recommend, TimelinePoint } from "@/lib/types";

import { CrowdBadge } from "./Crowd";
import styles from "./ForecastChart.module.css";

const BAR_CLASS: Record<Level, string> = {
  1: styles.bar1,
  2: styles.bar2,
  3: styles.bar3,
  4: styles.bar4,
};
// 막대 한 단계의 높이(px). CSS의 .bar1 ~ .bar4와 같아야 한다.
const STEP_HEIGHT = 24;
const BRACKET_GAP = 4;
// 왼쪽 축 글자: 각 단계 막대의 꼭대기 높이에 맞춘다.
const AXIS = [
  { label: "붐빔", level: 4 },
  { label: "약간 붐빔", level: 3 },
  { label: "보통", level: 2 },
  { label: "여유", level: 1 },
];

/** 앞으로 12시간. 그래프와 표를 바꿔 볼 수 있다(같은 정보를 색 없이도 읽을 수 있게). */
export function ForecastChart({
  timeline,
  recommend: given,
}: {
  timeline: TimelinePoint[];
  recommend: Recommend | null;
}) {
  const [view, setView] = useState<"chart" | "table">("chart");
  // 추천 구간이 그래프 범위를 벗어나면(서버 값이 어긋난 경우) 강조만 하지 않는다.
  const recommend =
    given && given.start_index >= 0 && given.start_index < given.end_index && given.end_index <= timeline.length
      ? given
      : null;
  const inRange = (index: number) =>
    recommend !== null && index >= recommend.start_index && index < recommend.end_index;

  return (
    <>
      <div className={styles.head}>
        <h2 className={styles.title}>앞으로 12시간</h2>
        <button
          type="button"
          className={styles.chip}
          aria-pressed={view === "chart"}
          onClick={() => setView("chart")}
        >
          그래프
        </button>
        <button
          type="button"
          className={styles.chip}
          aria-pressed={view === "table"}
          onClick={() => setView("table")}
        >
          표
        </button>
      </div>

      {view === "chart" ? (
        <div className={styles.chart}>
          <div className={styles.axis} aria-hidden="true">
            {AXIS.map((item) => (
              <span key={item.level} style={{ top: (4 - item.level) * STEP_HEIGHT + STEP_HEIGHT / 2 }}>
                {item.label}
              </span>
            ))}
          </div>
          <div
            className={styles.plot}
            style={{ gridTemplateColumns: `repeat(${timeline.length}, minmax(0, 1fr))` }}
            role="img"
            aria-label={chartSummary(timeline, recommend)}
          >
            {timeline.map((point, index) => (
              <div key={point.time} className={styles.barCell} style={{ gridColumn: index + 1 }}>
                <div className={`${styles.bar} ${BAR_CLASS[point.level]}`} />
              </div>
            ))}
            {timeline.map((point, index) => (
              <div
                key={`tick-${point.time}`}
                className={`${styles.tick} ${point.is_now ? styles.tickNow : ""}`}
                style={{ gridColumn: index + 1 }}
                aria-hidden="true"
              >
                {point.axis_label}
              </div>
            ))}
            {recommend ? (
              <div
                className={styles.recommend}
                style={{
                  gridColumn: `${recommend.start_index + 1} / ${recommend.end_index + 1}`,
                  paddingBottom:
                    timeline[recommend.start_index].level * STEP_HEIGHT + BRACKET_GAP,
                }}
                aria-hidden="true"
              >
                <span className={styles.tag}>{recommend.tag}</span>
                <span className={styles.stem} />
                <span className={styles.bracket} />
              </div>
            ) : null}
          </div>
        </div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">시각</th>
              <th scope="col">혼잡도</th>
            </tr>
          </thead>
          <tbody>
            {timeline.map((point, index) => (
              <tr key={point.time} className={inRange(index) ? styles.tableRecommended : ""}>
                <th scope="row">
                  {point.full_label}
                  {inRange(index) ? " (추천)" : ""}
                </th>
                <td>
                  <CrowdBadge level={point.level} label={point.level_label} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

function chartSummary(timeline: TimelinePoint[], recommend: Recommend | null): string {
  const parts = timeline.map((point) => `${point.full_label} ${point.level_label}`);
  const tip = recommend ? ` 추천 시간 ${recommend.tag}.` : "";
  return `앞으로 12시간 혼잡도 그래프.${tip} ${parts.join(", ")}`;
}
