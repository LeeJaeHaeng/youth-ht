"""국토교통부 연립다세대 전월세 실거래가 5년치 수집.

01_collect_apt_rent.py 와 동일 패턴이지만 엔드포인트와 출력 경로만 다름.
설계서 §1주차 데이터셋 2 그대로. 0주차 검증으로 대지권면적 응답 없음 확인됨.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import httpx
import polars as pl
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import (  # noqa: E402
    PROCESSED_DIR,
    Checkpoint,
    RateLimiter,
    env,
    get_with_retry,
    safe_run,
)
import importlib.util  # noqa: E402

_apt_path = Path(__file__).parent / "01_collect_apt_rent.py"
spec = importlib.util.spec_from_file_location("apt_rent", _apt_path)
apt = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(apt)  # type: ignore[union-attr]

from sigungu_codes import SAMPLE_SIGUNGU, load_all_sigungu  # noqa: E402

API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent"
OUT_PARQUET = PROCESSED_DIR / "villa_rent_history.parquet"
CHECKPOINT_NAME = "02_villa_rent"


def fetch_one(client: httpx.Client, key: str, lawd_cd: str, deal_ymd: str) -> pl.DataFrame:
    all_rows: list[dict] = []
    page = 1
    while True:
        params = {
            "serviceKey": key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ymd,
            "numOfRows": "1000",
            "pageNo": str(page),
        }
        r = get_with_retry(client, API_URL, params=params, timeout=30)
        rows = apt.parse_items(r.text)
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < 1000:
            break
        page += 1
    return apt.normalize(all_rows, lawd_cd, deal_ymd)


def collect(targets: list[tuple[str, str]], months: list[str], cp: Checkpoint) -> None:
    key = env("DATA_GO_KR_KEY_DECODING")
    rl = RateLimiter(calls_per_sec=1.0)

    with httpx.Client() as client:
        total = len(targets) * len(months)
        with tqdm(total=total, desc="villa_rent") as pbar:
            for lawd_cd, name in targets:
                for ymd in months:
                    ck = f"{lawd_cd}|{ymd}"
                    if cp.is_done(ck):
                        pbar.update(1)
                        continue
                    rl.wait()
                    try:
                        df = fetch_one(client, key, lawd_cd, ymd)
                        apt.append_parquet(df, OUT_PARQUET)
                        cp.mark(ck)
                    except Exception as e:  # noqa: BLE001
                        tqdm.write(f"[ERR] {ck} ({name}): {e}")
                    finally:
                        pbar.update(1)
                cp.save()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--start", default="2020-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--codes-csv", default=None)
    args = ap.parse_args()

    if not (args.dry_run or args.full):
        ap.error("--dry-run 또는 --full 중 하나 지정")

    if args.dry_run:
        targets = SAMPLE_SIGUNGU
        months = ["202401"]
    else:
        targets = load_all_sigungu(args.codes_csv)
        sy, sm = (int(x) for x in args.start.split("-"))
        if args.end:
            ey, em = (int(x) for x in args.end.split("-"))
        else:
            t = date.today()
            ey, em = (t.year, t.month - 1) if t.month > 1 else (t.year - 1, 12)
        months = apt.yyyymm_range(date(sy, sm, 1), date(ey, em, 1))

    print(f"수집 대상: {len(targets)} 시군구 × {len(months)} 개월 = {len(targets)*len(months)} 호출")
    safe_run(CHECKPOINT_NAME, lambda cp: collect(targets, months, cp))

    if OUT_PARQUET.exists():
        df = pl.read_parquet(OUT_PARQUET)
        print(f"\n[DONE] 누적 {len(df):,} 행 → {OUT_PARQUET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
