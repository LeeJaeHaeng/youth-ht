"""R-ONE 서비스 통계목록 페이징 조회 → 미분양 STATBL_ID 추출."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

KEY = os.getenv("REB_API_KEY")
URL = "https://www.reb.or.kr/r-one/openapi/SttsApiTbl.do"

KEYWORDS = ["미분양", "분양", "주택보급", "주택가격", "전세가격"]


def main() -> int:
    if not KEY:
        print("[FAIL] REB_API_KEY 미설정")
        return 1

    found: list[dict] = []
    seen = set()
    page_size = 1000  # max
    with httpx.Client(timeout=30) as client:
        for p in range(1, 20):
            params = {"KEY": KEY, "Type": "json", "pIndex": p, "pSize": page_size}
            r = client.get(URL, params=params)
            if r.status_code != 200:
                print(f"  HTTP {r.status_code} @ p={p}")
                break
            try:
                j = r.json()
            except Exception:
                print(f"  파싱 실패 @ p={p} — {r.text[:200]}")
                break
            # R-ONE 응답: {"SttsApiTbl": [{"head":[...]}, {"row":[...]}]}
            payload = j.get("SttsApiTbl") or j.get("StatisTbl") or []
            rows = []
            total = None
            for blk in payload:
                if "head" in blk:
                    for h in blk["head"]:
                        if "list_total_count" in h:
                            total = h["list_total_count"]
                if "row" in blk:
                    rows = blk["row"]
            if not rows:
                # check single-block format
                if isinstance(payload, dict) and "row" in payload:
                    rows = payload["row"]
            print(f"  p={p} rows={len(rows)} total={total}")
            for row in rows:
                nm = row.get("STATBL_NM", "")
                sid = row.get("STATBL_ID")
                if sid in seen:
                    continue
                seen.add(sid)
                if any(kw in nm for kw in KEYWORDS):
                    found.append({"id": sid, "name": nm, "cycle": row.get("DTACYCLE_CD"),
                                  "start": row.get("DATA_START_YY"), "end": row.get("DATA_END_YY")})
            if total and p * page_size >= int(total):
                break
            if len(rows) < page_size:
                break

    print()
    print(f"=== 키워드 매칭 {len(found)}건 ===")
    for f in found:
        print(f"  {f['id']:20s} {f['cycle']} {f['start']}~{f['end']} | {f['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
