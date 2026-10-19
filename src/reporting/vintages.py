"""Data vintages, read from the pipeline's own metadata (never typed): one definition for the figure engine, the digest and the registry.

Demand vintage  = first collection timestamp of the posting snapshot (outputs/market_summary.json: collected_at_range.min).
Supply vintage  = collection date of the GitHub supply collection (outputs/supply_summary.json: collection_date). The README fetch
                  runs past midnight, so the supply collection is written "d/d+1" (e.g. 2026-09-17/18) and its stale date counts from d+1.
Stale rule      = vintage + 91 days (13 weeks).
Fallbacks are returned only when the metadata file is absent (a clone without outputs) and are the caller's explicit default.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

STALE_AFTER_DAYS = 91
SUPPLY_COLLECTION_SPAN_DAYS = 1


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def add_days(iso: str, days: int) -> str:
    return (dt.date.fromisoformat(str(iso)[:10]) + dt.timedelta(days=days)).isoformat()


def demand_vintage(root: Path, default: str = "") -> str:
    summary = _read_json(root / "outputs" / "market_summary.json") or {}
    return str((summary.get("collected_at_range") or {}).get("min") or "")[:10] or default


def supply_collection_date(root: Path, default: str = "") -> str:
    summary = _read_json(root / "outputs" / "supply_summary.json") or {}
    manifest = _read_json(root / "data" / "processed" / "supply_build_manifest.json") or {}
    return str(summary.get("collection_date") or manifest.get("collection_date") or "")[:10] or default


def supply_vintage_label(root: Path, default: str = "") -> str:
    """'2026-09-17/18' (collection day / next day), or the plain date when the span crosses a month."""
    first = supply_collection_date(root)
    if not first:
        return default
    last = add_days(first, SUPPLY_COLLECTION_SPAN_DAYS)
    return f"{first}/{last[8:]}" if last[:7] == first[:7] else f"{first}/{last}"


def stale_after(vintage: str, extra_days: int = 0) -> str:
    return add_days(vintage, extra_days + STALE_AFTER_DAYS)
