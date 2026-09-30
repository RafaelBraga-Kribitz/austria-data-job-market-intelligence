"""Shared helpers for the Layer 2 / Layer 3 analysis scripts: loading the private processed tables, population
definitions, Wilson intervals, concentration measures, table writing with n on every row, and the public (aggregate-only)
view of the private LinkedIn slot."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
OUT = ROOT / "outputs"
CFG = json.load(open(ROOT / "config" / "supply_taxonomy.json", encoding="utf-8"))
CAP = json.load(open(ROOT / "config" / "capability_map.json", encoding="utf-8"))["capabilities"]
FAMILY_LABELS = {"data_analytics": "Data analytics", "bi": "BI", "data_science": "Data science", "data_engineering": "Data engineering",
                 "data_governance": "Data governance", "marketing_analytics": "Marketing analytics", "product_analytics": "Product analytics",
                 "business_analysis": "Business analysis", "ai_software_engineering": "AI software engineering (adjacent)", "other_data": "Other data (adjacent)", "ai_ml_generic": "ML/AI/data interest wording (adjacent)"}
CORE_FAMILIES = ["data_engineering", "data_science", "business_analysis", "data_analytics", "bi", "data_governance", "marketing_analytics", "product_analytics"]
REGIONS = ["Wien", "Steiermark", "Oberösterreich", "Salzburg", "Tirol", "Kärnten", "Vorarlberg", "Niederösterreich", "Burgenland", "unspecified (Austria)"]


def wilson(k, n, z: float = 1.96):
    if not n:
        return (float("nan"), float("nan"))
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round((c - h) / d, 3), round((c + h) / d, 3)


def load_candidates() -> pd.DataFrame:
    rows = [json.loads(l) for l in open(PROC / "supply_candidates.jsonl", encoding="utf-8")]
    df = pd.DataFrame(rows)
    # builds before 2026-09-30 carry only the raw website field; redaction nulls it after deriving has_blog
    from_blog = df["blog"].fillna("").astype(str).str.strip().ne("") if "blog" in df.columns else pd.Series(False, index=df.index)
    df["has_blog"] = df["has_blog"].where(df["has_blog"].notna(), from_blog).astype(bool) if "has_blog" in df.columns else from_blog
    df["is_austria"] = df["state"].notna() & ~(df["foreign_place_named"].fillna(False) & ~df["austria_named"].fillna(False))
    df["region"] = df["state"].where(df["is_austria"], None)
    df["is_t1"] = (df["data_tier"] == "T1_bio_declared") & df["bio_role_family"].isin(CORE_FAMILIES)
    df["is_bio_adjacent"] = df["bio_role_family"].isin(["ai_software_engineering", "other_data", "ai_ml_generic"])
    df["is_data"] = df["is_data_signal"].fillna(False) & df["is_austria"]
    df["frame_a"] = df["frames"].map(lambda f: "A" in (f or []))
    df["frame_b"] = df["frames"].map(lambda f: "B" in (f or []))
    df["frame_c"] = df["frames"].map(lambda f: "C" in (f or []))
    df["family"] = df["bio_role_family"].where(df["is_t1"], None)
    df["family_label"] = df["family"].map(FAMILY_LABELS)
    return df


def load_projects() -> pd.DataFrame:
    rows = [json.loads(l) for l in open(PROC / "supply_projects.jsonl", encoding="utf-8")]
    return pd.DataFrame(rows)


def load_evidence() -> pd.DataFrame:
    return pd.read_parquet(PROC / "supply_skill_evidence.parquet")


def share_table(series_of_lists_or_values: pd.Series, n: int, label: str, min_count: int = 1, top: int | None = None, explode: bool = True) -> pd.DataFrame:
    s = series_of_lists_or_values
    if explode:
        s = s.dropna().explode()
    s = s.dropna()
    vc = s.value_counts()
    vc = vc[vc >= min_count]
    if top:
        vc = vc.head(top)
    df = vc.reset_index(); df.columns = [label, "count"]
    df["n"] = n; df["share"] = (df["count"] / n).round(3)
    ci = [wilson(int(k), n) for k in df["count"]]
    df["ci_low"] = [c[0] for c in ci]; df["ci_high"] = [c[1] for c in ci]
    return df


def concentration(counts: pd.Series) -> dict:
    p = counts / counts.sum() if counts.sum() else counts
    ent = float(-(p[p > 0] * (p[p > 0].map(math.log2))).sum()) if len(p) else 0.0
    return {"distinct": int((counts > 0).sum()), "total": int(counts.sum()), "entropy_bits": round(ent, 3),
            "normalised_entropy": round(ent / math.log2(len(p)), 3) if len(p) > 1 else None, "hhi": round(float((p ** 2).sum()), 4),
            "top1_share": round(float(p.max()), 3) if len(p) else None, "top5_share": round(float(p.nlargest(5).sum()), 3) if len(p) else None}


def write(df: pd.DataFrame, name: str, note: str | None = None) -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    if note:
        df = df.copy(); df["note"] = note
    df.to_csv(TAB / f"{name}.csv", index=False)


def load_layer1_table(name: str) -> pd.DataFrame:
    return pd.read_csv(TAB / f"{name}.csv")


# ------------------------------------------------------------------ LinkedIn slot: the only view that may leave data/
LINKEDIN_MIN_CELL = 5
_LEAK = re.compile(r"linkedin\.com/in/|@", re.I)


def _str_col(df: pd.DataFrame | None, col: str) -> pd.Series:
    if df is None or not len(df) or col not in df.columns:
        return pd.Series([], dtype=str)
    return df[col].fillna("").astype(str).str.strip().replace({"nan": ""})


def _cells(values: pd.Series, min_cell: int = LINKEDIN_MIN_CELL) -> tuple[dict, int]:
    """Categories with >= min_cell rows, plus the suppressed remainder (blank values included). Secondary suppression moves
    the smallest shown cell into the remainder until the remainder is 0 or >= min_cell, so the published total minus the
    shown cells never reveals a cell below min_cell."""
    vc = values.value_counts()
    shown = {str(k): int(v) for k, v in vc.items() if int(v) >= min_cell and str(k) and not _LEAK.search(str(k))}
    rest = int(vc.sum()) - sum(shown.values())
    while 0 < rest < min_cell and shown:
        smallest = min(shown, key=lambda k: (shown[k], k))
        rest += shown.pop(smallest)
    return shown, rest


def public_linkedin_summary(counts: pd.DataFrame | None, profiles: pd.DataFrame | None) -> dict:
    """Tallies of the private LinkedIn slot that are safe to leave `outputs/`: no count grid, headline, pseudo-id, note or
    contact, and no cell below LINKEDIN_MIN_CELL profiles. Contract: the keys below are always present (export_supply_json
    reads `status`; tests/test_linkedin_slot.py pins the key set). NaN-safe for frames read with default pandas NA handling."""
    n_c = int(len(counts)) if counts is not None else 0
    n_p = int(len(profiles)) if profiles is not None else 0
    if n_c or n_p:
        status = (f"LinkedIn slot has private records: {n_c} search counts, {n_p} coded profiles (permitted channels only, D-018). "
                  "Tallies only: the count grid, headlines and pseudo-ids stay in data/.")
    else:
        status = ("NOT COLLECTED by automation (LinkedIn User Agreement 8.2, robots.txt; DECISION_LOG D-013/D-018). "
                  "The offline LinkedIn slot exists and is empty.")
    dates = sorted({d for d in pd.concat([_str_col(counts, "collection_date"), _str_col(profiles, "collection_date")]) if d})
    count_methods = {str(k): int(v) for k, v in _str_col(counts, "acquisition_method").str.lower().replace("", "unspecified").value_counts().items()}
    count_quality = {str(k): int(v) for k, v in _str_col(counts, "source_quality").str.upper().replace("", "unspecified").value_counts().items()}
    prof_methods, prof_methods_rest = _cells(_str_col(profiles, "acquisition_method").str.lower())
    prof_quality, prof_quality_rest = _cells(_str_col(profiles, "source_quality").str.upper())
    locations, loc_rest = _cells(_str_col(profiles, "location_text"))
    seen: Counter[str] = Counter()
    for raw in _str_col(profiles, "languages_stated"):
        for part in {p.strip() for p in raw.split(";")}:
            if part and not _LEAK.search(part):
                seen[part] += 1
    languages = {k: int(v) for k, v in sorted(seen.items()) if v >= LINKEDIN_MIN_CELL}
    return {
        "status": status,
        "linkedin_collection_dates": dates,
        "search_counts_recorded": n_c,
        "profiles_recorded": n_p,
        "search_counts_by_method": count_methods,
        "search_counts_by_source_quality": count_quality,
        "profiles_by_method_n_ge_5": prof_methods,
        "profiles_by_method_other_or_suppressed": prof_methods_rest,
        "profiles_by_source_quality_n_ge_5": prof_quality,
        "profiles_by_source_quality_other_or_suppressed": prof_quality_rest,
        "profiles_by_location_n_ge_5": locations,
        "profiles_by_location_other_or_suppressed": loc_rest,
        "languages_stated_n_ge_5": languages,
        "public_profile_aggregates": ("cells below 5 profiles are merged into *_other_or_suppressed (with secondary suppression, "
                                      "so totals cannot be differenced back to a small cell); a profile may state several languages"),
        "protocol": "docs/supply-methodology.md §7 (LinkedIn slot protocol)",
    }
