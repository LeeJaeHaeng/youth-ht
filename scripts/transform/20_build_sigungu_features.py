"""시군구 단위 통합 features 빌더 — LightGBM 학습 prototype용.

격자(SGIS) 매핑 전, 시군구(LAWD_CD 5자리) 단위로 다음을 통합:
- 아파트·연립다세대 전월세 (월별 평균/표준편차/거래량)
- HUG 사고율 (시점은 단일, broadcast)
- ECOS 기준금리 (월별, broadcast)

산출: data/processed/sigungu_monthly_features.parquet
컬럼: sigungu_code, year_month,
      rent_mean_won, rent_std_won, deposit_mean_won, transaction_count,
      area_mean_m2, building_year_mean,
      base_rate_pct, hug_acc_rate_pct,
      building_type (apt/villa)

격자 단위로 진행할 때는 grid_id로 group_by 키 변경 + SGIS Shapefile 매핑 추가.
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collect"))
from _http import PROCESSED_DIR  # noqa: E402

APT = PROCESSED_DIR / "apt_rent_history.parquet"
VILLA = PROCESSED_DIR / "villa_rent_history.parquet"
ECOS = PROCESSED_DIR / "ecos_rate.parquet"
HUG = PROCESSED_DIR / "hug_risk_by_sigungu.parquet"
OUT = PROCESSED_DIR / "sigungu_monthly_features.parquet"


def aggregate_rent(path: Path, btype: str) -> pl.DataFrame:
    """실거래 데이터 → 시군구 × 월 평균/표준/거래량 집계."""
    if not path.exists():
        print(f"[SKIP] {path} 없음")
        return pl.DataFrame()

    df = pl.read_parquet(path)
    print(f"  {path.name}: {len(df):,}행")

    # year_month 빌드
    if "deal_ymd" in df.columns:
        df = df.with_columns(
            pl.col("deal_ymd").str.strptime(pl.Date, "%Y%m").alias("year_month")
        )
    else:
        # dealYear/dealMonth 폴백
        df = df.with_columns(
            (pl.col("dealYear").cast(pl.Utf8) + pl.col("dealMonth").cast(pl.Utf8).str.zfill(2))
            .str.strptime(pl.Date, "%Y%m")
            .alias("year_month")
        )

    # 청년 평형(85m² 이하) + 월세 건만 (전세=monthlyRent 0 제외)
    # API 반환값: monthlyRent/deposit 단위 = 만원 → * 10_000 = 원
    df = df.filter(
        (pl.col("excluUseAr") <= 85)
        & (pl.col("monthlyRent") > 0)
        & (pl.col("monthlyRent").is_between(5, 1000))  # 5만~1,000만원 (이상치 제거)
    )

    return (
        df.group_by(["lawd_cd", "year_month"])
        .agg(
            [
                (pl.col("monthlyRent").mean() * 10_000).alias("rent_mean_won"),
                (pl.col("monthlyRent").std() * 10_000).alias("rent_std_won"),
                (pl.col("deposit").mean() * 10_000).alias("deposit_mean_won"),
                pl.col("monthlyRent").count().alias("transaction_count"),
                pl.col("excluUseAr").mean().alias("area_mean_m2"),
                pl.col("buildYear").cast(pl.Float64).mean().alias("building_year_mean"),
            ]
        )
        .with_columns(pl.lit(btype).alias("building_type"))
        .rename({"lawd_cd": "sigungu_code"})
    )


def main() -> int:
    apt_agg = aggregate_rent(APT, "apt")
    villa_agg = aggregate_rent(VILLA, "villa")

    if apt_agg.is_empty() and villa_agg.is_empty():
        print("[FAIL] 실거래가 데이터 없음 — 1주차 본 수집 후 재실행")
        return 1

    rent = pl.concat([df for df in [apt_agg, villa_agg] if not df.is_empty()])
    print(f"\nrent 집계: {len(rent):,}행")

    # ECOS 금리 broadcast
    if ECOS.exists():
        ecos = pl.read_parquet(ECOS).rename({"base_rate_pct": "base_rate_pct"})
        rent = rent.join(ecos, on="year_month", how="left")
        print(f"ECOS join 후: {len(rent):,}행 (금리 결손 {rent['base_rate_pct'].null_count()}건)")
    else:
        print("[WARN] ECOS 없음 — base_rate_pct 결손")

    # HUG 사고율 broadcast (시점 단일이므로 모든 월에 동일)
    if HUG.exists():
        hug = pl.read_parquet(HUG).select(
            ["sigungu_code", pl.col("acc_rate_pct").alias("hug_acc_rate_pct")]
        )
        rent = rent.join(hug, on="sigungu_code", how="left")
        print(f"HUG join 후: {len(rent):,}행")

    # 정렬 + 저장
    rent = rent.sort(["sigungu_code", "year_month", "building_type"])
    rent.write_parquet(OUT, compression="zstd")
    print(f"\n[DONE] {len(rent):,}행 → {OUT}")
    print("샘플:")
    print(rent.head(5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
