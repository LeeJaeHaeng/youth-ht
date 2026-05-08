"""검증 스크립트 공통 유틸 — 환경변수 로드, 결과 저장, 콘솔 포맷."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
VERIFY_DIR = ROOT / "data" / "verify"
RAW_DIR = ROOT / "data" / "raw"

load_dotenv(ROOT / ".env")


def env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        print(f"[FATAL] 환경변수 {key} 가 .env 에 없음", file=sys.stderr)
        sys.exit(2)
    return val


def banner(title: str) -> None:
    line = "=" * 70
    print(line)
    print(title)
    print(line)


def save_sample(name: str, data: Any) -> Path:
    """data/verify/{name}.json 에 샘플 저장."""
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    out = VERIFY_DIR / f"{name}.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"[SAVED] {out}")
    return out


def ok(msg: str) -> None:
    print(f"[ OK ] {msg}")


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
