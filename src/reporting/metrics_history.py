"""Weekly history of the salary-floor metrics -> data/private/metrics_history/history.csv (private, gitignored area).

    One row per (run_date, key). The registry (src/reporting/metrics_registry.py) calls this module twice per weekly run:
      1. while building: read the file, put the current run's rows over the stored rows of the same run_date and derive the
         `<key>__hist_*` registry keys (lowest, highest, median, mode, number of runs, first date, trend) for every tracked floor key;
      2. after writing outputs/metrics.json, with `--run-date`: upsert the current run's rows into the file.

Tracked keys (definition, not data): every registry key with unit `eur` whose name contains `floor` or starts with `never_ask`
(floor_*_eur, family_salary_floor_median_eur__*, salary_*__floor_*_eur, the junior-floor decision key, ...), plus the sample
sizes `floor_*_n`. Derived keys (`__hist_`) are never tracked. Only the `eur` keys get derived history keys.

Upsert: all stored rows of the run_date are replaced by the new ones, so a re-run of a run date is idempotent and never
duplicates rows. Rows are kept sorted by (run_date, key). The file is written atomically (src/pipeline/fsutil.py).

Statistics over the runs of one key (`series_stats`):
  min / max / median   plain statistics of the stored values, one value per run date;
  mode                 the most frequent value (values compared to the cent); ties -> the value whose latest occurrence is most recent;
  n / first_date       number of runs that have the key / date of the first of them;
  slope_per_week       ordinary least squares of value on date (euro per week); None below TREND_MIN_RUNS runs.
"""
from __future__ import annotations

import csv
import io
import re
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src" / "pipeline") not in sys.path:
    sys.path.append(str(ROOT / "src" / "pipeline"))
from fsutil import atomic_write_text  # noqa: E402

HISTORY_REL = Path("data") / "private" / "metrics_history" / "history.csv"
COLUMNS = ("run_date", "week_id", "demand_vintage", "key", "value", "unit", "n")
TREND_MIN_RUNS = 4          # below this many runs a slope says nothing: the trend text gives the plain change instead
FLAT_EUR_PER_WEEK = 50.0    # an OLS slope smaller than this (euro per week) counts as flat
_COUNT_KEY = re.compile(r"floor_[a-z0-9_]+_n")


def is_tracked(key: str, entry: dict) -> bool:
    """Is this registry key stored in the history?"""
    if key == "_meta" or "__hist_" in key or not isinstance(entry, dict):
        return False
    unit = entry.get("unit")
    if unit == "eur":
        return "floor" in key or key.startswith("never_ask")
    return unit == "count" and bool(_COUNT_KEY.fullmatch(key))


def has_derived_keys(entry: dict) -> bool:
    return entry.get("unit") == "eur"


def tracked_rows(registry: dict, run_date: str) -> list[dict]:
    """The history rows of one run, from a finished registry (dict as returned by build_registry)."""
    meta = registry.get("_meta") or {}
    rows = []
    for key in sorted(registry):
        entry = registry[key]
        if not is_tracked(key, entry) or not isinstance(entry.get("value"), (int, float)):
            continue
        rows.append({"run_date": run_date, "week_id": str(meta.get("week_id") or ""), "demand_vintage": str(meta.get("demand_vintage") or ""),
                     "key": key, "value": repr(float(entry["value"])), "unit": entry.get("unit", ""),
                     "n": "" if entry.get("n") is None else str(int(entry["n"]))})
    return rows


def read_history(path: Path | str | None) -> list[dict]:
    if path is None:
        return []
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as handle:
        return [dict(r) for r in csv.DictReader(handle)]


def upsert(existing: list[dict], new: list[dict], run_date: str) -> list[dict]:
    """Rows of `run_date` in `existing` are replaced by `new` (idempotent); the result is sorted by (run_date, key)."""
    kept = [r for r in existing if r["run_date"] != run_date]
    return sorted(kept + [dict(r, run_date=run_date) for r in new], key=lambda r: (r["run_date"], r["key"]))


def write_history(path: Path | str, rows: list[dict]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    atomic_write_text(path, buf.getvalue(), newline="")


def update_history_file(path: Path | str, registry: dict, run_date: str) -> list[dict]:
    """Upsert the run's tracked rows of `registry` into the file at `path`; return the rows now stored."""
    rows = upsert(read_history(path), tracked_rows(registry, run_date), run_date)
    write_history(path, rows)
    return rows


def series(rows: list[dict], key: str, up_to: str | None = None) -> list[tuple[date, float]]:
    """(run date, value) of one key in date order, one value per run date, only runs up to `up_to` (ISO date) when given."""
    by_date: dict[str, float] = {}
    for r in rows:
        if r["key"] != key or (up_to is not None and r["run_date"] > up_to):
            continue
        try:
            by_date[r["run_date"]] = float(r["value"])
        except (TypeError, ValueError):
            continue
    return [(date.fromisoformat(d), by_date[d]) for d in sorted(by_date)]


def series_stats(points: list[tuple[date, float]]) -> dict:
    """min, max, median, mode, n, first_date, last, change (last - first) and slope_per_week of a non-empty series."""
    values = [round(v, 2) for _, v in points]
    counts = Counter(values)
    top = max(counts.values())
    last_seen = {v: i for i, v in enumerate(values)}                   # index of the latest occurrence of each value
    mode = max((v for v, c in counts.items() if c == top), key=lambda v: last_seen[v])
    out = {"min": min(values), "max": max(values), "median": statistics.median(values), "mode": mode, "n": len(points),
           "first_date": points[0][0].isoformat(), "last": points[-1][1], "change": points[-1][1] - points[0][1], "slope_per_week": None}
    if len(points) >= TREND_MIN_RUNS:
        xs = [(d - points[0][0]).days for d, _ in points]
        mx, my = statistics.fmean(xs), statistics.fmean(v for _, v in points)
        var = sum((x - mx) ** 2 for x in xs)
        if var > 0:
            out["slope_per_week"] = 7 * sum((x - mx) * (v - my) for x, (_, v) in zip(xs, points)) / var
    return out
