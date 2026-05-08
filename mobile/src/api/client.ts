import type { RecommendItem, RecommendRequest, RecommendResponse } from '../types';

// 로컬 개발: http://localhost:8000, 배포: 실제 URL 변경
const BASE_URL = 'http://localhost:8000/api/v1';

async function apiFetch<T>(path: string, body?: object): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: body ? 'POST' : 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json() as Promise<T>;
}

export async function recommend(req: RecommendRequest): Promise<RecommendResponse> {
  return apiFetch<RecommendResponse>('/recommend', req);
}

export async function getReport(item: RecommendItem, req: RecommendRequest): Promise<string> {
  const body = {
    user_age: req.age,
    budget_won: req.budget_won,
    commute_limit_min: req.commute_limit_min,
    work_name: req.work_name,
    item,
  };
  const res = await apiFetch<{ text: string }>('/recommend/report', body);
  return res.text;
}

export async function getCompare(items: [RecommendItem, RecommendItem], req: RecommendRequest): Promise<string> {
  const body = {
    user_age: req.age,
    budget_won: req.budget_won,
    commute_limit_min: req.commute_limit_min,
    work_name: req.work_name,
    items,
  };
  const res = await apiFetch<{ text: string }>('/recommend/compare', body);
  return res.text;
}

export async function healthz(): Promise<boolean> {
  try {
    const res = await apiFetch<{ status: string }>('/healthz');
    return res.status === 'ok';
  } catch {
    return false;
  }
}
