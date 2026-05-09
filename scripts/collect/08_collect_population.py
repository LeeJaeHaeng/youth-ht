"""행안부 주민등록인구 수집기 (GRU #5 입력 — 시도별 연간 인구 변화율).

행정안전부 RegistrationPopulationByRegion API
- URL: https://apis.data.go.kr/1741000/RegistrationPopulationByRegion/getRegistrationPopulationByRegion
- 키: DATA_GO_KR_KEY_DECODING (URL decoded)
- 응답: 17 시도 × ~18년 = ~306행 (wrttimeid=연도, regi=시도명)

산출: data/processed/pop_change_by_sido.parquet
컬럼: sido_code(str 2자리), year(int), population(int), pop_change_rate(float)
"""
from __future__ import annotations

import os
from pathlib import Path

import polars as pl
import requests

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
OUT = PROCESSED / "pop_change_by_sido.parquet"

API_URL = "https://apis.data.go.kr/1741000/RegistrationPopulationByRegion/getRegistrationPopulationByRegion"

SIDO_NAME_TO_CODE: dict[str, str] = {
    "서울": "11", "부산": "26", "대구": "27", "인천": "28",
    "광주": "29", "대전": "30", "울산": "31", "세종": "36",
    "경기": "41", "강원": "42", "충북": "43", "충남": "44",
    "전북": "45", "전남": "46", "경북": "47", "경남": "48", "제주": "50",
    "강원특별자치도": "42", "전북특별자치도": "45",
}


def fetch_all(key: str) -> list[dict]:
    """전체 행 수집 (pSize=1000, 단일 페이지로 충분)."""
    params = {
        "serviceKey": key,
        "type": "json",
        "pageNo": "1",
        "numOfRows": "1000",
    }
    r = requests.get(API_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    # 행안부 자체 래핑 구조: {RegistrationPopulationByRegion: [{head:...}, {row:[...]}]}
    try:
        if "RegistrationPopulationByRegion" in data:
            sections = data["RegistrationPopulationByRegion"]
            for sec in sections:
                if "row" in sec:
                    return sec["row"]
        # 공공데이터포털 표준 응답 구조
        body = data["response"]["body"]
        items = body["items"]["item"]
        if isinstance(items, dict):
            items = [items]
        return items
    except (KeyError, TypeError) as e:
        raise RuntimeError(f"응답 파싱 실패: {e}\n{str(data)[:300]}")


def process(rows: list[dict]) -> pl.DataFrame:
    """원본 rows → sido_code × year × pop_change_rate."""
    df = pl.DataFrame(rows)
    print(f"  원본 컬럼: {df.columns}")

    # 전국 "계" 제외, 시도만
    df = df.filter(pl.col("regi") != "계")

    # sido_code 매핑
    sido_map = SIDO_NAME_TO_CODE
    df = df.with_columns(
        pl.col("regi").map_elements(
            lambda x: sido_map.get(x), return_dtype=pl.String
        ).alias("sido_code")
    )
    df = df.filter(pl.col("sido_code").is_not_null())

    # year, population 변환
    df = df.with_columns([
        pl.col("wrttimeid").cast(pl.Int64).alias("year"),
        pl.col("population_tot").cast(pl.Float64).fill_null(0).cast(pl.Int64).alias("population"),
    ])

    # 2019년 이후 (변화율 계산을 위해 2018도 포함)
    df = df.filter(pl.col("year") >= 2018).sort(["sido_code", "year"])

    # YoY 변화율: (현재 - 전년) / 전년 * 100
    df = df.with_columns(
        pl.col("population").shift(1).over("sido_code").alias("prev_population")
    )
    df = df.with_columns(
        ((pl.col("population") - pl.col("prev_population")) / pl.col("prev_population") * 100)
        .alias("pop_change_rate")
    )

    # 2019 이후만 최종 출력 (2018은 전년도 기준용)
    df = df.filter(pl.col("year") >= 2019)

    return df.select(["sido_code", "year", "population", "pop_change_rate"]).sort(["sido_code", "year"])


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    key = os.getenv("DATA_GO_KR_KEY_DECODING", "").strip()
    if not key:
        print("[FAIL] .env DATA_GO_KR_KEY_DECODING 없음")
        return 1

    print("[행안부] 주민등록인구 수집 시작")
    rows = fetch_all(key)
    print(f"[INFO] 원본 {len(rows)}행")

    df = process(rows)
    print(f"[INFO] 처리 완료: {len(df)}행, 시도 {df['sido_code'].n_unique()}개, "
          f"연도 {df['year'].n_unique()}개")
    print(f"  기간: {df['year'].min()} ~ {df['year'].max()}")
    print(df.head(5))

    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUT, compression="zstd")
    print(f"[DONE] → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
