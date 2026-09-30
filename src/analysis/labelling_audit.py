"""Hand-labelling audits: draw blind samples for the owner to label, then score the filled sheets.

Closes (once the owner has labelled): OQ-09 title-taxonomy recall (audit H6), OQ-16 + the language/salary
extractor audit (M22, M23, M42), OQ-12 project-quality rubric (L40), and summarises the private
application log of OQ-01/04/06 (M24). Protocol, label codes and time estimates: docs/labelling-protocol.md.

Subcommands
-----------
  sample            draw the recall sample (default 300 canonical postings) and the extractor sample
                    (default 100 core postings) into data/labels/<date>/
  sample-projects   draw 40 substantive GitHub projects for the OQ-12 rubric into data/labels/<date>/
  score             read the filled sheets of data/labels/<date>/ and write AGGREGATE-ONLY tables:
                      outputs/tables/Q10_title_recall.csv, Q10b_title_recall_misses_by_predicted_family.csv
                      outputs/tables/Q11_extractor_precision_recall.csv
                      outputs/tables/Q12_project_quality_rubric.csv, Q12b_project_structure_vs_quality.csv
                    plus private per-row diagnostics (missed titles etc.) inside data/labels/<date>/
  score-applications  summarise data/private/application_log.csv into data/private/ (private by default)
  init-application-log  write the empty application-log template (never overwrites)

Privacy and blindness
---------------------
* Everything under data/labels/ and data/private/ is private. Both folders are created with their own
  ".gitignore" containing "*" so that nothing in them can be committed by accident, even before the
  repository-level .gitignore lists them.
* Sheets carry only what a labeller needs (title, employer, a short excerpt, a reference into a private
  HTML file with the full ad text). The pipeline's predictions live in a separate *_key.csv that the
  labeller must not open before finishing; rows are shuffled so stratum membership is not visible.
* Public outputs contain counts, shares and intervals only: no posting ids, titles, employers, repository
  names or per-row labels (checked by assert_aggregate_only before writing).

Labelling guide (short form; the full guide with examples is docs/labelling-protocol.md)
-------------------------------------------------------------------------------------------
recall_sheet.csv      label_data_role: Y = data role of one of the eight core families
                      (docs/role-taxonomy.md); A = adjacent (AI/ML software engineering, actuary, generic
                      "analyst"); N = not a data role; ? = cannot decide. Judge the JOB, not the title
                      wording. label_family (optional, only for Y): DA BI DS DE DG MA PA BA.
extractor_sheet.csv   read the full text in extractor_texts.html#r<row_id>.
                      sk_<CODE>: 1 if the role requires, uses or prefers the skill (mentions only in the
                      company self-description or benefits = 0); blanks count as 0 once skills_done = 1.
                      de_class: REQ / PREF / ALT / NOTREQ / NONE; de_level: A / B1 / B2 / C1 / C2 / blank.
                      sal_basis: RANGE / MIN / NONE; sal_amount: lowest figure stated; sal_period: M / Y / H.
                      Tick skills_done / lang_done / sal_done (1) per block when finished.
projects_sheet.csv    open repo_url; score the five criteria 0 / 1 / 2 (absent / partial / clear); set
                      unavailable = 1 if the repository is gone or empty; rated_done = 1 when finished.

Usage
-----
  python src/analysis/labelling_audit.py sample [--date YYYY-MM-DD] [--n-recall 300] [--n-extractor 100]
                                                [--design stratified|srs] [--seed 20260930] [--force]
  python src/analysis/labelling_audit.py sample-projects [--date YYYY-MM-DD] [--n 40]
  python src/analysis/labelling_audit.py score --date YYYY-MM-DD [--only recall|extractor|projects]
  python src/analysis/labelling_audit.py init-application-log
  python src/analysis/labelling_audit.py score-applications
"""
from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
LABELS = ROOT / "data" / "labels"
PRIVATE = ROOT / "data" / "private"

DEFAULT_SEED = 20260930
CORE_FAMILIES = ["data_analytics", "bi", "data_science", "data_engineering", "data_governance",
                 "marketing_analytics", "product_analytics", "business_analysis"]
ADJACENT_FAMILIES = ["ai_software_engineering", "other_data"]
FAMILY_CODES = {"DA": "data_analytics", "BI": "bi", "DS": "data_science", "DE": "data_engineering",
                "DG": "data_governance", "MA": "marketing_analytics", "PA": "product_analytics", "BA": "business_analysis"}

# Recall strata: a posting outside the core set is "signal" when its title or text carries a data word, so
# that the stratum where a missed data role is plausible can be over-sampled and weighted back.
DATA_SIGNAL_RE = re.compile(
    r"\b(?:sql|python|power ?bi|tableau|qlik|business intelligence|"
    r"data ?(?:analy|scien|engineer|warehouse|management|governance|quality|platform)|"
    r"daten(?:analy|bank|modell|management|qualit|wissenschaft|pipeline)|statisti|machine learning|"
    r"k(?:ü|ue)nstliche intelligenz|ki|etl|dashboard|kpi|reporting|analytics|analytik)", re.I)
STRATUM_ALLOC = {"S1_pred_core": 0.2, "S2_noncore_data_signal": 0.6, "S3_noncore_no_signal": 0.2}

# Skills audited for OQ-16: the D04 learning-priority skills with demand share >= 8 % (the threshold below
# which D04 says "do not prioritise") plus R, the one pattern known to be ambiguous.
AUDIT_SKILLS = [
    ("SQL", "SQL"), ("PY", "Python"), ("DGQ", "Data Governance/Quality"), ("ETL", "ETL/ELT"),
    ("AZURE", "Azure"), ("PBI", "Power BI"), ("EXCEL", "Excel"), ("DMOD", "Data Modeling"),
    ("GENAI", "Generative AI / LLM"), ("CICD", "CI/CD"), ("REST", "REST APIs"), ("DBX", "Databricks"),
    ("MATH", "Mathematics"), ("DWH", "Data Warehouse (generic)"), ("GIT", "Git"), ("AWS", "AWS"), ("R", "R"),
]
SKILL_COLS = [c for c in ["programming_languages", "bi_tools", "cloud_platforms", "data_platforms", "python_ecosystem",
                          "data_engineering", "ml_ai", "statistics_methods"]]
# pipeline german_requirement -> human label code
GERMAN_MAP = {"required": "REQ", "required_implied": "REQ", "preferred": "PREF", "german_or_english": "ALT",
              "explicitly_not_required": "NOTREQ", "mentioned": "NONE", "not_mentioned": "NONE"}
GERMAN_CODES = ["REQ", "PREF", "ALT", "NOTREQ", "NONE"]
LEVEL_MAP = {"C2/native": "C2", "C1/fluent": "C1", "B2/good": "B2", "B1": "B1", "A1-A2": "A"}
RUBRIC = [("q_question", "question or objective stated"), ("q_method", "method appropriate to the question"),
          ("q_result", "result quantified"), ("q_limitations", "limitations acknowledged"),
          ("q_reproducible", "reproducible (data access + run instructions)")]
# rule-detected README structure that corresponds to each rubric criterion (for calibration, OQ-12)
RUBRIC_DETECTORS = {
    "q_question": ["rd_h_objective_overview", "rd_h_business_context"],
    "q_method": ["rd_h_methodology"],
    "q_result": ["rd_h_results", "rd_mentions_metrics"],
    "q_limitations": ["rd_h_limitations", "rd_mentions_limitations"],
    "q_reproducible": ["rd_h_reproducibility", "rd_mentions_reproduce_cmd"],
}
STRUCTURE_FLAGS = ["rd_h_objective_overview", "rd_h_methodology", "rd_h_results", "rd_h_limitations", "rd_h_reproducibility"]
MIN_CELL = 5  # suppression threshold for project aggregates (legal audit §10.1: headings only when >= 5 projects)
FORBIDDEN_PUBLIC_COLS = {"posting_uid", "source_id", "source_url", "title", "company", "employer", "excerpt", "row_id",
                         "repo_url", "repo_full_name", "project_id", "candidate_id", "notes", "description_text"}

APPLICATION_LOG_COLUMNS = [
    "app_id", "posting_uid", "posting_ref", "employer", "role_title", "role_family", "region", "posting_language",
    "stated_german_class", "stated_german_level", "own_german_meets_stated", "unmet_requirements",
    "channel", "application_language", "referral", "cover_letter", "cv_version", "portfolio_version",
    "application_date", "response", "response_date", "interview", "first_interview_date", "n_interview_rounds",
    "offer", "offer_date", "offer_annual_gross_eur", "outcome_final", "last_updated", "notes",
]


# ----------------------------------------------------------------------------------------------- helpers
def ensure_private_dir(path: Path) -> Path:
    """Create a private folder and drop a '*' .gitignore into its top-level private root."""
    path.mkdir(parents=True, exist_ok=True)
    for root in (LABELS, PRIVATE):
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        gi = root / ".gitignore"
        if not gi.exists():
            gi.write_text("# private: hand labels, application log, letters - never commit\n*\n", encoding="utf-8")
    return path


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if not n:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round((c - h) / d, 3), round((c + h) / d, 3)


def _as_list(x) -> list:
    if isinstance(x, (list, tuple, np.ndarray)):
        return list(x)
    if isinstance(x, str) and x.strip().startswith("["):
        try:
            return list(json.loads(x))
        except json.JSONDecodeError:
            return []
    return []


def _clean(s, n: int | None = None) -> str:
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if n is None or len(s) <= n else s[:n].rstrip() + " …"


def write_sheet(df: pd.DataFrame, path: Path) -> None:
    """Semicolon + UTF-8 BOM: opens as columns in German-locale Excel."""
    df.to_csv(path, sep=";", index=False, encoding="utf-8-sig")


def read_sheet(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return pd.read_csv(path, sep=None, engine="python", dtype=str, keep_default_na=False, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"cannot decode {path}; save it as 'CSV UTF-8'")


def _blank(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def _yes(v) -> bool:
    if _blank(v):
        return False
    return str(v).strip().lower() in {"1", "x", "y", "yes", "j", "ja", "true", "wahr"}


def _code(v) -> str:
    return "" if _blank(v) else str(v).strip().upper()


def parse_amount(v) -> float | None:
    """'3.500,00' / '3,500.00' / '3500' / '€ 48.000' -> float; blank -> None."""
    s = re.sub(r"[^\d.,]", "", str(v or ""))
    if not s:
        return None
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d{1,2})?", s):
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d{1,2})?", s):
        s = s.replace(",", "")
    elif re.fullmatch(r"\d+,\d{1,2}", s):
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def assert_aggregate_only(df: pd.DataFrame, name: str) -> None:
    bad = FORBIDDEN_PUBLIC_COLS & set(df.columns)
    if bad:
        raise ValueError(f"{name}: public table would carry row-level columns {sorted(bad)}")


def _write_texts_html(rows: list[dict], path: Path, heading: str) -> None:
    parts = ["<!doctype html><html lang='de'><head><meta charset='utf-8'><title>", html.escape(heading),
             "</title><style>body{font:15px/1.5 system-ui,sans-serif;max-width:52rem;margin:2rem auto;padding:0 1rem}"
             "section{border-top:2px solid #999;padding:1rem 0}h2{font-size:1.05rem}pre{white-space:pre-wrap;font:inherit}"
             ".meta{color:#555}</style></head><body><h1>", html.escape(heading),
             "</h1><p class='meta'>PRIVATE. Third-party advertisement texts for labelling only. Do not share or publish.</p>"]
    for r in rows:
        parts.append(f"<section id='r{r['row_id']}'><h2>#{r['row_id']} · {html.escape(_clean(r['title']))}</h2>"
                     f"<p class='meta'>{html.escape(_clean(r.get('employer')) or '(employer not stated)')}</p>")
        if r.get("salary_field"):
            parts.append(f"<p><b>Structured salary field shown by the source:</b> {html.escape(_clean(r['salary_field']))}</p>")
        parts.append(f"<pre>{html.escape(str(r.get('text') or '(no description)'))}</pre></section>")
    parts.append("</body></html>")
    path.write_text("".join(parts), encoding="utf-8")


def _guard_overwrite(paths: list[Path], force: bool) -> None:
    existing = [p for p in paths if p.exists()]
    if existing and not force:
        raise SystemExit("refusing to overwrite existing labelling files (labels may already be entered): "
                         + ", ".join(str(p) for p in existing) + "  - pass --force or use another --date")


def load_postings(path: Path | None = None) -> pd.DataFrame:
    return pd.read_parquet(path or PROC / "postings_dedup.parquet")


# ----------------------------------------------------------------------------------- recall (OQ-09)
def assign_recall_stratum(df: pd.DataFrame) -> pd.Series:
    core = df["role_family"].isin(CORE_FAMILIES)
    txt = df["title"].fillna("") + " " + df["description_text"].fillna("").str[:4000]
    sig = txt.str.contains(DATA_SIGNAL_RE) | df["role_family"].isin(ADJACENT_FAMILIES)
    return pd.Series(np.where(core, "S1_pred_core", np.where(sig, "S2_noncore_data_signal", "S3_noncore_no_signal")),
                     index=df.index)


def draw_recall_sample(df: pd.DataFrame, n: int = 300, design: str = "stratified",
                       seed: int = DEFAULT_SEED) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Probability sample of canonical postings. Returns (sheet, key, texts)."""
    canon = df[df["is_canonical"].astype(bool)].copy()
    canon["stratum"] = assign_recall_stratum(canon)
    rng = np.random.default_rng(seed)
    if design == "srs":
        take = canon.sample(n=min(n, len(canon)), random_state=seed).copy()
        take["stratum_N"] = len(canon)
        take["stratum_n"] = len(take)
        take["stratum"] = "SRS_all_canonical"
    elif design == "stratified":
        parts = []
        sizes = {s: int(round(n * a)) for s, a in STRATUM_ALLOC.items()}
        sizes["S2_noncore_data_signal"] += n - sum(sizes.values())
        for s, k in sizes.items():
            pop = canon[canon["stratum"] == s]
            k = min(k, len(pop))
            got = pop.sample(n=k, random_state=int(rng.integers(0, 2**31 - 1))).copy()
            got["stratum_N"] = len(pop)
            got["stratum_n"] = k
            parts.append(got)
        take = pd.concat(parts)
    else:
        raise ValueError(f"unknown design {design!r}")
    take = take.sample(frac=1, random_state=seed + 1).reset_index(drop=True)  # shuffle: strata not visible
    take["row_id"] = [f"{i + 1:03d}" for i in range(len(take))]
    sheet = pd.DataFrame({
        "row_id": take["row_id"], "title": take["title"].map(_clean), "employer": take["company"].map(_clean),
        "excerpt": take["description_text"].map(lambda s: _clean(s, 400)),
        "text_ref": "recall_texts.html#r" + take["row_id"],
        "label_data_role": "", "label_family": "", "notes": "",
    })
    key = pd.DataFrame({
        "row_id": take["row_id"], "posting_uid": take["posting_uid"], "design": design, "seed": seed,
        "stratum": take["stratum"], "stratum_N": take["stratum_N"], "stratum_n": take["stratum_n"],
        "pred_family": take["role_family"], "pred_core": take["role_family"].isin(CORE_FAMILIES),
        "pred_adjacent": take["role_family"].isin(ADJACENT_FAMILIES), "normalized_title": take["normalized_title"],
    })
    texts = [{"row_id": r, "title": t, "employer": e, "text": x}
             for r, t, e, x in zip(take["row_id"], take["title"], take["company"], take["description_text"])]
    return sheet, key, texts


def _weighted_recall(frame: pd.DataFrame, found_col: str) -> dict:
    pos = frame["truth"] == 1
    w = frame["w"]
    denom = float((w * pos).sum())
    return {"recall": float((w * pos * frame[found_col]).sum()) / denom if denom else float("nan"),
            "est_positives": denom, "est_missed": float((w * pos * (1 - frame[found_col])).sum())}


def score_recall(sheet: pd.DataFrame, key: pd.DataFrame, n_boot: int = 2000,
                 seed: int = DEFAULT_SEED) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (Q10 public, Q10b public, private misses)."""
    m = key.merge(sheet[["row_id", "label_data_role", "label_family"]], on="row_id", how="left")
    m["label"] = m["label_data_role"].map(_code).replace({"YES": "Y", "J": "Y", "NO": "N", "UNSURE": "?"})
    n_drawn = len(m)
    lab = m[m["label"].isin(["Y", "A", "N", "?"])].copy()
    if lab.empty:
        raise SystemExit("recall sheet has no labels yet")
    for c in ("pred_core", "pred_adjacent"):
        lab[c] = lab[c].map(lambda v: v if isinstance(v, bool) else str(v).strip().lower() == "true").astype(int)
    lab["stratum_N"] = lab["stratum_N"].astype(float)
    n_lab_by_stratum = lab.groupby("stratum")["row_id"].transform("count")
    lab["w"] = lab["stratum_N"] / n_lab_by_stratum
    lab["found_strict"] = lab["pred_core"]
    lab["found_lenient"] = ((lab["pred_core"] + lab["pred_adjacent"]) > 0).astype(int)
    design = str(lab["design"].iloc[0])

    def metrics(fr: pd.DataFrame, unsure_as: int | None) -> dict:
        f = fr[fr["label"] != "?"].copy() if unsure_as is None else fr.copy()
        f["truth"] = (f["label"] == "Y").astype(int)
        if unsure_as is not None:
            f.loc[f["label"] == "?", "truth"] = unsure_as
        s = _weighted_recall(f, "found_strict")
        l = _weighted_recall(f, "found_lenient")
        pc = f[f["pred_core"] == 1]
        prec = float((pc["w"] * pc["truth"]).sum() / pc["w"].sum()) if len(pc) else float("nan")
        return {"recall_core": s["recall"], "recall_core_or_adjacent": l["recall"], "precision_core": prec,
                "est_data_roles_in_corpus": s["est_positives"], "est_missed_data_roles": s["est_missed"]}

    point = metrics(lab, None)
    rng = np.random.default_rng(seed)
    boots = {k: [] for k in point}
    groups = [g for _, g in lab.groupby("stratum")]
    for _ in range(n_boot):
        bs = pd.concat([g.sample(n=len(g), replace=True, random_state=int(rng.integers(0, 2**31 - 1))) for g in groups])
        r = metrics(bs, None)
        for k, v in r.items():
            boots[k].append(v)
    sens = metrics(lab, 1)
    truth_pos = int((lab["label"] == "Y").sum())
    note = ("stratified probability sample of all canonical postings, inverse-probability weighted; CI = stratified bootstrap "
            f"({n_boot} reps)") if design == "stratified" else f"simple random sample; CI = bootstrap ({n_boot} reps)"
    rows = []
    for k, v in point.items():
        arr = np.array([x for x in boots[k] if not (isinstance(x, float) and math.isnan(x))])
        lo, hi = (np.percentile(arr, [2.5, 97.5]) if len(arr) else (float("nan"), float("nan")))
        nd = 0 if k.startswith("est_") else 3  # estimated posting counts are whole numbers
        rows.append({"metric": k, "estimate": round(v, nd) if not math.isnan(v) else None,
                     "ci_low": round(float(lo), nd), "ci_high": round(float(hi), nd),
                     "sensitivity_unsure_as_data_role": round(sens[k], nd) if not math.isnan(sens[k]) else None})
    q10 = pd.DataFrame(rows)
    q10["design"] = design
    q10["n_drawn"] = n_drawn
    q10["n_labelled"] = len(lab)
    q10["n_unsure"] = int((lab["label"] == "?").sum())
    q10["n_labelled_data_roles"] = truth_pos
    q10["n_canonical_frame"] = int(lab.groupby("stratum")["stratum_N"].first().sum())
    q10["note"] = note
    if design == "srs":  # a Wilson interval is also valid for the unweighted recall of an SRS
        pos = lab[lab["label"] == "Y"]
        lo, hi = wilson(int(pos["found_strict"].sum()), len(pos))
        q10.loc[q10.metric == "recall_core", "note"] = note + f"; Wilson 95% [{lo}, {hi}]"
    # Q10b: where the missed data roles went (predicted family), weighted and raw
    miss = lab[(lab["label"] == "Y") & (lab["found_strict"] == 0)]
    q10b = (miss.groupby("pred_family").agg(n_sample=("row_id", "count"), est_in_corpus=("w", "sum")).reset_index()
            if len(miss) else pd.DataFrame(columns=["pred_family", "n_sample", "est_in_corpus"]))
    q10b["est_in_corpus"] = q10b["est_in_corpus"].round(0)
    # family agreement among correctly found data roles
    both = lab[(lab["label"] == "Y") & (lab["found_strict"] == 1)].copy()
    both["fam_h"] = both["label_family"].map(_code).map(FAMILY_CODES)
    both = both[both["fam_h"].notna()]
    if len(both):
        k = int((both["fam_h"] == both["pred_family"]).sum())
        lo, hi = wilson(k, len(both))
        q10 = pd.concat([q10, pd.DataFrame([{"metric": "family_agreement_among_found", "estimate": round(k / len(both), 3),
                                             "ci_low": lo, "ci_high": hi, "design": design, "n_drawn": n_drawn,
                                             "n_labelled": len(both), "note": "unweighted; Wilson 95%"}])], ignore_index=True)
    private = miss[["row_id", "posting_uid", "pred_family", "normalized_title", "stratum"]].merge(
        sheet[["row_id", "title", "employer", "notes"]], on="row_id", how="left")
    return q10, q10b, private


# ------------------------------------------------------------------------- extractors (OQ-16, M23, M42)
def draw_extractor_sample(df: pd.DataFrame, n: int = 100,
                          seed: int = DEFAULT_SEED) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    core = df[df["is_canonical"].astype(bool) & df["role_family"].isin(CORE_FAMILIES)
              & df["description_text"].fillna("").str.len().gt(0)]
    take = core.sample(n=min(n, len(core)), random_state=seed + 7).reset_index(drop=True)
    take["row_id"] = [f"{i + 1:03d}" for i in range(len(take))]
    sheet = pd.DataFrame({"row_id": take["row_id"], "title": take["title"].map(_clean),
                          "employer": take["company"].map(_clean), "text_ref": "extractor_texts.html#r" + take["row_id"]})
    for code, _ in AUDIT_SKILLS:
        sheet[f"sk_{code}"] = ""
    for c in ["skills_done", "de_class", "de_level", "lang_done", "sal_basis", "sal_amount", "sal_period", "sal_done", "notes"]:
        sheet[c] = ""
    pred_sk = take[[f"skills_{c}" for c in SKILL_COLS]].apply(
        lambda r: sorted({x for v in r for x in _as_list(v)}), axis=1)
    key = pd.DataFrame({"row_id": take["row_id"], "posting_uid": take["posting_uid"], "seed": seed,
                        "pred_skills": pred_sk.map(lambda l: json.dumps([s for _, s in AUDIT_SKILLS if s in l], ensure_ascii=False)),
                        "pred_german_requirement": take["german_requirement"], "pred_german_level_bucket": take["german_level_bucket"],
                        "pred_salary_basis": take["salary_basis"], "pred_salary_min_annual_eur": take["salary_min_annual_eur"],
                        "pred_salary_max_annual_eur": take["salary_max_annual_eur"], "pred_salary_period": take["salary_period"],
                        "pred_salary_source": take["salary_source"]})
    texts = [{"row_id": r, "title": t, "employer": e, "text": x, "salary_field": s}
             for r, t, e, x, s in zip(take["row_id"], take["title"], take["company"], take["description_text"],
                                      take.get("salary_text_raw", pd.Series([None] * len(take))))]
    return sheet, key, texts


def _pr_rows(field: str, cls: str, y_true: pd.Series, y_pred: pd.Series) -> list[dict]:
    t, p = y_true.astype(bool), y_pred.astype(bool)
    tp, fp, fn = int((t & p).sum()), int((~t & p).sum()), int((t & ~p).sum())
    out = []
    for metric, k, n in (("precision", tp, tp + fp), ("recall", tp, tp + fn)):
        lo, hi = wilson(k, n)
        out.append({"field": field, "class": cls, "metric": metric, "value": round(k / n, 3) if n else None,
                    "ci_low": lo, "ci_high": hi, "k": k, "n": n, "n_rows": len(t)})
    return out


def score_extractor(sheet: pd.DataFrame, key: pd.DataFrame) -> pd.DataFrame:
    m = key.merge(sheet, on="row_id", how="left")
    rows: list[dict] = []
    # skills
    sk = m[m["skills_done"].map(_yes)]
    if len(sk):
        pred = sk["pred_skills"].map(lambda s: set(json.loads(s) if isinstance(s, str) and s else []))
        all_t, all_p = [], []
        for code, name in AUDIT_SKILLS:
            t = sk[f"sk_{code}"].map(_yes)
            p = pred.map(lambda s, name=name: name in s)
            rows += _pr_rows("skill", name, t, p)
            all_t.append(t)
            all_p.append(p)
        rows += _pr_rows("skill", "ALL (micro-average)", pd.concat(all_t, ignore_index=True), pd.concat(all_p, ignore_index=True))
    # German requirement
    lg = m[m["lang_done"].map(_yes)].copy()
    if len(lg):
        lg["h"] = lg["de_class"].map(_code)
        lg["p"] = lg["pred_german_requirement"].map(GERMAN_MAP).fillna("NONE")
        lg = lg[lg["h"].isin(GERMAN_CODES)]
        for c in GERMAN_CODES:
            rows += _pr_rows("german_requirement", c, lg["h"] == c, lg["p"] == c)
        k, n = int((lg["h"] == lg["p"]).sum()), len(lg)
        lo, hi = wilson(k, n)
        rows.append({"field": "german_requirement", "class": "5-class", "metric": "accuracy", "value": round(k / n, 3) if n else None,
                     "ci_low": lo, "ci_high": hi, "k": k, "n": n, "n_rows": n})
        lv = lg[(lg["h"] == "REQ") & (lg["p"] == "REQ") & lg["de_level"].map(_code).ne("")]
        if len(lv):
            hl = lv["de_level"].map(_code).replace({"A1": "A", "A2": "A", "NATIVE": "C2"})
            pl = lv["pred_german_level_bucket"].map(LEVEL_MAP).fillna("")
            k, n = int((hl == pl).sum()), len(lv)
            lo, hi = wilson(k, n)
            rows.append({"field": "german_level", "class": "bucket (both REQ)", "metric": "agreement", "value": round(k / n, 3),
                         "ci_low": lo, "ci_high": hi, "k": k, "n": n, "n_rows": n})
    # salary
    sa = m[m["sal_done"].map(_yes)].copy()
    if len(sa):
        sa["hb"] = sa["sal_basis"].map(_code)
        sa = sa[sa["hb"].isin(["RANGE", "MIN", "NONE"])]
        sa["pb"] = sa["pred_salary_basis"].fillna("none")
        rows += _pr_rows("salary", "figure present", sa["hb"] != "NONE", sa["pb"].isin(["range", "minimum_only", "implausible"]))
        both = sa[(sa["hb"] != "NONE") & sa["pb"].isin(["range", "minimum_only"])].copy()
        if len(both):
            k, n = int(((both["hb"] == "RANGE") == (both["pb"] == "range")).sum()), len(both)
            lo, hi = wilson(k, n)
            rows.append({"field": "salary", "class": "range vs minimum", "metric": "agreement", "value": round(k / n, 3),
                         "ci_low": lo, "ci_high": hi, "k": k, "n": n, "n_rows": n})
            both["amt"] = both["sal_amount"].map(parse_amount)
            both["per"] = both["sal_period"].map(_code).str[:1]
            both["h_annual"] = np.where(both["per"] == "M", both["amt"] * 14, np.where(both["per"] == "Y", both["amt"], np.nan))
            comp = both[both["h_annual"].notna()]
            if len(comp):
                pv = comp["pred_salary_min_annual_eur"].astype(float)
                ok = (pv - comp["h_annual"]).abs() <= np.maximum(0.02 * comp["h_annual"], 100)
                k, n = int(ok.sum()), len(comp)
                lo, hi = wilson(k, n)
                rows.append({"field": "salary", "class": "annual minimum within 2 %", "metric": "accuracy", "value": round(k / n, 3),
                             "ci_low": lo, "ci_high": hi, "k": k, "n": n, "n_rows": n})
                pp = comp["pred_salary_period"].fillna("").str[:1].str.upper()
                k = int((pp == comp["per"]).sum())
                lo, hi = wilson(k, n)
                rows.append({"field": "salary", "class": "period month/year", "metric": "agreement", "value": round(k / n, 3),
                             "ci_low": lo, "ci_high": hi, "k": k, "n": n, "n_rows": n})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------ project quality (OQ-12)
def draw_project_sample(projects: pd.DataFrame, n: int = 40,
                        seed: int = DEFAULT_SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    sub = projects[projects["is_substantive"].astype(bool)]
    take = sub.sample(n=min(n, len(sub)), random_state=seed + 13).reset_index(drop=True)
    take["row_id"] = [f"{i + 1:02d}" for i in range(len(take))]
    url = take.get("repo_full_name", pd.Series([None] * len(take))).map(
        lambda s: f"https://github.com/{s}" if isinstance(s, str) and "/" in s else "(unavailable: redacted)")
    sheet = pd.DataFrame({"row_id": take["row_id"], "repo_url": url})
    for c, _ in RUBRIC:
        sheet[c] = ""
    sheet["unavailable"] = ""
    sheet["rated_done"] = ""
    sheet["notes"] = ""
    feats = ["archetype", "readme_length_bucket"] + sorted({f for v in RUBRIC_DETECTORS.values() for f in v} | set(STRUCTURE_FLAGS))
    key = take[["row_id", "project_id"] + [f for f in feats if f in take.columns]].copy()
    key["seed"] = seed
    return sheet, key


def score_projects(sheet: pd.DataFrame, key: pd.DataFrame, n_boot: int = 2000,
                   seed: int = DEFAULT_SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = key.merge(sheet, on="row_id", how="left")
    r = m[m["rated_done"].map(_yes) & ~m["unavailable"].map(_yes)].copy()
    if r.empty:
        raise SystemExit("projects sheet has no completed ratings yet")
    for c, _ in RUBRIC:
        r[c] = pd.to_numeric(r[c], errors="coerce").clip(0, 2)
    r = r.dropna(subset=[c for c, _ in RUBRIC])
    r["total"] = r[[c for c, _ in RUBRIC]].sum(axis=1)
    n = len(r)
    q12 = []
    for c, label in RUBRIC:
        k_clear = int((r[c] == 2).sum())
        lo, hi = wilson(k_clear, n)
        q12.append({"criterion": label, "n_rated": n, "mean_score_0_2": round(r[c].mean(), 2),
                    "share_clear": round(k_clear / n, 3), "share_clear_ci_low": lo, "share_clear_ci_high": hi,
                    "share_absent": round(float((r[c] == 0).mean()), 3)})
    q12.append({"criterion": "TOTAL (0-10)", "n_rated": n, "mean_score_0_2": None, "share_clear": None,
                "median_total": float(r["total"].median()), "mean_total": round(r["total"].mean(), 2),
                "n_unavailable": int(m["unavailable"].map(_yes).sum())})
    q12 = pd.DataFrame(q12)
    rows = []
    # (a) mean rated quality with / without each structural feature (suppressed below MIN_CELL)
    for f in STRUCTURE_FLAGS:
        if f not in r.columns:
            continue
        has = r[f].map(lambda v: v if isinstance(v, bool) else str(v).lower() == "true")
        a, b = r[has], r[~has]
        ok = len(a) >= MIN_CELL and len(b) >= MIN_CELL
        rows.append({"analysis": "mean total with/without feature", "feature": f, "n_with": len(a), "n_without": len(b),
                     "mean_total_with": round(a["total"].mean(), 2) if ok else None,
                     "mean_total_without": round(b["total"].mean(), 2) if ok else None,
                     "note": "" if ok else f"suppressed: a cell below {MIN_CELL} projects"})
    # (b) detector calibration: rule flag vs human rating >= 1
    for c, dets in RUBRIC_DETECTORS.items():
        dets = [d for d in dets if d in r.columns]
        if not dets:
            continue
        det = r[dets].apply(lambda row: any(v if isinstance(v, bool) else str(v).lower() == "true" for v in row), axis=1)
        human = r[c] >= 1
        tp, fp, fn = int((det & human).sum()), int((det & ~human).sum()), int((~det & human).sum())
        for metric, k, nn in (("detector_precision", tp, tp + fp), ("detector_recall", tp, tp + fn)):
            lo, hi = wilson(k, nn)
            rows.append({"analysis": metric, "feature": c + " <- " + "|".join(dets), "n_with": nn, "k": k,
                         "value": round(k / nn, 3) if nn else None, "ci_low": lo, "ci_high": hi})
    # (c) rank correlation between a rule-detected structure index and rated quality
    idx = r[[f for f in STRUCTURE_FLAGS if f in r.columns]].apply(
        lambda row: sum(bool(v) if isinstance(v, bool) else str(v).lower() == "true" for v in row), axis=1)
    rho = float(pd.Series(idx.values).corr(pd.Series(r["total"].values), method="spearman")) if n > 2 else float("nan")
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n_boot):
        ii = rng.integers(0, n, n)
        a, b = pd.Series(idx.values[ii]), pd.Series(r["total"].values[ii])
        if a.nunique() > 1 and b.nunique() > 1:
            bs.append(a.corr(b, method="spearman"))
    lo, hi = (np.percentile(bs, [2.5, 97.5]) if bs else (float("nan"), float("nan")))
    rows.append({"analysis": "spearman(structure index 0-5, rated total)", "feature": "+".join(STRUCTURE_FLAGS),
                 "n_with": n, "value": round(rho, 3), "ci_low": round(float(lo), 3), "ci_high": round(float(hi), 3),
                 "note": f"bootstrap {n_boot} reps"})
    return q12, pd.DataFrame(rows)


# ------------------------------------------------------------------------- application log (OQ-01/04/06)
def init_application_log(path: Path | None = None) -> Path:
    path = path or PRIVATE / "application_log.csv"
    ensure_private_dir(path.parent)
    if path.exists():
        print(f"exists, not touched: {path}")
        return path
    write_sheet(pd.DataFrame(columns=APPLICATION_LOG_COLUMNS), path)
    return path


def summarise_applications(log: pd.DataFrame) -> pd.DataFrame:
    """Response / interview / offer rates by stated German class, whether the requirement was met, channel and
    portfolio version. Rates only; no employer, title or id columns."""
    lg = log.copy()
    lg = lg[lg["application_date"].str.strip() != ""]
    if lg.empty:
        return pd.DataFrame()
    lg["responded"] = lg["response"].map(_code).isin(["REJECTION", "SCREENING", "INTERVIEW", "OFFER"])
    lg["positive_response"] = lg["response"].map(_code).isin(["SCREENING", "INTERVIEW", "OFFER"]) | lg["interview"].map(_yes)
    lg["interviewed"] = lg["interview"].map(_yes) | lg["response"].map(_code).isin(["INTERVIEW", "OFFER"])
    lg["offered"] = lg["offer"].map(_yes)
    rows = []
    for dim in ["ALL", "stated_german_class", "own_german_meets_stated", "channel", "application_language", "portfolio_version", "referral"]:
        groups = [("ALL", lg)] if dim == "ALL" else list(lg.groupby(lg[dim].replace("", "(blank)")))
        for val, g in groups:
            row = {"dimension": dim, "value": val, "n_applications": len(g)}
            for c in ("responded", "positive_response", "interviewed", "offered"):
                k = int(g[c].sum())
                lo, hi = wilson(k, len(g))
                row.update({f"{c}_rate": round(k / len(g), 3), f"{c}_ci_low": lo, f"{c}_ci_high": hi})
            rows.append(row)
    out = pd.DataFrame(rows)
    out["note"] = "own applications; not randomised across ads - directional only (OQ-01)"
    return out


# ------------------------------------------------------------------------------------------------ CLI
def _write_public(df: pd.DataFrame, name: str) -> Path:
    assert_aggregate_only(df, name)
    TAB.mkdir(parents=True, exist_ok=True)
    p = TAB / name
    df.to_csv(p, index=False)
    return p


def cmd_sample(a: argparse.Namespace) -> None:
    folder = ensure_private_dir(LABELS / a.date)
    files = [folder / f for f in ("recall_sheet.csv", "recall_key.csv", "extractor_sheet.csv", "extractor_key.csv")]
    _guard_overwrite(files, a.force)
    df = load_postings()
    n_canon = int(df["is_canonical"].sum())
    print(f"canonical postings in frame: {n_canon} (docs quote 10,945)")
    sheet, key, texts = draw_recall_sample(df, a.n_recall, a.design, a.seed)
    write_sheet(sheet, files[0])
    write_sheet(key, files[1])
    _write_texts_html(texts, folder / "recall_texts.html", f"Recall sample {a.date} - full texts")
    print(key.groupby("stratum").agg(n=("row_id", "count"), N=("stratum_N", "first")).to_string())
    sheet, key, texts = draw_extractor_sample(df, a.n_extractor, a.seed)
    write_sheet(sheet, files[2])
    write_sheet(key, files[3])
    _write_texts_html(texts, folder / "extractor_texts.html", f"Extractor sample {a.date} - full texts")
    (folder / "README.txt").write_text(
        "PRIVATE labelling folder. Protocol: docs/labelling-protocol.md.\n"
        "Fill *_sheet.csv only. Do NOT open *_key.csv before labelling is finished (blind labelling).\n"
        "Save as 'CSV UTF-8'. Then run: python src/analysis/labelling_audit.py score --date " + a.date + "\n",
        encoding="utf-8")
    print(f"wrote {len(sheet)} extractor rows and the recall sheet to {folder}")


def cmd_sample_projects(a: argparse.Namespace) -> None:
    folder = ensure_private_dir(LABELS / a.date)
    files = [folder / "projects_sheet.csv", folder / "projects_key.csv"]
    _guard_overwrite(files, a.force)
    projects = pd.read_parquet(PROC / "supply_projects.parquet")
    sheet, key = draw_project_sample(projects, a.n, a.seed)
    write_sheet(sheet, files[0])
    write_sheet(key, files[1])
    print(f"wrote {len(sheet)} projects to {files[0]}")


def cmd_score(a: argparse.Namespace) -> None:
    folder = LABELS / a.date
    done = []
    if a.only in (None, "recall") and (folder / "recall_sheet.csv").exists():
        try:
            q10, q10b, priv = score_recall(read_sheet(folder / "recall_sheet.csv"), read_sheet(folder / "recall_key.csv"))
            done += [_write_public(q10, "Q10_title_recall.csv"), _write_public(q10b, "Q10b_title_recall_misses_by_predicted_family.csv")]
            write_sheet(priv, folder / "recall_misses_private.csv")
            print(q10.to_string(index=False))
        except SystemExit as e:
            print(f"recall: {e}")
    if a.only in (None, "extractor") and (folder / "extractor_sheet.csv").exists():
        q11 = score_extractor(read_sheet(folder / "extractor_sheet.csv"), read_sheet(folder / "extractor_key.csv"))
        if len(q11):
            done.append(_write_public(q11, "Q11_extractor_precision_recall.csv"))
            print(q11.to_string(index=False))
        else:
            print("extractor: no completed blocks yet")
    if a.only in (None, "projects") and (folder / "projects_sheet.csv").exists():
        try:
            q12, q12b = score_projects(read_sheet(folder / "projects_sheet.csv"), read_sheet(folder / "projects_key.csv"))
            done += [_write_public(q12, "Q12_project_quality_rubric.csv"), _write_public(q12b, "Q12b_project_structure_vs_quality.csv")]
            print(q12.to_string(index=False))
        except SystemExit as e:
            print(f"projects: {e}")
    stamp = {"scored_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "labels_folder": f"data/labels/{a.date}",
             "tables": [p.name for p in done]}
    if done:
        (folder / "score_manifest.json").write_text(json.dumps(stamp, indent=2), encoding="utf-8")
    print("public tables written:", ", ".join(p.name for p in done) or "none")


def cmd_score_applications(a: argparse.Namespace) -> None:
    path = PRIVATE / "application_log.csv"
    if not path.exists():
        raise SystemExit(f"no log at {path}; run init-application-log first")
    out = summarise_applications(read_sheet(path))
    if out.empty:
        print("log has no applications yet")
        return
    target = PRIVATE / "application_log_summary.csv"
    write_sheet(out, target)
    print(out.to_string(index=False))
    print(f"private summary: {target} (publish only by owner decision, aggregates only)")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--date", default=date.today().isoformat())
    s.add_argument("--n-recall", type=int, default=300)
    s.add_argument("--n-extractor", type=int, default=100)
    s.add_argument("--design", choices=["stratified", "srs"], default="stratified")
    s.add_argument("--seed", type=int, default=DEFAULT_SEED)
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_sample)
    p = sub.add_parser("sample-projects")
    p.add_argument("--date", default=date.today().isoformat())
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_sample_projects)
    c = sub.add_parser("score")
    c.add_argument("--date", required=True)
    c.add_argument("--only", choices=["recall", "extractor", "projects"])
    c.set_defaults(func=cmd_score)
    sub.add_parser("init-application-log").set_defaults(func=lambda a: print(init_application_log()))
    sub.add_parser("score-applications").set_defaults(func=cmd_score_applications)
    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main(sys.argv[1:])
