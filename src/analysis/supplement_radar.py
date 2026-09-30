"""T19 dated supplement aggregates from Arbeitnow raw and/or the private radar DB.

Never merges into the 2026-09-16 720-core snapshot. Public tables have no URL/snippet/description.
If volume is below MATERIAL_N Austrian data-role postings, only T19_supplement_status.csv is filled
with status=not_collected or below_threshold.

The hunter database (src/private/radar/jobs.db) is private and git-ignored; it is absent from the public
repository and from any fresh clone. Without it the script prints a notice and, if the existing T19 tables were
built from the database, leaves them untouched and reports them as NOT refreshed (they keep their collected_date),
instead of overwriting a published result with an Arbeitnow-only or empty status.

Usage: python src/analysis/supplement_radar.py
"""
from __future__ import annotations

import html
import json
import math
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "pipeline"))
sys.path.insert(0, str(ROOT / "src" / "acquisition"))
import normalize as N  # noqa: E402
from collect_arbeitnow import is_austria  # noqa: E402

TAB = ROOT / "outputs" / "tables"
TAB.mkdir(parents=True, exist_ok=True)
RAW_AN = ROOT / "data" / "raw" / "arbeitnow"
RAW_RADAR = ROOT / "data" / "raw" / "radar"
DB = ROOT / "src" / "private" / "radar" / "jobs.db"
if not DB.exists():
    DB = ROOT / "jobs.db"
MATERIAL_N = 20
CORE = ["data_analytics", "bi", "data_science", "data_engineering", "data_governance",
        "marketing_analytics", "product_analytics", "business_analysis"]
DESC_MIN = 50


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0, c - h), 3), round(min(1, c + h), 3))


def strip(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return html.unescape(re.sub(r"\s+", " ", s)).strip()


def source_label(source: str) -> str:
    s = (source or "radar").strip().lower()
    if s.startswith("indeed/linkedin:"):
        site = s.split(":", 1)[-1] or "unknown"
        return f"jobspy_{site}"
    return s or "radar"


def collected_date() -> str:
    for root in (RAW_RADAR, RAW_AN):
        if not root.exists():
            continue
        dates = sorted(p.name for p in root.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name))
        if dates:
            return dates[-1]
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def classify_row(title: str, desc: str, source: str, location: str = "") -> dict:
    tc, _ = N.clean_title(title or "")
    role = N.classify_role(tc)
    sk = N.extract_skills(desc or "", title or "")
    geo = N.normalize_location({"location_text": location or "", "description_text": ""})
    desc_s = strip(desc)
    return {
        "source": source_label(source),
        "state": geo.get("state") or "unspecified",
        "role_family": role.get("role_family"),
        "skills_all_tech": sorted({x for c in ("programming_languages", "bi_tools", "cloud_platforms", "data_platforms",
                                               "python_ecosystem", "data_engineering", "ml_ai", "statistics_methods")
                                   for x in sk.get(f"skills_{c}", []) or []}),
        "is_core": role.get("role_family") in CORE,
        "has_description": len(desc_s) >= DESC_MIN,
    }


def load_arbeitnow() -> list[dict]:
    if not RAW_AN.exists():
        return []
    dates = sorted(p for p in RAW_AN.iterdir() if p.is_dir())
    if not dates:
        return []
    latest = dates[-1]
    p = latest / "listings.jsonl"
    if not p.exists():
        return []
    rows = []
    for line in open(p, encoding="utf-8"):
        env = json.loads(line)
        rec = env.get("record") or {}
        if not rec.get("is_austria_location"):
            continue
        rows.append(classify_row(rec.get("title") or "", rec.get("description_text") or "",
                                 "arbeitnow", rec.get("location") or ""))
    return rows


def load_radar_db() -> tuple[list[dict], int]:
    """Return (Austria-location rows, total DB rows)."""
    if not DB.exists():
        return [], 0
    con = sqlite3.connect(DB)
    try:
        cur = con.execute("SELECT source, title, location, description FROM jobs")
        at_rows = []
        n_all = 0
        for src, title, loc, desc in cur.fetchall():
            n_all += 1
            if not is_austria(loc or ""):
                continue
            at_rows.append(classify_row(title or "", desc or "", src or "radar", loc or ""))
        return at_rows, n_all
    except sqlite3.Error:
        return [], 0
    finally:
        con.close()


def write_status(**kw):
    pd.DataFrame([kw]).to_csv(TAB / "T19_supplement_status.csv", index=False)


def _share_table(series: pd.Series, name: str, n: int) -> pd.DataFrame:
    t = series.value_counts().reset_index()
    t.columns = [name, "count"]
    t["n"] = n
    t["share"] = (t["count"] / n).round(3)
    return t


def previous_status() -> dict:
    p = TAB / "T19_supplement_status.csv"
    if not p.exists():
        return {}
    try:
        return pd.read_csv(p).iloc[0].to_dict()
    except (pd.errors.EmptyDataError, IndexError):
        return {}


def main() -> str:
    """Build the T19 tables; return the status written, or "not_refreshed" when nothing was written."""
    if not DB.exists():
        prev = previous_status()
        print("NOTICE: private hunter database not found (src/private/radar/jobs.db is git-ignored and never "
              "published); the radar part of T19 cannot be rebuilt here.")
        if int(prev.get("radar_db_rows", 0) or 0) > 0:
            print(f"T19 NOT refreshed: outputs/tables/T19_supplement_*.csv keep the {prev.get('status')} result of "
                  f"{prev.get('collected_date')} (radar_db_rows={prev.get('radar_db_rows')}); nothing was overwritten.")
            return "not_refreshed"
        print("Continuing with the Arbeitnow raw data only (if present).")
    an = load_arbeitnow()
    rd, n_db_all = load_radar_db()
    # Radar is the hunter universe; Arbeitnow rows already upserted there are not double-counted.
    all_rows = rd if rd else an
    n_at = len(an)
    n_db = len(rd)
    core = [r for r in all_rows if r["is_core"]]
    n_core = len(core)
    n_desc = sum(1 for r in core if r["has_description"])
    status = "not_collected"
    if n_at or n_db_all:
        status = "below_threshold" if n_core < MATERIAL_N else "published_aggregates"
    note = ("Separate universe from the 2026-09-16 720-core snapshot; never merged. "
            "No URLs or JD text. StepStone.at and Indeed.at live harvests stopped on HTTP 403. "
            "Hunter volume is python-jobspy LinkedIn jobs (Austria location strings) plus Arbeitnow.")
    if not DB.exists():
        note += " Private hunter database absent at build time: only Arbeitnow raw data was read."
    write_status(status=status, collected_date=collected_date(), material_n_threshold=MATERIAL_N,
                 arbeitnow_austria_rows=n_at, radar_db_rows=n_db_all, radar_austria_rows=n_db,
                 core_data_role_rows=n_core, core_with_description=n_desc, note=note)
    if status != "published_aggregates":
        print(f"T19 {status}: arbeitnow_AT={n_at} radar_db={n_db_all} radar_AT={n_db} core={n_core}")
        return status
    df = pd.DataFrame(core)
    n = len(df)
    _share_table(df.role_family, "role_family", n).to_csv(TAB / "T19_supplement_families.csv", index=False)
    _share_table(df.source, "source", n).to_csv(TAB / "T19_supplement_sources.csv", index=False)
    _share_table(df.state, "state", n).to_csv(TAB / "T19_supplement_states.csv", index=False)
    expl = df.skills_all_tech.explode().dropna()
    expl = expl[expl.astype(str).str.len() > 0]
    counts = expl.value_counts().reset_index()
    if counts.empty:
        skills = pd.DataFrame(columns=["skill", "count", "n", "share", "ci_low", "ci_high"])
    else:
        counts.columns = ["skill", "count"]
        counts["n"] = n
        counts["share"] = (counts["count"] / n).round(3)
        counts["ci_low"], counts["ci_high"] = zip(*[wilson(int(c), n) for c in counts["count"]])
        skills = counts
    skills.to_csv(TAB / "T19_supplement_skills.csv", index=False)
    print(f"T19 published_aggregates n_core={n} with_description={n_desc}")
    return status


if __name__ == "__main__":
    main()
