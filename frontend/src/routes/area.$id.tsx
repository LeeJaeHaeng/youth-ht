import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  Area as RechartsArea,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowLeft, Brain, Check, Loader2, ShieldCheck, Sparkles } from "lucide-react";
import { SiteFooter, SiteHeader } from "@/components/site-chrome";
import { ConfidencePill, RiskBadge } from "@/components/area-card";
import { AREAS, getArea, toArea, type Area } from "@/lib/mock-data";
import { fetchReport, hydrateResultCache, resultCache } from "@/lib/api";

export const Route = createFileRoute("/area/$id")({
  head: ({ params }) => {
    const a = resolveArea(params.id);
    return {
      meta: [
        { title: a ? `${a.name} — 안심 H+T 분석` : "동네 분석" },
        { name: "description", content: a ? `${a.name} 월세 예측·통근비·위험 점수 AI 분석` : "" },
      ],
    };
  },
  loader: ({ params }) => {
    const a = resolveArea(params.id);
    if (!a) throw notFound();
    return a;
  },
  component: AreaDetail,
});

function resolveArea(id: string): Area | undefined {
  hydrateResultCache();
  // 실 API 결과 캐시에서 먼저 탐색
  if (resultCache.items.length > 0 && resultCache.request) {
    const found = resultCache.items.find((it) => it.region_id === id);
    if (found) return toArea(found, resultCache.request!);
  }
  return getArea(id);
}

function AreaDetail() {
  const area = Route.useLoaderData() as Area;
  const others = AREAS.filter((a) => a.id !== area.id).slice(0, 3);
  const delta = area.rentForecast - area.rentNow;

  // AI 리포트 상태
  const [report, setReport] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  useEffect(() => {
    if (!area._raw || !area._req) return;
    setReportLoading(true);
    fetchReport(area._raw, area._req)
      .then((text) => setReport(text))
      .catch((e) => setReportError(e instanceof Error ? e.message : "리포트 생성 실패"))
      .finally(() => setReportLoading(false));
  }, [area.id, area._raw, area._req]);

  return (
    <div className="min-h-screen">
      <SiteHeader />

      <section className="border-b border-border/60 bg-card/40">
        <div className="mx-auto max-w-7xl px-4 py-8 md:px-6 md:py-10">
          <Link
            to="/recommend"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" /> 추천 결과로
          </Link>
          <div className="mt-3 flex flex-wrap items-end justify-between gap-3 md:mt-4 md:gap-4">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                {area.district}
              </div>
              <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight md:text-6xl">
                {area.name}
              </h1>
            </div>
            <ConfidencePill value={area.confidence} />
          </div>
          <div className="mt-5 flex flex-wrap gap-2 md:mt-6">
            {area.highlights.map((h) => (
              <span
                key={h}
                className="rounded-full bg-secondary px-3 py-1.5 text-xs text-secondary-foreground"
              >
                {h}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-4 py-8 md:px-6 md:py-12 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-8">
          {/* GRU 예측 차트 */}
          <div className="rounded-3xl border border-border bg-card p-6 shadow-soft md:p-8">
            <div className="flex items-baseline justify-between">
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground">
                  월세 예측 · GRU
                </div>
                <h2 className="mt-1 font-display text-2xl font-semibold tracking-tight">
                  6개월 후{" "}
                  <span className={delta > 0 ? "text-warn" : "text-success"}>
                    {area.rentForecast}만원
                  </span>
                </h2>
              </div>
              <div className="text-right">
                <div className="text-xs text-muted-foreground">vs 현재</div>
                <div className={`font-mono text-lg ${delta > 0 ? "text-warn" : "text-success"}`}>
                  {delta > 0 ? "+" : ""}
                  {delta.toFixed(1)}만
                </div>
              </div>
            </div>

            <div className="mt-6 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={area.forecastSeries}
                  margin={{ top: 10, right: 8, left: -16, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="m"
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "var(--card)",
                      border: "1px solid var(--border)",
                      borderRadius: 12,
                      fontSize: 12,
                    }}
                    formatter={(v: number) => [`${v}만원`, "월세"]}
                  />
                  <RechartsArea
                    type="monotone"
                    dataKey="v"
                    stroke="var(--primary)"
                    strokeWidth={2.5}
                    fill="url(#g)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 flex justify-between text-[10px] font-mono text-muted-foreground">
              <span>← 과거 5개월</span>
              <span>현재</span>
              <span>예측 +6개월 →</span>
            </div>
          </div>

          {/* AI 리포트 */}
          <div className="rounded-3xl border border-border bg-gradient-hero p-6 text-primary-foreground shadow-pop md:p-8">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wider opacity-80">
              <Brain className="h-3.5 w-3.5" /> AI 리포트 · Gemini 2.5 Flash
            </div>
            <h3 className="mt-3 font-display text-2xl font-semibold tracking-tight">
              왜 {area.name}을 추천했나요?
            </h3>

            {reportLoading && (
              <div className="mt-5 flex items-center gap-2 text-sm text-primary-foreground/70">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Gemini AI 리포트 생성 중…</span>
              </div>
            )}

            {reportError && !report && (
              <div className="mt-5 space-y-3 text-sm leading-relaxed text-primary-foreground/90">
                <p>
                  {area._req?.work_name ?? "직장"} 기준 통근{" "}
                  <span className="text-mint">{area.commuteMin}분</span>, 월세 {area.rentNow}만원,
                  보증금 {area.deposit.toLocaleString()}만원 수준입니다.
                </p>
                <p>
                  HUG 보증사고율 {area._raw?.hug_acc_rate_pct.toFixed(2) ?? "—"}%, 소득 대비 주거비
                  부담률 {area._raw ? `${(area._raw.burden_ratio * 100).toFixed(0)}%` : "—"}{" "}
                  수준입니다.
                </p>
                <p className="opacity-60 text-xs">
                  (AI 리포트 로드 실패 — 백엔드 연결을 확인하세요)
                </p>
              </div>
            )}

            {report && (
              <div className="mt-5 space-y-3 text-sm leading-relaxed text-primary-foreground/90 whitespace-pre-line">
                {report}
              </div>
            )}

            {!reportLoading && !report && !reportError && !area._raw && (
              <div className="mt-5 space-y-3 text-sm leading-relaxed text-primary-foreground/90">
                <p>
                  통근 <span className="text-mint">{area.commuteMin}분</span>, 월세 {area.rentNow}
                  만원으로 6개월 후 {delta > 0 ? `약 ${delta.toFixed(1)}만원 상승` : "안정"}{" "}
                  예상입니다.
                </p>
                <p className="opacity-60 text-xs">
                  AI 추천 받기를 실행하면 Gemini 맞춤 리포트를 제공합니다.
                </p>
              </div>
            )}
          </div>

          {/* 비교 테이블 */}
          <div className="rounded-3xl border border-border bg-card p-6 shadow-soft md:p-8">
            <div className="flex items-center justify-between">
              <h3 className="font-display text-xl font-semibold tracking-tight">
                비슷한 다른 동네와 비교
              </h3>
              <span className="font-mono text-[10px] text-muted-foreground">auto-generated</span>
            </div>
            <div className="mt-5 -mx-2 overflow-x-auto rounded-2xl border border-border md:mx-0">
              <table className="w-full min-w-[480px] text-sm">
                <thead className="bg-muted/60 text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-3 py-3 text-left font-medium md:px-4">동네</th>
                    <th className="px-3 py-3 text-right font-medium md:px-4">월세</th>
                    <th className="px-3 py-3 text-right font-medium md:px-4">통근</th>
                    <th className="px-3 py-3 text-right font-medium md:px-4">위험</th>
                    <th className="px-3 py-3 text-right font-medium md:px-4">신뢰도</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="bg-mint/10 font-medium">
                    <td className="px-3 py-3 md:px-4">
                      {area.name}{" "}
                      <span className="ml-1 text-[10px] text-mint-foreground">선택</span>
                    </td>
                    <td className="px-3 py-3 text-right md:px-4">{area.rentNow}만</td>
                    <td className="px-3 py-3 text-right md:px-4">{area.commuteMin}분</td>
                    <td className="px-3 py-3 text-right md:px-4">
                      <RiskBadge score={area.riskScore} />
                    </td>
                    <td className="px-3 py-3 text-right font-mono md:px-4">{area.confidence}%</td>
                  </tr>
                  {others.map((o) => (
                    <tr key={o.id} className="border-t border-border">
                      <td className="px-3 py-3 md:px-4">
                        <Link to="/area/$id" params={{ id: o.id }} className="hover:underline">
                          {o.name}
                        </Link>
                      </td>
                      <td className="px-3 py-3 text-right md:px-4">{o.rentNow}만</td>
                      <td className="px-3 py-3 text-right md:px-4">{o.commuteMin}분</td>
                      <td className="px-3 py-3 text-right md:px-4">
                        <RiskBadge score={o.riskScore} />
                      </td>
                      <td className="px-3 py-3 text-right font-mono md:px-4">{o.confidence}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <aside className="space-y-6 lg:col-span-4">
          <ScoreCard scores={area.scores} />
          <div className="rounded-3xl border border-border bg-card p-6 shadow-soft">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
              <ShieldCheck className="h-3.5 w-3.5" /> 안전성 체크리스트
            </div>
            <ul className="mt-4 space-y-2.5 text-sm">
              {[
                area._raw && area._raw.hug_acc_rate_pct < 1.5
                  ? "HUG 사고율 1.5% 미만"
                  : "HUG 보증보험 가입 가능",
                "등기부 근저당 비율 확인 권장",
                area._raw && area._raw.burden_ratio < 0.3
                  ? "소득 대비 주거비 30% 미만"
                  : "소득 대비 적정 주거비 수준",
                "계약 전 현장 방문 필수",
              ].map((t) => (
                <li key={t} className="flex items-start gap-2">
                  <Check className="mt-0.5 h-4 w-4 text-success" />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </div>

          {area._raw && (
            <div className="rounded-3xl border border-border bg-card p-6 shadow-soft">
              <div className="text-xs uppercase tracking-wider text-muted-foreground mb-3">
                핵심 지표
              </div>
              <div className="space-y-2 text-sm">
                <MetricRow
                  label="월 소득 대비 부담"
                  value={`${(area._raw.burden_ratio * 100).toFixed(1)}%`}
                />
                <MetricRow
                  label="6개월 후 부담 예측"
                  value={`${(area._raw.future_burden_6m_ratio * 100).toFixed(1)}%`}
                />
                <MetricRow
                  label="HUG 보증사고율"
                  value={`${area._raw.hug_acc_rate_pct.toFixed(2)}%`}
                />
                <MetricRow
                  label="실거래 표본수"
                  value={`${area._raw.confidence_breakdown?.["sample_score"] !== undefined ? "충분" : "보통"}`}
                />
              </div>
            </div>
          )}

          <div className="rounded-3xl border border-dashed border-border p-6">
            <Sparkles className="h-5 w-5 text-mint" />
            <p className="mt-3 text-sm text-muted-foreground">
              이 분석은 LightGBM·XGBoost·GRU·Gemini 2.5가 행안부·R-ONE·KOSIS 등 9개 공공데이터를
              기반으로 만들었어요. 실제 계약 전 현장 확인은 필수입니다.
            </p>
          </div>
        </aside>
      </section>
      <SiteFooter />
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono font-medium">{value}</span>
    </div>
  );
}

function ScoreCard({
  scores,
}: {
  scores: { housing: number; transport: number; safety: number; vibe: number };
}) {
  const items = [
    { k: "housing", l: "주거 가성비" },
    { k: "transport", l: "교통" },
    { k: "safety", l: "안전성" },
    { k: "vibe", l: "미래 전망" },
  ] as const;
  return (
    <div className="rounded-3xl border border-border bg-card p-6 shadow-soft">
      <div className="text-xs uppercase tracking-wider text-muted-foreground">종합 점수</div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="font-display text-5xl font-semibold tracking-tight">
          {Math.round((scores.housing + scores.transport + scores.safety + scores.vibe) / 4)}
        </span>
        <span className="text-sm text-muted-foreground">/ 100</span>
      </div>
      <div className="mt-6 space-y-4">
        {items.map((it) => {
          const v = scores[it.k];
          return (
            <div key={it.k}>
              <div className="mb-1.5 flex justify-between text-xs">
                <span className="text-muted-foreground">{it.l}</span>
                <span className="font-mono">{v}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <div className="h-full rounded-full bg-foreground" style={{ width: `${v}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
