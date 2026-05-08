"""Gemini API 검증 — 한국어 자연어 리포트 sanity check.

설계서 v2.2 §5 자연어 리포트 모듈 — DeepSeek-V3 → Gemini로 전환 (사용자 결정).
모델: gemini-2.5-flash (빠름·저렴, 한국어 강함)

검증 통과 기준:
- 정상 응답 (텍스트 추출)
- 한국어 출력이 자연스러움 (한글 비율 ≥ 30%)
- token usage 추출 가능 (비용 추정)

비용 (gemini-2.5-flash, 2026년 기준):
- input: $0.075 / 1M tokens (≤128k context)
- output: $0.30 / 1M tokens
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import banner, env, fail, ok, save_sample

MODEL = "gemini-2.5-flash"

PROMPT = """다음 청년 안심 H+T 추천 결과를 자연어 리포트로 변환해줘.

입력:
- 사용자: 25세 직장인, 직장=강남역, 예산 월 80만원, 통근 한계 40분
- 추천 1순위: 서울 관악구
  - 평균 월세: 71만원
  - 보증금 평균: 9,000만원
  - 통근시간: 28분
  - HUG 사고율: 2.7%

이 데이터를 바탕으로 추천 이유를 친근한 어조로 3문장으로 설명해줘.
"""


def main() -> int:
    banner("Task 10 — Gemini API")
    key = env("GEMINI_API_KEY")

    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        fail(f"google-genai 패키지 미설치: {e}")
        return 1

    client = genai.Client(api_key=key)

    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=PROMPT,
            config=types.GenerateContentConfig(
                system_instruction="당신은 청년 부동산 의사결정을 돕는 친근한 어시스턴트입니다.",
                temperature=0.7,
                max_output_tokens=600,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
    except Exception as e:
        fail(f"Gemini API 호출 실패: {type(e).__name__}: {e}")
        return 1

    msg = (resp.text or "").strip()
    usage = getattr(resp, "usage_metadata", None)

    print("\n📋 응답:")
    print(msg)
    print("\n📊 토큰 사용량:")
    pt = ct = total = 0
    if usage:
        pt = getattr(usage, "prompt_token_count", 0) or 0
        ct = getattr(usage, "candidates_token_count", 0) or 0
        total = getattr(usage, "total_token_count", 0) or 0
        print(f"  prompt: {pt}")
        print(f"  candidates: {ct}")
        print(f"  total: {total}")

    # gemini-2.5-flash 비용 (≤128k context)
    cost_usd = (pt * 0.075 + ct * 0.30) / 1_000_000
    cost_krw = cost_usd * 1380
    print(f"  예상 비용: ${cost_usd:.6f} ≈ {cost_krw:.4f}원")

    if not msg:
        fail("응답 메시지 비어있음")
        return 1

    hangul_ratio = sum(1 for c in msg if 0xAC00 <= ord(c) <= 0xD7A3) / max(len(msg), 1)
    print(f"\n🇰🇷 한글 문자 비율: {hangul_ratio:.1%}")
    if hangul_ratio < 0.3:
        fail("한국어 응답 품질 의심 — 한글 비율 30% 미만")
        return 1

    save_sample(
        "10_gemini",
        {
            "model": MODEL,
            "prompt_preview": PROMPT[:300],
            "response": msg,
            "usage": {"prompt": pt, "completion": ct, "total": total},
            "cost_krw_estimate": round(cost_krw, 4),
            "hangul_ratio": round(hangul_ratio, 3),
        },
    )
    ok("Gemini API 검증 통과 — 한국어 자연어 리포트 생성 성공")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
