"""국토교통 통계누리 OpenAPI 수집기 — 카카오맵 보조 데이터.

설계서 §1주차 후순위. 카카오맵이 OD 메인이라 이건 보조.

`.env` 슬롯:
  MOLIT_STAT_BASE_URL  — 정확한 베이스 URL
  MOLIT_STAT_AUTH_PARAM — KEY|apiKey|serviceKey
  MOLIT_STAT_TBL_IDS   — 콤마 구분 통계표 ID

산출: data/processed/molit_stat_<TBL_ID>.parquet (테이블별 분리)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import PROCESSED_DIR, env, get_with_retry  # noqa: E402


def fetch_one_table(client: httpx.Client, base_url: str, auth_param: str, key: str, tbl_id: str) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        params = {
            auth_param: key,
            "Type": "json",
            "pIndex": str(page),
            "pSize": "1000",
            "STATBL_ID": tbl_id,  # 통계누리 표준이 R-ONE과 유사하다고 가정. 미작동 시 사용자 파라미터 명세 보강 필요
        }
        r = get_with_retry(client, base_url, params=params, timeout=30)
        try:
            data = r.json()
        except Exception:
            print(f"  [ERR] page {page}: JSON 파싱 실패")
            break

        # 에러 코드 응답 처리
        if isinstance(data, dict) and "RESULT" in data:
            result = data["RESULT"]
            code = (result.get("CODE") or "")
            if code.startswith("ERROR"):
                print(f"  [STOP] {code}: {result.get('MESSAGE')}")
                break

        page_rows = _extract_rows(data)
        print(f"  table={tbl_id} page={page}: {len(page_rows)} rows")
        if not page_rows:
            break
        rows.extend(page_rows)
        if len(page_rows) < 1000:
            break
        page += 1
        if page > 50:
            break
    return rows


def _extract_rows(data) -> list[dict]:
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if not isinstance(data, dict):
        return []
    for v in data.values():
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and "row" in item and isinstance(item["row"], list):
                    return item["row"]
    return []


def main() -> int:
    base_url = os.getenv("MOLIT_STAT_BASE_URL", "").strip()
    if not base_url:
        print("[FAIL] .env MOLIT_STAT_BASE_URL 미설정")
        print("       사용자 액션 필요 — docs/user_action_required.md §C")
        return 2

    auth_param = os.getenv("MOLIT_STAT_AUTH_PARAM", "KEY").strip() or "KEY"
    tbl_ids_raw = os.getenv("MOLIT_STAT_TBL_IDS", "").strip()
    if not tbl_ids_raw:
        print("[FAIL] .env MOLIT_STAT_TBL_IDS 미설정 (콤마 구분 통계표 ID)")
        return 2

    tbl_ids = [t.strip() for t in tbl_ids_raw.split(",") if t.strip()]
    key = env("MOLIT_STAT_KEY")

    print(f"[INFO] BASE_URL={base_url}, AUTH_PARAM={auth_param}, TBL_IDS={tbl_ids}")

    with httpx.Client() as client:
        for tbl in tbl_ids:
            rows = fetch_one_table(client, base_url, auth_param, key, tbl)
            if not rows:
                print(f"[SKIP] {tbl}: 데이터 없음")
                continue
            df = pl.DataFrame(rows)
            out = PROCESSED_DIR / f"molit_stat_{tbl}.parquet"
            df.write_parquet(out, compression="zstd")
            print(f"[DONE] {tbl}: {len(df):,} 행 → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
