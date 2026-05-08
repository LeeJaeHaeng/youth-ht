"""직장 클러스터 좌표 부여 — work_clusters_seed.csv 의 query 키워드를
카카오 로컬 키워드 검색 API로 lat/lng 변환.

입력: docs/work_clusters_seed.csv (name, query, sido)
출력: docs/work_clusters.csv (cluster_id, name, lat, lng, youth_employment, sido)

설계서 §1주차 데이터셋 10 + work_cluster 테이블 입력.
"""
from __future__ import annotations

import csv
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "docs" / "work_clusters_seed.csv"
OUT = ROOT / "docs" / "work_clusters.csv"

load_dotenv(ROOT / ".env")
KEY = os.getenv("KAKAO_REST_KEY")

API = "https://dapi.kakao.com/v2/local/search/keyword.json"


def search_keyword(client: httpx.Client, query: str) -> tuple[float, float] | None:
    headers = {"Authorization": f"KakaoAK {KEY}"}
    params = {"query": query, "size": 1}
    r = client.get(API, headers=headers, params=params, timeout=15)
    if r.status_code != 200:
        print(f"  [HTTP {r.status_code}] {query}")
        return None
    docs = r.json().get("documents") or []
    if not docs:
        return None
    d = docs[0]
    return float(d["y"]), float(d["x"])  # y=lat, x=lng


def main() -> int:
    if not KEY:
        print("[FAIL] KAKAO_REST_KEY 미설정")
        return 1
    if not SEED.exists():
        print(f"[FAIL] {SEED} 없음")
        return 1

    out_rows: list[dict] = []
    fails: list[str] = []
    with SEED.open("r", encoding="utf-8") as f, httpx.Client() as client:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            query = row["query"]
            ll = search_keyword(client, query)
            if ll is None:
                fails.append(f"{row['name']} ({query})")
                continue
            lat, lng = ll
            out_rows.append(
                {
                    "cluster_id": i,
                    "name": row["name"],
                    "lat": lat,
                    "lng": lng,
                    "youth_employment": "",
                    "sido": row["sido"],
                }
            )
            print(f"  #{i:3d} {row['name']:30s} → ({lat:.5f}, {lng:.5f})")
            time.sleep(0.05)  # 카카오 키워드 검색 일 1만 호출 한도 — 안전 margin

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["cluster_id", "name", "lat", "lng", "youth_employment", "sido"],
        )
        w.writeheader()
        w.writerows(out_rows)

    print(f"\n[DONE] {len(out_rows)}개 클러스터 → {OUT}")
    if fails:
        print(f"[WARN] 좌표 부여 실패 {len(fails)}건:")
        for f in fails:
            print(f"  - {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
