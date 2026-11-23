import { Suspense } from "react";

import { AllPlaces } from "@/components/AllPlaces";
import { AnswerHero, heroStyles } from "@/components/AnswerHero";
import { BasisTime } from "@/components/BasisTime";
import { CrowdBadge } from "@/components/Crowd";
import { MainGnb } from "@/components/Gnb";
import { NearbyLauncher } from "@/components/NearbyLauncher";
import { Band, BottomBar, BottomSpace, Footer, LoadError, PageSkeleton } from "@/components/parts";
import { PlaceRow } from "@/components/PlaceRow";
import ui from "@/components/ui.module.css";
import { getHome } from "@/lib/data";

/** 홈 (HOM_01_001): 지금 여유로운 곳 한 줄 + 오늘의 여유 TOP 5 + 전체 121곳 */
export default function HomePage() {
  return (
    <>
      <MainGnb />
      <main className={ui.grow}>
        <Suspense fallback={<PageSkeleton />}>
          <HomeContent />
        </Suspense>
      </main>
      <Footer />
      <BottomSpace />
      <BottomBar>
        <NearbyLauncher
          source={{ kind: "location" }}
          label="지금 있는 곳, 붐비나요?"
          className={`${ui.button} ${ui.xl} ${ui.primary} ${ui.barOne}`}
          withIcon
        />
      </BottomBar>
    </>
  );
}

async function HomeContent() {
  const home = await getHome();
  if (home === null) return <LoadError />;

  if (home.answer === null) {
    return (
      <>
        <AnswerHero label="지금은" lines={["혼잡도를", "확인하고 있어요"]} />
        <p className={ui.sectionBody}>잠시 뒤에 다시 열어 주세요. 가려는 곳은 검색으로 찾을 수 있어요.</p>
        <AllPlaces total={home.place_count} />
      </>
    );
  }

  const best = home.answer.place;
  return (
    <>
      <AnswerHero
        label={home.answer.label}
        lines={[best.name]}
        detail={best.calm_text}
        href={`/place/${best.code}`}
      >
        <div className={heroStyles.status}>
          <CrowdBadge level={best.level} label={best.level_label} size="m" />
          {best.observed_at ? <BasisTime observedAt={best.observed_at} /> : null}
        </div>
      </AnswerHero>
      <Band />
      <section className={ui.section}>
        <h2 className={ui.sectionTitle}>오늘의 여유 TOP {home.top.length}</h2>
        <ol>
          {home.top.map((place, index) => (
            <PlaceRow key={place.code} place={place} rank={index + 1} second="calm" />
          ))}
        </ol>
        <AllPlaces total={home.place_count} />
      </section>
    </>
  );
}
