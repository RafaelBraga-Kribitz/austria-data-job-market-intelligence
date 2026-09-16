"""Build the PUBLIC (sanitised) version of this repository.

Policy (docs/legal-and-publication-audit.md, PUBLICATION_DECISION.md):
  PUBLIC  : code (except the LinkedIn and willhaben collectors), configs, schemas, docs, decision documents,
            aggregated tables, figures, JSON summaries, tests (integrity tests skip without processed data).
  PRIVATE : data/raw, data/processed, data/external (fetched third-party pages), logs, notebooks, PROGRESS.md,
            per-posting tables that carry free text, contact data or source URLs, and any column that holds
            verbatim posting text ("*snippet*", "description*", "url").
Every exported CSV/JSON is scanned; any e-mail address, phone number or free-text column aborts the export.

Usage:  python src/publish/export_public.py [target_dir]   (default: ../austria-data-job-market-intelligence-public)
The target directory is emptied (except its .git folder) and rebuilt, so the public git history never contains
private material.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = ROOT.parent / "austria-data-job-market-intelligence-public"

# ---- file-level policy -------------------------------------------------------------------------
INCLUDE_FILES = [
    "README.md", "AGENT_CONTEXT.md", "CAREER_DECISION_MAP.md", "DECISION_LOG.md", "PUBLICATION_DECISION.md",
    "LICENSE", "CITATION.cff", "requirements.txt", ".gitignore",
]
INCLUDE_DIRS = ["docs", "config", "schemas", "tests", "outputs/figures", "src/pipeline", "src/analysis", "src/reporting", "src/publish"]
INCLUDE_ACQUISITION = ["common.py", "collect_jobbarometer.py", "collect_eurostat_jvs.py"]  # public-body statistics / open API, no terms restriction found
# raw data that may be published: Eurostat is an openly licensed, documented API (docs/seasonality.md §2)
INCLUDE_RAW_DIRS = ["data/raw/eurostat_jvs"]
EXCLUDE_ACQUISITION = ["collect_eures.py", "collect_eures_styria_text.py", "collect_karriere.py", "collect_jobsat.py", "collect_linkedin.py", "collect_willhaben.py"]
# kept private: every posting source restricts automated extraction in its terms (docs/legal-and-publication-audit.md §2, §6)
EXCLUDE_TABLES = {
    "T09e_salary_observations.csv",   # per-posting rows with employer + salary + snippet
    "Q07a_salary_audit_sample.csv",   # verbatim salary snippets
    "Q07b_salary_implausible.csv",    # verbatim salary snippets
    "Q09_skill_spotcheck_sample.csv", # verbatim snippets + source URLs
    "T16a_adjacent_titles_styria.csv",# per-posting rows with source URLs
}
DROP_COLUMNS_RE = re.compile(r"snippet|^description$|description_text|description_html|source_url|\burl\b|company_url|raw_html|\bhtml\b", re.I)
# count columns such as "with_description" / "description_gt300" are aggregates and are kept
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+43|0043)\s?[\d\s/\-()]{6,}\d")
TEXT_COL_MAX = 200  # a CSV cell longer than this is treated as free text and rejected, unless the column is a known aggregate list
ALLOW_LONG_COLUMNS = {"top15_skills", "overlap_skills", "structural_skills", "unclassified_skills", "top_tech_skills", "top_business", "top_soft",
                      "defining_skills", "family_mix", "example_titles", "top_skills", "role_rule", "families", "sources", "states"}
# these hold semicolon-separated skill names, regex patterns or job titles produced by the analysis, never advertisement text


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def clean_table(src: Path, dst: Path) -> list[str]:
    df = pd.read_csv(src)
    dropped = [c for c in df.columns if DROP_COLUMNS_RE.search(str(c))]
    df = df.drop(columns=dropped)
    problems = []
    for c in df.columns:
        if df[c].dtype == object:
            s = df[c].dropna().astype(str)
            if (s.str.len().max() > TEXT_COL_MAX if len(s) else False) and c not in ALLOW_LONG_COLUMNS:
                problems.append(f"{src.name}:{c} has cells longer than {TEXT_COL_MAX} chars")
            if s.str.contains(EMAIL_RE).any():
                problems.append(f"{src.name}:{c} contains an e-mail address")
            if s.str.contains(PHONE_RE).any():
                problems.append(f"{src.name}:{c} contains a phone number")
    dst.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dst, index=False)
    return problems


def clean_json(src: Path, dst: Path) -> list[str]:
    d = json.loads(src.read_text(encoding="utf-8"))

    def scrub(o):
        if isinstance(o, dict):
            return {k: scrub(v) for k, v in o.items() if not DROP_COLUMNS_RE.search(str(k))}
        if isinstance(o, list):
            return [scrub(x) for x in o]
        return o

    d = scrub(d)
    txt = json.dumps(d, ensure_ascii=False, indent=1)
    problems = []
    if EMAIL_RE.search(txt):
        problems.append(f"{src.name} contains an e-mail address")
    if PHONE_RE.search(txt):
        problems.append(f"{src.name} contains a phone number")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(txt, encoding="utf-8")
    return problems


def scan_tree(target: Path) -> list[str]:
    """Final scan of everything exported (excluding .git)."""
    problems = []
    for p in target.rglob("*"):
        if p.is_dir() or ".git" in p.parts:
            continue
        if p.suffix.lower() in {".png", ".parquet", ".pyc"}:
            continue
        if p.name == "export_public.py":  # this file contains the scan patterns themselves
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        for m in EMAIL_RE.finditer(t):
            if m.group(0).lower().endswith(("@example.com", "@anthropic.com")):
                continue
            problems.append(f"{p.relative_to(target)}: e-mail {m.group(0)}")
        if PHONE_RE.search(t):
            problems.append(f"{p.relative_to(target)}: phone-number pattern")
        if re.search(r"(?i)(api[_-]?key|bearer [a-z0-9]|li_at=|JSESSIONID=|token=)", t) and p.suffix != ".md":
            problems.append(f"{p.relative_to(target)}: secret-like token")
    return problems


def main(target: Path) -> int:
    if target.exists():
        for child in target.iterdir():
            if child.name == ".git":
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    target.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []
    for f in INCLUDE_FILES:
        if (ROOT / f).exists():
            copy_file(ROOT / f, target / f)
        else:
            problems.append(f"missing required file {f}")
    for d in INCLUDE_DIRS:
        for p in (ROOT / d).rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                copy_file(p, target / p.relative_to(ROOT))
    for f in INCLUDE_ACQUISITION:
        copy_file(ROOT / "src" / "acquisition" / f, target / "src" / "acquisition" / f)
    for f in EXCLUDE_ACQUISITION:
        assert not (target / "src" / "acquisition" / f).exists()
    # tables
    for p in sorted((ROOT / "outputs" / "tables").glob("*.csv")):
        if p.name in EXCLUDE_TABLES:
            continue
        problems += clean_table(p, target / "outputs" / "tables" / p.name)
    for p in sorted((ROOT / "outputs").glob("*.json")):
        problems += clean_json(p, target / "outputs" / p.name)
    if (ROOT / "outputs" / "reports" / "digest.txt").exists():
        copy_file(ROOT / "outputs" / "reports" / "digest.txt", target / "outputs" / "reports" / "digest.txt")
    # keep empty data folders so that paths in code resolve
    for d in ["data/raw", "data/processed", "data/external"]:
        (target / d).mkdir(parents=True, exist_ok=True)
        (target / d / ".gitkeep").write_text("private in the public repository; see PUBLICATION_DECISION.md\n", encoding="utf-8")
    # openly licensed raw data that IS published, so the seasonality layer is reproducible end to end
    for d in INCLUDE_RAW_DIRS:
        for p in (ROOT / d).rglob("*"):
            if p.is_file():
                copy_file(p, target / p.relative_to(ROOT))
    problems += scan_tree(target)
    (target / "outputs" / "PUBLIC_EXPORT_MANIFEST.txt").write_text(
        "Built by src/publish/export_public.py\n"
        + "Excluded tables: " + ", ".join(sorted(EXCLUDE_TABLES)) + "\n"
        + "Excluded collectors: " + ", ".join(EXCLUDE_ACQUISITION) + "\n"
        + "Dropped column pattern: " + DROP_COLUMNS_RE.pattern + "\n", encoding="utf-8")
    if problems:
        print("EXPORT BLOCKED:")
        for x in problems:
            print("  -", x)
        return 1
    n = sum(1 for p in target.rglob("*") if p.is_file() and ".git" not in p.parts)
    print(f"public export OK: {n} files in {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET))
