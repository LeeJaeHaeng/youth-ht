"""R-ONE 미분양 통계 수집기 (GRU #6 입력 — 1km 내 신축 분양 호수).

베이스 URL은 0주차에 확인됨. STATBL_ID만 .env에 채우면 즉시 작동.

R-ONE OpenAPI 표준 응답 구조: 보통 다음 중 하나
  {"SttsApiTblData": [{"head": {...}}, {"row": [...]}]}
또는
  {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상"}, ...}

산출: data/processed/unsold_history.parquet
컬럼: region_code, year_month, unsold_units, completed_unsold_units, supply_units (가능한 경우)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import PROCESSED_DIR, env, get_with_retry  # noqa: E402

DATA_URL = "https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do"
OUT = PROCESSED_DIR / "unsold_history.parquet"


def fetch_all_pages(client: httpx.Client, key: str, statbl_id: str, dtacycle: str, wrttime_start: str) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        params = {
            "KEY": key,
            "Type": "json",
            "pIndex": str(page),
            "pSize": "1000",
            "STATBL_ID": statbl_id,
            "DTACYCLE_CD": dtacycle,
            "WRTTIME_IDTFR_ID": wrttime_start,
        }
        r = get_with_retry(client, DATA_URL, params=params, timeout=30)
        data = r.json()

        # 에러 응답
        if isinstance(data, dict) and "RESULT" in data:
            code = data["RESULT"].get("CODE", "")
            if code.startswith("ERROR") or code.startswith("INFO-2"):
                print(f"[STOP] {code}: {data['RESULT'].get('MESSAGE')}")
                break

        # SttsApiTblData 표준 구조
        page_rows = _extract_rows(data)
        print(f"  page {page}: {len(page_rows)} rows")
        if not page_rows:
            break
        rows.extend(page_rows)
        if len(page_rows) < 1000:
            break
        page += 1
        if page > 50:
            print("[WARN] 50페이지 초과 — 중단")
            break
    return rows


def _extract_rows(data) -> list[dict]:
    if not isinstance(data, dict):
        return []
    for v in data.values():
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and "row" in item and isinstance(item["row"], list):
                    return item["row"]
    return []


def normalize(rows: list[dict]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame()
    df = pl.DataFrame(rows)
    # R-ONE 표준 컬럼: WRTTIME_IDTFR_ID(시점), GIS_RGN_CD(지역), DTA_VAL(값), CLS_ID(분류)
    rename = {}
    if "WRTTIME_IDTFR_ID" in df.columns:
        rename["WRTTIME_IDTFR_ID"] = "year_month_raw"
    if "GIS_RGN_CD" in df.columns:
        rename["GIS_RGN_CD"] = "region_code"
    if "DTA_VAL" in df.columns:
        rename["DTA_VAL"] = "value"
    if rename:
        df = df.rename(rename)
    return df


def main() -> int:
    statbl_id = os.getenv("REB_UNSOLD_STATBL_ID", "").strip()
    if not statbl_id:
        print("[FAIL] .env REB_UNSOLD_STATBL_ID 미설정")
        print("       사용자 액션 필요 — docs/user_action_required.md §B")
        return 2

    key = env("REB_API_KEY")
    dtacycle = os.getenv("REB_UNSOLD_DTACYCLE_CD", "MM").strip()
    wrttime_start = os.getenv("REB_UNSOLD_WRTTIME_START", "202001").strip()

    print(f"[INFO] STATBL_ID={statbl_id}, DTACYCLE={dtacycle}, START={wrttime_start}")

    with httpx.Client() as client:
        rows = fetch_all_pages(client, key, statbl_id, dtacycle, wrttime_start)

    if not rows:
        print("[FAIL] 응답 없음")
        return 1

    df = normalize(rows)
    df.write_parquet(OUT, compression="zstd")
    print(f"[DONE] {len(df):,} 행 → {OUT}")
    print(f"컬럼: {df.columns}")
    print(df.head(3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
