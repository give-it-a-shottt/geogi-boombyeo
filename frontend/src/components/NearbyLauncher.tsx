"use client";

import { MapPinIcon, XIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import type { NearbyResponse } from "@/lib/types";

import { PlaceRow } from "./PlaceRow";
import sheet from "./Sheet.module.css";
import ui from "./ui.module.css";

type Source = { kind: "place"; code: string; name: string } | { kind: "location" };

type State =
  | { step: "idle" }
  | { step: "loading" }
  | { step: "done"; data: NearbyResponse }
  | { step: "error" };

const GEO_TIMEOUT_MS = 8000;
const GEO_MAX_AGE_MS = 60_000;
// 서버로 보내는 좌표의 소수 자리. 셋째 자리는 약 110m로, 5km 안의 장소를 찾기에 충분하다.
const COORDINATE_DIGITS = 3;

/** 위치를 알 수 없음: 권한 거부, 시간 초과, 지원하지 않는 브라우저. 문구가 아니라 종류로 구분한다. */
class LocationUnavailableError extends Error {}

function locate(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new LocationUnavailableError());
      return;
    }
    navigator.geolocation.getCurrentPosition(resolve, () => reject(new LocationUnavailableError()), {
      timeout: GEO_TIMEOUT_MS,
      maximumAge: GEO_MAX_AGE_MS,
    });
  });
}

/**
 * "근처 덜 붐비는 곳" 버튼과 시트.
 * - source.kind = "place": 보고 있는 장소 기준 (장소 상세)
 * - source.kind = "location": 내 위치 기준 (홈). 위치를 못 쓰면 검색으로 보낸다.
 */
export function NearbyLauncher({
  source,
  label,
  className,
  withIcon = false,
}: {
  source: Source;
  label: string;
  className: string;
  withIcon?: boolean;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [state, setState] = useState<State>({ step: "idle" });
  const router = useRouter();

  async function load(): Promise<NearbyResponse> {
    let url: string;
    if (source.kind === "place") {
      url = `/api/places/${encodeURIComponent(source.code)}/nearby`;
    } else {
      const position = await locate();
      const { latitude, longitude } = position.coords;
      // 위치는 이 요청에만 쓰고 저장하지 않는다. 필요한 만큼만 뭉툭하게 보낸다.
      url = `/api/nearby?lat=${latitude.toFixed(COORDINATE_DIGITS)}&lng=${longitude.toFixed(COORDINATE_DIGITS)}`;
    }
    const response = await fetch(url);
    if (!response.ok) throw new Error("근처 장소를 불러오지 못함");
    return (await response.json()) as NearbyResponse;
  }

  async function open() {
    if (state.step === "loading") return;
    setState({ step: "loading" });
    try {
      const data = await load();
      setState({ step: "done", data });
      showSheet();
    } catch (error) {
      // 위치 권한 거부 · 실패 → 검색으로 (유저플로우 B의 "아니오" 갈래)
      if (error instanceof LocationUnavailableError) {
        setState({ step: "idle" });
        router.push("/search?from=location");
        return;
      }
      setState({ step: "error" });
      showSheet();
    }
  }

  function showSheet() {
    // 이미 열린 시트에서 다시 시도할 때 showModal을 또 부르면 오류가 난다.
    if (!dialogRef.current?.open) dialogRef.current?.showModal();
  }

  function close() {
    dialogRef.current?.close();
  }

  return (
    <>
      <button type="button" className={className} onClick={open} aria-busy={state.step === "loading"}>
        {withIcon ? <MapPinIcon size={20} aria-hidden="true" /> : null}
        {state.step === "loading" ? "찾는 중이에요" : label}
      </button>

      <dialog
        ref={dialogRef}
        className={sheet.sheet}
        aria-labelledby="nearby-title"
        onClose={() => setState({ step: "idle" })}
        onClick={(event) => {
          // 시트 바깥(어두운 배경)을 누르면 닫는다.
          if (event.target === dialogRef.current) close();
        }}
      >
        <div className={sheet.head}>
          <h2 id="nearby-title" className={sheet.title}>
            근처 덜 붐비는 곳
          </h2>
          <button type="button" className={sheet.close} aria-label="닫기" onClick={close}>
            <XIcon size={24} aria-hidden="true" />
          </button>
        </div>
        <SheetBody state={state} source={source} onNavigate={close} onRetry={open} />
      </dialog>
    </>
  );
}

function SheetBody({
  state,
  source,
  onNavigate,
  onRetry,
}: {
  state: State;
  source: Source;
  onNavigate: () => void;
  onRetry: () => void;
}) {
  if (state.step === "error") {
    return (
      <>
        <p className={sheet.message}>
          <strong>불러오지 못했어요</strong>
          잠시 뒤에 다시 시도해 주세요.
        </p>
        <div className={sheet.actions}>
          <button
            type="button"
            className={`${ui.button} ${ui.l} ${ui.secondary} ${ui.block}`}
            onClick={onRetry}
          >
            다시 시도
          </button>
        </div>
      </>
    );
  }
  if (state.step === "loading") return <p className={sheet.message}>찾는 중이에요</p>;
  if (state.step !== "done") return null;

  const { base, alternatives } = state.data;
  const searchLink = (
    <div className={sheet.actions}>
      <Link href="/search" className={`${ui.button} ${ui.l} ${ui.secondary} ${ui.block}`}>
        검색하기
      </Link>
    </div>
  );

  if (base === null) {
    return (
      <>
        <p className={sheet.message}>
          <strong>근처에 확인할 수 있는 장소가 없어요</strong>
          서울 주요 121곳만 알려 드려요. 가려는 곳을 검색해 보세요.
        </p>
        {searchLink}
      </>
    );
  }

  const caption =
    source.kind === "location"
      ? `지금 가장 가까운 곳은 ${base.name}${base.level_label ? ` (${base.level_label})` : ""}`
      : `${base.name}에서 가까운 순`;

  if (alternatives.length === 0) {
    return (
      <>
        <p className={sheet.caption}>{caption}</p>
        <p className={sheet.message}>
          <strong>근처에 더 여유로운 곳이 없어요</strong>
          5km 안에서 찾았어요. 다른 곳을 검색해 보세요.
        </p>
        {searchLink}
      </>
    );
  }

  return (
    <>
      <p className={sheet.caption}>{caption}</p>
      <ul>
        {alternatives.map((place) => (
          <PlaceRow key={place.code} place={place} onNavigate={onNavigate} />
        ))}
      </ul>
    </>
  );
}
