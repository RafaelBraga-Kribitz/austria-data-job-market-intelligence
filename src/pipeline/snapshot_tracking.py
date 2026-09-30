"""Longitudinal posting identity across Layer 1 snapshots (OQ-07, OQ-15; audit M27).

Design
------
Each Layer 1 run is a one-day stock: build_interim.py reads only the *latest* dated raw folder per source,
so a run's data/processed/postings_dedup.parquet is exactly one snapshot. This module keeps a separate
history table, one row per ``posting_uid`` ever seen, and folds each new snapshot into it:

    posting_uid | source | first_seen | last_seen | n_snapshots | snapshot_dates | active_in_latest
                | company_norm | title_clean | state | role_family      (attributes of the latest sighting)

Key choice: ``posting_uid`` = "<source>:<source_id>" (build_interim.py), where source_id is the platform's
own id (EURES job id, karriere.at / LinkedIn / willhaben / jobs.at numeric ids). It is stable across runs
as long as the platform keeps the id for an unchanged ad. It is NOT stable when an employer re-posts
(new id, same job) - uid_stability() measures that by counting disappeared uids whose
(source, company_norm, title_clean) key reappears under a new uid.

``dedupe_group_id`` must never be used as a key: dedupe.py builds it from the row position of the
union-find root ("g<index>"), so it changes with every run. Cross-source identity per run is handled by
group_first_seen(): the first-seen date of a current dedupe group is the minimum over its members' uids,
which survives the canonical row switching source between runs.

Censoring: postings present in the first snapshot were already online before observation began
(left-censored); postings active in the latest snapshot have not ended yet (right-censored). Any
time-on-market statistic must report both flags; with two snapshots 3-6 months apart only
"still online after N days" shares are defensible, not durations.

The functions are pure (DataFrame in, DataFrame out). The CLI folds a snapshot into
data/processed/posting_history.parquet (private, git-ignored). It has not been run on real data.

Usage: python src/pipeline/snapshot_tracking.py --snapshot data/processed/postings_dedup.parquet --date 2026-09-16
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HISTORY_PATH = ROOT / "data" / "processed" / "posting_history.parquet"
KEY = "posting_uid"
CARRIED = ["source", "company_norm", "title_clean", "state", "role_family", "is_canonical"]
HISTORY_COLUMNS = [KEY, "first_seen", "last_seen", "n_snapshots", "snapshot_dates", "active_in_latest"] + CARRIED


def empty_history() -> pd.DataFrame:
    return pd.DataFrame(columns=HISTORY_COLUMNS)


def _dates(history: pd.DataFrame) -> list[str]:
    if history.empty:
        return []
    return sorted({d for s in history["snapshot_dates"] for d in str(s).split(";") if d})


def merge_snapshot(history: pd.DataFrame | None, snapshot: pd.DataFrame, snapshot_date: str) -> pd.DataFrame:
    """Fold one snapshot (all rows of a postings_dedup table, canonical or not) into the history.

    * snapshot_date: ISO date of the collection day. Must not be earlier than the latest date already in
      the history. Re-merging the same date is idempotent (no double counting).
    * Raises ValueError on missing/duplicate posting_uid, which would silently corrupt the counts.
    """
    snapshot_date = pd.Timestamp(snapshot_date).date().isoformat()
    history = empty_history() if history is None else history.copy()
    if KEY not in snapshot.columns:
        raise ValueError(f"snapshot has no {KEY} column")
    if snapshot[KEY].isna().any():
        raise ValueError(f"snapshot has rows without {KEY}")
    dup = snapshot[KEY][snapshot[KEY].duplicated()]
    if len(dup):
        raise ValueError(f"snapshot has duplicate {KEY}: {sorted(dup.unique())[:5]}")
    known = _dates(history)
    if known and snapshot_date < known[-1]:
        raise ValueError(f"snapshot {snapshot_date} is older than the latest merged snapshot {known[-1]}; "
                         "rebuild the history in date order")
    snap = snapshot[[KEY] + [c for c in CARRIED if c in snapshot.columns]].copy()
    for c in CARRIED:
        if c not in snap.columns:
            snap[c] = None
    h = history.set_index(KEY) if not history.empty else empty_history().set_index(KEY)
    s = snap.set_index(KEY)

    old = h.index.difference(s.index)
    both = h.index.intersection(s.index)
    new = s.index.difference(h.index)

    parts = []
    if len(old):
        o = h.loc[old].copy()
        o["active_in_latest"] = False
        parts.append(o)
    if len(both):
        b = h.loc[both].copy()
        already = b["snapshot_dates"].map(lambda x: snapshot_date in str(x).split(";"))
        b.loc[~already, "snapshot_dates"] = b.loc[~already, "snapshot_dates"].astype(str) + ";" + snapshot_date
        b.loc[~already, "n_snapshots"] = b.loc[~already, "n_snapshots"].astype(int) + 1
        b["last_seen"] = snapshot_date
        b["active_in_latest"] = True
        for c in CARRIED:
            b[c] = s.loc[both, c]
        parts.append(b)
    if len(new):
        n = s.loc[new].copy()
        n["first_seen"] = snapshot_date
        n["last_seen"] = snapshot_date
        n["n_snapshots"] = 1
        n["snapshot_dates"] = snapshot_date
        n["active_in_latest"] = True
        parts.append(n)
    out = pd.concat(parts) if parts else h
    out = out.reset_index().rename(columns={"index": KEY})
    out["n_snapshots"] = out["n_snapshots"].astype(int)
    out["active_in_latest"] = out["active_in_latest"].astype(bool)
    return out[HISTORY_COLUMNS].sort_values([KEY]).reset_index(drop=True)


def add_censoring(history: pd.DataFrame) -> pd.DataFrame:
    """Add left_censored / right_censored flags and days_observed (last_seen - first_seen)."""
    h = history.copy()
    dates = _dates(h)
    first, last = (dates[0], dates[-1]) if dates else (None, None)
    h["left_censored"] = h["first_seen"] == first
    h["right_censored"] = h["last_seen"] == last
    h["days_observed"] = (pd.to_datetime(h["last_seen"]) - pd.to_datetime(h["first_seen"])).dt.days
    return h


def group_first_seen(history: pd.DataFrame, snapshot: pd.DataFrame) -> pd.DataFrame:
    """First-seen per *current* dedupe group: min over all member uids (cross-source safe).

    Returns one row per dedupe_group_id of the snapshot with group_first_seen, n_members and
    n_members_seen_before (members whose uid was already in the history before this snapshot)."""
    if "dedupe_group_id" not in snapshot.columns:
        raise ValueError("snapshot has no dedupe_group_id")
    m = snapshot[[KEY, "dedupe_group_id"]].merge(history[[KEY, "first_seen"]], on=KEY, how="left")
    latest = _dates(history)[-1] if len(history) else None
    m["seen_before"] = m["first_seen"].notna() & (m["first_seen"] != latest)
    return (m.groupby("dedupe_group_id")
             .agg(group_first_seen=("first_seen", "min"), n_members=(KEY, "count"), n_members_seen_before=("seen_before", "sum"))
             .reset_index())


def uid_stability(previous: pd.DataFrame, current: pd.DataFrame) -> dict:
    """Aggregate check of posting_uid stability between two snapshots.

    suspected_rekeyed = uids that disappeared although a posting with the same (source, company_norm,
    title_clean) appears under a uid that is new in the current snapshot - a re-post or an id change.
    A high share means first-seen dates understate time on market for that source."""
    prev_ids, cur_ids = set(previous[KEY]), set(current[KEY])
    gone = previous[previous[KEY].isin(prev_ids - cur_ids)]
    fresh = current[current[KEY].isin(cur_ids - prev_ids)]
    k = ["source", "company_norm", "title_clean"]
    if all(c in previous.columns and c in current.columns for c in k):
        fresh_keys = set(map(tuple, fresh[k].dropna().astype(str).values))
        rekeyed = int(gone[k].dropna().astype(str).apply(tuple, axis=1).isin(fresh_keys).sum())
    else:
        rekeyed = None
    return {"n_previous": len(prev_ids), "n_current": len(cur_ids), "n_persisting": len(prev_ids & cur_ids),
            "n_disappeared": len(prev_ids - cur_ids), "n_new": len(cur_ids - prev_ids),
            "suspected_rekeyed": rekeyed,
            "share_persisting": round(len(prev_ids & cur_ids) / len(prev_ids), 3) if prev_ids else None}


def main() -> None:
    ap = argparse.ArgumentParser(description="Fold a postings_dedup snapshot into the private posting history")
    ap.add_argument("--snapshot", required=True, help="path to a postings_dedup.parquet of ONE collection run")
    ap.add_argument("--date", required=True, help="collection date of that run (YYYY-MM-DD)")
    ap.add_argument("--history", default=str(HISTORY_PATH))
    a = ap.parse_args()
    hp = Path(a.history)
    hist = pd.read_parquet(hp) if hp.exists() else empty_history()
    snap = pd.read_parquet(a.snapshot)
    out = merge_snapshot(hist, snap, a.date)
    out.to_parquet(hp, index=False)
    print(f"history: {len(out)} uids over snapshots {_dates(out)} -> {hp}")


if __name__ == "__main__":
    main()
