"""Pydantic 요청/응답 스키마."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    age: int = Field(..., ge=19, le=39, description="청년 연령 (19~39)")
    work_lat: float
    work_lng: float
    work_name: str = Field(..., max_length=64)
    budget_won: int = Field(..., ge=200_000, le=5_000_000, description="월 예산(원)")
    commute_limit_min: int = Field(60, ge=15, le=120)
    top_n: int = Field(10, ge=1, le=20)
    # 사용자 가중치 (0~1, 합계 1.0 — 미입력 시 설계서 기본값 사용)
    weight_burden: float | None = Field(None, ge=0.0, le=1.0)
    weight_commute: float | None = Field(None, ge=0.0, le=1.0)
    weight_safety: float | None = Field(None, ge=0.0, le=1.0)
    weight_future: float | None = Field(None, ge=0.0, le=1.0)


class RecommendItem(BaseModel):
    rank: int
    region_id: str
    region_name: str
    rent_mean_won: int
    deposit_mean_won: int
    commute_min: float
    hug_acc_rate_pct: float
    burden_ratio: float
    future_burden_6m_ratio: float
    score_burden: float
    score_commute: float
    score_safety: float
    score_future: float
    total_score: float
    confidence: int
    confidence_breakdown: dict
    lat: float = 0.0
    lng: float = 0.0


class RecommendResponse(BaseModel):
    user_age: int
    work_name: str
    budget_won: int
    commute_limit_min: int
    candidates_after_stage1: int
    items: list[RecommendItem]


class ReportRequest(BaseModel):
    item: RecommendItem
    user_age: int
    work_name: str
    budget_won: int
    commute_limit_min: int


class ReportResponse(BaseModel):
    text: str
    cached: bool
    cost_krw: float


class CompareRequest(BaseModel):
    items: list[RecommendItem] = Field(..., min_length=2, max_length=5)


class CompareResponse(BaseModel):
    text: str
    cached: bool
    cost_krw: float
