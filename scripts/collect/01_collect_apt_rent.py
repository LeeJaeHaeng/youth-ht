"""국토교통부 아파트 전월세 실거래가 5년치 수집.

설계서 §1주차 데이터셋 1 그대로. 0주차 검증 결과 반영:
- resultCode = "000" (3자리 신규 명세)
- 응답 XML 파싱으로 거래 dict 리스트 변환
- rate-limit 1초 1회 (공공데이터포털 일 1,000회 한도 가정 → 250 시군구 × 60월 = 15,000회 → 약 15일 분산)
- checkpoint: 시군구|YYYYMM 단위로 처리 키 저장

실행 모드:
  python 01_collect_apt_rent.py --dry-run            # 5개 시군구 × 1개월
  python 01_collect_apt_rent.py --full               # 250 시군구 × 60개월
  python 01_collect_apt_rent.py --full --resume      # checkpoint 이어서

입력: .env DATA_GO_KR_KEY_DECODING + sigungu_codes.py
출력: data/processed/apt_rent_history.parquet (zstd 압축 append)
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
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
from sigungu_codes import SAMPLE_SIGUNGU, load_all_sigungu  # noqa: E402

API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
OUT_PARQUET = PROCESSED_DIR / "apt_rent_history.parquet"
CHECKPOINT_NAME = "01_apt_rent"

NUMERIC_COLS = ("buildYear", "dealDay", "dealMonth", "dealYear", "floor")
INT_FROM_KOREAN = ("deposit", "monthlyRent")  # "20,000" → 20000


def yyyymm_range(start: date, end: date) -> list[str]:
    out: list[str] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y:04d}{m:02d}")
        m += 1
        if m > 12:
            y += 1
            m = 1
    return out


def parse_items(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    code = root.findtext(".//resultCode")
    if code not in ("00", "000"):
        msg = root.findtext(".//resultMsg")
        raise RuntimeError(f"API 실패 resultCode={code} ({msg})")
    rows: list[dict] = []
    for item in root.findall(".//item"):
        d = {child.tag: (child.text or "").strip() for child in item}
        rows.append(d)
    return rows


def normalize(rows: list[dict], lawd_cd: str, deal_ymd: str) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame()
    df = pl.DataFrame(rows)
    # 한국식 천단위 구분자 제거 + 숫자 캐스트
    casts = []
    for c in INT_FROM_KOREAN:
        if c in df.columns:
            casts.append(
                pl.col(c).str.replace_all(",", "").cast(pl.Int64, strict=False).alias(c)
            )
    for c in NUMERIC_COLS:
        if c in df.columns:
            casts.append(pl.col(c).cast(pl.Int32, strict=False).alias(c))
    if "excluUseAr" in df.columns:
        casts.append(pl.col("excluUseAr").cast(pl.Float32, strict=False).alias("excluUseAr"))
    df = df.with_columns(casts)
    return df.with_columns(
        [
            pl.lit(lawd_cd).alias("lawd_cd"),
            pl.lit(deal_ymd).alias("deal_ymd"),
        ]
    )


def fetch_one(client: httpx.Client, key: str, lawd_cd: str, deal_ymd: str) -> pl.DataFrame:
    """단일 (시군구, 월) 호출 — 모든 페이지 합쳐 반환."""
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
        rows = parse_items(r.text)
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < 1000:
            break
        page += 1
    return normalize(all_rows, lawd_cd, deal_ymd)


def append_parquet(df: pl.DataFrame, out: Path) -> None:
    """append 패턴 — 기존 파일이 있으면 vstack 후 저장."""
    if df.is_empty():
        return
    if out.exists():
        existing = pl.read_parquet(out)
        # 컬럼이 다를 수 있으므로 outer 합집합
        df = pl.concat([existing, df], how="diagonal_relaxed")
    df.write_parquet(out, compression="zstd")


def collect(targets: list[tuple[str, str]], months: list[str], cp: Checkpoint) -> None:
    key = env("DATA_GO_KR_KEY_DECODING")
    rl = RateLimiter(calls_per_sec=1.0)  # 안전한 보수값

    with httpx.Client(http2=False) as client:
        total = len(targets) * len(months)
        with tqdm(total=total, desc="apt_rent") as pbar:
            for lawd_cd, name in targets:
                for ymd in months:
                    ck = f"{lawd_cd}|{ymd}"
                    if cp.is_done(ck):
                        pbar.update(1)
                        continue
                    rl.wait()
                    try:
                        df = fetch_one(client, key, lawd_cd, ymd)
                        append_parquet(df, OUT_PARQUET)
                        cp.mark(ck)
                    except Exception as e:  # noqa: BLE001
                        tqdm.write(f"[ERR] {ck} ({name}): {e}")
                    finally:
                        pbar.update(1)
                # 시군구마다 checkpoint 저장 (장시간 작업 안전)
                cp.save()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="5개 시군구 × 1개월")
    ap.add_argument("--full", action="store_true", help="전체 250 시군구 × 60개월")
    ap.add_argument("--start", default="2020-01", help="시작 YYYY-MM")
    ap.add_argument("--end", default=None, help="종료 YYYY-MM (기본: 현재 월의 전월)")
    ap.add_argument(
        "--codes-csv",
        default=None,
        help="시군구 코드 CSV (없으면 SAMPLE 5개)",
    )
    args = ap.parse_args()

    if not (args.dry_run or args.full):
        ap.error("--dry-run 또는 --full 중 하나 지정")

    if args.dry_run:
        targets = SAMPLE_SIGUNGU
        months = ["202401"]
    else:
        targets = load_all_sigungu(args.codes_csv)
        start_y, start_m = (int(x) for x in args.start.split("-"))
        if args.end:
            end_y, end_m = (int(x) for x in args.end.split("-"))
        else:
            today = date.today()
            end_y, end_m = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
        months = yyyymm_range(date(start_y, start_m, 1), date(end_y, end_m, 1))

    print(f"수집 대상: {len(targets)} 시군구 × {len(months)} 개월 = {len(targets)*len(months)} 호출")
    safe_run(CHECKPOINT_NAME, lambda cp: collect(targets, months, cp))

    if OUT_PARQUET.exists():
        df = pl.read_parquet(OUT_PARQUET)
        print(f"\n[DONE] 누적 {len(df):,} 행 → {OUT_PARQUET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
