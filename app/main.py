"""FastAPI 진입점 — 청년 안심 H+T 추천 시스템.

설계서 v2.2 §6 백엔드 API 설계.

엔드포인트:
- POST /api/v1/recommend         사용자 입력 → Top N 추천
- POST /api/v1/recommend/report  단일 추천 → Gemini 자연어 리포트
- POST /api/v1/recommend/compare Top 3 → 비교 매트릭스 자연어
- GET  /api/v1/healthz           Health check

dev:
  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI

from app.routers import recommend

app = FastAPI(
    title="청년 안심 H+T 추천 API",
    version="0.1.0-prototype",
    description="청년 거주지 추천 + Gemini 자연어 리포트",
)

app.include_router(recommend.router, prefix="/api/v1", tags=["recommend"])


@app.get("/api/v1/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
