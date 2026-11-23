"use client";

import { useState } from "react";

import type { PlaceListResponse } from "@/lib/types";

import styles from "./List.module.css";
import { PlaceRow } from "./PlaceRow";
import ui from "./ui.module.css";

const PAGE_SIZE = 20;

type State =
  | { step: "closed" }
  | { step: "loading" }
  | { step: "open"; data: PlaceListResponse }
  | { step: "error" };

/** "전체 121곳 펼치기": 누르면 목록을 불러와 분류 칩과 함께 여유 순으로 보여 준다. */
export function AllPlaces({ total }: { total: number }) {
  const [state, setState] = useState<State>({ step: "closed" });
  const [category, setCategory] = useState<string | null>(null);
  const [visible, setVisible] = useState(PAGE_SIZE);

  async function open() {
    setState({ step: "loading" });
    try {
      const response = await fetch("/api/places");
      if (!response.ok) throw new Error("목록을 불러오지 못함");
      setState({ step: "open", data: (await response.json()) as PlaceListResponse });
    } catch {
      setState({ step: "error" });
    }
  }

  if (state.step !== "open") {
    return (
      <div className={styles.more}>
        <button
          type="button"
          className={`${ui.button} ${ui.l} ${ui.secondary} ${ui.block}`}
          onClick={open}
          disabled={state.step === "loading"}
        >
          {state.step === "loading" ? "불러오는 중" : `전체 ${total}곳 펼치기`}
        </button>
        {state.step === "error" ? (
          <p className={styles.status} role="alert">
            목록을 불러오지 못했어요. 다시 눌러 주세요.
          </p>
        ) : null}
      </div>
    );
  }

  const { places, categories } = state.data;
  const filtered = category ? places.filter((place) => place.category === category) : places;
  const choose = (value: string | null) => {
    setCategory(value);
    setVisible(PAGE_SIZE);
  };

  return (
    <section className={ui.section} aria-label={`전체 ${total}곳`}>
      <h2 className={ui.sectionTitle}>전체 {total}곳, 여유로운 순</h2>
      <div className={styles.chips} role="group" aria-label="분류">
        <button
          type="button"
          className={styles.chip}
          aria-pressed={category === null}
          onClick={() => choose(null)}
        >
          전체
        </button>
        {categories.map((item) => (
          <button
            key={item.value}
            type="button"
            className={styles.chip}
            aria-pressed={category === item.value}
            onClick={() => choose(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <ul>
        {filtered.slice(0, visible).map((place) => (
          <PlaceRow key={place.code} place={place} second={category ? "none" : "category"} />
        ))}
      </ul>
      {visible < filtered.length ? (
        <div className={styles.more}>
          <button
            type="button"
            className={`${ui.button} ${ui.l} ${ui.secondary} ${ui.block}`}
            onClick={() => setVisible((count) => count + PAGE_SIZE)}
          >
            더 보기 ({Math.min(visible, filtered.length)} / {filtered.length})
          </button>
        </div>
      ) : null}
    </section>
  );
}
