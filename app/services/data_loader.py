"""실제 processed parquet 기반 RegionFeature 로더.

최초 호출 시 파일 존재 여부 확인 → 실제 데이터 사용, 없으면 mock 반환.

데이터 흐름:
  sigungu_monthly_features.parquet → 최신 월 rent/deposit/count
  kakao_od.parquet                  → sigungu × cluster commute_min
  docs/work_clusters.csv            → cluster lat/lng
  hug_risk_by_sigungu.parquet       → sigungu hug_acc_rate_pct
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import polars as pl

from app.services.recommender import RegionFeature

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"

YOUTH_MEDIAN_INCOME_WON = 2_500_000  # KOSIS 수집 전 고정 (청년 중위소득 월 250만원)
MIN_TRANSACTION_COUNT = 3  # 표본 부족 컷


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(max(a, 0.0)))


@lru_cache(maxsize=1)
def _load_clusters() -> list[dict]:
    csv = DOCS / "work_clusters.csv"
    if not csv.exists():
        return []
    return pl.read_csv(csv).to_dicts()


@lru_cache(maxsize=1)
def _load_od() -> pl.DataFrame | None:
    p = PROCESSED / "kakao_od.parquet"
    if not p.exists():
        return None
    return pl.read_parquet(p)


@lru_cache(maxsize=1)
def _load_hug() -> dict[str, float]:
    p = PROCESSED / "hug_risk_by_sigungu.parquet"
    if not p.exists():
        return {}
    df = pl.read_parquet(p).select(["sigungu_code", "acc_rate_pct"])
    return dict(zip(df["sigungu_code"].to_list(), df["acc_rate_pct"].to_list()))


@lru_cache(maxsize=1)
def _load_gru_predictions() -> dict[str, float]:
    """gru_predictions.parquet → {sigungu_code: pred_rent_norm_6m}.

    GRU 학습 완료 전: 빈 dict (future_burden_6m = burden_now 그대로).
    """
    p = PROCESSED / "gru_predictions.parquet"
    if not p.exists():
        return {}
    df = pl.read_parquet(p)
    # group_by 결과가 List[str]로 저장된 경우 첫 원소 추출
    if df.schema.get("sigungu_code") == pl.List(pl.String):
        df = df.with_columns(pl.col("sigungu_code").list.first())
    df6 = df.filter(pl.col("horizon_months") == 6)
    return dict(zip(df6["sigungu_code"].to_list(), df6["pred_rent_norm"].to_list()))


@lru_cache(maxsize=1)
def _load_sigungu_centroid() -> tuple[dict[str, str], dict[str, float], dict[str, float]]:
    """sigungu_centroid.parquet → (names, lats, lngs)."""
    p = PROCESSED / "sigungu_centroid.parquet"
    if not p.exists():
        return {}, {}, {}
    df = pl.read_parquet(p)
    name_col = next((c for c in ("name", "sigungu_name") if c in df.columns), None)
    codes = df["sigungu_code"].to_list()
    names = dict(zip(codes, df[name_col].to_list())) if name_col else {}
    lats = dict(zip(codes, df["lat"].to_list())) if "lat" in df.columns else {}
    lngs = dict(zip(codes, df["lng"].to_list())) if "lng" in df.columns else {}
    return names, lats, lngs


def _load_sigungu_names() -> dict[str, str]:
    return _load_sigungu_centroid()[0]


def nearest_cluster_id(work_lat: float, work_lng: float) -> int | None:
    clusters = _load_clusters()
    if not clusters:
        return None
    best = min(clusters, key=lambda c: _haversine_km(
        work_lat, work_lng, float(c["lat"]), float(c["lng"])
    ))
    return int(best["cluster_id"])


def load_region_features(work_lat: float, work_lng: float) -> list[RegionFeature] | None:
    """실제 데이터 기반 RegionFeature 목록 반환. 데이터 불충분 시 None.

    None이면 호출자가 mock으로 fallback.
    """
    feat_path = PROCESSED / "sigungu_monthly_features.parquet"
    if not feat_path.exists():
        return None

    feat = pl.read_parquet(feat_path)
    if feat["sigungu_code"].n_unique() < 3:
        return None  # 시군구 3개 미만 → mock fallback

    # 최신 월 데이터만 사용 (year_month 컬럼이 Date 타입)
    latest = feat["year_month"].max()
    feat = feat.filter(pl.col("year_month") == latest)

    # building_type 별로 평균 집계 (apt + villa 통합)
    feat = feat.group_by("sigungu_code").agg([
        pl.col("rent_mean_won").mean().alias("rent_mean_won"),
        pl.col("deposit_mean_won").mean().alias("deposit_mean_won"),
        pl.col("transaction_count").sum().alias("transaction_count"),
        pl.col("area_mean_m2").mean().alias("area_mean_m2"),
    ])

    # HUG 사고율 join
    hug = _load_hug()

    # OD 매트릭스에서 통근시간 lookup
    od = _load_od()
    cluster_id = nearest_cluster_id(work_lat, work_lng)
    commute_map: dict[str, float] = {}
    if od is not None and cluster_id is not None:
        od_cluster = od.filter(pl.col("cluster_id") == cluster_id)
        commute_map = dict(zip(
            od_cluster["sigungu_code"].to_list(),
            od_cluster["commute_min"].to_list(),
        ))

    sg_names, sg_lats, sg_lngs = _load_sigungu_centroid()
    gru_preds = _load_gru_predictions()

    # rent 정규화 역변환용 통계 (gru_predictions는 normalized 값)
    rent_mean_all = float(feat["rent_mean_won"].mean() or 1)
    rent_std_all = float(feat["rent_mean_won"].std() or 1)

    features: list[RegionFeature] = []

    for row in feat.to_dicts():
        sg = row["sigungu_code"]
        rent = int(row["rent_mean_won"] or 0)
        deposit = int(row["deposit_mean_won"] or 0)
        count = int(row["transaction_count"] or 0)
        if count < MIN_TRANSACTION_COUNT or rent <= 0:
            continue

        commute = commute_map.get(sg, 9999.0)
        hug_rate = hug.get(sg, 0.0)
        burden = rent / YOUTH_MEDIAN_INCOME_WON

        # GRU 6개월 후 예측 (있으면 사용, 없으면 현재값)
        if sg in gru_preds:
            pred_rent = gru_preds[sg] * rent_std_all + rent_mean_all
            future_burden = max(0.0, pred_rent / YOUTH_MEDIAN_INCOME_WON)
        else:
            future_burden = burden

        features.append(RegionFeature(
            region_id=sg,
            region_name=sg_names.get(sg, sg),
            rent_mean_won=rent,
            deposit_mean_won=deposit,
            rent_n=count,
            commute_min=commute,
            hug_acc_rate_pct=hug_rate,
            burden_now=round(burden, 3),
            future_burden_6m=round(future_burden, 3),
            lat=sg_lats.get(sg, 0.0),
            lng=sg_lngs.get(sg, 0.0),
        ))

    return features if features else None
