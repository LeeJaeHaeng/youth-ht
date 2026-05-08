"""행정안전부 주민등록인구 OpenAPI 검증.

`.env`의 `POPULATION_API_URL` 슬롯이 채워지면 그 URL로 검증한다.
비어 있으면 후보 5개 엔드포인트 탐색(0주차 결과: 모두 실패).

사용자 액션:
  1) data.go.kr 마이페이지 → '행정안전부_통계연보_지역별 주민등록인구' 상세
  2) End Point 복사 → .env 의 POPULATION_API_URL 에 붙여넣기
  3) 본 스크립트 재실행 — 즉시 검증 통과 가능
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import banner, env, fail, ok, save_sample

CANDIDATES_FALLBACK = [
    ("https://apis.data.go.kr/1741000/StanReginCd/getStanReginCdList", "행정표준코드"),
    ("https://apis.data.go.kr/1741000/admmSexdAgePopulation/selectAdmmSexdAgePopulation", "성연령별인구"),
    ("https://apis.data.go.kr/1741000/RegPopulation/selectRegPopulation", "지역별인구"),
]


def call(url: str, key: str, extra: dict[str, str]) -> requests.Response | None:
    params = {
        "serviceKey": key,
        "type": "json",
        "pageNo": "1",
        "numOfRows": "5",
        **extra,
    }
    try:
        return requests.get(url, params=params, timeout=20)
    except requests.RequestException:
        return None


def parse_extra(s: str) -> dict[str, str]:
    if not s:
        return {}
    out: dict[str, str] = {}
    for chunk in s.split("&"):
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def main() -> int:
    banner("Task 03 — 행정안전부 주민등록인구 OpenAPI")
    key = env("DATA_GO_KR_KEY_DECODING")

    user_url = os.getenv("POPULATION_API_URL", "").strip()
    extra = parse_extra(os.getenv("POPULATION_EXTRA_PARAMS", ""))

    if user_url:
        # ------ 정상 모드: 사용자 채워진 명세로 직접 검증 ------
        print(f"[USER] 사용자 지정 URL: {user_url}")
        r = call(user_url, key, extra)
        if r is None:
            fail("네트워크 오류")
            return 1
        print(f"Status: {r.status_code}, len={len(r.content)}B")
        print(r.text[:1500])

        if r.status_code != 200:
            fail(f"HTTP {r.status_code}")
            return 1

        ct = (r.headers.get("Content-Type") or "").lower()
        parsed: dict | None = None
        if "json" in ct or r.text.lstrip().startswith("{"):
            try:
                parsed = r.json()
                print(f"JSON 키: {list(parsed.keys())[:10]}")
            except Exception as e:  # noqa: BLE001
                fail(f"JSON 파싱 실패: {e}")
                return 1
        else:
            try:
                root = ET.fromstring(r.text)
                print(f"XML 루트: {root.tag}")
                parsed = {"root": root.tag}
            except ET.ParseError:
                fail("응답 형식 미확인 (JSON/XML 모두 실패)")
                return 1

        save_sample(
            "03_population",
            {
                "endpoint": user_url,
                "extra_params": extra,
                "status": r.status_code,
                "preview": r.text[:2000],
                "parsed_keys": parsed,
            },
        )
        ok("사용자 명세 기반 검증 통과")
        return 0

    # ------ Fallback: .env 슬롯 미채움 시 후보 탐색 ------
    print("[INFO] POPULATION_API_URL 미설정 — 후보 엔드포인트 탐색")
    print("       .env 채우면 즉시 정상 검증 모드 진입")
    results = []
    success: requests.Response | None = None
    for url, label in CANDIDATES_FALLBACK:
        r = call(url, key, {})
        results.append({"url": url, "label": label, "status": r.status_code if r else None})
        print(f"[{r.status_code if r else 'NET ERR'}] {label}")
        if r and r.status_code == 200 and "Unexpected" not in r.text and len(r.text) > 50:
            success = r
            break

    save_sample("03_population", {"mode": "fallback_search", "results": results})
    if success:
        ok("후보 탐색에서 응답 발견 — 위 URL을 .env POPULATION_API_URL 에 등록 권장")
        return 0
    fail("후보 모두 실패 — 사용자 액션 필요 (docs/user_action_required.md §A)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
