"""카카오 주소 API — 시군구 단위 검색 테스트."""
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
KEY = os.getenv("KAKAO_REST_KEY")
H = {"Authorization": f"KakaoAK {KEY}"}

queries = [
    "서울특별시 종로구",
    "경기도 수원시",
    "강원도 춘천시",
    "강원특별자치도 춘천시",
    "전라북도 전주시",
    "전북특별자치도 전주시",
    "경기도 수원시 영통구",
]

for q in queries:
    r = httpx.get("https://dapi.kakao.com/v2/local/search/address.json", headers=H,
                  params={"query": q, "size": 1}, timeout=15)
    docs = r.json().get("documents") or []
    if docs:
        d = docs[0]
        print(f"OK  {q!r:35s} → {d.get('y')},{d.get('x')} addr={d.get('address_name')}")
    else:
        print(f"MISS {q!r}: HTTP={r.status_code} body={r.text[:200]}")

    # 키워드 검색도 동시 테스트
    r2 = httpx.get("https://dapi.kakao.com/v2/local/search/keyword.json", headers=H,
                   params={"query": q, "size": 1}, timeout=15)
    docs2 = r2.json().get("documents") or []
    if docs2:
        print(f"  KW  → {docs2[0].get('y')},{docs2[0].get('x')} place={docs2[0].get('place_name')}")
