"""추천 룰 엔진 — Stage 1 필터 + Stage 2 점수 + Top N.

설계서 v2.2 §3 추천 엔진 설계.

Stage 1 (필터): 하드 컷
  - commute_min ≤ user.commute_limit_min
  - rent_mean ≤ user.budget_won × 1.10  (10% 여유)
  - hug_acc_rate ≤ 5.0%   (안심 컷)
  - 표본 부족 (rent_n < 5) 제외

Stage 2 (가중치 점수, 0~100):
  - 부담률 점수    (w=0.40): (1 - rent_mean / budget_won) clip [0,1]
  - 통근 점수     (w=0.30): (1 - commute_min / commute_limit_min) clip [0,1]
  - 안전 점수     (w=0.20): (1 - hug_acc_rate / 5.0) clip [0,1]
  - 미래변화 점수  (w=0.10): (1 - max(future_burden_6m - burden_now, 0) / 0.10) clip [0,1]

신뢰도 별도 계산 (services/confidence.py).

산출:
  list[Recommendation] (rank, region, scores, total_score)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(slots=True)
class UserQuery:
    age: int
    work_lat: float
    work_lng: float
    work_name: str
    budget_won: int
    commute_limit_min: int
    weight_burden: float | None = None
    weight_commute: float | None = None
    weight_safety: float | None = None
    weight_future: float | None = None


@dataclass(slots=True)
class RegionFeature:
    """추천 평가 입력 — 시군구 또는 격자 단위."""
    region_id: str          # sigungu_code 또는 grid_id
    region_name: str
    rent_mean_won: int
    deposit_mean_won: int
    rent_n: int             # 표본 수 (신뢰도 계산용)
    commute_min: float
    hug_acc_rate_pct: float
    burden_now: float       # H+T 통합 부담률 (rent + utility)/(income) 0~1
    future_burden_6m: float # GRU 예측 6개월 후 (없으면 burden_now)
    lat: float = 0.0        # 시군구 centroid 위도 (지도 마커용)
    lng: float = 0.0        # 시군구 centroid 경도
    extras: dict = field(default_factory=dict)


@dataclass(slots=True)
class Recommendation:
    rank: int
    region: RegionFeature
    score_burden: float
    score_commute: float
    score_safety: float
    score_future: float
    total_score: float       # 0~100

    def as_dict(self) -> dict:
        r = self.region
        return {
            "rank": self.rank,
            "region_id": r.region_id,
            "region_name": r.region_name,
            "rent_mean_won": r.rent_mean_won,
            "deposit_mean_won": r.deposit_mean_won,
            "commute_min": round(r.commute_min, 1),
            "hug_acc_rate_pct": round(r.hug_acc_rate_pct, 2),
            "burden_ratio": round(r.burden_now, 3),
            "future_burden_6m_ratio": round(r.future_burden_6m, 3),
            "score_burden": round(self.score_burden, 3),
            "score_commute": round(self.score_commute, 3),
            "score_safety": round(self.score_safety, 3),
            "score_future": round(self.score_future, 3),
            "total_score": round(self.total_score, 1),
            "lat": r.lat,
            "lng": r.lng,
        }


# ──────────────────────────────────────────────────────────
# Stage 1 — 하드 필터
# ──────────────────────────────────────────────────────────
HUG_SAFE_THRESHOLD = 5.0  # %
BUDGET_OVERRUN_TOLERANCE = 1.10  # 10% 여유 허용
MIN_RENT_SAMPLE = 5


def stage1_filter(user: UserQuery, regions: Iterable[RegionFeature]) -> list[RegionFeature]:
    out: list[RegionFeature] = []
    for r in regions:
        if r.rent_n < MIN_RENT_SAMPLE:
            continue
        if r.commute_min > user.commute_limit_min:
            continue
        if r.rent_mean_won > user.budget_won * BUDGET_OVERRUN_TOLERANCE:
            continue
        if r.hug_acc_rate_pct > HUG_SAFE_THRESHOLD:
            continue
        out.append(r)
    return out


# ──────────────────────────────────────────────────────────
# Stage 2 — 가중치 점수
# ──────────────────────────────────────────────────────────
WEIGHTS = {"burden": 0.40, "commute": 0.30, "safety": 0.20, "future": 0.10}
HUG_SCORE_DENOM = 5.0   # %
FUTURE_BURDEN_TOLERATE = 0.10  # +10%p 까지 허용


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _effective_weights(user: UserQuery) -> dict[str, float]:
    """사용자 가중치 입력 시 정규화, 없으면 설계서 기본값."""
    wb = user.weight_burden
    wc = user.weight_commute
    ws = user.weight_safety
    wf = user.weight_future
    if all(v is not None for v in (wb, wc, ws, wf)):
        total = (wb or 0) + (wc or 0) + (ws or 0) + (wf or 0)
        if total > 0:
            return {
                "burden": (wb or 0) / total,
                "commute": (wc or 0) / total,
                "safety": (ws or 0) / total,
                "future": (wf or 0) / total,
            }
    return WEIGHTS


def score_region(user: UserQuery, r: RegionFeature) -> tuple[float, float, float, float, float]:
    """단일 region의 4 sub-score + total(0~100)."""
    s_burden = _clip01(1.0 - r.rent_mean_won / max(user.budget_won, 1))
    s_commute = _clip01(1.0 - r.commute_min / max(user.commute_limit_min, 1))
    s_safety = _clip01(1.0 - r.hug_acc_rate_pct / HUG_SCORE_DENOM)
    delta = max(r.future_burden_6m - r.burden_now, 0.0)
    s_future = _clip01(1.0 - delta / FUTURE_BURDEN_TOLERATE)
    w = _effective_weights(user)
    total = (
        w["burden"] * s_burden
        + w["commute"] * s_commute
        + w["safety"] * s_safety
        + w["future"] * s_future
    ) * 100.0
    return s_burden, s_commute, s_safety, s_future, total


def stage2_score(user: UserQuery, candidates: Iterable[RegionFeature]) -> list[Recommendation]:
    scored: list[Recommendation] = []
    for r in candidates:
        sb, sc, ss, sf, total = score_region(user, r)
        scored.append(Recommendation(
            rank=0,  # 임시 — 정렬 후 배정
            region=r,
            score_burden=sb,
            score_commute=sc,
            score_safety=ss,
            score_future=sf,
            total_score=total,
        ))
    scored.sort(key=lambda x: -x.total_score)
    for i, rec in enumerate(scored, 1):
        rec.rank = i
    return scored


# ──────────────────────────────────────────────────────────
# 통합 — Top N 추천
# ──────────────────────────────────────────────────────────
def recommend(user: UserQuery, regions: Iterable[RegionFeature], top_n: int = 10) -> list[Recommendation]:
    candidates = stage1_filter(user, regions)
    if not candidates:
        return []
    scored = stage2_score(user, candidates)
    return scored[:top_n]


if __name__ == "__main__":
    # Mock prototype — 실제 features 빌더 대체 예정
    user = UserQuery(
        age=25, work_lat=37.498, work_lng=127.028, work_name="강남역",
        budget_won=800_000, commute_limit_min=40,
    )
    mocks = [
        RegionFeature("11620", "서울 관악구", 710_000, 90_000_000, 320, 28, 2.7, 0.32, 0.34),
        RegionFeature("11590", "서울 동작구", 780_000, 110_000_000, 280, 25, 1.8, 0.36, 0.36),
        RegionFeature("11650", "서울 서초구", 1_200_000, 200_000_000, 500, 18, 0.9, 0.55, 0.56),  # 예산 초과 → Stage1 컷
        RegionFeature("11305", "서울 강북구", 580_000, 60_000_000, 150, 38, 4.2, 0.28, 0.31),
        RegionFeature("41135", "경기 성남시 분당구", 850_000, 130_000_000, 280, 35, 1.2, 0.40, 0.42),  # 예산 초과(허용 내)
        RegionFeature("11710", "서울 송파구", 950_000, 150_000_000, 350, 22, 1.5, 0.45, 0.47),  # 예산 초과
        RegionFeature("11215", "서울 광진구", 720_000, 95_000_000, 220, 30, 3.5, 0.34, 0.35),
    ]
    recs = recommend(user, mocks, top_n=5)
    print(f"Top {len(recs)} 추천 (Stage 1 통과 후 정렬):")
    for rec in recs:
        d = rec.as_dict()
        print(
            f"  #{d['rank']:2d} {d['region_name']:20s} "
            f"월세 {d['rent_mean_won']:>9,}원 통근 {d['commute_min']}분 "
            f"HUG {d['hug_acc_rate_pct']:.1f}% → 총점 {d['total_score']}/100 "
            f"(burden={d['score_burden']}, commute={d['score_commute']}, safety={d['score_safety']}, future={d['score_future']})"
        )
