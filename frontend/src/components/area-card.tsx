import { Link } from "@tanstack/react-router";
import { ArrowUpRight, ShieldCheck, TrainFront, TrendingUp } from "lucide-react";
import type { Area } from "@/lib/mock-data";

export function AreaCard({ area, rank }: { area: Area; rank?: number }) {
  const delta = area.rentForecast - area.rentNow;
  const up = delta > 0;
  return (
    <Link
      to="/area/$id"
      params={{ id: area.id }}
      className="group relative flex flex-col overflow-hidden rounded-3xl border border-border/70 bg-card p-6 shadow-soft transition-all hover:-translate-y-1 hover:shadow-pop"
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            {rank !== undefined && (
              <span className="font-mono text-xs text-muted-foreground">
                #{String(rank).padStart(2, "0")}
              </span>
            )}
            <span className="text-xs text-muted-foreground">{area.district}</span>
          </div>
          <h3 className="mt-1 font-display text-2xl font-semibold tracking-tight">{area.name}</h3>
        </div>
        <ConfidencePill value={area.confidence} />
      </div>

      <div className="mt-6 grid grid-cols-3 gap-3">
        <Metric
          icon={<TrendingUp className="h-3.5 w-3.5" />}
          label="현재 월세"
          value={`${area.rentNow}만`}
          sub={
            <span className={up ? "text-warn" : "text-success"}>
              {up ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}만 (6M)
            </span>
          }
        />
        <Metric
          icon={<TrainFront className="h-3.5 w-3.5" />}
          label="통근"
          value={`${area.commuteMin}분`}
          sub={<span>월 {area.commuteCost}만원</span>}
        />
        <Metric
          icon={<ShieldCheck className="h-3.5 w-3.5" />}
          label="위험점수"
          value={String(area.riskScore)}
          sub={<RiskBadge score={area.riskScore} />}
        />
      </div>

      <div className="mt-5 flex flex-wrap gap-1.5">
        {area.highlights.map((h) => (
          <span
            key={h}
            className="rounded-full bg-secondary px-2.5 py-1 text-[11px] text-secondary-foreground"
          >
            {h}
          </span>
        ))}
      </div>

      <div className="mt-6 flex items-center justify-between border-t border-dashed border-border pt-4 text-sm">
        <span className="text-muted-foreground">상세 분석 · AI 리포트</span>
        <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
      </div>
    </Link>
  );
}

function Metric({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: React.ReactNode;
}) {
  return (
    <div className="rounded-xl bg-muted/60 p-3">
      <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-muted-foreground">
        {icon} {label}
      </div>
      <div className="mt-1 font-display text-lg font-semibold">{value}</div>
      <div className="text-[11px] text-muted-foreground">{sub}</div>
    </div>
  );
}

export function ConfidencePill({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-1.5 rounded-full border border-mint/40 bg-mint/15 px-2.5 py-1 text-[11px] font-medium text-mint-foreground">
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-mint opacity-60" />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-mint" />
      </span>
      신뢰도 {value}%
    </div>
  );
}

export function RiskBadge({ score }: { score: number }) {
  const t =
    score < 25
      ? { l: "안전", c: "text-success" }
      : score < 40
        ? { l: "보통", c: "text-warn" }
        : { l: "주의", c: "text-destructive" };
  return <span className={t.c}>{t.l}</span>;
}
