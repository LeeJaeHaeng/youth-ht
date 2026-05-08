export interface RecommendItem {
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
  lat?: number;
  lng?: number;
}

export interface RecommendResponse {
  user_age: number;
  work_name: string;
  budget_won: number;
  commute_limit_min: number;
  candidates_after_stage1: number;
  items: RecommendItem[];
}

export interface RecommendRequest {
  age: number;
  work_lat: number;
  work_lng: number;
  work_name: string;
  budget_won: number;
  commute_limit_min: number;
  top_n?: number;
  weight_burden?: number;
  weight_commute?: number;
  weight_safety?: number;
  weight_future?: number;
}

export type RootStackParamList = {
  Home: undefined;
  Results: { response: RecommendResponse; request: RecommendRequest };
  Detail: { item: RecommendItem; request: RecommendRequest };
  Compare: { items: [RecommendItem, RecommendItem]; request: RecommendRequest };
};
