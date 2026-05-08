"""LLM 서비스 — Gemini 2.5 Flash + Supabase llm_cache (SQLite fallback).

설계서 v2.2 §5 자연어 리포트 모듈 — 사용자 결정으로 DeepSeek-V3 → Gemini 전환.

- 모델: gemini-2.5-flash (thinking_budget=0 — 짧은 한국어 리포트에 사고 토큰 불필요)
- 비용: input $0.075/1M, output $0.30/1M (DeepSeek 대비 절반 + 한국어 품질 우수)
- 캐시: Supabase llm_cache 테이블 우선, 미연결 시 로컬 SQLite fallback
"""
from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

MODEL = "gemini-2.5-flash"
CACHE_DB = ROOT / "data" / "llm_cache.db"

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LLMResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    cached: bool

    @property
    def cost_usd(self) -> float:
        # gemini-2.5-flash (≤128k context)
        return (self.prompt_tokens * 0.075 + self.completion_tokens * 0.30) / 1_000_000

    @property
    def cost_krw(self) -> float:
        return self.cost_usd * 1380


_client: genai.Client | None = None
_supa_client = None  # supabase.Client


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY 미설정")
        _client = genai.Client(api_key=api_key)
    return _client


def _get_supa():
    """Supabase 클라이언트 반환. SUPABASE_URL/KEY 미설정 시 None."""
    global _supa_client
    if _supa_client is not None:
        return _supa_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not (url and key):
        return None
    try:
        from supabase import create_client
        _supa_client = create_client(url, key)
        return _supa_client
    except Exception as e:
        logger.warning("Supabase 클라이언트 초기화 실패: %s → SQLite fallback", e)
        return None


def _cache_key(model: str, system: str, user: str, temperature: float) -> str:
    h = hashlib.sha256()
    for part in (model, system, user, f"{temperature:.2f}"):
        h.update(part.encode())
        h.update(b"\x00")
    return h.hexdigest()


# ── Supabase 캐시 ────────────────────────────────────────────


def _supa_read(key: str) -> LLMResponse | None:
    supa = _get_supa()
    if supa is None:
        return None
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        res = (
            supa.table("llm_cache")
            .select("response,prompt_tokens,completion_tokens,expires_at")
            .eq("cache_key", key)
            .execute()
        )
        rows = res.data
        if not rows:
            return None
        row = rows[0]
        expires_at = row.get("expires_at")
        if expires_at:
            try:
                if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
                    return None
            except ValueError:
                pass
        return LLMResponse(
            text=row["response"],
            prompt_tokens=row.get("prompt_tokens") or 0,
            completion_tokens=row.get("completion_tokens") or 0,
            cached=True,
        )
    except Exception as e:
        logger.warning("Supabase 캐시 read 실패: %s", e)
        return None


def _supa_write(key: str, resp: LLMResponse, ttl_days: int = 30) -> bool:
    supa = _get_supa()
    if supa is None:
        return False
    try:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat()
        supa.table("llm_cache").upsert({
            "cache_key": key,
            "response": resp.text,
            "prompt_tokens": resp.prompt_tokens,
            "completion_tokens": resp.completion_tokens,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at,
        }).execute()
        return True
    except Exception as e:
        logger.warning("Supabase 캐시 write 실패: %s", e)
        return False


# ── SQLite fallback 캐시 ─────────────────────────────────────


def _ensure_sqlite() -> sqlite3.Connection:
    CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CACHE_DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_cache (
          cache_key TEXT PRIMARY KEY,
          response  TEXT NOT NULL,
          prompt_tokens INTEGER,
          completion_tokens INTEGER,
          created_at TEXT NOT NULL,
          expires_at TEXT
        )
        """
    )
    conn.commit()
    return conn


def _read_cache(key: str) -> LLMResponse | None:
    cached = _supa_read(key)
    if cached:
        return cached
    with _ensure_sqlite() as conn:
        row = conn.execute(
            "SELECT response, prompt_tokens, completion_tokens, expires_at FROM llm_cache WHERE cache_key=?",
            (key,),
        ).fetchone()
    if not row:
        return None
    text, pt, ct, expires_at = row
    if expires_at:
        try:
            if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
                return None
        except ValueError:
            pass
    return LLMResponse(text=text, prompt_tokens=pt or 0, completion_tokens=ct or 0, cached=True)


def _write_cache(key: str, resp: LLMResponse, ttl_days: int = 30) -> None:
    if _supa_write(key, resp, ttl_days):
        return
    expires_at = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat()
    with _ensure_sqlite() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO llm_cache(cache_key, response, prompt_tokens, completion_tokens, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                key,
                resp.text,
                resp.prompt_tokens,
                resp.completion_tokens,
                datetime.now(timezone.utc).isoformat(),
                expires_at,
            ),
        )
        conn.commit()


def chat(
    user_prompt: str,
    *,
    system_prompt: str = "당신은 청년 부동산 의사결정을 돕는 친근한 어시스턴트입니다.",
    temperature: float = 0.7,
    max_tokens: int = 800,
    use_cache: bool = True,
) -> LLMResponse:
    """Gemini 2.5 Flash 호출. 캐시 hit이면 API 호출 생략."""
    key = _cache_key(MODEL, system_prompt, user_prompt, temperature)
    if use_cache:
        cached = _read_cache(key)
        if cached:
            logger.info("[CACHE HIT] %s tokens %d/%d", key[:8], cached.prompt_tokens, cached.completion_tokens)
            return cached

    client = _get_client()
    resp = client.models.generate_content(
        model=MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    msg = (resp.text or "").strip()
    usage = getattr(resp, "usage_metadata", None)
    pt = getattr(usage, "prompt_token_count", 0) or 0 if usage else 0
    ct = getattr(usage, "candidates_token_count", 0) or 0 if usage else 0

    out = LLMResponse(text=msg, prompt_tokens=pt, completion_tokens=ct, cached=False)
    if use_cache and msg:
        _write_cache(key, out)
    return out


# ──────────────────────────────────────────────────────────
# 프롬프트 템플릿 — 설계서 v2.2 §5 자연어 리포트 스펙
# ──────────────────────────────────────────────────────────


def render_recommendation_report(rec: dict[str, Any]) -> str:
    return f"""다음 청년 거주지 추천 결과를 자연어 리포트로 작성해주세요.

[사용자]
- 나이: {rec['user_age']}세 직장인
- 직장: {rec['work_name']}
- 예산(월): {rec['user_budget_won']:,}원
- 통근 한계: {rec['commute_limit_min']}분

[추천 #{rec['rank']}: {rec['region_name']}]
- 평균 월세: {rec['rent_mean_won']:,}원
- 평균 보증금: {rec['deposit_mean_won']:,}원
- 통근 시간: {rec['commute_min']}분
- HUG 사고율: {rec['hug_acc_rate_pct']:.1f}%
- 현재 H+T 부담률: {rec['burden_ratio']:.0%}
- 6개월 후 예상 부담률: {rec['future_burden_6m_ratio']:.0%}
- 신뢰도: {rec['confidence']}/100

위 데이터를 바탕으로:
1. 이 동네가 사용자에게 적합한 핵심 이유 (1문장)
2. 주의해야 할 한 가지 (HUG 위험·미래 부담률 변화 등에서 자동 판단, 1문장)
3. 의사결정 팁 (1문장)

전체 3문장, 친근한 어조, 이모지 사용 금지."""


def render_comparison_report(top3: list[dict]) -> str:
    rows = []
    for r in top3:
        rows.append(
            f"- {r['region_name']}: 월세 {r['rent_mean_won']:,}원, 통근 {r['commute_min']}분, "
            f"HUG {r['hug_acc_rate_pct']:.1f}%, 신뢰도 {r['confidence']}/100"
        )
    listing = "\n".join(rows)
    return f"""다음은 한 청년에게 추천된 Top 3 거주지입니다.

{listing}

각 동네의 주된 장점과 trade-off를 1줄씩 비교해주세요.
형식: "A동네는 X에서 우위, B동네는 Y에서 우위, C동네는 Z에서 우위" 형태로 한 단락.
이모지 사용 금지, 5문장 이내."""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample = {
        "user_age": 25, "user_budget_won": 800000, "commute_limit_min": 40,
        "work_name": "강남역", "rank": 1, "region_name": "서울 관악구",
        "rent_mean_won": 710000, "deposit_mean_won": 90000000,
        "commute_min": 28, "hug_acc_rate_pct": 2.7,
        "burden_ratio": 0.32, "future_burden_6m_ratio": 0.34, "confidence": 87,
    }
    prompt = render_recommendation_report(sample)
    resp = chat(prompt)
    print(f"[CACHED={resp.cached}] tokens {resp.prompt_tokens}/{resp.completion_tokens}")
    print(f"비용: {resp.cost_krw:.4f}원")
    print("\n응답:\n" + resp.text)
