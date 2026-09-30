"""Build the PUBLIC (sanitised) version of this repository.

Policy (docs/legal-and-publication-audit.md §7 and §11, PUBLICATION_DECISION.md):
  PUBLIC  : the author's code except the six posting-collector scripts (five posting sources: EURES incl. its regional
            text sweep, karriere.at, jobs.at, LinkedIn, willhaben) and except src/private/; configurations (with a
            neutral example profile in place of the owner's config/profile.json); schemas, docs, decision documents,
            aggregated tables, figures, JSON summaries, the digest, tests (integrity tests skip without processed data),
            the openly licensed Eurostat raw data, and a purpose-written public .gitignore (src/publish/public.gitignore).
  PRIVATE : data/raw (except Eurostat), data/processed, data/external (fetched third-party pages), logs, PROGRESS.md,
            the owner's personal strategy documents (CAREER_ASSUMPTIONS_REVIEW.md, library_strategy/,
            docs/profile-specific-demand-supply-analysis.md, docs/linkedin-slot-interface.md, config/profile.json),
            the synthetic fixtures of the private radar parsers, per-posting tables that carry free text, contact data
            or source URLs, and any column that holds verbatim posting text or a link ("*snippet*", "description*",
            "*_url*", "*_html*"). Internal posting ids ("source:source_id") are replaced by keyed hashes.

Guard: every exported file is scanned. An e-mail address, a phone number (international or Austrian domestic
format), a posting URL of a job board, a secret-like token (also in .md), a GitHub login from the private candidate
list, a non-allow-listed URL, a raw source posting id or an over-long free-text cell in a table, a suppression-threshold breach in C02/C19e,
or a private path in the tree blocks the export.

Atomicity: the tree is built in a staging directory next to the target and moved into the target only when the
scan finds nothing. A blocked export leaves the target (and its .git) exactly as it was.

Usage:  python src/publish/export_public.py [target_dir]   (default: ../austria-data-job-market-intelligence-public)
On success the target is emptied (except its .git folder) and replaced by the staged tree, so the public git
history never contains private material.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = ROOT.parent / "austria-data-job-market-intelligence-public"

# ---- file-level policy -------------------------------------------------------------------------
INCLUDE_FILES = [
    "README.md", "AGENT_CONTEXT.md", "CAREER_DECISION_MAP.md", "CAREER_SUPPLY_DEMAND_MAP.md", "DECISION_LOG.md", "PUBLICATION_DECISION.md",
    "LICENSE", "CITATION.cff", "requirements.txt", ".gitattributes",
]
# copied when present (packaging and CI metadata)
OPTIONAL_FILES = ["pyproject.toml", "run_all.py"]
OPTIONAL_DIRS = [".github"]
# the public .gitignore is purpose-written; the private one names private tools and folders and is never exported
PUBLIC_GITIGNORE = "src/publish/public.gitignore"
INCLUDE_DIRS = ["docs", "config", "schemas", "tests", "outputs/figures", "src/pipeline", "src/analysis",
                "src/reporting", "src/publish",
                # the visual decision layer: house style, vendored Lato (SIL OFL 1.1) and the figure engine,
                # without which outputs/figures/BQ* cannot be rebuilt by an outside reader
                "src/viz"]
INCLUDE_ACQUISITION = ["common.py", "collect_jobbarometer.py", "collect_eurostat_jvs.py",
                       # Layer 2 (2026-09-17): documented public APIs / open datasets / manual-entry ingestion — no source records inside
                       "collect_github_supply.py", "collect_eurostat_supply.py", "ingest_stackoverflow_survey.py", "ingest_linkedin_manual.py",
                       # D-023: documented Arbeitnow job-board API (raw stays gitignored)
                       "collect_arbeitnow.py"]
# raw data that may be published: Eurostat is an openly licensed, documented API (docs/seasonality.md §2)
INCLUDE_RAW_DIRS = ["data/raw/eurostat_jvs", "data/raw/eurostat_supply"]
# Layer 2 individual-level material stays private: data/raw/github_supply, data/raw/linkedin_supply, data/external/stackoverflow_survey,
# data/processed/supply_* (candidates, projects, evidence, quality review samples) — none of these paths is in any INCLUDE list.
EXCLUDE_ACQUISITION = ["collect_eures.py", "collect_eures_styria_text.py", "collect_karriere.py", "collect_jobsat.py", "collect_linkedin.py", "collect_willhaben.py"]
# six posting-collector scripts for five posting sources stay private (terms: docs/legal-and-publication-audit.md §2, §6).
# Arbeitnow is a documented public API (D-023); its raw records stay gitignored.
EXCLUDE_DOCS = {
    "profile-specific-demand-supply-analysis.md",  # the owner's personal strategy (Layer 3 profile layer)
    "linkedin-slot-interface.md",                  # LinkedIn slot interface: private by owner decision 2026-09-30 (D-026)
}
# Public-only presentation files (the portfolio README, its banner and author portrait, the README quality-gate workflow)
# live here in the private repository. Every file under the folder is copied over the staged tree at the same relative
# path (overwriting, e.g. README.md) once the tree is built and before the scans run, so every scan covers it. The folder
# itself is never exported under its own name (EXCLUDE_PATHS; PRIVATE_NEVER re-checks it).
PUBLIC_OVERLAY = "src/publish/public_overlay"
# paths (relative, "/"-separated) inside INCLUDE_DIRS that are never exported; a trailing "/" excludes a folder
EXCLUDE_PATHS = {
    "config/profile.json",          # the owner's own profile stays private (D-026); replaced by the neutral example below
    "config/profile.example.json",  # exported under the name config/profile.json instead
    "tests/fixtures/radar/",        # hand-written fixtures that only exercise the private radar parsers (the test skips without them)
    PUBLIC_OVERLAY + "/",           # exported only at its target paths (apply_overlay)
}
# public path -> private source: the public tree gets the neutral example profile under the name the code reads
SUBSTITUTE_FILES = {"config/profile.json": "config/profile.example.json"}
# never allowed anywhere in the public tree, whatever the INCLUDE lists say
PRIVATE_NEVER = ["src/private/", "library_strategy/", "logs/", "data/processed/profile_fit/",
                 "data/raw/radar/", "data/raw/arbeitnow/", "data/raw/github_supply/", "data/raw/linkedin_supply/",
                 "data/external/stackoverflow_survey/", "data/labels/", "data/private/",
                 "CAREER_ASSUMPTIONS_REVIEW.md", "PROGRESS.md",
                 "docs/profile-specific-demand-supply-analysis.md", "docs/linkedin-slot-interface.md",
                 PUBLIC_OVERLAY + "/"]  # the overlay reaches the public tree only at its target paths
EXCLUDE_TABLES = {
    "T09e_salary_observations.csv",   # per-posting rows with employer + salary + snippet
    "Q07a_salary_audit_sample.csv",   # verbatim salary snippets
    "Q07b_salary_implausible.csv",    # verbatim salary snippets
    "Q09_skill_spotcheck_sample.csv", # verbatim snippets + source URLs
    "T16a_adjacent_titles_styria.csv",# per-posting rows with source URLs
}
# snippet / verbatim description / any url or html column, as a whole name or an "_"-separated part of one
# ("source_url", "html_url", "repo_urls", "raw_html"); count columns such as "with_description" or
# "description_gt300" are aggregates and are kept
DROP_COLUMNS_RE = re.compile(r"snippet|^description$|description_text|description_html|(^|_)urls?($|_)|(^|_)html($|_)", re.I)
# internal posting identifiers are "source:source_id" (e.g. a LinkedIn job id) in the private tables; the export replaces
# them by a keyed hash so that public rows stay joinable across tables without revealing the source record. Key: the
# EXPORT_UID_KEY environment variable (keep it private to trace public rows back); a random per-run key otherwise.
PSEUDONYMISE_COLUMNS = {"posting_uid"}
# a raw "source:source_id" value surviving anywhere in a table is a source posting identifier
SOURCE_ID_RE = re.compile(r"\b(?:eures|eures_textsearch|karriere|linkedin|willhaben|jobsat|arbeitnow|jobspy_\w+):[\w-]{5,}", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# placeholder addresses: reserved example domains (RFC 2606/6761), the ".tld" placeholder, one-letter domains such as
# "a@b.at" in unit tests, and the co-author trailer of commit messages
EMAIL_ALLOWED_SUFFIXES = ("@example.com", "@example.org", "@example.net", ".example", ".invalid", ".test", ".tld",
                          ".localhost", "@anthropic.com")
# international (+43 / 0043) and Austrian domestic formats ("0316 123456", "0664/1234567", "(01) 234 56 78");
# a match counts only with 8-15 digits, so dates, years and counts do not trigger it
PHONE_RE = re.compile(r"(?:\+43|0043)\s?[\d\s/\-()]{6,}\d"
                      r"|(?<![\w.,:/-])\(?0[1-9]\d{0,4}\)?[ /-]{1,3}\d{2,}(?:[ /-]?\d{2,}){0,4}")
# synthetic numbers written into tests on purpose (tests/test_pipeline.py: a phone number must not be read as a salary)
PHONE_ALLOWED = {"0316 2026 12345"}
# links to individual job advertisements (realistic id lengths only, so documentation of the endpoints does not trigger)
POSTING_URL_RE = re.compile(
    r"linkedin\.com/jobs/view/[\w%-]*\d{8,}|linkedin\.com/jobs-guest/jobs/api/jobPosting/\d{6,}"
    r"|karriere\.at/jobs/\d{5,}|willhaben\.at/jobs/job/\S+?/\d{5,}|jobs\.at/i/\d{5,}"
    r"|europa\.eu/eures/portal/jv-se/jv-details/\w{8,}|indeed\.com/viewjob\?jk=[0-9a-f]{12,}"
    r"|stepstone\.\w+/stellenangebote--\S+?-\d{6,}", re.I)
URL_RE = re.compile(r"https?://([^/\s\"',;)]+)[^\s\"',;)]*", re.I)
# hosts whose URLs are identifiers of open taxonomies/statistics, not links to source records
URL_ALLOWED_HOSTS = {"data.europa.eu", "ec.europa.eu", "creativecommons.org"}
SECRET_RE = re.compile(
    r"(?i)api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}|bearer\s+[A-Za-z0-9._\-]{20,}|li_at=[A-Za-z0-9_\-]{10,}"
    r"|JSESSIONID=[A-Za-z0-9._\-]{10,}|[?&]token=[A-Za-z0-9._\-]{16,}"
    r"|\bgh[pousr]_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{20,}|\bAKIA[0-9A-Z]{16}\b"
    r"|-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
TEXT_COL_MAX = 200  # a CSV cell longer than this is treated as free text and rejected, unless the column is a known aggregate list
ALLOW_LONG_COLUMNS = {"top15_skills", "overlap_skills", "structural_skills", "unclassified_skills", "top_tech_skills", "top_business", "top_soft",
                      "defining_skills", "family_mix", "example_titles", "top_skills", "role_rule", "families", "sources", "states",
                      # Layer 2 aggregate columns (skill/theme/format names with counts, JSON dicts of counts, reading notes, table descriptions)
                      "defining_features", "families_T1", "top_titles", "skills_top", "methods_top", "formats_top", "seniority", "regions",
                      "note", "interpretation", "rule_provenance_T1", "frame_combinations", "by_reason", "cross_source_dedup", "measure",
                      "status", "protocol", "signal", "evidence", "feature", "caveat", "field", "query", "answer", "item",
                      "error_types", "definition", "sample", "reviewer", "observability",
                      # D05: the estimation specification written by salary_premium.py (model, controls, corrections)
                      "model"}
# these hold semicolon-separated skill names, regex patterns or job titles produced by the analysis, never advertisement text.
# ("description" is not listed: a column of that exact name is dropped by DROP_COLUMNS_RE before this check.)
# Suppression thresholds of the Layer 2 phrase tables (legal audit §10.6): table -> (count column, minimum)
SUPPRESSION_RULES = {
    "C02_raw_bio_title_distribution.csv": ("count", 3),      # raw-bio phrases shared by >= 3 accounts
    "C19e_common_readme_headings.csv": ("projects", 5),      # README headings used in >= 5 projects
}
# private list of GitHub logins (Layer 2); read only to check that none leaks, never printed
LOGIN_SOURCES = ["data/processed/supply_candidates.parquet", "data/processed/supply_candidates.jsonl"]
LOGIN_MIN_LEN = 4  # shorter logins collide with ordinary tokens (units, codes); they are still checked as whole table cells
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".parquet", ".pyc", ".ttf", ".otf", ".woff", ".woff2", ".zip", ".pdf"}
# Upstream licence texts must be exported byte-for-byte or the licence stops being the
# licence. The SIL Open Font License of the vendored Lato faces carries the foundry's
# contact address in its own text; it is a licence contact, not a data subject.
SCAN_EXEMPT_FILES = {"src/viz/styles/fonts/OFL.txt"}
# Detector code and its unit tests use made-up examples of the formats they detect ("0316/877-1234", "name@host.tld").
# These files skip only the e-mail and phone checks; secrets, posting URLs and logins are still scanned. Keep the list
# short: new tests should assemble such values at run time (see tests/test_export_public.py) instead of being added here.
PATTERN_SOURCE_FILES = {"src/publish/export_public.py", "src/pipeline/redact_layer1_contacts.py", "tests/test_redact_layer1.py"}


def _rel(p: Path, base: Path) -> str:
    return str(p.relative_to(base)).replace("\\", "/")


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def is_excluded(rel: str) -> bool:
    if rel.startswith("docs/") and rel.rsplit("/", 1)[-1] in EXCLUDE_DOCS:
        return True
    return any(rel == x or (x.endswith("/") and rel.startswith(x)) for x in EXCLUDE_PATHS)


def apply_overlay(root: Path, stage: Path) -> list[str]:
    """Copy every file under PUBLIC_OVERLAY over the staged tree at the same relative path; return the paths written."""
    base = root / PUBLIC_OVERLAY
    if not base.is_dir():
        return []
    written = []
    for p in sorted(base.rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts or p.suffix == ".pyc":
            continue
        rel = _rel(p, base)
        copy_file(p, stage / rel)
        written.append(rel)
    return written


def is_placeholder_email(addr: str) -> bool:
    a = addr.lower()
    return a.endswith(EMAIL_ALLOWED_SUFFIXES) or len(a.split("@", 1)[1].split(".")[0]) == 1


def phone_hits(text: str) -> list[str]:
    return [m.group(0) for m in PHONE_RE.finditer(text)
            if 8 <= sum(ch.isdigit() for ch in m.group(0)) <= 15 and m.group(0).strip() not in PHONE_ALLOWED]


def foreign_urls(text: str) -> list[str]:
    return [m.group(0) for m in URL_RE.finditer(text) if m.group(1).lower() not in URL_ALLOWED_HOSTS]


def load_private_logins(root: Path = ROOT) -> set[str]:
    """Lower-cased GitHub logins from the private candidate table; empty when the file is absent."""
    for rel in LOGIN_SOURCES:
        p = root / rel
        if not p.exists():
            continue
        try:
            if p.suffix == ".parquet":
                s = pd.read_parquet(p, columns=["login"])["login"]
            else:
                s = pd.read_json(p, lines=True)["login"]
        except Exception:  # noqa: BLE001 - unreadable file: fall through to the next source
            continue
        # after the Layer 2 redaction (D-028) logins are sha1 pseudonyms; those cannot appear in exported text
        return {v for v in (str(x).strip().lower() for x in s.dropna()) if v and not re.fullmatch(r"[0-9a-f]{16}", v)}
    return set()


def owner_logins(root: Path = ROOT) -> set[str]:
    """The repository owner's own GitHub account (from CITATION.cff) may appear in links to this repository."""
    p = root / "CITATION.cff"
    if not p.exists():
        return set()
    return {m.lower() for m in re.findall(r"github\.com/([A-Za-z0-9-]+)/", p.read_text(encoding="utf-8"))}


_RUN_KEY = secrets.token_bytes(32)


def uid_key() -> bytes:
    k = os.environ.get("EXPORT_UID_KEY", "")
    return k.encode("utf-8") if k else _RUN_KEY


def pseudonymise(value, key: bytes) -> str:
    return "p_" + hmac.new(key, str(value).encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def clean_table(src: Path, dst: Path, logins: set[str] | frozenset = frozenset()) -> list[str]:
    df = pd.read_csv(src)
    dropped = [c for c in df.columns if DROP_COLUMNS_RE.search(str(c))]
    df = df.drop(columns=dropped)
    for c in PSEUDONYMISE_COLUMNS & set(df.columns):
        key = uid_key()
        df[c] = df[c].map(lambda v: v if pd.isna(v) else pseudonymise(v, key))
    problems = []
    for c in df.columns:
        if df[c].dtype == object:
            s = df[c].dropna().astype(str)
            if (s.str.len().max() > TEXT_COL_MAX if len(s) else False) and c not in ALLOW_LONG_COLUMNS:
                problems.append(f"{src.name}:{c} has cells longer than {TEXT_COL_MAX} chars")
            if s.str.contains(EMAIL_RE).any():
                problems.append(f"{src.name}:{c} contains an e-mail address")
            if any(phone_hits(v) for v in s):
                problems.append(f"{src.name}:{c} contains a phone number")
            if any(foreign_urls(v) for v in s):
                problems.append(f"{src.name}:{c} contains a URL")
            if s.str.contains(SOURCE_ID_RE).any():
                problems.append(f"{src.name}:{c} contains a source posting identifier")
            if logins and s.str.strip().str.lower().isin(logins).any():
                problems.append(f"{src.name}:{c} contains a value equal to a private GitHub login (value not shown)")
    dst.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dst, index=False)
    return problems


def clean_json(src: Path, dst: Path, logins: set[str] | frozenset = frozenset()) -> list[str]:
    d = json.loads(src.read_text(encoding="utf-8"))
    leaves: list[str] = []

    def scrub(o):
        if isinstance(o, dict):
            return {k: scrub(v) for k, v in o.items() if not DROP_COLUMNS_RE.search(str(k))}
        if isinstance(o, list):
            return [scrub(x) for x in o]
        if isinstance(o, str):
            leaves.append(o)
        return o

    d = scrub(d)
    txt = json.dumps(d, ensure_ascii=False, indent=1)
    problems = []
    if EMAIL_RE.search(txt):
        problems.append(f"{src.name} contains an e-mail address")
    if phone_hits(txt):
        problems.append(f"{src.name} contains a phone number")
    if any(foreign_urls(v) for v in leaves):
        problems.append(f"{src.name} contains a URL")
    if logins and any(v.strip().lower() in logins for v in leaves):
        problems.append(f"{src.name} contains a value equal to a private GitHub login (value not shown)")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(txt, encoding="utf-8")
    return problems


def check_suppression(tree: Path) -> list[str]:
    """Re-verify the Layer 2 suppression thresholds on the exported tables (a regressed analysis run must not leak rare phrases)."""
    problems = []
    for name, (col, minimum) in SUPPRESSION_RULES.items():
        p = tree / "outputs" / "tables" / name
        if not p.exists():
            continue
        df = pd.read_csv(p)
        if col not in df.columns:
            problems.append(f"{name}: suppression column '{col}' missing, threshold >= {minimum} cannot be verified")
            continue
        counts = pd.to_numeric(df[col], errors="coerce")
        bad = int((counts.isna() | (counts < minimum)).sum())
        if bad:
            problems.append(f"{name}: {bad} row(s) below the suppression threshold {col} >= {minimum}")
    return problems


def scan_tree(target: Path, logins: set[str] | frozenset = frozenset(), allowed_logins: set[str] | frozenset = frozenset()) -> list[str]:
    """Final scan of everything exported (excluding .git)."""
    problems = []
    # links to a GitHub account anywhere; "@login" mentions outside Python (where "@" starts a decorator)
    link_re = re.compile(r"(?i)github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})")
    mention_re = re.compile(r"(?<![\w.])@([A-Za-z0-9][A-Za-z0-9-]{0,38})")
    for p in target.rglob("*"):
        if p.is_dir() or ".git" in p.relative_to(target).parts:
            continue
        rel = _rel(p, target)
        if rel in SCAN_EXEMPT_FILES:
            continue
        # Binary formats are not text: reading them as text produces false positives.
        # SVG stays in the scan - it is text and could carry data.
        if p.suffix.lower() in BINARY_SUFFIXES:
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        if rel not in PATTERN_SOURCE_FILES:
            for m in EMAIL_RE.finditer(t):
                if is_placeholder_email(m.group(0)):
                    continue
                problems.append(f"{rel}: e-mail {m.group(0)}")
            if phone_hits(t):
                problems.append(f"{rel}: phone-number pattern")
        if POSTING_URL_RE.search(t):
            problems.append(f"{rel}: link to an individual job advertisement")
        if SECRET_RE.search(t):
            problems.append(f"{rel}: secret-like token")
        if logins:
            found = list(link_re.finditer(t)) + ([] if p.suffix == ".py" else list(mention_re.finditer(t)))
            hits = {m.group(1).lower() for m in found}
            if any(h in logins and h not in allowed_logins and len(h) >= LOGIN_MIN_LEN for h in hits):
                problems.append(f"{rel}: mentions a private GitHub login (value not shown)")
    return problems


def check_private_paths(tree: Path) -> list[str]:
    problems = []
    for leak in tree.rglob("*"):
        rel = _rel(leak, tree)
        if leak.is_dir() or rel.split("/", 1)[0] == ".git":
            continue
        if leak.name in {"jobs.db", "snapshot_ranked.csv"} or rel.endswith(".db"):
            problems.append(f"hunter/score artifact leaked: {rel}")
        if "/profile_fit/" in f"/{rel}" or rel.startswith("data/raw/radar/") or rel.startswith("data/raw/arbeitnow/"):
            problems.append(f"private collection leaked: {rel}")
        if rel in PRIVATE_NEVER or any(x.endswith("/") and rel.startswith(x) for x in PRIVATE_NEVER):
            problems.append(f"private path leaked: {rel}")
    for f in EXCLUDE_ACQUISITION:
        if (tree / "src" / "acquisition" / f).exists():
            problems.append(f"posting collector leaked: src/acquisition/{f}")
    # exported code must not import an unexported collector at module level: the public tests and scripts would fail
    # on import (a guarded import inside a function, or pytest.importorskip, is fine)
    private_mods = "|".join(re.escape(f[:-3]) for f in EXCLUDE_ACQUISITION)
    import_re = re.compile(rf"^(?:import|from)\s+({private_mods})\b", re.M)
    for p in tree.rglob("*.py"):
        for mod in sorted({m.group(1) for m in import_re.finditer(p.read_text(encoding="utf-8", errors="ignore"))}):
            problems.append(f"{_rel(p, tree)} imports the unexported collector {mod} at module level")
    return sorted(set(problems))


def build(root: Path, stage: Path) -> list[str]:
    """Write the public tree into `stage` and return every problem found (empty list = publishable)."""
    problems: list[str] = []
    logins = load_private_logins(root)
    if not logins:
        print("note: no clear-text GitHub login list available (absent or pseudonymised by the Layer 2 redaction); "
              "the login check is skipped, the other checks still run")
    if not os.environ.get("EXPORT_UID_KEY"):
        print("note: EXPORT_UID_KEY not set - posting_uid values are hashed with a one-off key (public rows stay "
              "joinable within this export; trace them privately by row order of the private tables)")
    for f in INCLUDE_FILES:
        if (root / f).exists():
            copy_file(root / f, stage / f)
        else:
            problems.append(f"missing required file {f}")
    for f in OPTIONAL_FILES:
        if (root / f).exists():
            copy_file(root / f, stage / f)
    if (root / PUBLIC_GITIGNORE).exists():
        copy_file(root / PUBLIC_GITIGNORE, stage / ".gitignore")
    else:
        problems.append(f"missing public .gitignore template {PUBLIC_GITIGNORE}")
    for d in INCLUDE_DIRS + [x for x in OPTIONAL_DIRS if (root / x).is_dir()]:
        for p in (root / d).rglob("*"):
            if not p.is_file() or "__pycache__" in p.parts or p.suffix == ".pyc":
                continue
            rel = _rel(p, root)
            if is_excluded(rel):
                continue
            copy_file(p, stage / rel)
    for dst, src in SUBSTITUTE_FILES.items():
        if (root / src).exists():
            copy_file(root / src, stage / dst)
        else:
            problems.append(f"missing substitute {src} for {dst}")
    for f in INCLUDE_ACQUISITION:
        copy_file(root / "src" / "acquisition" / f, stage / "src" / "acquisition" / f)
    # tables
    for p in sorted((root / "outputs" / "tables").glob("*.csv")):
        if p.name in EXCLUDE_TABLES:
            continue
        problems += clean_table(p, stage / "outputs" / "tables" / p.name, logins)
    for p in sorted((root / "outputs").glob("*.json")):
        problems += clean_json(p, stage / "outputs" / p.name, logins)
    if (root / "outputs" / "reports" / "digest.txt").exists():
        copy_file(root / "outputs" / "reports" / "digest.txt", stage / "outputs" / "reports" / "digest.txt")
    # keep empty data folders so that paths in code resolve
    for d in ["data/raw", "data/processed", "data/external"]:
        (stage / d).mkdir(parents=True, exist_ok=True)
        (stage / d / ".gitkeep").write_text("private in the public repository; see PUBLICATION_DECISION.md\n", encoding="utf-8")
    # openly licensed raw data that IS published, so the seasonality layer is reproducible end to end
    for d in INCLUDE_RAW_DIRS:
        for p in (root / d).rglob("*"):
            if p.is_file():
                copy_file(p, stage / p.relative_to(root))
    # public-only presentation files, last so that they win (README.md); the scans below cover them like any other file
    overlay = apply_overlay(root, stage)
    (stage / "outputs").mkdir(parents=True, exist_ok=True)
    (stage / "outputs" / "PUBLIC_EXPORT_MANIFEST.txt").write_text(
        "Built by src/publish/export_public.py\n"
        + "Excluded tables: " + ", ".join(sorted(EXCLUDE_TABLES)) + "\n"
        + "Excluded collectors: " + ", ".join(EXCLUDE_ACQUISITION) + "\n"
        + "Excluded documents and paths: " + ", ".join(sorted(EXCLUDE_DOCS | EXCLUDE_PATHS)) + "\n"
        + "Pseudonymised columns (keyed hash): " + ", ".join(sorted(PSEUDONYMISE_COLUMNS)) + "\n"
        + "config/profile.json is a neutral example (config/profile.example.json in the private repository)\n"
        + f"Public overlay ({PUBLIC_OVERLAY}, copied over the tree): " + (", ".join(overlay) or "none") + "\n"
        + "Dropped column pattern: " + DROP_COLUMNS_RE.pattern + "\n", encoding="utf-8")
    # the public profile must never be the owner's own file
    real, pub = root / "config" / "profile.json", stage / "config" / "profile.json"
    if real.exists() and pub.exists() and real.read_bytes() == pub.read_bytes():
        problems.append("config/profile.json in the export is the owner's private profile")
    problems += check_suppression(stage)
    problems += scan_tree(stage, logins, owner_logins(root))
    problems += check_private_paths(stage)
    return problems


def _clear(target: Path) -> None:
    for child in target.iterdir():
        if child.name == ".git":
            continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()


def main(target: Path, root: Path = ROOT) -> int:
    target = Path(target).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.staging-", dir=target.parent))
    try:
        problems = build(root, stage)
        if problems:
            print("EXPORT BLOCKED (target left unchanged):")
            for x in problems:
                print("  -", x)
            return 1
        target.mkdir(parents=True, exist_ok=True)
        _clear(target)
        for child in stage.iterdir():
            shutil.move(str(child), str(target / child.name))
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    n = sum(1 for p in target.rglob("*") if p.is_file() and ".git" not in p.relative_to(target).parts)
    print(f"public export OK: {n} files in {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET))
