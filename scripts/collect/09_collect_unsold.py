"""R-ONE 미분양 통계 수집기 (GRU #6 입력 — 시도별 월간 미분양 호수).

한국부동산원 R-ONE SttsApiTblData API
- STATBL_ID: T237973129847263 (미분양현황 월별)
- 시도 + 시군구 단위 데이터 포함
- 날짜 필터 없이 전체 조회 후 2020-01 ~ 현재까지 필터링

산출: data/processed/unsold_by_sido.parquet
컬럼: sido_code(str 2자리), year_month(YYYYMM str), unsold_units(int)
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import polars as pl
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
OUT = PROCESSED / "unsold_by_sido.parquet"

DATA_URL = "https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do"

# 시도명 → 2자리 코드
SIDO_NAME_TO_CODE: dict[str, str] = {
    "서울": "11", "부산": "26", "대구": "27", "인천": "28",
    "광주": "29", "대전": "30", "울산": "31", "세종": "36",
    "경기": "41", "강원": "42", "충북": "43", "충남": "44",
    "전북": "45", "전남": "46", "경북": "47", "경남": "48", "제주": "50",
    # 특별자치도 별칭
    "전북특별자치도": "45", "강원특별자치도": "42",
}


def fetch_all(key: str, statbl_id: str) -> list[dict]:
    """전체 페이지 수집 (날짜 필터 없음)."""
    rows: list[dict] = []
    page = 1
    while True:
        params = {
            "KEY": key, "Type": "json",
            "pIndex": str(page), "pSize": "1000",
            "STATBL_ID": statbl_id, "DTACYCLE_CD": "MM",
        }
        r = requests.get(DATA_URL, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()

        try:
            total = data["SttsApiTblData"][0]["head"][0]["list_total_count"]
            page_rows = data["SttsApiTblData"][1]["row"]
        except (KeyError, IndexError):
            print(f"  page {page}: 응답 구조 이상 → 중단")
            break

        rows.extend(page_rows)
        fetched = len(rows)
        print(f"  page {page}: +{len(page_rows)}행 (누적 {fetched}/{total})")

        if fetched >= total or len(page_rows) < 1000:
            break
        page += 1
        time.sleep(0.3)

    return rows


def process(rows: list[dict]) -> pl.DataFrame:
    """원본 rows → sido_code × year_month × unsold_units."""
    df = pl.DataFrame(rows)

    # 필요 컬럼만
    df = df.select([
        pl.col("WRTTIME_IDTFR_ID").alias("year_month"),
        pl.col("CLS_FULLNM").alias("cls_fullnm"),
        pl.col("DTA_VAL").alias("unsold_raw"),
    ])

    # "계" 행만 (시도 합계)
    df = df.filter(pl.col("cls_fullnm").str.ends_with(">계"))

    # 시도명 추출: "강원>계" → "강원"
    df = df.with_columns(
        pl.col("cls_fullnm").str.split(">").list.first().alias("sido_name")
    )

    # 시도 코드 매핑
    sido_map = SIDO_NAME_TO_CODE
    df = df.with_columns(
        pl.col("sido_name").map_elements(
            lambda x: sido_map.get(x), return_dtype=pl.String
        ).alias("sido_code")
    )
    df = df.filter(pl.col("sido_code").is_not_null())

    # 2020-01 이후만
    df = df.filter(pl.col("year_month") >= "202001")

    # unsold_units 숫자 변환
    df = df.with_columns(
        pl.col("unsold_raw").cast(pl.Float64).fill_null(0).cast(pl.Int64).alias("unsold_units")
    )

    return df.select(["sido_code", "year_month", "unsold_units"]).sort(["sido_code", "year_month"])


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    key = os.getenv("REB_API_KEY", "").strip()
    statbl_id = os.getenv("REB_UNSOLD_STATBL_ID", "T237973129847263").strip()

    if not key:
        print("[FAIL] .env REB_API_KEY 없음")
        return 1

    print(f"[R-ONE] 미분양 전체 수집 시작 (STATBL_ID={statbl_id})")
    rows = fetch_all(key, statbl_id)
    print(f"[INFO] 수집 완료: {len(rows):,}행")

    if not rows:
        print("[FAIL] 데이터 없음")
        return 1

    df = process(rows)
    print(f"[INFO] 처리 완료: {len(df):,}행, 시도 {df['sido_code'].n_unique()}개, "
          f"월 {df['year_month'].n_unique()}개")
    print(f"  기간: {df['year_month'].min()} ~ {df['year_month'].max()}")
    print(df.head(5))

    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUT, compression="zstd")
    print(f"[DONE] → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
