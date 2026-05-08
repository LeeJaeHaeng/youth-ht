"""카카오모빌리티 길찾기 API 검증 (강남역 → 판교역).

검증 통과 기준:
- routes 1개 이상
- summary.distance / summary.duration 추출 가능
- summary.fare 구조 확인 (taxi / toll)
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import banner, env, fail, ok, save_sample

API_URL = "https://apis-navi.kakaomobility.com/v1/directions"


def main() -> int:
    banner("Task 08 — 카카오모빌리티 길찾기 (강남역 → 판교역)")
    key = env("KAKAO_REST_KEY")

    headers = {"Authorization": f"KakaoAK {key}"}
    params = {
        "origin": "127.0276,37.4979",
        "destination": "127.1112,37.3947",
        "priority": "RECOMMEND",
    }

    try:
        r = requests.get(API_URL, headers=headers, params=params, timeout=15)
    except requests.RequestException as e:
        fail(f"네트워크 오류: {e}")
        return 1

    print(f"Status: {r.status_code}, len={len(r.content)}B")

    if r.status_code != 200:
        fail(f"HTTP {r.status_code}")
        print(r.text[:600])
        return 1

    try:
        data = r.json()
    except Exception as e:  # noqa: BLE001
        fail(f"JSON 파싱 실패: {e}")
        return 1

    routes = data.get("routes") or []
    if not routes:
        fail(f"경로 없음: {data}")
        return 1

    summary = routes[0].get("summary") or {}
    distance = summary.get("distance")
    duration = summary.get("duration")
    fare = summary.get("fare") or {}
    print(f"  거리: {distance}m")
    print(f"  시간: {duration}s ({(duration or 0)//60}분)")
    print(f"  요금: taxi={fare.get('taxi')}, toll={fare.get('toll')}")

    if distance is None or duration is None:
        fail("distance/duration 누락")
        return 1

    save_sample(
        "08_kakao",
        {
            "endpoint": API_URL,
            "params": params,
            "summary": summary,
            "result_code": routes[0].get("result_code"),
            "result_msg": routes[0].get("result_msg"),
        },
    )
    ok("카카오 길찾기 API 검증 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
