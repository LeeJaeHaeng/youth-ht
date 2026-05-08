"""행정안전부 주민등록인구 수집기 (GRU #5 입력 — 격자 인구 변화율).

`.env` POPULATION_API_URL 채워지면 즉시 작동. 수집 결과를 표준 컬럼으로 정규화.

설계서 §1주차 데이터셋 7. 청년(19~34세) 인구 추출.

산출: data/processed/population_history.parquet
컬럼: region_code, year_month, total_pop, youth_pop, male_pop, female_pop
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import PROCESSED_DIR, env, get_with_retry  # noqa: E402

OUT = PROCESSED_DIR / "population_history.parquet"


def parse_extra(s: str) -> dict[str, str]:
    if not s:
        return {}
    out: dict[str, str] = {}
    for chunk in s.split("&"):
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def fetch_page(client: httpx.Client, url: str, key: str, page: int, page_size: int = 1000, **extra: str) -> tuple[list[dict], str]:
    """단일 페이지 호출. (rows, content_type) 반환."""
    params = {
        "serviceKey": key,
        "type": "json",
        "pageNo": str(page),
        "numOfRows": str(page_size),
        **extra,
    }
    r = get_with_retry(client, url, params=params, timeout=30)
    ct = (r.headers.get("Content-Type") or "").lower()
    if "json" in ct or r.text.lstrip().startswith("{"):
        data = r.json()
        # 공공데이터포털 표준: response.body.items.item 또는 평탄한 구조
        rows = _extract_rows_json(data)
        return rows, "json"
    # XML
    root = ET.fromstring(r.text)
    rows = [{c.tag: (c.text or "").strip() for c in item} for item in root.findall(".//item")]
    return rows, "xml"


def _extract_rows_json(data: dict | list) -> list[dict]:
    """다양한 JSON 응답 형태에서 row 리스트 추출 — 사용자 명세 unknown 대응."""
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if not isinstance(data, dict):
        return []
    # 공공데이터포털 표준
    body = data.get("response", {}).get("body") if "response" in data else None
    if body:
        items = body.get("items")
        if isinstance(items, dict):
            item = items.get("item")
            if isinstance(item, list):
                return item
            if isinstance(item, dict):
                return [item]
        elif isinstance(items, list):
            return items
    # 직접 result 형태
    for key in ("result", "rows", "data", "list"):
        v = data.get(key)
        if isinstance(v, list):
            return [r for r in v if isinstance(r, dict)]
    return []


def normalize(rows: list[dict]) -> pl.DataFrame:
    """행안부 응답 컬럼명을 우리 표준 스키마로 매핑. 알려진 후보 모두 시도."""
    if not rows:
        return pl.DataFrame()

    df = pl.DataFrame(rows)
    cols = df.columns

    # 컬럼명 후보 (실제 명세 확인 후 정확화)
    def first(*candidates: str) -> str | None:
        for c in candidates:
            if c in cols:
                return c
        return None

    code_col = first("admm_cd", "admmCd", "regionCd", "행정구역코드", "stdgCd")
    ym_col = first("stdg_dt", "stdgDt", "기준연월", "stdgYm")
    total_col = first("ttl_popltn_co", "ttlPopltnCo", "총인구", "popltnCnt")
    male_col = first("male_popltn_co", "malePopltnCo", "남자인구")
    female_col = first("female_popltn_co", "femalePopltnCo", "여자인구")

    rename_map: dict[str, str] = {}
    if code_col:
        rename_map[code_col] = "region_code"
    if ym_col:
        rename_map[ym_col] = "year_month"
    if total_col:
        rename_map[total_col] = "total_pop"
    if male_col:
        rename_map[male_col] = "male_pop"
    if female_col:
        rename_map[female_col] = "female_pop"

    if rename_map:
        df = df.rename(rename_map)
    return df


def main() -> int:
    url = os.getenv("POPULATION_API_URL", "").strip()
    if not url:
        print("[FAIL] .env POPULATION_API_URL 미설정")
        print("       사용자 액션 필요 — docs/user_action_required.md §A")
        return 2

    key = env("DATA_GO_KR_KEY_DECODING")
    extra = parse_extra(os.getenv("POPULATION_EXTRA_PARAMS", ""))

    print(f"[INFO] URL: {url}")
    print(f"[INFO] extra: {extra}")

    all_rows: list[dict] = []
    page = 1
    with httpx.Client() as client:
        while True:
            rows, fmt = fetch_page(client, url, key, page, **extra)
            print(f"  page {page}: {len(rows)} rows ({fmt})")
            if not rows:
                break
            all_rows.extend(rows)
            if len(rows) < 1000:
                break
            page += 1
            if page > 100:
                print("[WARN] 100페이지 초과 — 중단")
                break

    if not all_rows:
        print("[FAIL] 응답 없음")
        return 1

    df = normalize(all_rows)
    df.write_parquet(OUT, compression="zstd")
    print(f"[DONE] {len(df):,} 행 → {OUT}")
    print(f"컬럼: {df.columns}")
    print(df.head(3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
