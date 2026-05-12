/**
 * FastAPI 백엔드 클라이언트
 * 엔드포인트: POST /api/v1/recommend, /api/v1/recommend/report
 */

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "";

// ── 타입 ──────────────────────────────────────────────────────────────────────

export type ApiRecommendItem = {
  rank: number;
  region_id: string;
  region_name: string;
  rent_mean_won: number;
  deposit_mean_won: number;
  commute_min: number;
  hug_acc_rate_pct: number;
  burden_ratio: number;
  future_burden_6m_ratio: number;
  score_burden: number;
  score_commute: number;
  score_safety: number;
  score_future: number;
  total_score: number;
  confidence: number;
  confidence_breakdown: Record<string, number>;
  lat: number;
  lng: number;
};

export type ApiRecommendRequest = {
  age: number;
  work_lat: number;
  work_lng: number;
  work_name: string;
  budget_won: number;
  commute_limit_min: number;
  top_n?: number;
};

export type ApiRecommendResponse = {
  user_age: number;
  work_name: string;
  budget_won: number;
  commute_limit_min: number;
  candidates_after_stage1: number;
  items: ApiRecommendItem[];
};

// ── 직장 위치 프리셋 ───────────────────────────────────────────────────────────

export const OFFICE_PRESETS: Record<string, { lat: number; lng: number }> = {
  여의도: { lat: 37.5213, lng: 126.9246 },
  강남: { lat: 37.4979, lng: 127.0276 },
  판교: { lat: 37.3946, lng: 127.1111 },
  광화문: { lat: 37.5713, lng: 126.9769 },
  마곡: { lat: 37.5594, lng: 126.8308 },
  구로디지털: { lat: 37.4851, lng: 126.9014 },
  을지로: { lat: 37.5659, lng: 126.9826 },
  상암DMC: { lat: 37.5762, lng: 126.8932 },
  동대문: { lat: 37.5711, lng: 127.0097 },
  잠실: { lat: 37.5133, lng: 127.1 },
};

// ── API 호출 ──────────────────────────────────────────────────────────────────

export async function fetchRecommend(req: ApiRecommendRequest): Promise<ApiRecommendResponse> {
  const res = await fetch(`${BASE}/api/v1/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`추천 API 오류 (${res.status}): ${detail.slice(0, 200)}`);
  }
  return res.json() as Promise<ApiRecommendResponse>;
}

export async function fetchReport(
  item: ApiRecommendItem,
  req: ApiRecommendRequest,
): Promise<string> {
  const res = await fetch(`${BASE}/api/v1/recommend/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      item,
      user_age: req.age,
      work_name: req.work_name,
      budget_won: req.budget_won,
      commute_limit_min: req.commute_limit_min,
    }),
  });
  if (!res.ok) throw new Error(`리포트 API 오류 (${res.status})`);
  const data = (await res.json()) as { text: string };
  return data.text;
}

// ── 결과 캐시 (추천 → 상세 페이지 전달용) ────────────────────────────────────

export const resultCache: {
  items: ApiRecommendItem[];
  request: ApiRecommendRequest | null;
} = { items: [], request: null };

const RESULT_CACHE_KEY = "youth-ht:last-recommend-result";

export function saveResultCache(items: ApiRecommendItem[], request: ApiRecommendRequest) {
  resultCache.items = items;
  resultCache.request = request;

  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(RESULT_CACHE_KEY, JSON.stringify({ items, request }));
}

export function hydrateResultCache() {
  if (resultCache.items.length > 0 && resultCache.request) return;
  if (typeof window === "undefined") return;

  const raw = window.sessionStorage.getItem(RESULT_CACHE_KEY);
  if (!raw) return;

  try {
    const data = JSON.parse(raw) as {
      items?: ApiRecommendItem[];
      request?: ApiRecommendRequest;
    };
    if (Array.isArray(data.items) && data.request) {
      resultCache.items = data.items;
      resultCache.request = data.request;
    }
  } catch {
    window.sessionStorage.removeItem(RESULT_CACHE_KEY);
  }
}
