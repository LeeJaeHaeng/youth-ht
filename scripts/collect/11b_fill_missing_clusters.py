"""work_clusters 미적중 8건 자동 보강 — 카카오 주소+키워드 dual fallback.

기존: 카카오 키워드 검색만 사용 → 시청·역 등 일반 키워드는 결과 다수, 1순위가 의도 외.
보강: 더 구체적 query (시청 좌표 우선) + 주소 API fallback.
"""
from __future__ import annotations

import csv
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

KEY = os.getenv("KAKAO_REST_KEY")
HEADERS = {"Authorization": f"KakaoAK {KEY}"}
KW_API = "https://dapi.kakao.com/v2/local/search/keyword.json"
ADDR_API = "https://dapi.kakao.com/v2/local/search/address.json"

WORK_CSV = ROOT / "docs" / "work_clusters.csv"

# 미적중 8건 — 시청 / 역 등 명확한 query로 좌표 부여
NEW_CLUSTERS = [
    # name,                  query (kw search), sido, addr (fallback)
    ("경남 창원",          "창원시청",        "경남", "경상남도 창원시 의창구 중앙대로 151"),
    ("경남 김해",          "김해시청",        "경남", "경상남도 김해시 김해대로 2401"),
    ("충북 청주",          "청주시청",        "충북", "충청북도 청주시 상당구 상당로 155"),
    ("충남 천안",          "천안시청",        "충남", "충청남도 천안시 서북구 번영로 156"),
    ("강원 춘천",          "춘천시청",        "강원", "강원특별자치도 춘천시 시청길 11"),
    ("전북 전주",          "전주시청",        "전북", "전북특별자치도 전주시 완산구 노송광장로 10"),
    ("전남 여수",          "여수시청",        "전남", "전라남도 여수시 시청로 1"),
    ("제주 제주시",        "제주시청",        "제주", "제주특별자치도 제주시 광양9길 10"),
]


def kw_search(client: httpx.Client, query: str) -> tuple[float, float] | None:
    r = client.get(KW_API, headers=HEADERS, params={"query": query, "size": 1}, timeout=15)
    if r.status_code != 200:
        return None
    docs = r.json().get("documents") or []
    return (float(docs[0]["y"]), float(docs[0]["x"])) if docs else None


def addr_search(client: httpx.Client, address: str) -> tuple[float, float] | None:
    r = client.get(ADDR_API, headers=HEADERS, params={"query": address, "size": 1}, timeout=15)
    if r.status_code != 200:
        return None
    docs = r.json().get("documents") or []
    return (float(docs[0]["y"]), float(docs[0]["x"])) if docs else None


def main() -> int:
    if not KEY:
        print("[FATAL] KAKAO_REST_KEY 미설정")
        return 1

    # 기존 CSV 로드
    rows: list[dict] = []
    with WORK_CSV.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    existing_names = {r["name"] for r in rows}
    next_id = max(int(r["cluster_id"]) for r in rows) + 1

    new_rows = []
    with httpx.Client() as client:
        for name, query, sido, addr in NEW_CLUSTERS:
            if name in existing_names:
                print(f"  [SKIP] {name} 이미 존재")
                continue
            ll = kw_search(client, query)
            if ll is None:
                print(f"  [FALLBACK→addr] {name}: kw 미적중")
                ll = addr_search(client, addr)
            if ll is None:
                print(f"  [FAIL] {name}")
                continue
            new_rows.append({
                "cluster_id": next_id,
                "name": name,
                "lat": ll[0],
                "lng": ll[1],
                "youth_employment": "",
                "sido": sido,
            })
            print(f"  [OK]   id={next_id} {name:15s} ({ll[0]:.5f}, {ll[1]:.5f})")
            next_id += 1
            time.sleep(0.05)

    if not new_rows:
        print("\n[DONE] 추가할 클러스터 없음")
        return 0

    rows.extend([{**r, "lat": str(r["lat"]), "lng": str(r["lng"])} for r in new_rows])

    with WORK_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cluster_id", "name", "lat", "lng", "youth_employment", "sido"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\n[DONE] {len(new_rows)}건 추가 → 총 {len(rows)} 클러스터 → {WORK_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
