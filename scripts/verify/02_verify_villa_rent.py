"""국토교통부 연립다세대 전월세 실거래가 API 검증.

엔드포인트는 아파트와 다름 (RTMSDataSvcRHRent).
같은 공공데이터포털 키 사용 가능 여부 + 대지권면적 필드 확인.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import banner, env, fail, ok, save_sample

API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent"
EXPECTED_FIELDS = {
    "deposit",
    "monthlyRent",
    "excluUseAr",
    "umdNm",
    "dealYear",
    "dealMonth",
    "dealDay",
    "floor",
    "buildYear",
}


def main() -> int:
    banner("Task 02 — 국토교통부 연립다세대 전월세 실거래가 API")
    key = env("DATA_GO_KR_KEY_DECODING")

    params = {
        "serviceKey": key,
        "LAWD_CD": "11680",
        "DEAL_YMD": "202401",
        "numOfRows": "10",
        "pageNo": "1",
    }

    try:
        r = requests.get(API_URL, params=params, timeout=20)
    except requests.RequestException as e:
        fail(f"네트워크 오류: {e}")
        return 1

    print(f"Status: {r.status_code}, len={len(r.content)}B")
    print(r.text[:600])
    print("...")

    if r.status_code != 200:
        fail(f"HTTP {r.status_code}")
        return 1

    try:
        root = ET.fromstring(r.text)
    except ET.ParseError as e:
        fail(f"XML 파싱 실패: {e}")
        return 1

    result_code = root.findtext(".//resultCode")
    items = root.findall(".//item")
    print(f"resultCode={result_code}, 받은 거래={len(items)}")

    if result_code not in ("00", "000"):
        fail(f"resultCode={result_code}")
        return 1
    if not items:
        fail("거래 건수 0")
        return 1

    fields = {child.tag for child in items[0]}
    missing = EXPECTED_FIELDS - fields
    if missing:
        fail(f"기대 필드 누락: {missing}")
        print(f"실제 필드: {fields}")
        return 1

    sample = {child.tag: child.text for child in items[0]}
    print("샘플 거래 1건:")
    for k, v in sample.items():
        print(f"  {k}: {v}")

    has_land_area = any("land" in f.lower() or "plottage" in f.lower() for f in fields)
    print(f"대지권면적 관련 필드 존재 여부: {has_land_area}")

    save_sample(
        "02_villa_rent",
        {
            "endpoint": API_URL,
            "result_code": result_code,
            "total_count": len(items),
            "first_item": sample,
            "fields": sorted(fields),
            "has_land_area_field": has_land_area,
        },
    )
    ok("연립다세대 전월세 API 검증 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
