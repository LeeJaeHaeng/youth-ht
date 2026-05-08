"""ECOS 한국은행 기준금리 5년치 시계열 수집 — GRU #4 입력.

0주차 검증에서 75개월 호출 성공 확인됨. 본격 수집은 단순히 결과 저장만.
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import PROCESSED_DIR, env, get_with_retry  # noqa: E402

OUT = PROCESSED_DIR / "ecos_rate.parquet"


def main() -> int:
    key = env("ECOS_API_KEY")
    url = (
        f"https://ecos.bok.or.kr/api/StatisticSearch"
        f"/{key}/json/kr/1/1000/722Y001/M/202001/202612/0101000"
    )
    with httpx.Client() as client:
        r = get_with_retry(client, url, timeout=30)
    rows = r.json()["StatisticSearch"]["row"]
    df = pl.DataFrame(rows).with_columns(
        [
            pl.col("TIME").str.strptime(pl.Date, "%Y%m").alias("year_month"),
            pl.col("DATA_VALUE").cast(pl.Float64).alias("base_rate_pct"),
        ]
    ).select(["year_month", "base_rate_pct"])
    df.write_parquet(OUT, compression="zstd")
    print(f"[DONE] {len(df)} months → {OUT}")
    print(df.tail(5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
