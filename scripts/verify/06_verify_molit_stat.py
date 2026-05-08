"""국토교통 통계누리 OpenAPI 검증.

`.env` MOLIT_STAT_BASE_URL + MOLIT_STAT_AUTH_PARAM 채우면 즉시 작동.
미채움 시 알려진 후보들로 fallback 탐색.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import banner, env, fail, ok, save_sample

# 0주차 결과: 알려진 후보 모두 404. 정확한 베이스 URL은 사용자 마이페이지 확인.
CANDIDATES_FALLBACK = [
    "https://stat.molit.go.kr/portal/openapi/service/StatTblList.do",
    "http://stat.molit.go.kr/portal/openapi/service/StatTblList.do",
]


def main() -> int:
    banner("Task 06 — 국토교통 통계누리 OpenAPI")
    key = env("MOLIT_STAT_KEY")

    base_url = os.getenv("MOLIT_STAT_BASE_URL", "").strip()
    auth_param = os.getenv("MOLIT_STAT_AUTH_PARAM", "KEY").strip() or "KEY"

    if base_url:
        # ------ 정상 모드 ------
        print(f"[USER] BASE_URL={base_url}, AUTH_PARAM={auth_param}")
        params: dict[str, str] = {auth_param: key, "Type": "json", "pIndex": "1", "pSize": "5"}
        try:
            r = requests.get(base_url, params=params, timeout=20)
        except requests.RequestException as e:
            fail(f"네트워크 오류: {e}")
            return 1

        print(f"Status: {r.status_code}, len={len(r.content)}B")
        print(r.text[:1500])

        if r.status_code != 200:
            fail(f"HTTP {r.status_code}")
            return 1

        try:
            data = r.json()
            print(f"JSON 키: {list(data.keys())[:10]}")
        except Exception:
            data = {"raw": r.text[:1000]}

        save_sample(
            "06_molit_stat",
            {"endpoint": base_url, "auth_param": auth_param, "preview": r.text[:2000], "data": data},
        )
        ok("통계누리 OpenAPI 호출 성공")
        return 0

    # ------ Fallback ------
    print("[INFO] MOLIT_STAT_BASE_URL 미설정 — 알려진 후보 탐색 (0주차 결과: 모두 404)")
    print("       사용자 액션 필요 — docs/user_action_required.md §C")
    results = []
    for url in CANDIDATES_FALLBACK:
        try:
            r = requests.get(url, params={"KEY": key, "Type": "json"}, timeout=15)
            results.append({"url": url, "status": r.status_code})
            print(f"[{r.status_code}] {url}")
        except requests.RequestException as e:
            results.append({"url": url, "error": str(e)})
            print(f"[ERR] {url}: {e}")

    save_sample("06_molit_stat", {"mode": "fallback_search", "results": results})
    fail("후보 모두 404 — 사용자 마이페이지 확인 필요")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
