"""한국부동산원 R-ONE OpenAPI 검증.

베이스 URL은 확정: https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do
필수 파라미터: KEY, Type, pIndex, pSize, STATBL_ID, DTACYCLE_CD

`.env` REB_UNSOLD_STATBL_ID 가 채워지면 미분양 데이터 직접 호출.
미채움 시 정상 베이스 URL로 빈 호출만 보내 파라미터 에러 메시지 확인.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import banner, env, fail, ok, save_sample

DATA_URL = "https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do"


def main() -> int:
    banner("Task 05 — R-ONE 부동산통계 OpenAPI")
    key = env("REB_API_KEY")
    statbl_id = os.getenv("REB_UNSOLD_STATBL_ID", "").strip()
    dtacycle = os.getenv("REB_UNSOLD_DTACYCLE_CD", "MM").strip()
    wrttime = os.getenv("REB_UNSOLD_WRTTIME_START", "202001").strip()

    if not statbl_id:
        # 미채움 — 빈 호출로 파라미터 에러 메시지 확인 (서비스 가용성 판단)
        print("[INFO] REB_UNSOLD_STATBL_ID 미설정 — 베이스 URL 가용성만 점검")
        try:
            r = requests.get(
                DATA_URL,
                params={"KEY": key, "Type": "json", "pIndex": "1", "pSize": "5"},
                timeout=15,
            )
        except requests.RequestException as e:
            fail(f"네트워크 오류: {e}")
            return 1
        print(f"Status: {r.status_code}")
        print(r.text[:600])
        save_sample(
            "05_reb",
            {
                "endpoint": DATA_URL,
                "mode": "no_statbl_id",
                "status": r.status_code,
                "preview": r.text[:1500],
            },
        )
        # ERROR-310 또는 RESULT-CODE 메시지 받으면 베이스 URL은 살아있다는 뜻
        if r.status_code == 200 and ("RESULT" in r.text or "ERROR" in r.text):
            ok("베이스 URL 살아있음 — STATBL_ID만 .env 채우면 즉시 작동")
            return 0
        fail("베이스 URL 미응답")
        return 1

    # ------ 정상 모드 ------
    print(f"[USER] STATBL_ID={statbl_id}, DTACYCLE_CD={dtacycle}, WRTTIME={wrttime}")
    params = {
        "KEY": key,
        "Type": "json",
        "pIndex": "1",
        "pSize": "10",
        "STATBL_ID": statbl_id,
        "DTACYCLE_CD": dtacycle,
        "WRTTIME_IDTFR_ID": wrttime,
    }
    try:
        r = requests.get(DATA_URL, params=params, timeout=20)
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
    except Exception as e:  # noqa: BLE001
        fail(f"JSON 파싱 실패: {e}")
        return 1

    # 에러 응답 체크
    if isinstance(data, dict) and data.get("RESULT", {}).get("CODE", "").startswith("ERROR"):
        fail(f"R-ONE 에러: {data['RESULT']}")
        return 1

    save_sample(
        "05_reb",
        {
            "endpoint": DATA_URL,
            "params": {k: v for k, v in params.items() if k != "KEY"},
            "preview": r.text[:2000],
            "payload_keys": list(data.keys()) if isinstance(data, dict) else None,
        },
    )
    ok("R-ONE 미분양 데이터 호출 성공")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
