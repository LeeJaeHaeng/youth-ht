"""SGIS 1km 격자 Shapefile → centroid + 시군구 매핑.

사용자 액션 필요:
  1) https://sgis.kostat.go.kr/ 로그인
  2) "통계지리정보서비스 → 통계지도 → 격자형 1km 경계" 다운로드 신청
  3) 받은 Shapefile을 data/raw/grid_1km/grid_1km.shp 로 배치

산출: data/processed/grid_centroid.parquet
컬럼: grid_id, sigungu_code, centroid_lat, centroid_lng
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collect"))
from _http import PROCESSED_DIR, RAW_DIR  # noqa: E402

SHP = RAW_DIR / "grid_1km" / "grid_1km.shp"
OUT = PROCESSED_DIR / "grid_centroid.parquet"


def main() -> int:
    if not SHP.exists():
        print(f"[FAIL] {SHP} 없음")
        print("       사용자 액션 필요 — sgis.kostat.go.kr 에서 1km 격자 Shapefile 다운로드 후 배치")
        return 2

    # geopandas 로드는 사용자가 Shapefile 배치 후 실행될 때만
    import geopandas as gpd

    gdf = gpd.read_file(SHP).to_crs("EPSG:4326")
    print(f"격자 개수: {len(gdf):,}")
    print(f"컬럼: {gdf.columns.tolist()}")

    # 격자 ID 컬럼 후보
    # SGIS 1km 격자: SPO_NO_CD=격자코드(10자), SECT_CD=시군구코드(5자리)
    id_col = next(
        (c for c in ("SPO_NO_CD", "GRID_CD", "grid_cd", "GRID_ID", "grid_id", "ID", "id") if c in gdf.columns),
        None,
    )
    sg_col = next(
        (c for c in ("SECT_CD", "SGG_CD", "sigungu_code") if c in gdf.columns),
        None,
    )
    if not id_col:
        print("[FAIL] grid_id 컬럼 미검출")
        print(f"실제 컬럼: {gdf.columns.tolist()}")
        return 1

    gdf["centroid"] = gdf.geometry.centroid
    gdf["centroid_lat"] = gdf["centroid"].y
    gdf["centroid_lng"] = gdf["centroid"].x

    cols = {id_col: "grid_id", "centroid_lat": "centroid_lat", "centroid_lng": "centroid_lng"}
    keep = [id_col, "centroid_lat", "centroid_lng"]
    if sg_col:
        keep.append(sg_col)
        cols[sg_col] = "sigungu_code"

    out = gdf[keep].rename(columns=cols)
    if "sigungu_code" not in out.columns:
        out["sigungu_code"] = None
    out.to_parquet(OUT, compression="zstd")
    print(f"[DONE] {len(out):,} 격자 → {OUT}")
    print(f"시군구 코드 예시: {out['sigungu_code'].unique()[:5].tolist() if 'sigungu_code' in out.columns else 'N/A'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
