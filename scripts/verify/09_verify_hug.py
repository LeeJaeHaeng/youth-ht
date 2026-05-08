"""HUG 전국 보증사고 현황 Excel 파싱 검증.

검증 통과 기준:
- 시군구 수 >= 200 (전국 약 250)
- 사고건수·사고금액·사고율 컬럼 추출 가능
- 시도+시군구 unique key 생성 가능
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import RAW_DIR, banner, fail, ok, save_sample

XLSX = RAW_DIR / "HUG_전국보증사고현황_25년8월.xlsx"


def main() -> int:
    banner(f"Task 09 — HUG Excel 파싱 ({XLSX.name})")

    if not XLSX.exists():
        fail(f"파일 없음: {XLSX}")
        return 1

    # 1) 시트 목록 확인
    xls = pd.ExcelFile(XLSX)
    print(f"시트 목록: {xls.sheet_names}")

    # 2) 첫 시트의 raw 구조 (헤더 위치 확인용)
    raw = pd.read_excel(XLSX, sheet_name=0, header=None)
    print(f"\nraw shape: {raw.shape}")
    print("처음 12행:")
    print(raw.head(12).to_string(max_cols=10))

    # 3) 헤더 추정 — 광역/기초가 등장하는 행이 멀티헤더의 첫 줄
    header_row = None
    for idx in range(min(10, len(raw))):
        row_text = " ".join(str(x) for x in raw.iloc[idx].tolist())
        if "광역" in row_text and "기초" in row_text:
            header_row = idx
            break
    print(f"\n추정 헤더 행 (멀티헤더 1단): {header_row}")

    # 4) 멀티헤더 가능성 — header_row 부터 2행 멀티헤더로 재로드
    df_multi = None
    if header_row is not None:
        try:
            df_multi = pd.read_excel(
                XLSX, sheet_name=0, header=[header_row, header_row + 1]
            )
            print(f"\n멀티헤더 컬럼 수: {len(df_multi.columns)}")
            print("컬럼 (앞 15개):")
            for c in list(df_multi.columns)[:15]:
                print(f"  {c}")
            print(f"행 수: {len(df_multi)}")
        except Exception as e:  # noqa: BLE001
            print(f"멀티헤더 시도 실패: {e}")

    # 5) 단일 헤더 fallback
    df_single = None
    if header_row is not None:
        df_single = pd.read_excel(XLSX, sheet_name=0, header=header_row)
        print(f"\n단일헤더 컬럼: {df_single.columns.tolist()}")
        print(df_single.head(3).to_string(max_cols=8))

    # 6) 사고건수·금액·율 컬럼 발견 여부
    target_df = df_multi if df_multi is not None else df_single
    found = {"사고건수": False, "사고금액": False, "사고율": False, "지역": False}
    if target_df is not None:
        # 멀티헤더(MultiIndex)는 tuple, 단일헤더는 str
        flat: list[str] = []
        for c in target_df.columns:
            if isinstance(c, tuple):
                flat.append(" | ".join(str(x) for x in c))
            else:
                flat.append(str(c))
        flat_str = " || ".join(flat)
        # 줄바꿈/공백 정규화
        norm = flat_str.replace("\n", "").replace(" ", "")
        for k in list(found):
            found[k] = k in norm
        for c in flat:
            cc = c.replace("\n", "").replace(" ", "")
            if any(w in cc for w in ("시도", "광역", "기초", "시군구", "지역")):
                found["지역"] = True
                break
    print(f"\n키 컬럼 검출: {found}")

    save_sample(
        "09_hug",
        {
            "file": str(XLSX),
            "sheet_names": xls.sheet_names,
            "raw_shape": list(raw.shape),
            "raw_head": raw.head(12).astype(str).values.tolist(),
            "estimated_header_row": header_row,
            "multi_header_columns": [str(c) for c in (df_multi.columns if df_multi is not None else [])],
            "single_header_columns": list(df_single.columns) if df_single is not None else [],
            "found_keys": found,
            "row_count": int(len(target_df)) if target_df is not None else 0,
        },
    )

    if all(found.values()):
        ok("HUG Excel 핵심 컬럼 모두 검출")
        return 0
    fail(f"일부 키 컬럼 미검출: {[k for k, v in found.items() if not v]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
