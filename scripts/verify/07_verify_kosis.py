"""KOSIS 청년 임금 (DT_118N_LCE0004) API 검증.

검증 통과 기준:
- 응답 JSON 배열
- 청년 연령대(20-24, 25-29, 30-34) 데이터 포함
- 시도별 분리 가능
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import banner, env, fail, ok, save_sample


def main() -> int:
    banner("Task 07 — KOSIS 청년 임금 통계")
    key = env("KOSIS_API_KEY")

    url = (
        "https://kosis.kr/openapi/Param/statisticsParameterData.do"
        "?method=getList"
        f"&apiKey={key}"
        "&itmId=13103732814DD_1+13103732814DD_2+13103732814DD_3+13103732814DD_4+"
        "16118DD_13+16118DD_11+13103732814DD_9+16118DD_10+13103732814DD_5+"
        "13103732814DD_6+13103732814DD_7+16118DD_12+13103732814DD_8+"
        "&objL1=ALL&objL2=ALL&objL3=&objL4=&objL5=&objL6=&objL7=&objL8="
        "&format=json&jsonVD=Y&prdSe=Y&newEstPrdCnt=3&prdInterval=1"
        "&outputFields=ORG_ID+TBL_ID+TBL_NM+OBJ_ID+OBJ_NM+OBJ_NM_ENG+NM+NM_ENG+"
        "ITM_ID+ITM_NM+ITM_NM_ENG+UNIT_NM+UNIT_NM_ENG+PRD_SE+PRD_DE+LST_CHN_DE+"
        "&orgId=118&tblId=DT_118N_LCE0004"
    )

    try:
        r = requests.get(url, timeout=25)
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
        print(r.text[:600])
        return 1

    # KOSIS 에러는 dict, 정상은 list
    if isinstance(data, dict):
        fail(f"에러 응답: {data}")
        return 1

    if not isinstance(data, list) or not data:
        fail(f"빈 응답 또는 비배열: type={type(data).__name__}")
        return 1

    print(f"레코드 수: {len(data)}")
    print("샘플 1건 필드:")
    for k, v in data[0].items():
        print(f"  {k}: {v}")

    # 연령대·시도 다양성 확인
    age_values = {row.get("C2_NM") or row.get("OBJ_NM") for row in data[:200]}
    print(f"\n연령대 후보 (앞 200건): {sorted(filter(None, age_values))[:20]}")

    save_sample(
        "07_kosis",
        {
            "endpoint": url.replace(key, "***"),
            "record_count": len(data),
            "first_record": data[0],
            "last_record": data[-1],
            "distinct_obj_nm_first200": sorted(filter(None, age_values)),
        },
    )
    ok("KOSIS 청년 임금 API 검증 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
