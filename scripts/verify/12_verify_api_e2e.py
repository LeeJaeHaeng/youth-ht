"""FastAPI E2E — /api/v1/recommend → /report 통합 검증.

prototype mock 데이터 기반. 실제 추천 + Gemini 리포트 한 번 호출.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# 1) Health
r = client.get("/api/v1/healthz")
print("[healthz]", r.status_code, r.json())

# 2) 추천 — 강남 직장 25세 청년 80만원 / 통근 40분
req = {
    "age": 25,
    "work_lat": 37.498,
    "work_lng": 127.028,
    "work_name": "강남역",
    "budget_won": 800_000,
    "commute_limit_min": 40,
    "top_n": 5,
}
r = client.post("/api/v1/recommend", json=req)
print(f"\n[recommend] HTTP {r.status_code}")
data = r.json()
print(f"  Stage1 통과: {data['candidates_after_stage1']}, 반환: {len(data['items'])}")
for it in data["items"][:3]:
    print(f"  #{it['rank']} {it['region_name']:15s} 총점 {it['total_score']}/100, 신뢰도 {it['confidence']}/100, 월세 {it['rent_mean_won']:,}원")

# 3) 1순위 자연어 리포트 — Gemini 호출
top1 = data["items"][0]
report_req = {
    "item": top1,
    "user_age": req["age"],
    "work_name": req["work_name"],
    "budget_won": req["budget_won"],
    "commute_limit_min": req["commute_limit_min"],
}
r = client.post("/api/v1/recommend/report", json=report_req)
print(f"\n[report] HTTP {r.status_code}")
rj = r.json()
print(f"  cached={rj['cached']}, 비용={rj['cost_krw']}원")
print(f"  텍스트:\n  {rj['text']}")

# 4) Top 3 비교
cmp_req = {"items": data["items"][:3]}
r = client.post("/api/v1/recommend/compare", json=cmp_req)
print(f"\n[compare] HTTP {r.status_code}")
rj = r.json()
print(f"  cached={rj['cached']}, 비용={rj['cost_krw']}원")
print(f"  텍스트:\n  {rj['text']}")
