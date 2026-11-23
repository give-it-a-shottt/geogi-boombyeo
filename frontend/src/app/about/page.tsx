import type { Metadata } from "next";

import { SubGnb } from "@/components/Gnb";
import { Footer } from "@/components/parts";
import ui from "@/components/ui.module.css";

export const metadata: Metadata = {
  title: "서비스 소개와 데이터 출처",
  description: "거기붐벼?가 무엇을 알려 주는지, 데이터가 어디서 오고 얼마나 늦는지 설명해요.",
  alternates: { canonical: "/about" },
};

/** 서비스 소개 · 데이터 출처 (INF_01_001) */
export default function AboutPage() {
  return (
    <>
      <SubGnb title="서비스 소개" />
      <main className={`${ui.grow} ${ui.prose}`}>
        <section>
          <h2>무엇을 알려 주나요</h2>
          <p>
            서울 주요 121곳이 지금 붐비는지, 몇 시에 가면 덜 붐비는지, 근처에 덜 붐비는 곳이 어디인지
            알려 드려요. 정보를 펼쳐 놓는 대신 &ldquo;언제 가면 되는지&rdquo;를 한 문장으로 먼저 말해요.
          </p>
        </section>
        <section>
          <h2>데이터 출처</h2>
          <p>
            서울특별시{" "}
            <a
              href="https://data.seoul.go.kr/dataList/OA-21285/A/1/datasetView.do"
              target="_blank"
              rel="noopener noreferrer"
            >
              서울 실시간 도시데이터
            </a>
            를 사용해요. 이 데이터는 공공누리 제1유형(출처 표시)으로 개방되어 있어요.
          </p>
        </section>
        <section>
          <h2>알아 두세요</h2>
          <ul>
            <li>혼잡도는 통신 데이터를 바탕으로 한 추정치이고, 약 25분 늦게 들어와요.</li>
            <li>앞으로 12시간의 혼잡도는 서울시가 제공하는 예측값이라 실제와 다를 수 있어요.</li>
            <li>서울시가 정한 121곳만 확인할 수 있어요. 그 밖의 장소는 아직 알려 드리지 못해요.</li>
            <li>혼잡도는 여유, 보통, 약간 붐빔, 붐빔 네 단계예요.</li>
          </ul>
        </section>
        <section>
          <h2>위치 정보</h2>
          <p>
            &ldquo;지금 있는 곳, 붐비나요?&rdquo;를 누를 때만 위치를 사용해요. 가까운 장소를 찾는 데만 쓰고
            저장하지 않아요. 로그인이나 회원 가입은 없어요.
          </p>
        </section>
      </main>
      <Footer />
    </>
  );
}
