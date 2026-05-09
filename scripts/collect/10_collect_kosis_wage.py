"""KOSIS 청년 월임금총액 수집기 (GRU #8 입력 — 청년 임금).

KOSIS 공유서비스 API
- orgId=118, tblId=DT_118N_LCE0004 (연령별 임금 및 근로시간)
- 항목: 월임금총액 (ITM_ID=16118DD_10), 단위=천원
- 연령: 29세이하, 30~39세 (청년 가중 평균)
- 주기: 연간 (prdSe=A)

산출: data/processed/kosis_youth_wage.parquet
컬럼: year(int), youth_wage_won(int) — 가중평균 청년 월임금
      + data/processed/kosis_youth_wage_latest.json  (최신연도 단일값)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import polars as pl
import requests

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
OUT_PARQUET = PROCESSED / "kosis_youth_wage.parquet"
OUT_JSON = PROCESSED / "kosis_youth_wage_latest.json"

KOSIS_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
ORG_ID = "118"
TBL_ID = "DT_118N_LCE0004"
ITM_ID_WAGE = "16118DD_10"   # 월임금총액

# 29세이하:30-39세 가중치 (행안부 청년인구 기준 근사)
W_UNDER29 = 0.45
W_30TO39 = 0.55


def fetch_wage(key: str) -> list[dict]:
    """29세이하 + 30~39세 월임금총액 전연도 조회."""
    params = {
        "method": "getList",
        "apiKey": key,
        "itmId": ITM_ID_WAGE,
        "objL1": "ALL",
        "objL2": "ALL",
        "format": "json",
        "jsonVD": "Y",
        "prdSe": "A",
        "newEstPrdCnt": "20",   # 최근 20년
        "prdInterval": "1",
        "orgId": ORG_ID,
        "tblId": TBL_ID,
    }
    r = requests.get(KOSIS_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(f"응답 형식 이상: {str(data)[:200]}")
    return data


def process(rows: list[dict]) -> pl.DataFrame:
    """29세이하 + 30-39세 연도별 가중평균 → youth_wage_won."""
    # C2_NM 확인 (연령 구분)
    age_groups = set(r.get("C2_NM", "") for r in rows)
    print(f"  연령 그룹: {age_groups}")

    target_ages = {"29세이하", "30~39세"}
    filtered = [r for r in rows
                if r.get("C2_NM") in target_ages
                and r.get("C1_NM") == "전체근로자"   # 비정규/특수형태 제외
                and r.get("DT")]

    yearly: dict[int, dict[str, float]] = {}
    for r in filtered:
        year = int(r["PRD_DE"])
        age = r["C2_NM"]
        # DT 단위: 천원 → 원 변환
        wage_won = float(r["DT"]) * 1000
        yearly.setdefault(year, {})[age] = wage_won

    out_rows = []
    for year, wages in sorted(yearly.items()):
        w29 = wages.get("29세이하", 0)
        w30 = wages.get("30~39세", 0)
        if w29 > 0 and w30 > 0:
            weighted = w29 * W_UNDER29 + w30 * W_30TO39
        elif w29 > 0:
            weighted = w29
        elif w30 > 0:
            weighted = w30
        else:
            continue
        out_rows.append({"year": year, "youth_wage_won": int(weighted),
                          "wage_under29": int(w29), "wage_30to39": int(w30)})

    return pl.DataFrame(out_rows).sort("year")


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    key = os.getenv("KOSIS_API_KEY", "").strip()
    if not key:
        print("[FAIL] .env KOSIS_API_KEY 없음")
        return 1

    print("[KOSIS] 청년 월임금총액 수집 시작")
    rows = fetch_wage(key)
    print(f"[INFO] 원본 {len(rows)}건")

    df = process(rows)
    print(f"[INFO] 처리 완료: {len(df)}연도")
    print(df)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUT_PARQUET, compression="zstd")
    print(f"[DONE] → {OUT_PARQUET}")

    # 최신값 JSON (data_loader 빠른 로드용)
    latest = df.sort("year").tail(1).to_dicts()[0]
    OUT_JSON.write_text(json.dumps(latest, ensure_ascii=False, indent=2))
    print(f"[DONE] 최신값: {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
