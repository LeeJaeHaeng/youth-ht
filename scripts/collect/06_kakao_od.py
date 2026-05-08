"""카카오 Directions API — 시군구 centroid × 직장 클러스터 OD 매트릭스 빌드.

입력:
  data/processed/sigungu_centroid.parquet  — 268 시군구 (lat, lng)
  docs/work_clusters.csv                  — 108 직장 클러스터 (lat, lng)

출력:
  data/processed/kakao_od.parquet
  컬럼: sigungu_code, cluster_id, commute_min (자동차 기준)

규모: 268 × 108 = 28,944 쌍
실행 시간: 약 45분 (5 calls/sec, 카카오 월 30만 한도 내)
카카오 Directions API: https://developers.kakao.com/docs/latest/ko/local/dev-guide#search-by-keyword

로컬 실행:
  python scripts/collect/06_kakao_od.py

환경변수: KAKAO_REST_KEY (.env)
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx
import polars as pl
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import PROCESSED_DIR, Checkpoint, RateLimiter, env, safe_run  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CLUSTERS_CSV = ROOT / "docs" / "work_clusters.csv"
CENTROID_PARQUET = PROCESSED_DIR / "sigungu_centroid.parquet"
OUT_PARQUET = PROCESSED_DIR / "kakao_od.parquet"
CHECKPOINT_NAME = "06_kakao_od"

KAKAO_DIRECTIONS_URL = "https://apis.openapi.sk.com/tmap/routes"
KAKAO_LOCAL_URL = "https://dapi.kakao.com/v2/local/search/address.json"


def load_clusters() -> list[dict]:
    """work_clusters.csv → [{cluster_id, name, lat, lng}, ...]."""
    if not CLUSTERS_CSV.exists():
        raise FileNotFoundError(f"{CLUSTERS_CSV} 없음 — docs/work_clusters.csv 필요")
    df = pl.read_csv(CLUSTERS_CSV)
    required = {"cluster_id", "lat", "lng"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"work_clusters.csv 컬럼 누락: {missing}")
    return df.to_dicts()


def load_centroids() -> list[dict]:
    """sigungu_centroid.parquet → [{sigungu_code, name, lat, lng}, ...]."""
    if not CENTROID_PARQUET.exists():
        raise FileNotFoundError(f"{CENTROID_PARQUET} 없음 — 12_resolve_sigungu_centroid.py 먼저 실행")
    return pl.read_parquet(CENTROID_PARQUET).to_dicts()


KAKAO_NAVI_URL = "https://apis-navi.kakaomobility.com/v1/directions"


def kakao_car_directions(client: httpx.Client, key: str,
                         origin_lat: float, origin_lng: float,
                         dest_lat: float, dest_lng: float) -> float | None:
    """카카오모빌리티 자동차 길찾기 → 소요시간(분). 실패 시 None."""
    headers = {"Authorization": f"KakaoAK {key}"}
    params = {
        "origin": f"{origin_lng},{origin_lat}",
        "destination": f"{dest_lng},{dest_lat}",
        "priority": "RECOMMEND",
    }
    try:
        r = client.get(KAKAO_NAVI_URL, headers=headers, params=params, timeout=15)
    except Exception:
        return None

    if r.status_code != 200:
        return None
    try:
        routes = r.json().get("routes") or []
        if routes:
            summary = routes[0].get("summary") or {}
            duration_sec = summary.get("duration", 0)
            return round(duration_sec / 60, 1)
    except Exception:
        pass
    return None


def haversine_min(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """직선거리 기반 통근시간 근사 (API 실패 fallback). 평균 30km/h 가정."""
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    dist_km = 2 * R * math.asin(math.sqrt(a))
    return round(dist_km / 30 * 60, 1)  # 30km/h 평균


def collect(cp: Checkpoint) -> None:
    key = env("KAKAO_REST_KEY")
    clusters = load_clusters()
    centroids = load_centroids()

    rl = RateLimiter(calls_per_sec=5.0)
    rows: list[dict] = []

    total = len(centroids) * len(clusters)
    print(f"OD 매트릭스: {len(centroids)} 시군구 × {len(clusters)} 클러스터 = {total:,} 쌍")

    with httpx.Client() as client:
        with tqdm(total=total, desc="kakao_od") as pbar:
            for sg in centroids:
                for cl in clusters:
                    ck = f"{sg['sigungu_code']}|{cl['cluster_id']}"
                    if cp.is_done(ck):
                        pbar.update(1)
                        continue

                    rl.wait()
                    commute_min = kakao_car_directions(
                        client, key,
                        sg["lat"], sg["lng"],
                        float(cl["lat"]), float(cl["lng"]),
                    )
                    if commute_min is None:
                        # fallback: 직선거리 근사
                        commute_min = haversine_min(
                            sg["lat"], sg["lng"],
                            float(cl["lat"]), float(cl["lng"]),
                        )

                    rows.append({
                        "sigungu_code": sg["sigungu_code"],
                        "cluster_id": int(cl["cluster_id"]),
                        "commute_min": commute_min,
                    })
                    cp.mark(ck)
                    pbar.update(1)

                # 시군구마다 저장
                if rows:
                    _save(rows)
                    rows = []
                cp.save()

    if rows:
        _save(rows)


def _save(rows: list[dict]) -> None:
    df_new = pl.DataFrame(rows)
    if OUT_PARQUET.exists():
        existing = pl.read_parquet(OUT_PARQUET)
        df_new = pl.concat([existing, df_new])
    df_new.write_parquet(OUT_PARQUET, compression="zstd")


def main() -> int:
    if not CENTROID_PARQUET.exists():
        print(f"[FAIL] {CENTROID_PARQUET} 없음")
        return 1
    if not CLUSTERS_CSV.exists():
        print(f"[FAIL] {CLUSTERS_CSV} 없음")
        return 1

    safe_run(CHECKPOINT_NAME, collect)

    if OUT_PARQUET.exists():
        df = pl.read_parquet(OUT_PARQUET)
        size_mb = OUT_PARQUET.stat().st_size / 1024 / 1024
        print(f"\n[DONE] OD 매트릭스: {len(df):,} 쌍 ({size_mb:.1f}MB) → {OUT_PARQUET}")
        print(f"  통근시간 범위: {df['commute_min'].min():.0f}분 ~ {df['commute_min'].max():.0f}분")
        print(f"  평균: {df['commute_min'].mean():.1f}분")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
