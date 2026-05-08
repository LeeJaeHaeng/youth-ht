"""Kaggle 데이터 수집 스크립트 — 아파트 + 연립다세대 전월세 5년치.

## Kaggle 실행 방법
1. Kaggle 노트북 생성 (New Notebook → Script 또는 Notebook)
2. Secrets 추가 (Settings → Add-ons → Secrets):
   - DATA_GO_KR_KEY_DECODING: 공공데이터포털 일반 인증키(Decoding)
3. 이 파일 전체 복사 붙여넣기 후 실행
4. 완료 후 Output 탭 → 파일 다운로드 (apt_rent.parquet, villa_rent.parquet)
   또는 "Save Version" → Dataset으로 저장 → 다음 노트북에서 활용

## 수집 범위
- 수도권 + 광역시 113개 시군구 (KNOWN_METRO)
- 2020-01 ~ 현재 전월 (약 75개월)
- 예상 호출 수: 113 × 75 × 2 = 16,950 회
- 예상 소요: 2.5 ~ 3시간 (2 calls/sec)
- 예상 출력 크기: apt ~500MB, villa ~200MB (zstd parquet)

## 로컬 실행 방법
  pip install httpx polars tqdm
  DATA_GO_KR_KEY_DECODING=<키> python collect_rent.py
"""
from __future__ import annotations

import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import httpx
import polars as pl
from tqdm import tqdm

# ── 환경 ─────────────────────────────────────────────────────────────────────
IS_KAGGLE = Path("/kaggle").exists()
OUT_DIR = Path("/kaggle/working") if IS_KAGGLE else Path("data/processed")
CKPT_DIR = Path("/kaggle/working") if IS_KAGGLE else Path("data/checkpoints")
OUT_DIR.mkdir(parents=True, exist_ok=True)
CKPT_DIR.mkdir(parents=True, exist_ok=True)

# Kaggle Secrets는 os.environ에 자동 주입되지 않음 → UserSecretsClient로 직접 읽어야 함
if IS_KAGGLE:
    try:
        from kaggle_secrets import UserSecretsClient
        DATA_KEY = UserSecretsClient().get_secret("DATA_GO_KR_KEY_DECODING")
    except Exception:
        DATA_KEY = os.environ.get("DATA_GO_KR_KEY_DECODING", "")
else:
    DATA_KEY = os.environ.get("DATA_GO_KR_KEY_DECODING", "")

if not DATA_KEY:
    raise RuntimeError("DATA_GO_KR_KEY_DECODING 미설정. Kaggle Secrets에 추가하세요.")

# ── 시군구 목록 ───────────────────────────────────────────────────────────────
KNOWN_METRO: list[tuple[str, str]] = [
    # 서울 25개 자치구
    ("11110", "서울 종로구"), ("11140", "서울 중구"), ("11170", "서울 용산구"),
    ("11200", "서울 성동구"), ("11215", "서울 광진구"), ("11230", "서울 동대문구"),
    ("11260", "서울 중랑구"), ("11290", "서울 성북구"), ("11305", "서울 강북구"),
    ("11320", "서울 도봉구"), ("11350", "서울 노원구"), ("11380", "서울 은평구"),
    ("11410", "서울 서대문구"), ("11440", "서울 마포구"), ("11470", "서울 양천구"),
    ("11500", "서울 강서구"), ("11530", "서울 구로구"), ("11545", "서울 금천구"),
    ("11560", "서울 영등포구"), ("11590", "서울 동작구"), ("11620", "서울 관악구"),
    ("11650", "서울 서초구"), ("11680", "서울 강남구"), ("11710", "서울 송파구"),
    ("11740", "서울 강동구"),
    # 부산 16개
    ("26110", "부산 중구"), ("26140", "부산 서구"), ("26170", "부산 동구"),
    ("26200", "부산 영도구"), ("26230", "부산 부산진구"), ("26260", "부산 동래구"),
    ("26290", "부산 남구"), ("26320", "부산 북구"), ("26350", "부산 해운대구"),
    ("26380", "부산 사하구"), ("26410", "부산 금정구"), ("26440", "부산 강서구"),
    ("26470", "부산 연제구"), ("26500", "부산 수영구"), ("26530", "부산 사상구"),
    ("26710", "부산 기장군"),
    # 대구 8개
    ("27110", "대구 중구"), ("27140", "대구 동구"), ("27170", "대구 서구"),
    ("27200", "대구 남구"), ("27230", "대구 북구"), ("27260", "대구 수성구"),
    ("27290", "대구 달서구"), ("27710", "대구 달성군"),
    # 인천 10개
    ("28110", "인천 중구"), ("28140", "인천 동구"), ("28177", "인천 미추홀구"),
    ("28185", "인천 연수구"), ("28200", "인천 남동구"), ("28237", "인천 부평구"),
    ("28245", "인천 계양구"), ("28260", "인천 서구"), ("28710", "인천 강화군"),
    ("28720", "인천 옹진군"),
    # 광주 5개
    ("29110", "광주 동구"), ("29140", "광주 서구"), ("29155", "광주 남구"),
    ("29170", "광주 북구"), ("29200", "광주 광산구"),
    # 대전 5개
    ("30110", "대전 동구"), ("30140", "대전 중구"), ("30170", "대전 서구"),
    ("30200", "대전 유성구"), ("30230", "대전 대덕구"),
    # 울산 5개
    ("31110", "울산 중구"), ("31140", "울산 남구"), ("31170", "울산 동구"),
    ("31200", "울산 북구"), ("31710", "울산 울주군"),
    # 세종 1개
    ("36110", "세종특별자치시"),
    # 경기 핵심 (분구 기준)
    ("41111", "경기 수원 장안구"), ("41113", "경기 수원 권선구"),
    ("41115", "경기 수원 팔달구"), ("41117", "경기 수원 영통구"),
    ("41131", "경기 성남 수정구"), ("41133", "경기 성남 중원구"),
    ("41135", "경기 성남 분당구"),
    ("41150", "경기 의정부시"),
    ("41171", "경기 안양 만안구"), ("41173", "경기 안양 동안구"),
    ("41190", "경기 부천시"),
    ("41210", "경기 광명시"), ("41220", "경기 평택시"),
    ("41271", "경기 안산 상록구"), ("41273", "경기 안산 단원구"),
    ("41281", "경기 고양 덕양구"), ("41285", "경기 고양 일산동구"), ("41287", "경기 고양 일산서구"),
    ("41290", "경기 과천시"), ("41310", "경기 구리시"),
    ("41360", "경기 남양주시"),
    ("41370", "경기 오산시"), ("41390", "경기 시흥시"),
    ("41410", "경기 군포시"), ("41430", "경기 의왕시"), ("41450", "경기 하남시"),
    ("41461", "경기 용인 처인구"), ("41463", "경기 용인 기흥구"), ("41465", "경기 용인 수지구"),
    ("41480", "경기 파주시"),
    ("41500", "경기 이천시"), ("41550", "경기 안성시"),
    ("41570", "경기 김포시"),
    ("41590", "경기 화성시"), ("41610", "경기 광주시"),
    ("41630", "경기 양주시"), ("41650", "경기 포천시"), ("41670", "경기 여주시"),
]

APT_URL   = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
VILLA_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent"

# ── 날짜 범위 ─────────────────────────────────────────────────────────────────
def yyyymm_range(start: date, end: date) -> list[str]:
    out = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y:04d}{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out

today = date.today()
end_ym = date(today.year, today.month - 1, 1) if today.month > 1 else date(today.year - 1, 12, 1)
MONTHS = yyyymm_range(date(2020, 1, 1), end_ym)
print(f"수집 기간: 2020-01 ~ {end_ym.strftime('%Y-%m')} ({len(MONTHS)}개월)")
print(f"시군구: {len(KNOWN_METRO)}개")
print(f"예상 호출 수: {len(KNOWN_METRO) * len(MONTHS) * 2:,} (아파트+연립)")

# ── 체크포인트 ────────────────────────────────────────────────────────────────
class Checkpoint:
    def __init__(self, name: str) -> None:
        self.path = CKPT_DIR / f"{name}.json"
        self.done: set[str] = set()
        if self.path.exists():
            try:
                self.done = set(json.loads(self.path.read_text()))
            except Exception:
                pass
        print(f"[CKPT] {name}: {len(self.done)}건 이미 완료 (resume)")

    def is_done(self, key: str) -> bool:
        return key in self.done

    def mark(self, key: str) -> None:
        self.done.add(key)

    def save(self) -> None:
        self.path.write_text(json.dumps(sorted(self.done)))


# ── XML 파싱 ──────────────────────────────────────────────────────────────────
def parse_xml(text: str) -> list[dict]:
    root = ET.fromstring(text)
    code = root.findtext(".//resultCode") or ""
    if code not in ("00", "000"):
        msg = root.findtext(".//resultMsg") or ""
        raise RuntimeError(f"API 오류 resultCode={code}: {msg}")
    return [{c.tag: (c.text or "").strip() for c in item}
            for item in root.findall(".//item")]


def normalize(rows: list[dict], lawd_cd: str, ymd: str) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame()
    df = pl.DataFrame(rows)
    casts = []
    for c in ("deposit", "monthlyRent"):
        if c in df.columns:
            casts.append(pl.col(c).str.replace_all(",", "").cast(pl.Int64, strict=False).alias(c))
    for c in ("buildYear", "dealDay", "dealMonth", "dealYear", "floor"):
        if c in df.columns:
            casts.append(pl.col(c).cast(pl.Int32, strict=False).alias(c))
    if "excluUseAr" in df.columns:
        casts.append(pl.col("excluUseAr").cast(pl.Float32, strict=False).alias("excluUseAr"))
    if casts:
        df = df.with_columns(casts)
    return df.with_columns([pl.lit(lawd_cd).alias("lawd_cd"), pl.lit(ymd).alias("deal_ymd")])


def fetch_one(client: httpx.Client, url: str, lawd_cd: str, ymd: str) -> pl.DataFrame:
    all_rows: list[dict] = []
    page = 1
    while True:
        params = {"serviceKey": DATA_KEY, "LAWD_CD": lawd_cd,
                  "DEAL_YMD": ymd, "numOfRows": "1000", "pageNo": str(page)}
        for attempt in range(5):
            try:
                r = client.get(url, params=params, timeout=30)
                if r.status_code >= 500:
                    raise httpx.HTTPStatusError(f"{r.status_code}", request=r.request, response=r)
                break
            except (httpx.HTTPError, httpx.TimeoutException):
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)
        rows = parse_xml(r.text)
        all_rows.extend(rows)
        if len(rows) < 1000:
            break
        page += 1
    return normalize(all_rows, lawd_cd, ymd)


def append_parquet(df: pl.DataFrame, out: Path) -> None:
    if df.is_empty():
        return
    if out.exists():
        existing = pl.read_parquet(out)
        df = pl.concat([existing, df], how="diagonal_relaxed")
    df.write_parquet(out, compression="zstd")


# ── 수집 실행 ─────────────────────────────────────────────────────────────────
def collect(url: str, out: Path, ckpt_name: str) -> None:
    cp = Checkpoint(ckpt_name)
    rl_interval = 0.5  # 2 calls/sec

    with httpx.Client(http2=False) as client:
        total = len(KNOWN_METRO) * len(MONTHS)
        with tqdm(total=total, desc=ckpt_name) as pbar:
            for lawd_cd, name in KNOWN_METRO:
                for ymd in MONTHS:
                    ck = f"{lawd_cd}|{ymd}"
                    if cp.is_done(ck):
                        pbar.update(1)
                        continue
                    time.sleep(rl_interval)
                    try:
                        df = fetch_one(client, url, lawd_cd, ymd)
                        append_parquet(df, out)
                        cp.mark(ck)
                    except Exception as e:
                        tqdm.write(f"[ERR] {ck} ({name}): {e}")
                    finally:
                        pbar.update(1)
                cp.save()

    cp.save()
    if out.exists():
        df = pl.read_parquet(out)
        size_mb = out.stat().st_size / 1024 / 1024
        print(f"\n[DONE] {ckpt_name}: {len(df):,}행 ({size_mb:.1f}MB) → {out}")
    else:
        print(f"\n[WARN] {ckpt_name}: 수집 데이터 없음")


print("\n=== 아파트 전월세 수집 시작 ===")
collect(APT_URL, OUT_DIR / "apt_rent_history.parquet", "apt_rent")

print("\n=== 연립다세대 전월세 수집 시작 ===")
collect(VILLA_URL, OUT_DIR / "villa_rent_history.parquet", "villa_rent")

print("\n=== 완료 ===")
print(f"출력 디렉토리: {OUT_DIR}")
for f in OUT_DIR.glob("*.parquet"):
    print(f"  {f.name}: {f.stat().st_size / 1024 / 1024:.1f}MB")
