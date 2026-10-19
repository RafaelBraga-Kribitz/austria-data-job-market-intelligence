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

Recurring (weekly) runs. Two opt-in helpers keep a recurring run polite:
- `--reuse-from auto|YYYY-MM-DD` on the detail stages copies the detail records of ids that an earlier dated
  folder of the same source already holds (`reuse_details`), keeping their original `collected_at` and adding
  `reused_from`, so only new ids are fetched. It is off unless asked for.
- Stop-on-block is ON by default: a Session raises `SourceBlocked` after BLOCK_LIMIT consecutive 403/429/999
  responses or block pages; `run_guarded` turns it into exit code 75. No retry trick, proxy or header rotation exists:
  a blocked source simply stops for the run. The only opt-out is the explicit `--no-stop-on-block` flag (or
  AJMI_STOP_ON_BLOCK=0 / Session(stop_on_block=False)); the weekly orchestrator never opts out.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
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


def stop_on_block_default() -> bool:
    """True unless AJMI_STOP_ON_BLOCK=0 was set (by --no-stop-on-block or on purpose)."""
    return os.environ.get("AJMI_STOP_ON_BLOCK", "1").strip() != "0"


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
    ap.add_argument("--no-stop-on-block", action="store_true",
                    help="do NOT stop the source after 3 consecutive 403/429/999 or block pages (default: stop, exit code 75); "
                         "never used by the weekly orchestrator")
    for flag, kw in extra.items():
        ap.add_argument(f"--{flag}", **kw)
    a = ap.parse_args()
    if a.no_stop_on_block:
        os.environ["AJMI_STOP_ON_BLOCK"] = "0"
        print("[WARN] --no-stop-on-block: the source will NOT stop on repeated 403/429/999 (manual run, your decision)", flush=True)
    return a


def is_transient(status) -> bool:
    """True for outcomes worth retrying on a later run: no response, 403 (throttle/WAF), 408, 429, 5xx, 599."""
    return status is None or status in (403, 408, 429) or status >= 500


BLOCK_STATUSES = (403, 429, 999)
BLOCK_LIMIT = 3               # consecutive blocked responses that stop a source (when stop_on_block is on)
EXIT_BLOCKED = 75             # process exit code of a collector that stopped on a block (sysexits EX_TEMPFAIL)
BLOCK_PAGE_MARKERS = ("just a moment", "cf-browser-verification", "g-recaptcha", "h-captcha", "captcha-delivery",
                      "access denied", "unusual traffic", "are you a robot", "verify you are human")
BLOCK_URL_MARKERS = ("/authwall", "/checkpoint/", "/captcha")


class SourceBlocked(RuntimeError):
    """The source answered BLOCK_LIMIT times in a row with 403/429/999 or a block page: stop, do not work around."""

    def __init__(self, message: str, status=None, url: str | None = None):
        super().__init__(message)
        self.status = status
        self.url = url


def looks_like_block_page(r) -> bool:
    """True for a challenge / login wall served instead of content (conservative: short HTML bodies and known URLs only)."""
    url = (getattr(r, "url", "") or "").lower()
    if any(m in url for m in BLOCK_URL_MARKERS):
        return True
    text = getattr(r, "text", "") or ""
    if r.status_code != 200 or len(text) > 12000:
        return False
    head = text[:6000].lower()
    return any(m in head for m in BLOCK_PAGE_MARKERS)


class Session:
    """requests session with delay + backoff."""

    def __init__(self, delay: float = 1.0, headers: dict | None = None, max_retries: int = 4,
                 stop_on_block: bool | None = None):
        self.stop_on_block = stop_on_block_default() if stop_on_block is None else stop_on_block
        self.blocked_streak = 0
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
            self._track_block(r, url)
            return r
        self.n_failed += 1
        if last is not None:
            self._track_block(last, url)
        return last

    def _track_block(self, r, url: str) -> None:
        """Count consecutive blocked responses; raise SourceBlocked at BLOCK_LIMIT when stop_on_block is on."""
        if not self.stop_on_block:
            return
        if r.status_code in BLOCK_STATUSES or looks_like_block_page(r):
            self.blocked_streak += 1
            if self.blocked_streak >= BLOCK_LIMIT:
                raise SourceBlocked(f"{self.blocked_streak} consecutive blocked responses (last: HTTP {r.status_code}) "
                                    f"at {url[:120]}", r.status_code, url)
        else:
            self.blocked_streak = 0

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)

    def summary(self) -> str:
        return f"requests={self.n_requests} errors={self.n_errors} failed={self.n_failed}"


def status_of(r) -> int | None:
    return r.status_code if r is not None else None


def run_guarded(fn, *args, **kw):
    """Run a collector entry point; a SourceBlocked ends the process with EXIT_BLOCKED instead of a traceback."""
    try:
        return fn(*args, **kw)
    except SourceBlocked as e:
        print(f"[BLOCKED] source stopped for this run (no workaround attempted): {e}", flush=True)
        sys.exit(EXIT_BLOCKED)


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
        self.empty_streak = 0              # consecutive sweeps whose first page was an empty HTTP-200 page (see end_of_sweep)

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


EMPTY_PAGE_LIMIT = 5          # consecutive empty first pages that stop a source (stop-on-block on); observed legitimate maximum is 2


def end_of_sweep(w: RawWriter, last: bool, pos: int, max_pos: int, full: bool, /, **fields) -> bool:
    """Log one successful page (`fields` go to the query log); return True when the sweep stops here.

    `last`: the source signalled the end. When `pos` (page or start offset) reaches `max_pos` without
    that signal the sweep is cut by our page cap: logged complete=True, truncated=True if the page was full.

    An empty HTTP-200 FIRST page (`returned == 0` on page 1 / start 0) is not a finished sweep: it is a rate-limit page, a soft
    block or a broken template as often as a keyword without hits. It is logged complete=False, empty_first_page=True (so a resumed
    run asks again and the weekly scan counts it apart from errors) and the sweep stops. EMPTY_PAGE_LIMIT of them in a row (any
    page with items resets the count) raise SourceBlocked when stop-on-block is on."""
    if fields.get("returned") == 0:
        if fields.get("page") == 1 or fields.get("start") == 0:
            w.empty_streak += 1
            w.log_query(**fields, complete=False, empty_first_page=True)
            if w.empty_streak >= EMPTY_PAGE_LIMIT and stop_on_block_default():
                raise SourceBlocked(f"{w.empty_streak} consecutive sweeps began with an empty HTTP-200 page: soft block suspected "
                                    "(no workaround attempted)", 200, None)
            return True
    elif fields.get("returned") is not None:
        w.empty_streak = 0
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


# ---------------------------------------------------------------- incremental detail passes (weekly runs)
REUSE_MAX_AGE_DAYS = 60
RUN_FOLDER_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REUSE_ARGS = {
    "reuse-from": {"default": None, "metavar": "auto|YYYY-MM-DD",
                   "help": "details stage: copy detail records of ids already held by an earlier dated folder of this source "
                           "(auto = the most recent earlier folder with details.jsonl) and fetch only the new ids; "
                           "copies keep their collected_at and gain reused_from (default: off)"},
    "reuse-max-age-days": {"type": int, "default": REUSE_MAX_AGE_DAYS,
                           "help": f"with --reuse-from: copy only records collected at most this many days ago (default {REUSE_MAX_AGE_DAYS})"},
}


def previous_run_dir(source: str, run_date: str, need: str = "details.jsonl") -> Path | None:
    """Most recent folder of `source` named exactly YYYY-MM-DD, strictly earlier than run_date, holding `need`."""
    base = RAW / source
    if not base.is_dir():
        return None
    names = sorted(p.name for p in base.iterdir()
                   if p.is_dir() and RUN_FOLDER_RE.match(p.name) and p.name < run_date and (p / need).exists())
    return base / names[-1] if names else None


def _parse_ts(v) -> datetime | None:
    try:
        t = datetime.fromisoformat(str(v))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def reuse_details(w: RawWriter, wanted, done: set, reuse_from: str | None,
                  max_age_days: int = REUSE_MAX_AGE_DAYS, usable=None) -> tuple[int, str | None]:
    """Copy detail envelopes for ids in `wanted` (and not yet in `done`) from an earlier dated folder into w's details.jsonl.

    The copy keeps the envelope untouched (original `collected_at`) and adds `reused_from: <source folder name>`. Records
    older than `max_age_days`, rejected by `usable(envelope)` (e.g. `detail_done`: transient statuses are fetched again) or
    unparseable are not copied, so the caller's normal fetch loop picks those ids up. `done` is updated in place.
    Returns (number copied, name of the folder copied from or None). A resumed folder copies nothing twice because the
    ids are then already in `done`."""
    if not reuse_from or reuse_from == "none":
        return 0, None
    prev = previous_run_dir(w.source, w.run_date) if reuse_from == "auto" else RAW / w.source / date_arg(reuse_from)
    if prev is None or prev == w.dir or not (prev / "details.jsonl").exists():
        print(f"  reuse: no earlier details.jsonl for {w.source} ({reuse_from}); fetching everything", flush=True)
        return 0, None
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    wanted = wanted if isinstance(wanted, (set, frozenset)) else set(wanted)
    fh = w._fh("details")
    n = stale = rejected = 0
    with open(prev / "details.jsonl", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                e = json.loads(line)
                lid = e["listing_id"]
            except (ValueError, KeyError, TypeError):
                continue
            if lid not in wanted or lid in done:
                continue
            try:
                if usable is not None and not usable(e):
                    rejected += 1
                    continue
            except (KeyError, TypeError, AttributeError):
                rejected += 1
                continue
            ts = _parse_ts(e.get("collected_at"))
            if ts is None or ts < cutoff:
                stale += 1
                continue
            e["reused_from"] = prev.name
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            done.add(lid)
            n += 1
    fh.flush()
    print(f"  reuse: {n} detail record(s) copied from {prev.name} ({stale} older than {max_age_days} d, {rejected} not reusable)",
          flush=True)
    if n or not (w.dir / "reuse_log.json").exists():
        info = {"reused_from": prev.name, "n_reused": n, "n_too_old": stale, "n_not_reusable": rejected,
                "max_age_days": max_age_days, "at": now_iso()}
        (w.dir / "reuse_log.json").write_text(json.dumps(info, indent=1) + "\n", encoding="utf-8")
    return n, prev.name
