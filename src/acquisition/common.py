"""Shared helpers for all collectors.

Design principles
- Every raw observation is written as one JSON line, untouched, with a
  collection envelope (source, collected_at, query that produced it).
- A query log records every request (query text, page, result count) so that
  source coverage and platform bias can be audited later.
- Polite by default: fixed delays between requests, exponential backoff on
  429/5xx, and a hard cap on pages per query.
"""
from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
BASE_HEADERS = {"User-Agent": UA, "Accept-Language": "de-AT,de;q=0.9,en;q=0.8"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class Session:
    """requests session with delay + backoff."""

    def __init__(self, delay: float = 1.0, headers: dict | None = None, max_retries: int = 4):
        self.s = requests.Session()
        self.s.headers.update(BASE_HEADERS)
        if headers:
            self.s.headers.update(headers)
        self.delay = delay
        self.max_retries = max_retries
        self.n_requests = 0
        self.n_errors = 0

    def request(self, method: str, url: str, **kw) -> requests.Response | None:
        kw.setdefault("timeout", 45)
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.delay * (0.7 + 0.6 * random.random()))
                r = self.s.request(method, url, **kw)
                self.n_requests += 1
                if r.status_code in (429, 500, 502, 503, 504):
                    wait = 20 * (2 ** attempt)
                    print(f"  [{r.status_code}] backoff {wait}s: {url[:90]}", flush=True)
                    time.sleep(wait)
                    continue
                return r
            except requests.RequestException as e:
                self.n_errors += 1
                print(f"  [err] {e.__class__.__name__}: {url[:90]}", flush=True)
                time.sleep(5 * (attempt + 1))
        return None

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)


class RawWriter:
    """Append-only JSONL writer for one source; keeps a query log and manifest."""

    def __init__(self, source: str, run_date: str | None = None):
        self.source = source
        self.run_date = run_date or today()
        self.dir = RAW / source / self.run_date
        self.dir.mkdir(parents=True, exist_ok=True)
        self._files = {}
        self.query_log = self.dir / "query_log.jsonl"

    def _fh(self, name: str):
        if name not in self._files:
            self._files[name] = open(self.dir / f"{name}.jsonl", "a", encoding="utf-8")
        return self._files[name]

    def write(self, name: str, record: dict, **envelope):
        env = {"source": self.source, "collected_at": now_iso(), **envelope, "record": record}
        self._fh(name).write(json.dumps(env, ensure_ascii=False) + "\n")

    def log_query(self, **fields):
        with open(self.query_log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": now_iso(), **fields}, ensure_ascii=False) + "\n")

    def existing_ids(self, name: str, id_path) -> set:
        """Return the set of ids already present in <name>.jsonl (for resume)."""
        p = self.dir / f"{name}.jsonl"
        ids = set()
        if p.exists():
            with open(p, encoding="utf-8") as f:
                for line in f:
                    try:
                        ids.add(id_path(json.loads(line)))
                    except Exception:
                        pass
        return ids

    def close(self):
        for fh in self._files.values():
            fh.close()
        self._files = {}


def load_queries() -> dict:
    with open(ROOT / "config" / "queries.json", encoding="utf-8") as f:
        return json.load(f)
