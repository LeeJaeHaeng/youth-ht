"""한국은행 ECOS API — 기준금리(722Y001 / 0101000) 검증.

검증 통과 기준:
- StatisticSearch.row 배열 존재
- 데이터 건수 >= 24 (2년치 월별 최소)
- TIME 형식 = YYYYMM
- DATA_VALUE 숫자 변환 가능
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import banner, env, fail, ok, save_sample


def main() -> int:
    banner("Task 04 — 한국은행 ECOS 기준금리")
    key = env("ECOS_API_KEY")

    url = (
        f"https://ecos.bok.or.kr/api/StatisticSearch"
        f"/{key}/json/kr/1/100/722Y001/M/202001/202612/0101000"
    )

    try:
        r = requests.get(url, timeout=20)
    except requests.RequestException as e:
        fail(f"네트워크 오류: {e}")
        return 1

    print(f"Status: {r.status_code}, len={len(r.content)}B")

    if r.status_code != 200:
        fail(f"HTTP {r.status_code}")
        return 1

    try:
        data = r.json()
    except Exception as e:  # noqa: BLE001
        fail(f"JSON 파싱 실패: {e}")
        print(r.text[:600])
        return 1

    print(f"최상위 키: {list(data.keys())}")
    if "RESULT" in data:
        fail(f"ECOS 에러: {data['RESULT']}")
        return 1
    if "StatisticSearch" not in data:
        fail("StatisticSearch 키 없음")
        return 1

    block = data["StatisticSearch"]
    rows = block.get("row", [])
    total = block.get("list_total_count")
    print(f"list_total_count={total}, row 길이={len(rows)}")

    if len(rows) < 24:
        fail(f"데이터 건수 부족: {len(rows)} < 24")
        return 1

    # 형식·값 검증
    sample = rows[-3:]
    for row in sample:
        t, v = row.get("TIME"), row.get("DATA_VALUE")
        if not (t and len(t) == 6 and t.isdigit()):
            fail(f"TIME 형식 이상: {t}")
            return 1
        try:
            float(v)
        except (TypeError, ValueError):
            fail(f"DATA_VALUE 숫자 변환 실패: {v}")
            return 1
        print(f"  {t}: {v}%")

    save_sample(
        "04_ecos",
        {
            "endpoint": url.replace(key, "***"),
            "list_total_count": total,
            "row_count": len(rows),
            "first_row": rows[0],
            "last_row": rows[-1],
        },
    )
    ok("ECOS 기준금리 API 검증 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
