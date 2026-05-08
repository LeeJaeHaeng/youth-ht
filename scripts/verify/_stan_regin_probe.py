"""법정동코드 API 응답 구조 탐사."""
import os, json
from pathlib import Path
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

KEY = os.getenv("DATA_GO_KR_KEY_DECODING")
URL = "https://apis.data.go.kr/1741000/StanReginCd/getStanReginCdList"

# 시도 1: type=json + 기본
for params in [
    {"ServiceKey": KEY, "type": "json", "pageNo": 1, "numOfRows": 3, "flag": "Y"},
    {"serviceKey": KEY, "type": "json", "pageNo": 1, "numOfRows": 3},
    {"ServiceKey": KEY, "pageNo": 1, "numOfRows": 3},
]:
    print("===", {k: ('***' if 'Key' in k else v) for k, v in params.items()})
    r = httpx.get(URL, params=params, timeout=30)
    print("HTTP", r.status_code, "len", len(r.content))
    body = r.text[:1500]
    print(body)
    print()
