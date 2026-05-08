"""LightGBM rent 모델 학습 데이터 prep — 시군구 features에서 X/y 분리.

설계서 §모델 학습 (LightGBM rent). 0주차/1주차 검증 통과 데이터로 prototype.
실제 본 학습은 2주차에 격자 단위 features로 재구성.

산출:
  data/processed/lgbm_train.parquet — X 피처 + y(monthly_rent_won)
  data/processed/lgbm_train_meta.json — 컬럼 명세
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collect"))
from _http import PROCESSED_DIR  # noqa: E402

FEATURES = PROCESSED_DIR / "sigungu_monthly_features.parquet"
OUT_DATA = PROCESSED_DIR / "lgbm_train.parquet"
OUT_META = PROCESSED_DIR / "lgbm_train_meta.json"


FEATURE_COLS = [
    "deposit_mean_won",
    "transaction_count",
    "area_mean_m2",
    "building_year_mean",
    "base_rate_pct",
    "hug_acc_rate_pct",
    "year",
    "month",
    "sigungu_code_int",
    "is_villa",
]
TARGET_COL = "rent_mean_won"


def main() -> int:
    if not FEATURES.exists():
        print(f"[FAIL] {FEATURES} 없음 — 20_build_sigungu_features.py 먼저 실행")
        return 1

    df = pl.read_parquet(FEATURES)
    print(f"입력: {len(df):,}행, 컬럼 {df.columns}")

    # 결측 타겟 제거
    df = df.filter(pl.col(TARGET_COL).is_not_null())

    # 파생 피처
    df = df.with_columns(
        [
            pl.col("year_month").dt.year().alias("year"),
            pl.col("year_month").dt.month().alias("month"),
            pl.col("sigungu_code").cast(pl.Int64).alias("sigungu_code_int"),
            (pl.col("building_type") == "villa").cast(pl.Int8).alias("is_villa"),
        ]
    )

    out = df.select([*FEATURE_COLS, TARGET_COL]).drop_nulls()
    print(f"학습 데이터: {len(out):,}행 (결측 제거 후)")

    out.write_parquet(OUT_DATA, compression="zstd")
    OUT_META.write_text(
        json.dumps(
            {
                "feature_cols": FEATURE_COLS,
                "target_col": TARGET_COL,
                "n_rows": len(out),
                "categorical": ["sigungu_code_int", "is_villa", "month"],
                "note": "시군구 단위 prototype — 격자 단위 본 학습은 SGIS Shapefile 확보 후 진행",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[DONE] → {OUT_DATA}, {OUT_META}")
    print(out.head(3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
