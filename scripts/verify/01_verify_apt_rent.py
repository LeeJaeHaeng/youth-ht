"""국토교통부 아파트 전월세 실거래가 API 검증.

검증 통과 기준:
- HTTP 200
- resultCode == "00"
- 거래 건수 >= 1
- 필드: 보증금액, 월세금액, 전용면적, 법정동, 계약년월일, 층, 건축년도
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import banner, env, fail, ok, save_sample

API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
EXPECTED_FIELDS = {
    "deposit",  # 보증금액
    "monthlyRent",  # 월세금액
    "excluUseAr",  # 전용면적
    "umdNm",  # 법정동
    "dealYear",  # 계약년
    "dealMonth",  # 계약월
    "dealDay",  # 계약일
    "floor",  # 층
    "buildYear",  # 건축년도
}


def main() -> int:
    banner("Task 01 — 국토교통부 아파트 전월세 실거래가 API")
    key = env("DATA_GO_KR_KEY_DECODING")

    params = {
        "serviceKey": key,
        "LAWD_CD": "11680",  # 강남구
        "DEAL_YMD": "202401",
        "numOfRows": "10",
        "pageNo": "1",
    }

    try:
        r = requests.get(API_URL, params=params, timeout=20)
    except requests.RequestException as e:
        fail(f"네트워크 오류: {e}")
        return 1

    print(f"Status: {r.status_code}, CT: {r.headers.get('Content-Type')}, len={len(r.content)}B")
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
    result_msg = root.findtext(".//resultMsg")
    print(f"resultCode={result_code}, resultMsg={result_msg}")

    items = root.findall(".//item")
    print(f"받은 거래 건수: {len(items)}")

    if result_code not in ("00", "000"):
        fail(f"resultCode={result_code} ({result_msg})")
        return 1
    if not items:
        fail("거래 건수 0 — 다른 시군구/월로 재시도 필요")
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

    save_sample(
        "01_apt_rent",
        {
            "endpoint": API_URL,
            "params": {k: v for k, v in params.items() if k != "serviceKey"},
            "result_code": result_code,
            "total_count": len(items),
            "first_item": sample,
            "fields": sorted(fields),
        },
    )
    ok("아파트 전월세 API 검증 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
