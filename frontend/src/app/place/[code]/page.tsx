import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { ShareButton } from "@/components/actions";
import { AnswerHero, heroStyles } from "@/components/AnswerHero";
import { BasisTime } from "@/components/BasisTime";
import { CrowdBadge, PersonMeter } from "@/components/Crowd";
import { ForecastChart } from "@/components/ForecastChart";
import chart from "@/components/ForecastChart.module.css";
import { SubGnb } from "@/components/Gnb";
import { NearbyLauncher } from "@/components/NearbyLauncher";
import {
  Band,
  BottomBar,
  BottomSpace,
  Footer,
  LoadError,
  PageSkeleton,
  StaleNotice,
} from "@/components/parts";
import { PlaceRow } from "@/components/PlaceRow";
import ui from "@/components/ui.module.css";
import { getPlaceDetail } from "@/lib/data";
import { findKnownPlace, KNOWN_PLACES } from "@/lib/places";
import type { PlaceDetailResponse } from "@/lib/types";

type Props = PageProps<"/place/[code]">;

/** 121곳을 빌드 때 미리 만든다(검색엔진용). 목록에 없는 코드는 404. */
export function generateStaticParams() {
  return KNOWN_PLACES.map((place) => ({ code: place.code }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { code } = await params;
  const place = findKnownPlace(code);
  if (!place) return { title: "없는 장소" };
  const title = `${place.name} 혼잡도, 지금 붐비나요?`;
  const description = `${place.name}의 지금 혼잡도와 앞으로 12시간 예측. 몇 시에 가면 덜 붐비는지 알려 드려요.`;
  return {
    title,
    description,
    alternates: { canonical: `/place/${place.code}` },
    openGraph: { title, description, url: `/place/${place.code}` },
  };
}

/** 장소 상세 (PLC_01_001 · 예측 없음 PLC_01_003 · 데이터 지연 CMN_01_001) */
export default async function PlacePage({ params }: Props) {
  const { code } = await params;
  const known = findKnownPlace(code);
  if (!known) notFound();

  return (
    <>
      <SubGnb title={known.name} action={<ShareButton title={`${known.name} 혼잡도`} />} />
      <Suspense fallback={<PageSkeleton />}>
        <PlaceContent code={known.code} name={known.name} />
      </Suspense>
    </>
  );
}

async function PlaceContent({ code, name }: { code: string; name: string }) {
  const detail = await getPlaceDetail(code);
  if (detail === null) {
    return (
      <main className={ui.grow}>
        <LoadError />
      </main>
    );
  }
  const { status, answer } = detail;

  if (status === null || answer === null) {
    return (
      <>
        <main className={ui.grow}>
          <AnswerHero label={`${name}의 혼잡도를`} lines={["아직 확인하지", "못했어요"]} />
          <LoadError title="조금 뒤에 다시 확인해 주세요" />
        </main>
        <Footer />
        <BottomSpace />
        <Actions detail={detail} />
      </>
    );
  }

  const hasForecast = detail.timeline.length > 1;
  return (
    <>
      <main className={ui.grow}>
        <AnswerHero label={answer.label} lines={answer.lines} detail={answer.detail}>
          <div className={heroStyles.status}>
            <span className={heroStyles.now}>지금</span>
            <PersonMeter level={status.level} />
            <CrowdBadge level={status.level} label={status.level_label} size="m" />
          </div>
          <BasisTime observedAt={status.observed_at} />
        </AnswerHero>

        {status.stale ? <StaleNotice observedAt={status.observed_at} /> : null}

        <Band />
        <section className={ui.section}>
          <div className={ui.sectionBody}>
            {hasForecast ? (
              <ForecastChart timeline={detail.timeline} recommend={detail.recommend} />
            ) : (
              <>
                <h2 className={chart.title}>앞으로 12시간</h2>
                <p className={chart.note}>
                  {status.stale
                    ? "새 값이 들어오면 예측을 다시 보여 드릴게요."
                    : "지금은 예측을 알 수 없어서 지금 혼잡도만 보여 드려요."}
                </p>
              </>
            )}
          </div>
        </section>

        {/* 붐빌 때는 하단 버튼이 같은 일을 하므로 이 구역을 두지 않는다. */}
        {detail.primary_action === "directions" && detail.nearby_top ? (
          <>
            <Band />
            <section className={ui.section}>
              <h2 className={ui.sectionTitle}>지금 가까운 여유로운 곳</h2>
              <ul>
                <PlaceRow place={detail.nearby_top} />
              </ul>
            </section>
          </>
        ) : null}
      </main>
      <Footer />
      <BottomSpace />
      <Actions detail={detail} />
    </>
  );
}

/** 하단 버튼. Primary는 항상 하나: 여유 · 보통이면 길찾기, 붐비면 근처 덜 붐비는 곳. */
function Actions({ detail }: { detail: PlaceDetailResponse }) {
  const directions = (style: string) => (
    <a
      href={detail.directions_url}
      target="_blank"
      rel="noopener noreferrer"
      className={`${ui.button} ${ui.xl} ${style} ${ui.barOne}`}
    >
      길찾기
    </a>
  );
  if (detail.primary_action === "directions") {
    return <BottomBar>{directions(ui.primary)}</BottomBar>;
  }
  return (
    <BottomBar>
      {directions(ui.secondary)}
      <NearbyLauncher
        source={{ kind: "place", code: detail.place.code, name: detail.place.name }}
        label="근처 덜 붐비는 곳"
        className={`${ui.button} ${ui.xl} ${ui.primary} ${ui.barTwo}`}
      />
    </BottomBar>
  );
}
