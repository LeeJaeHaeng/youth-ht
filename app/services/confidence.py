"""신뢰도 점수 — 룰 기반 0~100.

설계서 v2.2 §3 신뢰도 컴포넌트.

구성 요소 (총합 100점):
1. rent 표본 수 (max 30점)
   - n ≥ 50: 30, ≥ 30: 25, ≥ 10: 15, ≥ 5: 8, < 5: 0
2. HUG 데이터 최신성 (max 20점)
   - 최근 3개월: 20, 6개월: 15, 12개월: 10, 그 이상: 5
3. 통근시간 출처 (max 20점)
   - STCIS 대중교통 실측: 20
   - 카카오 Directions 자동차: 12
   - 직선거리 fallback: 5
4. 모델 분산 (max 30점)
   - LightGBM 예측 std/mean(CV) ≤ 0.05: 30, ≤ 0.10: 22, ≤ 0.20: 12, > 0.20: 5
   - 모델 미적용 시 (룰 기반만): 18 (default)

페널티:
- 데이터 불일치 (rent < deposit/100 같은 outlier): -10
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConfidenceInputs:
    rent_n: int                       # rent 표본 수
    hug_data_age_months: int          # HUG 데이터 최신성 (개월)
    commute_source: str               # "stcis" | "kakao_car" | "linear"
    model_cv: float | None = None     # 모델 예측 std/mean (없으면 None → 룰 기반)
    has_outlier: bool = False         # 데이터 일관성 위반 여부


def _score_sample(n: int) -> int:
    if n >= 50: return 30
    if n >= 30: return 25
    if n >= 10: return 15
    if n >= 5:  return 8
    return 0


def _score_hug_freshness(months: int) -> int:
    if months <= 3:  return 20
    if months <= 6:  return 15
    if months <= 12: return 10
    return 5


def _score_commute(source: str) -> int:
    return {"stcis": 20, "kakao_car": 12, "linear": 5}.get(source, 5)


def _score_model(cv: float | None) -> int:
    if cv is None:
        return 18  # 룰 기반 baseline
    if cv <= 0.05: return 30
    if cv <= 0.10: return 22
    if cv <= 0.20: return 12
    return 5


def compute_confidence(c: ConfidenceInputs) -> tuple[int, dict]:
    """신뢰도 정수 점수(0~100) + 컴포넌트 dict 반환."""
    parts = {
        "sample":   _score_sample(c.rent_n),
        "hug":      _score_hug_freshness(c.hug_data_age_months),
        "commute":  _score_commute(c.commute_source),
        "model":    _score_model(c.model_cv),
    }
    total = sum(parts.values())
    if c.has_outlier:
        parts["outlier_penalty"] = -10
        total -= 10
    total = max(0, min(100, total))
    return total, parts


if __name__ == "__main__":
    # 시연 — 4가지 신뢰도 시나리오
    cases = [
        ("이상 — 풍부한 데이터 + 정확한 모델",
         ConfidenceInputs(rent_n=80, hug_data_age_months=2, commute_source="stcis", model_cv=0.04)),
        ("실전 — 표준 데이터 + 룰 기반",
         ConfidenceInputs(rent_n=25, hug_data_age_months=5, commute_source="kakao_car", model_cv=None)),
        ("저표본 — 시골 시군구 prototype",
         ConfidenceInputs(rent_n=6, hug_data_age_months=10, commute_source="linear", model_cv=None)),
        ("이상치 포함 — 데이터 일관성 X",
         ConfidenceInputs(rent_n=40, hug_data_age_months=4, commute_source="kakao_car", model_cv=0.18, has_outlier=True)),
    ]
    for desc, inp in cases:
        score, parts = compute_confidence(inp)
        print(f"\n[{desc}] = {score}/100")
        for k, v in parts.items():
            print(f"  {k}: {v}")
