import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Brain, Compass, LineChart, ShieldCheck, Sparkles, Target } from "lucide-react";
import { SiteFooter, SiteHeader } from "@/components/site-chrome";
import { AreaCard } from "@/components/area-card";
import { AREAS } from "@/lib/mock-data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "안심 H+T — 청년을 위한 주거+교통 의사결정 AI" },
      {
        name: "description",
        content:
          "월세, 통근비, 보증사고 위험까지 — 6개월 후 변화를 예측해 설명해주는 청년 주거 추천 AI.",
      },
      { property: "og:title", content: "안심 H+T — 청년 주거 의사결정 AI" },
      { property: "og:description", content: "설명 가능한 추천 · 미래 월세 예측 · 신뢰도 점수" },
    ],
  }),
  component: Home,
});

function Home() {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <Hero />
      <Trusted />
      <HowItWorks />
      <SamplePicks />
      <CTA />
      <SiteFooter />
    </div>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-gradient-hero opacity-[0.04]" />
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 md:gap-12 md:px-6 md:py-20 lg:grid-cols-12 lg:py-28">
        <div className="lg:col-span-7">
          <div className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card px-3 py-1 text-[11px] text-muted-foreground shadow-soft md:text-xs">
            <span className="h-1.5 w-1.5 rounded-full bg-mint" />
            v2.2 · GRU + Gemini 2.5 Flash
          </div>
          <h1 className="mt-5 font-display text-[2.5rem] font-semibold leading-[1.05] tracking-tight text-balance md:mt-6 md:text-6xl lg:text-7xl">
            "어디 살지" 결정,
            <br />
            <span className="bg-gradient-hero bg-clip-text text-transparent">
              AI가 설명해 드릴게요.
            </span>
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground md:mt-6 md:text-lg">
            월세 · 통근비 · 보증사고 위험까지 한 번에. 단순 추천이 아니라
            <span className="text-foreground"> 6개월 후 월세 예측</span>과
            <span className="text-foreground"> 왜 추천했는지</span>를 함께 보여주는 청년 주거
            의사결정 AI.
          </p>
          <div className="mt-7 flex flex-col gap-2.5 sm:flex-row sm:flex-wrap sm:items-center sm:gap-3 md:mt-8">
            <Link
              to="/recommend"
              className="group inline-flex items-center justify-center gap-2 rounded-full bg-foreground px-6 py-3.5 text-sm font-medium text-background transition-transform hover:scale-[1.02]"
            >
              내 조건으로 추천 받기
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <Link
              to="/about"
              className="inline-flex items-center justify-center gap-2 rounded-full border border-border bg-card px-6 py-3.5 text-sm font-medium text-foreground hover:bg-muted"
            >
              어떻게 작동해요?
            </Link>
          </div>
          <div className="mt-10 grid max-w-lg grid-cols-3 gap-4 border-t border-border/60 pt-6 md:mt-12 md:gap-6 md:pt-8">
            <Stat n="9" l="공공 데이터 소스" />
            <Stat n="30K+" l="격자 분석" />
            <Stat n="6M" l="월세 예측 horizon" />
          </div>
        </div>

        <div className="relative lg:col-span-5">
          <HeroPreview />
        </div>
      </div>
    </section>
  );
}

function Stat({ n, l }: { n: string; l: string }) {
  return (
    <div>
      <div className="font-display text-2xl font-semibold tracking-tight md:text-3xl">{n}</div>
      <div className="mt-1 text-[11px] text-muted-foreground md:text-xs">{l}</div>
    </div>
  );
}

function HeroPreview() {
  return (
    <div className="relative">
      <div className="absolute -inset-6 rounded-[2rem] bg-gradient-mint opacity-30 blur-2xl" />
      <div className="relative rounded-3xl border border-border bg-card p-6 shadow-pop">
        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">
            오늘의 Top Pick
          </div>
          <div className="rounded-full bg-mint/15 px-2 py-1 text-[10px] text-mint-foreground">
            신뢰도 92%
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <h3 className="font-display text-3xl font-semibold">망원동</h3>
          <span className="text-sm text-muted-foreground">서울 마포구</span>
        </div>

        <div className="mt-5 grid grid-cols-3 gap-2 text-center">
          {[
            { l: "월세", v: "58", s: "만원" },
            { l: "통근", v: "34", s: "분" },
            { l: "위험", v: "18", s: "/100" },
          ].map((x) => (
            <div key={x.l} className="rounded-xl bg-muted/60 p-3">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                {x.l}
              </div>
              <div className="font-display text-xl font-semibold">
                {x.v}
                <span className="ml-0.5 text-xs font-normal text-muted-foreground">{x.s}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-5 rounded-2xl border border-dashed border-border p-4">
          <div className="flex items-center gap-2 text-xs font-medium">
            <Brain className="h-3.5 w-3.5 text-primary" /> AI 리포트
          </div>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            "직장(여의도)까지 평균 34분, 6개월 뒤 월세는 약{" "}
            <span className="text-foreground">+4만원</span> 상승 예상이에요. HUG 사고율이 강서구
            평균의 1/3 수준이라 보증금 회수 위험이 낮아요."
          </p>
        </div>

        <div className="mt-5 flex items-center justify-between text-xs text-muted-foreground">
          <span>vs 강남 대비 월세 −37%</span>
          <span className="font-mono">conf · 0.92</span>
        </div>
      </div>

      <div className="absolute -bottom-6 -left-6 hidden rounded-2xl border border-border bg-card p-3 shadow-soft md:block">
        <div className="flex items-center gap-2 text-xs">
          <ShieldCheck className="h-4 w-4 text-success" />
          HUG 사고율 0.4%
        </div>
      </div>
    </div>
  );
}

function Trusted() {
  const sources = ["국토교통부", "한국은행 ECOS", "HUG", "KOSIS", "한국부동산원", "행정안전부"];
  return (
    <section className="border-y border-border/60 bg-card/50">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-center gap-x-10 gap-y-3 px-6 py-6 text-xs text-muted-foreground">
        <span className="uppercase tracking-[0.2em]">Powered by</span>
        {sources.map((s) => (
          <span key={s} className="font-display text-sm tracking-tight text-foreground/80">
            {s}
          </span>
        ))}
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    { i: <Compass />, t: "조건 입력", d: "직장 위치, 예산, 출퇴근 한계 시간을 알려주세요." },
    {
      i: <Target />,
      t: "후보 추출",
      d: "30,000개 격자에서 카카오맵 OD 기반으로 통근 가능 지역만 좁혀요.",
    },
    {
      i: <LineChart />,
      t: "예측 + 위험 평가",
      d: "GRU가 6개월 후 월세를, 룰 엔진이 HUG 사고율을 점수화해요.",
    },
    {
      i: <Sparkles />,
      t: "설명 + 비교",
      d: "Gemini 2.5 Flash가 '왜 여기인지' 자연어로 비교 리포트를 만들어요.",
    },
  ];
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 md:px-6 md:py-24">
      <div className="grid items-end gap-6 md:grid-cols-2">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            How it works
          </div>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight md:text-5xl">
            추천이 아니라
            <br />
            <span className="text-muted-foreground">의사결정을 돕는 AI.</span>
          </h2>
        </div>
        <p className="text-sm text-muted-foreground md:text-base md:text-right">
          블랙박스 점수가 아닌, 모든 추천에{" "}
          <span className="text-foreground">설명·신뢰도·비교</span>를 함께 제공합니다.
        </p>
      </div>

      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4 md:mt-12">
        {steps.map((s, i) => (
          <div
            key={s.t}
            className="group relative rounded-2xl border border-border bg-card p-5 shadow-soft transition-colors hover:border-foreground/30 md:p-6"
          >
            <div className="font-mono text-xs text-muted-foreground">0{i + 1}</div>
            <div className="mt-5 grid h-10 w-10 place-items-center rounded-xl bg-foreground text-background [&>svg]:h-4 [&>svg]:w-4 md:mt-6">
              {s.i}
            </div>
            <h3 className="mt-4 font-display text-lg font-semibold">{s.t}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.d}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function SamplePicks() {
  return (
    <section className="mx-auto max-w-7xl px-4 pb-16 md:px-6 md:pb-24">
      <div className="mb-6 flex items-end justify-between gap-4 md:mb-8">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">샘플 결과</div>
          <h2 className="mt-3 font-display text-2xl font-semibold tracking-tight md:text-4xl">
            여의도 직장 · 보증금 2,500만 이하
          </h2>
        </div>
        <Link
          to="/recommend"
          className="hidden items-center gap-1 text-sm text-muted-foreground hover:text-foreground md:flex"
        >
          전체 보기 <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 md:gap-5">
        {AREAS.map((a, i) => (
          <AreaCard key={a.id} area={a} rank={i + 1} />
        ))}
      </div>
      <Link
        to="/recommend"
        className="mt-6 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground md:hidden"
      >
        전체 보기 <ArrowRight className="h-4 w-4" />
      </Link>
    </section>
  );
}

function CTA() {
  return (
    <section className="mx-auto max-w-7xl px-4 pb-16 md:px-6 md:pb-24">
      <div className="relative overflow-hidden rounded-3xl bg-gradient-hero p-7 text-primary-foreground md:p-16">
        <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-mint/30 blur-3xl" />
        <div className="relative max-w-2xl">
          <h2 className="font-display text-3xl font-semibold tracking-tight md:text-5xl">
            3분이면 충분해요.
          </h2>
          <p className="mt-3 text-sm text-primary-foreground/80 md:mt-4 md:text-base">
            조건 몇 가지만 알려주면, 9개 공공 데이터로 분석한 맞춤 동네를 신뢰도 점수와 함께
            보여드려요.
          </p>
          <Link
            to="/recommend"
            className="mt-6 inline-flex items-center gap-2 rounded-full bg-background px-6 py-3.5 text-sm font-medium text-foreground hover:bg-mint md:mt-8"
          >
            지금 추천 받기 <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}
