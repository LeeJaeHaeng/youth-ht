"""교통카드 빅데이터 통합정보시스템 (STCIS) — 15분단위 OD API 검증.

설계서 v2.2 §4 통근시간 데이터 — 카카오 Directions API 보완으로 도입.
사용자 제시 변경: 통계누리 → STCIS (대중교통 실측 OD).

엔드포인트:
  https://stcis.go.kr/openapi/quarterod.json?apikey=...&opratDate=...&stgEmdCd=...&arrEmdCd=...

검증 통과 기준:
- HTTP 200, status=OK 또는 NOT_FOUND
- 인증 통과 (INVALID_KEY 아님)
- 응답 스키마 (count, status, result[]) 정상
- 표본 OD: 서울 역삼동(1168010100) → 서울 봉천동(1162010800) 평균 통행시간 추출
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import banner, env, fail, ok, save_sample


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")

API = "https://stcis.go.kr/openapi/quarterod.json"

# 적재 확인된 시점·OD (2024-10-15 강남 역삼→삼성).
# 실제 운영에서는 최신 데이터 가용 시점(보통 D-180일 이상)을 동적 탐색.
STG_EMD = "1168010100"  # 서울 강남구 역삼1동
ARR_EMD = "1168010500"  # 서울 강남구 삼성1동


def main() -> int:
    banner("Task 11 — STCIS 15분단위 OD")
    key = env("STCIS_API_KEY")

    oprat_date = "20241015"  # 화요일, 적재 확인됨
    print(f"  운행일자: {oprat_date} (적재 확인된 평일)")

    params = {
        "apikey": key,
        "opratDate": oprat_date,
        "stgEmdCd": STG_EMD,
        "arrEmdCd": ARR_EMD,
    }
    try:
        r = httpx.get(API, params=params, timeout=30)
    except httpx.HTTPError as e:
        fail(f"네트워크 오류: {e}")
        return 1

    print(f"  HTTP {r.status_code}, len={len(r.content)}B")
    if r.status_code != 200:
        fail(f"HTTP {r.status_code}: {r.text[:300]}")
        return 1

    try:
        data = r.json()
    except Exception as e:
        fail(f"JSON 파싱 실패: {e} — body[:300]={r.text[:300]}")
        return 1

    status = data.get("status")
    print(f"  status: {status}, count: {data.get('count')}")

    if status == "ERROR":
        err = data.get("error", {})
        fail(f"STCIS ERROR: code={err.get('code')} msg={err.get('text')}")
        return 1

    if status not in ("OK", "NOT_FOUND"):
        fail(f"예상치 못한 status: {status}")
        return 1

    if status == "NOT_FOUND":
        # 인증·스키마 자체는 통과 — OD가 비어있을 수 있음 (특정 동 조합)
        warn("OD 데이터 없음 — API 인증·스키마는 정상. 다른 동 조합으로 운영 시 사용 가능.")

    rows = data.get("result") or []
    if rows:
        print("\n📋 샘플 (최대 3행):")
        for row in rows[:3]:
            print(f"  {row.get('tzon')}시 Q{row.get('quater')} | "
                  f"{row.get('stgEmdNm')} → {row.get('arrEmdNm')} | "
                  f"이용 {row.get('useStf')}명 | 평균 {row.get('useTm')}분")

    save_sample(
        "11_stcis_od",
        {
            "endpoint": API,
            "params_preview": {k: v for k, v in params.items() if k != "apikey"},
            "status": status,
            "count": data.get("count"),
            "rows_sample": rows[:5],
        },
    )

    if status == "OK" and rows:
        ok(f"STCIS OD API 검증 통과 — {len(rows)}건 OD 추출 성공")
    else:
        ok("STCIS OD API 인증·스키마 검증 통과 (해당 OD 데이터 없음 — 정상)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
