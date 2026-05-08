"""HUG Excel → 시군구 단위 위험점수 Parquet.

0주차 검증으로 확인된 구조:
- 시트 '시군구' 1개
- 행 0: 타이틀, 행 2-3: 멀티헤더 (광역/기초/사고건수/사고금액/사고율)
- 행 5+ : 데이터 (전국/수도권/지방/시도소계 + 시군구 행)

산출물: data/processed/hug_risk_by_sigungu.parquet
컬럼: sigungu_code(5자리), sido_name, sigungu_name,
      acc_count, acc_amount_won, acc_rate_pct
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collect"))
from _http import PROCESSED_DIR, RAW_DIR  # noqa: E402

XLSX = RAW_DIR / "HUG_전국보증사고현황_25년8월.xlsx"
OUT = PROCESSED_DIR / "hug_risk_by_sigungu.parquet"

# 합계 행 (시군구 단위 분석에서 제외)
SKIP_BASIC = {"소계"}


def main() -> int:
    if not XLSX.exists():
        print(f"[FAIL] {XLSX} 없음")
        return 1

    raw = pd.read_excel(XLSX, sheet_name="시군구", header=None)
    # 행 5부터 데이터, 컬럼 0=시군구코드, 1=광역, 2=기초, 3=사고건수, 4=사고금액, 5=사고율
    df = raw.iloc[5:, :].copy()
    df.columns = ["code", "sido", "basic", "acc_count", "acc_amount_won", "acc_rate_pct"]
    df = df.dropna(subset=["sido", "basic"])
    df = df[~df["basic"].isin(SKIP_BASIC)]  # 시도/광역/지방 합계 행 제외
    df = df[df["code"].notna()]  # 시군구코드 없는 합계 행 추가 제외

    # pandas mixed-type 컬럼을 미리 정리 (polars 변환 안정화)
    df["code"] = (
        pd.to_numeric(df["code"], errors="coerce")
        .astype("Int64")
        .astype(str)
        .str.zfill(5)
    )
    df["sido"] = df["sido"].astype(str)
    df["basic"] = df["basic"].astype(str)
    df["acc_count"] = pd.to_numeric(df["acc_count"], errors="coerce").astype("Int64")
    df["acc_amount_won"] = pd.to_numeric(df["acc_amount_won"], errors="coerce").astype("Int64")
    df["acc_rate_pct"] = pd.to_numeric(df["acc_rate_pct"], errors="coerce").astype("Float32")

    out = pl.from_pandas(df.reset_index(drop=True)).rename(
        {
            "code": "sigungu_code",
            "sido": "sido_name",
            "basic": "sigungu_name",
        }
    ).select(
        ["sigungu_code", "sido_name", "sigungu_name", "acc_count", "acc_amount_won", "acc_rate_pct"]
    )

    out.write_parquet(OUT, compression="zstd")
    print(f"[DONE] {len(out)} 시군구 → {OUT}")
    print(out.head(5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
