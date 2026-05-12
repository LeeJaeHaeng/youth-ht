import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Database, Layers, Shield } from "lucide-react";
import { SiteFooter, SiteHeader } from "@/components/site-chrome";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "어떻게 작동해요? — 안심 H+T" },
      { name: "description", content: "9개 공공 데이터, 4종 AI 모델로 청년 주거를 분석합니다." },
    ],
  }),
  component: About,
});

function About() {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <section className="mx-auto max-w-5xl px-4 py-12 md:px-6 md:py-20">
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Methodology</div>
        <h1 className="mt-3 font-display text-3xl font-semibold tracking-tight md:text-6xl text-balance">
          블랙박스가 아닌, 설명 가능한 AI.
        </h1>
        <p className="mt-5 max-w-2xl text-base text-muted-foreground md:mt-6 md:text-lg">
          모든 추천은 9개 공공 데이터 + 4종 AI 모델의 합의 결과입니다. 점수 옆에 항상 신뢰도와
          근거를 함께 보여드려요.
        </p>

        <div className="mt-12 grid gap-4 sm:grid-cols-2 md:mt-16 md:grid-cols-3 md:gap-6">
          <Block
            icon={<Database />}
            t="9개 공공 데이터"
            d="국토부 실거래가, HUG 보증사고, ECOS 기준금리, KOSIS 청년 임금, 부동산원 분양, 행안부 인구 등."
          />
          <Block
            icon={<Layers />}
            t="4종 AI 모델"
            d="LightGBM(현재 월세) · XGBoost(통근비) · GRU(6개월 예측) · Gemini 2.5 Flash(자연어 리포트)."
          />
          <Block
            icon={<Shield />}
            t="신뢰도 점수"
            d="앙상블 분산과 데이터 커버리지에서 confidence를 산출, 0~100%로 투명하게 공개."
          />
        </div>

        <div className="mt-12 rounded-3xl border border-border bg-card p-6 shadow-soft md:mt-16 md:p-8">
          <h2 className="font-display text-xl font-semibold tracking-tight md:text-2xl">
            파이프라인
          </h2>
          <ol className="mt-6 space-y-5">
            {[
              [
                "조건 입력",
                "직장·예산·통근 한계를 받아 30,000개 격자에서 후보 추출 (카카오맵 OD).",
              ],
              ["피처 결합", "격자별 8개 피처로 GRU 시계열 입력 텐서 구성, 정규화 후 추론."],
              ["위험 점수", "HUG 사고율을 시군구→격자로 매핑, 룰 엔진으로 0~100 환산."],
              [
                "설명 생성",
                "Top-K 동네에 대해 Gemini 2.5 Flash가 '왜 여기인지'와 비교 분석을 자연어로 작성.",
              ],
              ["신뢰도 산출", "앙상블 표준편차 + 데이터 커버리지를 결합해 confidence 산출."],
            ].map(([t, d], i) => (
              <li key={t} className="flex gap-4">
                <span className="font-mono text-xs text-muted-foreground">0{i + 1}</span>
                <div>
                  <div className="font-medium">{t}</div>
                  <div className="text-sm text-muted-foreground">{d}</div>
                </div>
              </li>
            ))}
          </ol>
        </div>

        <Link
          to="/recommend"
          className="mt-12 inline-flex items-center gap-2 rounded-full bg-foreground px-6 py-3.5 text-sm font-medium text-background"
        >
          직접 시도해보기 <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
      <SiteFooter />
    </div>
  );
}

function Block({ icon, t, d }: { icon: React.ReactNode; t: string; d: string }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
      <div className="grid h-10 w-10 place-items-center rounded-xl bg-foreground text-background [&>svg]:h-4 [&>svg]:w-4">
        {icon}
      </div>
      <div className="mt-4 font-display text-lg font-semibold">{t}</div>
      <p className="mt-2 text-sm text-muted-foreground">{d}</p>
    </div>
  );
}
