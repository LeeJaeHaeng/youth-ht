"""DeepSeek-V3 API 검증 — 한국어 자연어 리포트 sanity check.

설계서 §0주차 금요일 + §5 DeepSeek API 통합 설계.
DeepSeek API는 OpenAI SDK 호환. 베이스 URL: https://api.deepseek.com

검증 통과 기준:
- HTTP 200 + 정상 응답
- 모델: deepseek-chat (V3)
- 한국어 출력이 자연스러움
- token usage 추출 가능 (비용 추정)
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import banner, env, fail, ok, save_sample

API_URL = "https://api.deepseek.com/chat/completions"

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
    banner("Task 10 — DeepSeek-V3 API")
    key = env("DEEPSEEK_API_KEY")

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "당신은 청년 부동산 의사결정을 돕는 친근한 어시스턴트입니다."},
            {"role": "user", "content": PROMPT},
        ],
        "temperature": 0.7,
        "max_tokens": 500,
    }

    try:
        with httpx.Client(timeout=60) as client:
            r = client.post(API_URL, headers=headers, json=payload)
    except httpx.HTTPError as e:
        fail(f"네트워크 오류: {e}")
        return 1

    print(f"Status: {r.status_code}, len={len(r.content)}B")

    if r.status_code != 200:
        fail(f"HTTP {r.status_code}: {r.text[:600]}")
        return 1

    data = r.json()
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message", {}).get("content", "")
    usage = data.get("usage", {})

    print("\n📋 응답:")
    print(msg)
    print("\n📊 토큰 사용량:")
    print(f"  prompt: {usage.get('prompt_tokens')}")
    print(f"  completion: {usage.get('completion_tokens')}")
    print(f"  total: {usage.get('total_tokens')}")

    # 비용 추정 (input $0.14 / 1M, output $0.28 / 1M)
    pt = usage.get("prompt_tokens", 0)
    ct = usage.get("completion_tokens", 0)
    cost_usd = (pt * 0.14 + ct * 0.28) / 1_000_000
    cost_krw = cost_usd * 1380  # 1 USD ≈ 1,380원 (2026년 시점 가정)
    print(f"  예상 비용: ${cost_usd:.6f} ≈ {cost_krw:.2f}원")

    if not msg:
        fail("응답 메시지 비어있음")
        return 1

    # 한국어 sanity check (한글 비율)
    hangul_ratio = sum(1 for c in msg if 0xAC00 <= ord(c) <= 0xD7A3) / max(len(msg), 1)
    print(f"\n🇰🇷 한글 문자 비율: {hangul_ratio:.1%}")
    if hangul_ratio < 0.3:
        fail("한국어 응답 품질 의심 — 한글 비율 30% 미만")
        return 1

    save_sample(
        "10_deepseek",
        {
            "endpoint": API_URL,
            "model": payload["model"],
            "prompt_preview": PROMPT[:300],
            "response": msg,
            "usage": usage,
            "cost_krw_estimate": round(cost_krw, 2),
            "hangul_ratio": round(hangul_ratio, 3),
        },
    )
    ok("DeepSeek API 검증 통과 — 한국어 자연어 리포트 생성 성공")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
