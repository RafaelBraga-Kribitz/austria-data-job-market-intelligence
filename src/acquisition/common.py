"""Shared helpers for all collectors.

Design principles
- Every raw observation is written as one JSON line, untouched, with a
  collection envelope (source, collected_at, query that produced it).
- A query log records every request (query text, page, result count) so that
  source coverage and platform bias can be audited later. The last logged page
  of a sweep carries complete=True (and truncated=True when a page cap, not the
  source, ended it); `completed_queries` reads this back so a resumed run skips
  finished sweeps.
- Polite by default: fixed delays between requests, exponential backoff on
  429/5xx, and a hard cap on pages per query.

Dates. Collection folders are named by the collection day in Austrian local time
(`today()`, Europe/Vienna); `collected_at` envelopes stay UTC ISO timestamps. Folders
written before 2026-09-30 by the RawWriter collectors were named by the UTC day
(identical for every run so far except eurostat_jvs/2026-09-16, fetched 00:24 Vienna
time on 09-17); github_supply and eurostat_supply used the machine's local day. Every
collector takes --date YYYY-MM-DD to continue an existing folder on a later day.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
BASE_HEADERS = {"User-Agent": UA, "Accept-Language": "de-AT,de;q=0.9,en;q=0.8"}
TZ_NAME = "Europe/Vienna"
RETRY_STATUS = (429, 500, 502, 503, 504)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[\w.-]*$")  # folder names may carry a suffix (e.g. a test subset)


def local_tz() -> ZoneInfo:
    try:
        return ZoneInfo(TZ_NAME)
    except ZoneInfoNotFoundError:  # Windows has no system tz database; the tzdata package provides it
        raise SystemExit(f"time zone {TZ_NAME} not found: pip install tzdata") from None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today() -> str:
    """Collection day in Austrian local time (YYYY-MM-DD); names the raw folder of a run."""
    return datetime.now(local_tz()).strftime("%Y-%m-%d")


def date_arg(v: str) -> str:
    """argparse type for --date: a folder name starting with YYYY-MM-DD, no path separators."""
    if not DATE_RE.match(v):
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {v!r}")
    return v


def cli(doc: str | None, stages: tuple[str, ...] | None = None, **extra) -> argparse.Namespace:
    """Standard collector command line: optional stage + --date (default: today())."""
    ap = argparse.ArgumentParser(description=(doc or "").split("\n")[0])
    if stages:
        ap.add_argument("stage", nargs="?", default=stages[0], choices=stages)
    ap.add_argument("--date", type=date_arg, default=None,
                    help=f"collection folder to write/continue (default: today in {TZ_NAME})")
    for flag, kw in extra.items():
        ap.add_argument(f"--{flag}", **kw)
    return ap.parse_args()


def is_transient(status) -> bool:
    """True for outcomes worth retrying on a later run: no response, 403 (throttle/WAF), 408, 429, 5xx, 599."""
    return status is None or status in (403, 408, 429) or status >= 500


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
        self.n_errors = 0   # failed attempts (network exception or 429/5xx), retried or not
        self.n_failed = 0   # requests that still had no usable response after all retries

    def request(self, method: str, url: str, **kw) -> requests.Response | None:
        """Return the first non-429/5xx response; after the last retry return the last 429/5xx
        response (so callers can log its status), or None if every attempt raised."""
        kw.setdefault("timeout", 45)
        last = None
        for attempt in range(self.max_retries):
            final = attempt == self.max_retries - 1
            try:
                time.sleep(self.delay * (0.7 + 0.6 * random.random()))
                r = self.s.request(method, url, **kw)
                self.n_requests += 1
            except requests.RequestException as e:
                self.n_errors += 1
                print(f"  [err] {e.__class__.__name__}: {url[:90]}", flush=True)
                if not final:
                    time.sleep(5 * (attempt + 1))
                continue
            if r.status_code in RETRY_STATUS:
                self.n_errors += 1
                last = r
                if final:
                    print(f"  [{r.status_code}] giving up after {self.max_retries} attempts: {url[:90]}", flush=True)
                    break
                wait = 20 * (2 ** attempt)
                print(f"  [{r.status_code}] backoff {wait}s: {url[:90]}", flush=True)
                time.sleep(wait)
                continue
            return r
        self.n_failed += 1
        return last

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)

    def summary(self) -> str:
        return f"requests={self.n_requests} errors={self.n_errors} failed={self.n_failed}"


def status_of(r) -> int | None:
    return r.status_code if r is not None else None


class RawWriter:
    """Append-only JSONL writer for one source; keeps a query log and manifest."""

    def __init__(self, source: str, run_date: str | None = None):
        self.source = source
        self.run_date = run_date or today()
        self.dir = RAW / source / self.run_date
        self.dir.mkdir(parents=True, exist_ok=True)
        self._files = {}
        self.query_log = self.dir / "query_log.jsonl"
        self.skipped: dict[str, int] = {}  # unparseable lines per file name, from the last read

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

    def read(self, path: Path):
        """Yield parsed lines of a JSONL file; count (in self.skipped) and report unparseable ones."""
        if path.exists():
            if path.stem in self._files:  # make buffered writes visible
                self._files[path.stem].flush()
            bad = 0
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        yield json.loads(line)
                    except ValueError:
                        bad += 1
            self.skipped[path.stem] = bad
            if bad:
                print(f"  [warn] {path.name}: {bad} unparseable line(s) skipped", flush=True)

    def existing_ids(self, name: str, id_path, keep=None) -> set:
        """Return the set of ids already present in <name>.jsonl (for resume).

        `keep(envelope)` optionally filters rows (e.g. drop transient failures so they are retried).
        Lines that do not parse, or lack the id, are counted in self.skipped[name] and reported."""
        ids = set()
        bad = 0
        for e in self.read(self.dir / f"{name}.jsonl"):
            try:
                if keep is None or keep(e):
                    ids.add(id_path(e))
            except (KeyError, TypeError, IndexError):
                bad += 1
        if bad:
            self.skipped[name] = self.skipped.get(name, 0) + bad
            print(f"  [warn] {name}.jsonl: {bad} line(s) without the resume id skipped", flush=True)
        return ids

    def completed_queries(self, keys: tuple[str, ...], legacy=None) -> set[tuple]:
        """Sweeps (tuples of the `keys` query-log fields) whose last page was logged complete=True.

        `legacy(entry)` decides for entries written before the complete flag existed."""
        done = set()
        for e in self.read(self.query_log):
            if any(e.get(k) is None for k in keys):
                continue
            if e.get("complete") or ("complete" not in e and legacy is not None and e.get("status") == 200 and legacy(e)):
                done.add(tuple(e[k] for k in keys))
        return done

    def close(self):
        for fh in self._files.values():
            fh.close()
        self._files = {}


def detail_done(e: dict) -> bool:
    """keep= filter for details.jsonl: a stored detail counts as done unless its status is transient."""
    return not is_transient(e["record"].get("status", 200))


def end_of_sweep(w: RawWriter, last: bool, pos: int, max_pos: int, full: bool, /, **fields) -> bool:
    """Log one successful page (`fields` go to the query log); return True when the sweep stops here.

    `last`: the source signalled the end. When `pos` (page or start offset) reaches `max_pos` without
    that signal the sweep is cut by our page cap: logged complete=True, truncated=True if the page was full."""
    capped = not last and pos >= max_pos
    extra = {"complete": last or capped}
    if last or capped:
        extra["truncated"] = capped and full
        if capped and full:
            print(f"  [cap] page cap {max_pos} reached with a full page: results truncated", flush=True)
    w.log_query(**fields, **extra)
    return last or capped


def load_queries() -> dict:
    with open(ROOT / "config" / "queries.json", encoding="utf-8") as f:
        return json.load(f)
