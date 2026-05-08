"""STCIS OD — 다양한 날짜·OD 조합 탐색."""
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

KEY = os.getenv("STCIS_API_KEY")
URL = "https://stcis.go.kr/openapi/quarterod.json"

trials = [
    ("20241015", "1168010100", "1168010500", "서울 강남 역삼→삼성"),
    ("20240517", "1168010100", "1168010500", "서울 강남 역삼→삼성"),
    ("20231013", "1168010100", "1168010500", "서울 강남 역삼→삼성"),
    ("20241015", "1117010100", "1117010600", "서울 종로 효자→삼청"),
    ("20240315", "1162010800", "1168010100", "서울 봉천→역삼 (역방향)"),
    ("20240315", "1117010100", "1162010800", "서울 종로→봉천"),
]
for d, s, a, name in trials:
    r = httpx.get(URL, params={"apikey": KEY, "opratDate": d, "stgEmdCd": s, "arrEmdCd": a}, timeout=30)
    j = r.json() if r.status_code == 200 else {}
    status = j.get("status")
    count = j.get("count")
    print(f"{d} {name}: HTTP={r.status_code} status={status} count={count}")
    rows = j.get("result") or []
    if rows:
        row = rows[0]
        print(f"  샘플: {row.get('tzon')}시 Q{row.get('quater')} 이용={row.get('useStf')}명 통행={row.get('useTm')}분")
        break
