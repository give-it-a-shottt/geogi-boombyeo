"use client";

import { CaretLeftIcon, MagnifyingGlassIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import type { SearchResponse } from "@/lib/types";

import styles from "./List.module.css";
import { PlaceRow } from "./PlaceRow";

const DEBOUNCE_MS = 200;
const MAX_QUERY_LENGTH = 50;
const RECENT_KEY = "geogi:recent-searches";
const RECENT_MAX = 5;

function readRecent(): string[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]");
    return Array.isArray(value) ? value.filter((item) => typeof item === "string") : [];
  } catch {
    return [];
  }
}

function writeRecent(items: string[]) {
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(items));
  } catch {
    // 저장소를 못 쓰는 환경(사생활 보호 모드 등)에서는 최근 검색 없이 동작한다.
  }
}

type Result = { query: string; data: SearchResponse } | { query: string; data: null };

/** 장소 검색. 121곳 안에서 이름 · 별칭으로 찾고, 없으면 비슷한 곳을 제안한다. */
export function SearchScreen() {
  // 홈에서 위치를 못 써서 넘어온 경우(?from=location) 안내를 보여 준다.
  const fromLocation = useSearchParams().get("from") === "location";
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [recent, setRecent] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // 최근 검색은 이 기기의 브라우저에만 있다. 화면이 뜬 뒤에 읽는다.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRecent(readRecent());
    inputRef.current?.focus();
  }, []);

  const trimmed = query.trim();

  useEffect(() => {
    if (!trimmed) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(trimmed)}`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("검색 실패");
        setResult({ query: trimmed, data: (await response.json()) as SearchResponse });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setResult({ query: trimmed, data: null });
      }
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [trimmed]);

  function remember() {
    if (!trimmed) return;
    const next = [trimmed, ...recent.filter((item) => item !== trimmed)].slice(0, RECENT_MAX);
    setRecent(next);
    writeRecent(next);
  }

  function clearRecent() {
    setRecent([]);
    writeRecent([]);
  }

  // 입력이 바뀐 직후에는 이전 검색어의 결과가 남아 있으므로, 지금 검색어의 결과만 보여 준다.
  const current = result && result.query === trimmed ? result : null;

  return (
    <>
      <form
        className={styles.searchBar}
        role="search"
        onSubmit={(event) => {
          event.preventDefault();
          remember();
        }}
      >
        <Link href="/" className={styles.back} aria-label="뒤로">
          <CaretLeftIcon size={24} aria-hidden="true" />
        </Link>
        <label className={styles.field}>
          <MagnifyingGlassIcon size={20} aria-hidden="true" />
          <span className="srOnly">장소 이름</span>
          <input
            ref={inputRef}
            className={styles.input}
            type="search"
            value={query}
            maxLength={MAX_QUERY_LENGTH}
            placeholder="어디가 궁금하세요? 예) 성수, 홍대"
            autoComplete="off"
            enterKeyHint="search"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </form>

      <div aria-live="polite">
        {!trimmed ? (
          <>
            {fromLocation ? (
              <p className={styles.hint}>
                <strong>위치를 확인하지 못했어요</strong>
                <span>지금 있는 곳이나 가려는 곳의 이름으로 찾아보세요.</span>
              </p>
            ) : null}
            {recent.length > 0 ? (
              <>
                <h2 className={styles.groupTitle}>
                  최근 검색
                  <button type="button" className={styles.clear} onClick={clearRecent}>
                    지우기
                  </button>
                </h2>
                <ul>
                  {recent.map((item) => (
                    <li key={item}>
                      <button type="button" className={styles.recent} onClick={() => setQuery(item)}>
                        {item}
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className={styles.status}>서울 주요 121곳의 혼잡도를 알려 드려요.</p>
            )}
          </>
        ) : current === null ? (
          <p className={styles.status}>찾는 중이에요</p>
        ) : current.data === null ? (
          <p className={styles.status} role="alert">
            검색하지 못했어요. 잠시 뒤에 다시 시도해 주세요.
          </p>
        ) : current.data.results.length > 0 ? (
          <ul>
            {current.data.results.map((place) => (
              <PlaceRow key={place.code} place={place} onNavigate={remember} />
            ))}
          </ul>
        ) : (
          <>
            <p className={styles.hint}>
              <strong>&lsquo;{trimmed}&rsquo;은(는) 아직 알려 드릴 수 없어요</strong>
              <span>서울 주요 121곳만 확인할 수 있어요. 혹시 이곳인가요?</span>
            </p>
            <ul>
              {current.data.suggestions.map((place) => (
                <PlaceRow key={place.code} place={place} />
              ))}
            </ul>
          </>
        )}
      </div>
    </>
  );
}
