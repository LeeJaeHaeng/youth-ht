"""추천 라우터 — Top N + Gemini 자연어 리포트."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    CompareRequest, CompareResponse, RecommendItem, RecommendRequest,
    RecommendResponse, ReportRequest, ReportResponse,
)
from app.services import llm
from app.services.confidence import ConfidenceInputs, compute_confidence
from app.services.data_loader import load_region_features
from app.services.recommender import RegionFeature, UserQuery, recommend, stage1_filter

router = APIRouter()

_MOCK_REGIONS: list[RegionFeature] = [
    RegionFeature("11620", "서울 관악구", 710_000, 90_000_000, 320, 28, 2.7, 0.32, 0.34),
    RegionFeature("11590", "서울 동작구", 780_000, 110_000_000, 280, 25, 1.8, 0.36, 0.36),
    RegionFeature("11305", "서울 강북구", 580_000, 60_000_000, 150, 38, 4.2, 0.28, 0.31),
    RegionFeature("11215", "서울 광진구", 720_000, 95_000_000, 220, 30, 3.5, 0.34, 0.35),
    RegionFeature("11650", "서울 서초구", 1_200_000, 200_000_000, 500, 18, 0.9, 0.55, 0.56),
    RegionFeature("11710", "서울 송파구", 950_000, 150_000_000, 350, 22, 1.5, 0.45, 0.47),
    RegionFeature("11440", "서울 마포구", 880_000, 130_000_000, 260, 32, 2.0, 0.41, 0.43),
    RegionFeature("11680", "서울 강남구", 1_350_000, 240_000_000, 480, 12, 0.8, 0.62, 0.63),
    RegionFeature("41135", "경기 성남시 분당구", 850_000, 130_000_000, 280, 35, 1.2, 0.40, 0.42),
    RegionFeature("11380", "서울 은평구", 690_000, 80_000_000, 180, 42, 3.0, 0.31, 0.33),
]


def _get_region_features(work_lat: float, work_lng: float) -> tuple[list[RegionFeature], bool]:
    """실제 parquet 로드 시도 → 실패 시 mock 반환. (regions, is_mock)"""
    real = load_region_features(work_lat, work_lng)
    if real:
        return real, False
    return _MOCK_REGIONS, True


def _confidence_for(r: RegionFeature) -> tuple[int, dict]:
    return compute_confidence(ConfidenceInputs(
        rent_n=r.rent_n,
        hug_data_age_months=4,            # HUG 25년 8월 → 26년 5월 ~ 9개월
        commute_source="kakao_car",        # 현재 prototype은 자동차
        model_cv=None,                     # 룰 기반 baseline
    ))


@router.post("/recommend", response_model=RecommendResponse)
def post_recommend(req: RecommendRequest) -> RecommendResponse:
    user = UserQuery(
        age=req.age, work_lat=req.work_lat, work_lng=req.work_lng,
        work_name=req.work_name, budget_won=req.budget_won,
        commute_limit_min=req.commute_limit_min,
        weight_burden=req.weight_burden,
        weight_commute=req.weight_commute,
        weight_safety=req.weight_safety,
        weight_future=req.weight_future,
    )
    regions, is_mock = _get_region_features(req.work_lat, req.work_lng)
    survivors = stage1_filter(user, regions)
    recs = recommend(user, regions, top_n=req.top_n)

    items: list[RecommendItem] = []
    for rec in recs:
        conf, breakdown = _confidence_for(rec.region)
        d = rec.as_dict()
        items.append(RecommendItem(**d, confidence=conf, confidence_breakdown=breakdown))

    return RecommendResponse(
        user_age=req.age,
        work_name=req.work_name,
        budget_won=req.budget_won,
        commute_limit_min=req.commute_limit_min,
        candidates_after_stage1=len(survivors),
        items=items,
    )


@router.post("/recommend/report", response_model=ReportResponse)
def post_report(req: ReportRequest) -> ReportResponse:
    rec_dict = {
        "user_age": req.user_age,
        "user_budget_won": req.budget_won,
        "commute_limit_min": req.commute_limit_min,
        "work_name": req.work_name,
        "rank": req.item.rank,
        "region_name": req.item.region_name,
        "rent_mean_won": req.item.rent_mean_won,
        "deposit_mean_won": req.item.deposit_mean_won,
        "commute_min": req.item.commute_min,
        "hug_acc_rate_pct": req.item.hug_acc_rate_pct,
        "burden_ratio": req.item.burden_ratio,
        "future_burden_6m_ratio": req.item.future_burden_6m_ratio,
        "confidence": req.item.confidence,
    }
    prompt = llm.render_recommendation_report(rec_dict)
    try:
        resp = llm.chat(prompt)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return ReportResponse(text=resp.text, cached=resp.cached, cost_krw=round(resp.cost_krw, 4))


@router.post("/recommend/compare", response_model=CompareResponse)
def post_compare(req: CompareRequest) -> CompareResponse:
    items_dict = [{
        "region_name": it.region_name,
        "rent_mean_won": it.rent_mean_won,
        "commute_min": it.commute_min,
        "hug_acc_rate_pct": it.hug_acc_rate_pct,
        "confidence": it.confidence,
    } for it in req.items]
    prompt = llm.render_comparison_report(items_dict)
    try:
        resp = llm.chat(prompt)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return CompareResponse(text=resp.text, cached=resp.cached, cost_krw=round(resp.cost_krw, 4))
