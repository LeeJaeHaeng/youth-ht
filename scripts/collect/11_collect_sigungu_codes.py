"""행정안전부 행정표준코드 — 법정동코드 OpenAPI에서 전국 시군구 5자리 코드 수집.

엔드포인트: https://apis.data.go.kr/1741000/StanReginCd/getStanReginCdList
인증: ServiceKey (DATA_GO_KR_KEY_DECODING — httpx 자동 인코딩)

전국 약 20,560행 → umd_cd=000, ri_cd=00 인 시군구 자체 행만 추출 → 약 250개.
산출:
- data/raw/sigungu_codes.csv (code,name,sido)
"""
from __future__ import annotations

import csv
import math
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

URL = "https://apis.data.go.kr/1741000/StanReginCd/getStanReginCdList"
KEY = os.getenv("DATA_GO_KR_KEY_DECODING")
OUT = ROOT / "data" / "raw" / "sigungu_codes.csv"


def fetch(client: httpx.Client, page: int, size: int = 1000) -> tuple[list[dict], int]:
    params = {"ServiceKey": KEY, "type": "json", "pageNo": page, "numOfRows": size}
    r = client.get(URL, params=params, timeout=60)
    r.raise_for_status()
    blocks = r.json().get("StanReginCd") or []
    rows: list[dict] = []
    total = 0
    for blk in blocks:
        if "row" in blk:
            rows = blk["row"]
        if "head" in blk:
            for h in blk["head"]:
                if isinstance(h, dict) and "totalCount" in h:
                    total = int(h["totalCount"])
    return rows, total


def main() -> int:
    if not KEY:
        print("[FATAL] DATA_GO_KR_KEY_DECODING 미설정")
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    seen: dict[str, tuple[str, str]] = {}

    with httpx.Client() as client:
        rows, total = fetch(client, 1)
        pages = math.ceil(total / 1000)
        print(f"전체 {total} → {pages} 페이지")

        for p in range(1, pages + 1):
            if p > 1:
                rows, _ = fetch(client, p)
            for r in rows:
                # 시군구 자체 행 = umd_cd '000' AND ri_cd '00' AND sgg_cd != '000' (시도 제외)
                umd = str(r.get("umd_cd", "")).zfill(3)
                ri = str(r.get("ri_cd", "")).zfill(2)
                sgg = str(r.get("sgg_cd", "")).zfill(3)
                sido = str(r.get("sido_cd", "")).zfill(2)
                if umd != "000" or ri != "00" or sgg == "000":
                    continue
                code10 = str(r.get("region_cd", "")).zfill(10)
                code5 = code10[:5]
                full_name = r.get("locatadd_nm", "").strip()
                # 시도명 추출
                sido_nm = full_name.split()[0] if full_name else ""
                if code5 not in seen:
                    seen[code5] = (full_name, sido_nm)
            print(f"  p={p}/{pages} 누적 시군구={len(seen)}")

    # 세종특별자치시는 sgg_cd=000이라 위 필터에서 빠짐 — 추가 처리
    # 세종 region_cd = 3611000000 (sido_cd=36, sgg_cd=110, umd_cd=000)
    # 이미 위에서 통과 — 세종시는 sigungu code도 별도임. 36110 ✅

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "name", "sido"])
        for code, (name, sido) in sorted(seen.items()):
            w.writerow([code, name, sido])

    print(f"\n[DONE] {len(seen)} 시군구 → {OUT}")
    # 분포 요약
    by_sido: dict[str, int] = {}
    for _, (_, sido) in seen.items():
        by_sido[sido] = by_sido.get(sido, 0) + 1
    print("\n시도별:")
    for sido, cnt in sorted(by_sido.items(), key=lambda kv: -kv[1]):
        print(f"  {sido:10s} {cnt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
