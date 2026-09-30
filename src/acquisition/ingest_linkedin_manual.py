"""Layer 2 LinkedIn slot: validation and ingestion of LinkedIn observations acquired through permitted channels (offline, private).

Why this shape. LinkedIn's User Agreement 8.2 and robots.txt prohibit automated access to the member-facing site
(docs/legal-and-publication-audit.md §2, DECISION_LOG D-013/D-018), and automated collection of member profiles would be
profiling of identifiable persons under GDPR. A member may search and read LinkedIn manually; a licensee of LinkedIn's own
products (Talent Insights, Recruiter, Campaign Manager / Marketing API) may export what that licence grants; and third-party
licensed datasets carry their own terms. All of those produce the SAME two tables here, distinguished by `acquisition_method`,
so the analysis code never needs to know how a row was obtained. The slot is therefore channel-agnostic but not rule-agnostic:
rows tagged with a scraped / automated-member-site method are rejected (see FORBIDDEN_METHODS). FORBIDDEN_METHODS (incl.
`guest_endpoint`, `jobspy`) govern this member/candidate slot only: src/acquisition/collect_linkedin.py is a separate Layer 1
job-postings collector (2026-09-16, public guest job endpoint, D-022) and never touches member profiles. The file name, the
`profiles_manual.csv` name and `source = "linkedin_manual"` predate the channel-agnostic design and are kept as stable labels:
they mean "LinkedIn slot", whatever the channel.

Contract, value domains and per-channel coverage: docs/linkedin-slot-interface.md. Protocol: docs/supply-methodology.md §7.

Inputs (data/raw/linkedin_supply/<date>/; empty templates come from --templates, never from an ingest run):
  search_counts.csv   one row per population count: query grid (title keyword, location filter, language/other filters),
                      the count the channel reported, timestamp. Counts are NOT unique people; treat as an index (§5).
  profiles_manual.csv one row per individual-level record, identified only by a pseudonymous id assigned by the observer
                      (never a name or URL): headline, current title, location, seniority label, years of experience
                      (explicit only), education level/field, certifications, languages with stated level, skills listed,
                      featured/project sections, GitHub/Kaggle/portfolio links present (yes/no), open-to-work signal,
                      career-transition wording. Only fields visible without connecting; no inference from photos/names.

Outputs (data/processed/, private; written only when at least one table has rows):
  supply_linkedin_counts.csv    search_counts.csv (contract columns) + collection_date
  supply_linkedin_profiles.csv  profiles_manual.csv (contract columns) + collection_date, source = "linkedin_manual"
  In both, acquisition_method is lower-cased, booleans are written as true/false (blank = not stated), result_count as an
  integer, and a blank source_quality is defaulted from the acquisition method. src/pipeline/build_supply.py folds the
  profile rows into the candidate table.

Usage:
  python src/acquisition/ingest_linkedin_manual.py --templates [--date YYYY-MM-DD]   write/upgrade empty templates (default: today, Vienna)
  python src/acquisition/ingest_linkedin_manual.py [--date YYYY-MM-DD] [--check] [--replace]
      validate and ingest one dated folder (default: the latest existing one); --check writes nothing; --replace allows
      replacing processed tables that hold another collection date (never merged, docs/linkedin-slot-interface.md §6.5)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SLOT_DIR = Path("data") / "raw" / "linkedin_supply"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# acquisition_method -> (default source_quality, individual-level records permitted?). Grades follow the scale of
# docs/supply-methodology.md §2 (A direct structured source ... C indexed/secondary result); manual_ui is C for both tables
# (observer-transcribed from a personalised, relevance-ranked search; aligned with §7 and the interface doc §1).
METHODS = {
    "manual_ui":             ("C", True),   # hand-read and hand-typed by the observer from the member site
    "talent_insights":       ("A", False),  # LinkedIn Talent Insights export (licensed seat); aggregate talent pools
    "ads_audience_estimate": ("C", False),  # Campaign Manager / Marketing API audience forecast; modelled and bucketed
    "recruiter_export":      ("B", True),   # LinkedIn Recruiter export under that contract
    "official_api":          ("B", True),   # approved LinkedIn API app, within the scopes granted
    "member_data_export":    ("B", True),   # "Get a copy of your data" - the observer's own account only
    "licensed_vendor":       ("B", True),   # third-party dataset licensed for research; licence named in evidence_ref
    "economic_graph":        ("A", False),  # LinkedIn Economic Graph / open aggregate publications
    "survey_self_report":    ("B", True),   # respondents describing their own LinkedIn presence
}
FORBIDDEN_METHODS = ("scrape", "scraped", "crawler", "browser_automation", "headless", "selenium", "puppeteer",
                     "playwright", "api_unofficial", "guest_endpoint", "jobspy", "proxy_rotation")
QUALITY = ("A", "B", "C", "D", "E")

COUNT_COLS = ["observed_at", "observer", "acquisition_method", "evidence_ref", "query_title", "location_filter",
              "extra_filters", "language_filter", "result_count", "count_is_capped", "source_quality", "notes"]
PROFILE_COLS = ["pseudo_id", "observed_at", "observer", "acquisition_method", "evidence_ref", "headline", "current_title",
                "location_text", "seniority_label", "years_experience_explicit", "education_level", "education_field",
                "certifications", "languages_stated", "skills_listed", "has_featured_section", "n_projects_listed",
                "has_github_link", "has_kaggle_link", "has_portfolio_link", "open_to_work_signal", "transition_wording",
                "prior_domain", "industry_stated", "consultant_freelance_signal", "source_quality", "notes"]
COUNT_REQUIRED = ["observed_at", "observer", "acquisition_method", "evidence_ref", "query_title", "location_filter",
                  "result_count", "count_is_capped"]
PROFILE_REQUIRED = ["pseudo_id", "observed_at", "observer", "acquisition_method", "evidence_ref", "current_title", "location_text"]
COUNT_BOOLS = ["count_is_capped"]
PROFILE_BOOLS = ["has_featured_section", "has_github_link", "has_kaggle_link", "has_portfolio_link", "open_to_work_signal",
                 "consultant_freelance_signal"]
PROFILE_INTS = ["years_experience_explicit", "n_projects_listed"]
ENUMS = {
    "seniority_label": ("student", "junior", "unlabelled", "senior", "lead_head", "unknown"),
    "education_level": ("BSc", "MSc", "PhD", "FH", "HTL", "bootcamp", "none_stated"),
    "prior_domain": ("marketing", "business", "finance", "engineering", "science", "economics", "statistics", "software", "social"),
}
LEAK = re.compile(r"linkedin\.com/in/|@", re.I)
TRUE_WORDS = ("true", "yes", "y", "1", "1.0")
FALSE_WORDS = ("false", "no", "n", "0", "0.0")


def parse_bool(value) -> str | None:
    """Shared boolean parser of the slot: 'true' / 'false', '' for not stated, None for an unreadable value."""
    v = "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value).strip().lower()
    if v in ("", "nan"):
        return ""
    if v in TRUE_WORDS:
        return "true"
    if v in FALSE_WORDS:
        return "false"
    return None


def _lines(mask: pd.Series) -> str:
    """CSV line numbers (header = line 1) of the flagged rows; never the cell content, which may be personal."""
    idx = [int(i) + 2 for i in mask[mask].index[:5]]
    more = int(mask.sum()) - len(idx)
    return ", ".join(map(str, idx)) + (f" (+{more} more)" if more > 0 else "")


def read_table(path: Path, cols: list[str]) -> tuple[pd.DataFrame, bool]:
    """Read one slot CSV as strings (blank = not stated). Returns (frame, stale_template): a header-only file with an older
    header (e.g. the 2026-09-17 templates) is read as an empty current-schema table and flagged for --templates to upgrade."""
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=cols), True
    df = df.apply(lambda s: s.str.strip())
    if not len(df) and list(df.columns) != cols:
        return pd.DataFrame(columns=cols), True
    return df, False


def templates(folder: Path) -> list[str]:
    """Write missing templates; rewrite header-only templates whose header is outdated. Filled files are never touched."""
    folder.mkdir(parents=True, exist_ok=True)
    done = []
    for name, cols in (("search_counts.csv", COUNT_COLS), ("profiles_manual.csv", PROFILE_COLS)):
        p = folder / name
        if not p.exists():
            pd.DataFrame(columns=cols).to_csv(p, index=False)
            done.append(f"template written: {p}")
        elif read_table(p, cols)[1]:
            pd.DataFrame(columns=cols).to_csv(p, index=False)
            done.append(f"header-only template upgraded to the current schema: {p}")
    return done


def check_methods(df: pd.DataFrame, name: str, individual: bool) -> list:
    """Validate acquisition_method; returns a list of problems (empty = clean)."""
    problems = []
    if not len(df):
        return problems
    m = df["acquisition_method"].fillna("").astype(str).str.strip().str.lower()
    if (m == "").any():
        problems.append(f"{name}: {(m == '').sum()} row(s) without acquisition_method (allowed: {', '.join(sorted(METHODS))})")
    forbidden = m.map(lambda v: any(f in v for f in FORBIDDEN_METHODS))
    if forbidden.any():
        problems.append(f"{name}: automated collection from the member site is out of scope (D-013/D-018): {sorted(set(m[forbidden]))}")
    unknown = sorted(set(m[(m != "") & ~m.isin(METHODS) & ~forbidden]))
    if unknown:
        problems.append(f"{name}: unknown acquisition_method {unknown}; allowed: {', '.join(sorted(METHODS))}")
    if individual:
        aggregate_only = sorted({v for v in m if v in METHODS and not METHODS[v][1]})
        if aggregate_only:
            problems.append(f"{name}: {aggregate_only} deliver aggregates only; those figures belong in search_counts.csv")
    return problems


def default_quality(df: pd.DataFrame) -> pd.Series:
    m = df["acquisition_method"].fillna("").astype(str).str.strip().str.lower()
    fallback = m.map(lambda v: METHODS.get(v, ("C", True))[0])
    stated = df["source_quality"].fillna("").astype(str).str.strip().str.upper()
    return stated.where(stated != "", fallback)


def leak_problems(df: pd.DataFrame, name: str) -> list:
    """URL / e-mail leak guard over every column of the file (contract columns and any extra column)."""
    out = []
    for col in df.columns:
        hit = df[col].fillna("").astype(str).str.contains(LEAK)
        if hit.any():
            out.append(f"{name}: column {col} contains a profile URL or an e-mail (lines {_lines(hit)}); remove it (pseudonymous ids only)")
    return out


def normalise(df: pd.DataFrame, bools: list[str]) -> tuple[pd.DataFrame, list]:
    """Lower-case acquisition_method, upper-case source_quality, booleans to true/false/'' (problems for unreadable ones)."""
    df = df.copy()
    problems = []
    df["acquisition_method"] = df["acquisition_method"].str.lower()
    df["source_quality"] = df["source_quality"].str.upper()
    for col in bools:
        parsed = df[col].map(parse_bool)
        bad = parsed.isna()
        if bad.any():
            problems.append(f"column {col}: not a boolean (true/false, yes/no, 1/0 or blank) on lines {_lines(bad)}")
        df[col] = parsed.fillna("")
    return df, problems


def _required(df: pd.DataFrame, cols: list[str], name: str) -> list:
    out = []
    for col in cols:
        blank = df[col] == ""
        if blank.any():
            out.append(f"{name}: required column {col} is blank on lines {_lines(blank)}")
    return out


def _timestamps(df: pd.DataFrame, name: str) -> list:
    s = df["observed_at"]
    parsed = pd.to_datetime(s, errors="coerce", format="ISO8601", utc=True)
    bad = (s != "") & parsed.isna()
    return [f"{name}: observed_at is not an ISO date/datetime on lines {_lines(bad)}"] if bad.any() else []


def _non_negative_int(s: pd.Series) -> pd.Series:
    """True where a non-blank value is not a non-negative integer."""
    num = pd.to_numeric(s.where(s != ""), errors="coerce")
    return (s != "") & (num.isna() | (num < 0) | (num != num.round()))


def validate_counts(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    name = "search_counts.csv"
    df, problems = normalise(df, COUNT_BOOLS)
    problems = [f"{name}: {p}" for p in problems]
    if not len(df):
        return df, problems
    problems += _required(df, COUNT_REQUIRED, name)
    problems += check_methods(df, name, individual=False)
    problems += _timestamps(df, name)
    bad = _non_negative_int(df["result_count"])
    if bad.any():
        problems.append(f"{name}: result_count is not a non-negative integer on lines {_lines(bad)}")
    bad = (df["source_quality"] != "") & ~df["source_quality"].isin(QUALITY)
    if bad.any():
        problems.append(f"{name}: source_quality outside A–E on lines {_lines(bad)}")
    return df, problems


def validate_profiles(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    name = "profiles_manual.csv"
    df, problems = normalise(df, PROFILE_BOOLS)
    problems = [f"{name}: {p}" for p in problems]
    if not len(df):
        return df, problems
    problems += _required(df, PROFILE_REQUIRED, name)
    problems += check_methods(df, name, individual=True)
    problems += _timestamps(df, name)
    ids = df["pseudo_id"]
    dup = (ids != "") & ids.duplicated(keep=False)
    if dup.any():
        problems.append(f"{name}: duplicate pseudo_id on lines {_lines(dup)}")
    for col, allowed in ENUMS.items():
        bad = (df[col] != "") & ~df[col].isin(allowed)
        if bad.any():
            problems.append(f"{name}: {col} outside {' · '.join(allowed)} on lines {_lines(bad)}")
    for col in PROFILE_INTS:
        bad = _non_negative_int(df[col])
        if bad.any():
            problems.append(f"{name}: {col} is not a non-negative integer on lines {_lines(bad)}")
    bad = (df["source_quality"] != "") & ~df["source_quality"].isin(QUALITY)
    if bad.any():
        problems.append(f"{name}: source_quality outside A–E on lines {_lines(bad)}")
    return df, problems


def latest_folder(base: Path) -> str | None:
    """Latest collection folder named exactly YYYY-MM-DD (suffixed test folders are ignored)."""
    if not base.exists():
        return None
    names = sorted(p.name for p in base.iterdir() if p.is_dir() and DATE_RE.match(p.name))
    return names[-1] if names else None


def _processed_dates(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        return set()
    return set(df["collection_date"]) - {""} if "collection_date" in df.columns else set()


def public_linkedin_summary(counts: pd.DataFrame, profiles: pd.DataFrame) -> dict:
    """Moved to src/analysis/supply_common.py (analysis must not import collector code). This thin forwarder remains only for
    the private cockpit (src/private/linkedin_coder/server.py), which imports it from here."""
    analysis = str(Path(__file__).resolve().parents[1] / "analysis")
    if analysis not in sys.path:
        sys.path.insert(0, analysis)
    from supply_common import public_linkedin_summary as summary
    return summary(counts, profiles)


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description="LinkedIn slot: templates, validation and ingestion (offline, private).")
    ap.add_argument("--date", default=None, help="collection folder YYYY-MM-DD (default: latest existing folder; --templates: today)")
    ap.add_argument("--templates", action="store_true", help="write missing templates / upgrade header-only ones, then stop")
    ap.add_argument("--check", action="store_true", help="validate the folder without writing to data/processed/")
    ap.add_argument("--replace", action="store_true", help="allow replacing processed tables of another collection date")
    a = ap.parse_args(argv)
    base = root / SLOT_DIR
    if a.date is not None and not DATE_RE.match(a.date):
        print(f"--date must be YYYY-MM-DD, got {a.date!r}")
        return 1
    if a.templates:
        date = a.date
        if date is None:
            from common import today  # Europe/Vienna collection day; imported here so validation never loads the HTTP helpers
            date = today()
        folder = base / date
        for line in templates(folder) or [f"templates already current in {folder}"]:
            print(line)
        print(f"fill them (docs/linkedin-slot-interface.md §2), then: python src/acquisition/ingest_linkedin_manual.py --date {date} --check")
        return 0
    date = a.date or latest_folder(base)
    if date is None:
        print(f"no collection folder under {base}; start one with --templates [--date YYYY-MM-DD]")
        return 1
    folder = base / date
    paths = {"search_counts.csv": folder / "search_counts.csv", "profiles_manual.csv": folder / "profiles_manual.csv"}
    missing_files = [n for n, p in paths.items() if not p.exists()]
    if missing_files:
        print(f"{folder}: missing {missing_files}; write templates with --templates --date {date} (nothing ingested)")
        return 1
    counts, stale_c = read_table(paths["search_counts.csv"], COUNT_COLS)
    profs, stale_p = read_table(paths["profiles_manual.csv"], PROFILE_COLS)
    for name, stale in (("search_counts.csv", stale_c), ("profiles_manual.csv", stale_p)):
        if stale:
            print(f"note: {name} is a header-only template with an older header; read as empty (upgrade: --templates --date {date})")
    missing = [c for c in COUNT_COLS if c not in counts.columns] + [c for c in PROFILE_COLS if c not in profs.columns]
    if missing:
        print("schema problem, missing columns:", missing)
        return 1
    problems = leak_problems(counts, "search_counts.csv") + leak_problems(profs, "profiles_manual.csv")
    extra = [c for c in list(counts.columns) + list(profs.columns) if c not in COUNT_COLS + PROFILE_COLS]
    counts, p1 = validate_counts(counts[COUNT_COLS])
    profs, p2 = validate_profiles(profs[PROFILE_COLS])
    problems += p1 + p2
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    counts["source_quality"] = default_quality(counts)
    profs["source_quality"] = default_quality(profs)
    if len(counts):
        counts["result_count"] = pd.to_numeric(counts["result_count"]).astype(int).astype(str)
    if extra:
        print(f"note: columns outside the contract are not carried to data/processed/: {sorted(set(extra))}")
    if a.check:
        print(f"linkedin slot OK ({date}): {len(counts)} counts, {len(profs)} profiles validated (nothing written; --check)")
        return 0
    if not len(counts) and not len(profs):
        print(f"nothing to ingest: both tables in {folder} are empty; data/processed/ left unchanged")
        return 1
    out = root / "data" / "processed"
    targets = (out / "supply_linkedin_counts.csv", out / "supply_linkedin_profiles.csv")
    other = set().union(*(_processed_dates(p) for p in targets)) - {date}
    if other and not a.replace:
        print(f"data/processed/ holds LinkedIn tables of collection date(s) {sorted(other)}; dates are never merged. "
              f"Re-run with --replace to replace them with {date}.")
        return 1
    out.mkdir(exist_ok=True, parents=True)
    counts.assign(collection_date=date).to_csv(targets[0], index=False)
    profs.assign(collection_date=date, source="linkedin_manual").to_csv(targets[1], index=False)
    tally = lambda df: ", ".join(f"{k}={v}" for k, v in df["acquisition_method"].value_counts().items()) or "none"  # noqa: E731
    print(f"linkedin slot ({date}): {len(counts)} counts ({tally(counts)}), {len(profs)} coded profiles ({tally(profs)}) "
          "-> data/processed/ (private)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
