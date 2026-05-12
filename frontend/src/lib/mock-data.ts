import type { ApiRecommendItem, ApiRecommendRequest } from "./api";

export type Area = {
  id: string;
  name: string;
  district: string;
  rentNow: number;
  rentForecast: number;
  deposit: number;
  commuteCost: number;
  commuteMin: number;
  riskScore: number;
  confidence: number;
  highlights: string[];
  forecastSeries: { m: string; v: number }[];
  scores: { housing: number; transport: number; safety: number; vibe: number };
  lat?: number;
  lng?: number;
  // 원본 API 응답 (상세 페이지 보고서용)
  _raw?: ApiRecommendItem;
  _req?: ApiRecommendRequest;
};

// ── API 응답 → Area 변환 ───────────────────────────────────────────────────────

const YOUTH_INCOME_WON = 2_601_000; // KOSIS 2024 29세이하 월임금

function buildHighlights(item: ApiRecommendItem, workName: string): string[] {
  const tags: string[] = [];
  if (item.commute_min < 30) tags.push(`${workName}까지 ${Math.round(item.commute_min)}분`);
  else if (item.commute_min < 45) tags.push(`통근 ${Math.round(item.commute_min)}분`);
  if (item.hug_acc_rate_pct < 1.0) tags.push("HUG 사고율 낮음");
  else if (item.hug_acc_rate_pct < 2.0) tags.push("HUG 사고율 보통");
  if (item.burden_ratio < 0.25) tags.push("월세 부담 낮음");
  if (item.future_burden_6m_ratio < item.burden_ratio) tags.push("6개월 후 안정 예상");
  else if (item.future_burden_6m_ratio > item.burden_ratio * 1.05) tags.push("월세 상승 주의");
  if (item.deposit_mean_won < 50_000_000) tags.push("보증금 부담 낮음");
  return tags.slice(0, 3);
}

function buildSeries(rentNow: number, rentForecast: number): Area["forecastSeries"] {
  const drift = (rentForecast - rentNow) / 6;
  return Array.from({ length: 12 }, (_, i) => {
    const month = i - 5;
    const base =
      month <= 0
        ? rentNow - drift * 0.3 * -month + Math.sin(i * 1.7) * 1.5
        : rentNow + drift * month;
    return {
      m: `${month >= 0 ? "+" : ""}${month}`,
      v: Math.round(base * 10) / 10,
    };
  });
}

export function toArea(item: ApiRecommendItem, req: ApiRecommendRequest): Area {
  const rentNow = Math.round(item.rent_mean_won / 10_000);
  const futureRent = Math.round((item.future_burden_6m_ratio * YOUTH_INCOME_WON) / 10_000);
  const parts = item.region_name.split(" ");
  const district = parts.length >= 2 ? parts.slice(0, -1).join(" ") : item.region_name;

  return {
    id: item.region_id,
    name: parts[parts.length - 1] ?? item.region_name,
    district,
    rentNow,
    rentForecast: Math.max(rentNow - 5, futureRent),
    deposit: Math.round(item.deposit_mean_won / 10_000),
    commuteCost: Math.round(item.commute_min * 0.12),
    commuteMin: Math.round(item.commute_min),
    riskScore: Math.min(99, Math.round(item.hug_acc_rate_pct * 15)),
    confidence: item.confidence,
    highlights: buildHighlights(item, req.work_name),
    forecastSeries: buildSeries(rentNow, Math.max(rentNow - 5, futureRent)),
    scores: {
      housing: Math.round(Math.min(1, item.score_burden) * 100),
      transport: Math.round(Math.min(1, item.score_commute) * 100),
      safety: Math.round(Math.min(1, item.score_safety) * 100),
      vibe: Math.round(Math.min(1, item.score_future) * 100),
    },
    lat: item.lat ?? undefined,
    lng: item.lng ?? undefined,
    _raw: item,
    _req: req,
  };
}

// ── 모의 데이터 (API 불가 시 폴백) ────────────────────────────────────────────

const series = (start: number, drift: number) =>
  Array.from({ length: 12 }, (_, i) => ({
    m: `${i - 5 >= 0 ? "+" : ""}${i - 5}`,
    v: Math.round((start + (i - 5) * drift + Math.sin(i) * 1.2) * 10) / 10,
  }));

export const AREAS: Area[] = [
  {
    id: "mangwon",
    name: "망원동",
    district: "서울 마포구",
    rentNow: 58,
    rentForecast: 62,
    deposit: 2000,
    commuteCost: 7.2,
    commuteMin: 34,
    riskScore: 18,
    confidence: 92,
    highlights: ["6호선 도보 7분", "한강·시장 인접", "HUG 사고율 낮음"],
    forecastSeries: series(56, 0.6),
    scores: { housing: 82, transport: 88, safety: 91, vibe: 95 },
    lat: 37.5562,
    lng: 126.9015,
  },
  {
    id: "sungshin",
    name: "성신여대입구",
    district: "서울 성북구",
    rentNow: 52,
    rentForecast: 53,
    deposit: 1500,
    commuteCost: 6.4,
    commuteMin: 41,
    riskScore: 24,
    confidence: 88,
    highlights: ["4호선 직결", "원룸 공급 풍부", "야간 유동인구 ↑"],
    forecastSeries: series(51, 0.2),
    scores: { housing: 86, transport: 84, safety: 80, vibe: 78 },
    lat: 37.5929,
    lng: 127.0156,
  },
  {
    id: "gaehwa",
    name: "개화산역",
    district: "서울 강서구",
    rentNow: 47,
    rentForecast: 49,
    deposit: 1200,
    commuteCost: 8.8,
    commuteMin: 52,
    riskScore: 31,
    confidence: 81,
    highlights: ["보증금 부담 ↓", "신축 다세대 다수", "5호선 종점"],
    forecastSeries: series(46, 0.35),
    scores: { housing: 90, transport: 70, safety: 76, vibe: 65 },
    lat: 37.562,
    lng: 126.8077,
  },
  {
    id: "sinchon",
    name: "신촌",
    district: "서울 서대문구",
    rentNow: 65,
    rentForecast: 71,
    deposit: 2500,
    commuteCost: 6.0,
    commuteMin: 28,
    riskScore: 22,
    confidence: 90,
    highlights: ["2호선 핵심", "대학가 인프라", "월세 상승 압력"],
    forecastSeries: series(63, 1.0),
    scores: { housing: 70, transport: 92, safety: 84, vibe: 90 },
    lat: 37.5549,
    lng: 126.9363,
  },
];

export const getArea = (id: string) => AREAS.find((a) => a.id === id);
