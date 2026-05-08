"""1주차 데이터 수집 공통 HTTP 유틸 — 재시도, rate-limit, checkpoint."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable

import httpx
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
CHECKPOINT_DIR = ROOT / "data" / "checkpoints"

for d in (RAW_DIR, PROCESSED_DIR, CHECKPOINT_DIR):
    d.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")


def env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"환경변수 {key} 가 .env 에 없음")
    return val


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    reraise=True,
)
def get_with_retry(client: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
    """5회 지수 백오프 재시도. 4xx도 재시도하지 않고 즉시 raise."""
    r = client.get(url, **kwargs)
    if r.status_code >= 500:
        raise httpx.HTTPStatusError(f"{r.status_code}", request=r.request, response=r)
    return r


class RateLimiter:
    """단순 토큰 버킷 (calls_per_sec) — API rate limit 준수용."""

    def __init__(self, calls_per_sec: float = 1.0) -> None:
        self.interval = 1.0 / calls_per_sec
        self._last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        delta = now - self._last
        if delta < self.interval:
            time.sleep(self.interval - delta)
        self._last = time.monotonic()


class Checkpoint:
    """JSON 파일 기반 처리 키 기록 — 재실행 시 이미 끝난 키 스킵."""

    def __init__(self, name: str) -> None:
        self.path = CHECKPOINT_DIR / f"{name}.json"
        self.done: set[str] = set()
        if self.path.exists():
            try:
                self.done = set(json.loads(self.path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                self.done = set()

    def is_done(self, key: str) -> bool:
        return key in self.done

    def mark(self, key: str) -> None:
        self.done.add(key)

    def save(self) -> None:
        self.path.write_text(
            json.dumps(sorted(self.done), ensure_ascii=False), encoding="utf-8"
        )


def safe_run(name: str, work: Callable[[Checkpoint], None]) -> None:
    """예외에도 checkpoint 저장하도록 보장."""
    cp = Checkpoint(name)
    try:
        work(cp)
    finally:
        cp.save()
        print(f"[CHECKPOINT] {name}: {len(cp.done)} keys saved → {cp.path}")
