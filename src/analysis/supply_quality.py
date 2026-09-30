"""Layer 2 data-quality audit: tables SQ01–SQ11 and outputs/supply_data_quality.json.

Checks: duplicate accounts/repositories, missingness of bio/location/company, geography conflicts, stale profiles,
taxonomy failures (bio has a data word but no family), classification samples for manual precision review (private),
skill false-positive risk list, frame overlap, and the search-cap losses. Feeds docs/supply-data-quality.md.
SQ10/SQ11 summarise the hand-labelled precision reviews (D-021) from the private label files
data/processed/supply_quality_{bio,repo}_precision_labels.csv; without them the existing tables are kept.

Usage: python src/analysis/supply_quality.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

from supply_common import CFG, OUT, PROC, ROOT, load_candidates, load_evidence, load_projects, wilson, write


# After src/pipeline/redact_supply_raw.py has run, bio/login/blog/company/location_text are null and rows carry
# `redacted`; the tables below need those fields, so a re-run would silently degrade them. Refuse instead.
FROZEN_ON = "2026-09-30"


def refuse_if_redacted(c: pd.DataFrame) -> None:
    flagged = c["redacted"].eq(True) if "redacted" in c.columns else pd.Series(False, index=c.index)
    if flagged.any():
        n = int(flagged.sum())
        raise SystemExit(f"{Path(__file__).name}: {n} candidate rows are redacted (personal free text removed by "
                         f"redact_supply_raw.py). The Layer 2 analysis was frozen on {FROZEN_ON}; the tables in "
                         "outputs/tables are that frozen version and are NOT regenerated from redacted data.")


# Reviewer annotations of the 2026-09-18 precision reviews (D-021). The counts are recomputed from the label files on
# every run; the sample description, error typology and reviewer are the reviewer's own record and are carried as text.
PRECISION_REVIEWS = {
    "SQ10_bio_classification_precision": {
        "labels": "supply_quality_bio_precision_labels.csv",
        "sample": "P_T1 random sample (seed 11), reviewed 2026-09-18",
        "error_types": "company/organisation account read as person (2); engineering bio with ML words read as data science (1); "
                       "finance/quant wording read as data science (1); students/researchers counted as declared roles (lenient only)",
    },
    "SQ11_project_classification_precision": {
        "labels": "supply_quality_repo_precision_labels.csv",
        "sample": "substantive projects of P_data, random (seed 21), reviewed 2026-09-18",
        "definition": "strict = a data/ML/analytics project in the Layer 1 sense; lenient = data-adjacent tooling (SQL guides, dataset collections, "
                      "metric exporters, visualisation components, bioinformatics tools)",
        "error_types": "API/tooling repos matched by an AI/LLM vendor word (1); generic software matched by a tool word such as spark/sql (2); "
                       "data-adjacent tooling counted as projects (7, lenient)",
    },
}


def precision_table(spec: dict) -> pd.DataFrame | None:
    """One-row precision summary from a private label file (None when the file is absent)."""
    f = PROC / spec["labels"]
    if not f.exists():
        return None
    lab = pd.read_csv(f)
    n = len(lab)
    strict, lenient = int(lab.strict_correct.astype(bool).sum()), int(lab.lenient_correct.astype(bool).sum())
    row = {"sample": spec["sample"], "n": n, "strict_correct": strict, "strict_precision": round(strict / n, 3) if n else None,
           "lenient_correct": lenient, "lenient_precision": round(lenient / n, 3) if n else None}
    if "definition" in spec:
        row["definition"] = spec["definition"]
    row["error_types"] = spec["error_types"]
    row["reviewer"] = "repository author"
    return pd.DataFrame([row])


def write_precision_tables() -> None:
    for name, spec in PRECISION_REVIEWS.items():
        t = precision_table(spec)
        if t is None:
            print(f"NOTICE: data/processed/{spec['labels']} not found - {name} NOT refreshed (existing table kept)", file=sys.stderr)
            continue
        write(t, name)


def main() -> None:
    c = load_candidates(); refuse_if_redacted(c); p = load_projects(); e = load_evidence()
    raw = ROOT / "data" / "raw" / "github_supply" / json.loads((PROC / "supply_build_manifest.json").read_text())["collection_date"]
    search = pd.DataFrame([json.loads(l) for l in open(raw / "users_search.jsonl", encoding="utf-8")])
    summ = pd.DataFrame([json.loads(l) for l in open(raw / "search_summary.jsonl", encoding="utf-8")])
    profiles = [json.loads(l) for l in open(raw / "profiles.jsonl", encoding="utf-8")]
    gh = c[c.source == "github"]; P_all = gh[gh.is_austria]; P_data = P_all[P_all.is_data]; P_T1 = P_all[P_all.is_t1]

    # SQ01 search-cap losses and query coverage
    capped = summ[(summ.total_count > 1000) | ((summ.frame == "C") & (summ.total_count > summ.retrieved))]
    sq01 = pd.DataFrame([{"queries_run": len(summ), "frame_A": int((summ.frame == "A").sum()), "frame_B": int((summ.frame == "B").sum()), "frame_C": int((summ.frame == "C").sum()),
                          "queries_hitting_1000_cap": int((summ.total_count > 1000).sum()), "frame_C_truncated_slices": int(((summ.frame == "C") & (summ.total_count > summ.retrieved)).sum()),
                          "frame_C_total_available": int(summ[summ.frame == "C"].total_count.sum()), "frame_C_retrieved": int(summ[summ.frame == "C"].retrieved.sum()),
                          "search_rows": len(search), "unique_accounts_searched": int(search.login.nunique()), "profiles_fetched": len([x for x in profiles if x.get("id")]), "profiles_failed": len([x for x in profiles if not x.get("id")]),
                          "organisations_or_bots_dropped": int((search.type != "User").sum())}])
    write(sq01, "SQ01_search_coverage_and_caps",
          note="profiles_failed = profile records without an id in profiles.jsonl; collection runs after 2026-09-30 log "
               "transient failures to retry.jsonl instead, so from those runs on it counts definitive failures only")
    write(capped[["query", "frame", "total_count", "retrieved"]], "SQ01a_capped_queries")

    # SQ02 duplicates
    dup_login = int(gh.login.duplicated().sum()); dup_id = int(gh.candidate_id.duplicated().sum()); dup_repo = int(p.project_id.duplicated().sum())
    frames = gh.frames.map(lambda f: "+".join(sorted(f)))
    sq02 = pd.DataFrame([{"duplicate_logins": dup_login, "duplicate_candidate_ids": dup_id, "duplicate_project_ids": dup_repo, "accounts_in_multiple_frames": int(gh.frames.map(len).gt(1).sum()),
                          "frame_combinations": json.dumps(frames.value_counts().to_dict()), "median_search_hits_per_account": float(gh.n_search_hits.median()),
                          "cross_source_dedup": "not applicable: GitHub is the only automated source; Stack Overflow survey is anonymous; manual LinkedIn records use observer-assigned pseudo ids and cannot be matched"}])
    write(sq02, "SQ02_duplicates")

    # SQ03 missingness
    rows = []
    for name, sub in (("P_all", P_all), ("P_data", P_data), ("P_T1", P_T1)):
        n = len(sub)
        for field, mask in (("bio", ~sub.has_bio), ("company", ~sub.has_company), ("location with state", sub.state.isna() | (sub.state == "unspecified (Austria)")), ("website/blog", sub.blog.fillna("").astype(str).eq("")),
                            ("no owned repository", sub.n_repos_owned == 0), ("education wording", sub.edu_levels_any.map(len) == 0), ("seniority wording", ~sub.seniority_bio.isin(["student", "junior", "senior", "lead_head"])),
                            ("any skill evidence", sub.skills_any.map(len) == 0), ("bio language (bio ≤ 40 chars)", sub.bio_language.isna())):
            k = int(mask.sum())
            rows.append({"population": name, "missing": field, "count": k, "n": n, "share": round(k / n, 3) if n else None})
    write(pd.DataFrame(rows), "SQ03_missingness")

    # SQ04 geography quality
    sq04 = pd.DataFrame([{"population": "all GitHub accounts fetched", "n": len(gh), "austrian_signal": int(gh.is_austria.sum()), "dropped_no_austrian_signal": int((~gh.is_austria).sum()),
                          "foreign_place_also_named": int(gh.foreign_place_named.sum()), "multi_location": int(gh.multi_location.sum()), "austria_only_no_state": int((gh.geo_confidence == "austria_only").sum()),
                          "state_and_city": int((gh.geo_confidence == "state_and_city").sum()), "state_only": int((gh.geo_confidence == "state_only").sum()),
                          "styria_frame_B_but_state_not_styria": int((gh.frame_b & gh.is_austria & ~gh.is_styria).sum()), "note": "frame B tokens include Styrian town names that also exist elsewhere (e.g. Weiz≠, Baden), and 'Graz' inside other strings; state is decided by geo.json"}])
    write(sq04, "SQ04_geography_quality")
    loc_examples = gh[gh.frame_b & gh.is_austria & ~gh.is_styria].location_text.value_counts().head(20).reset_index(); loc_examples.columns = ["location_text", "accounts"]
    (PROC / "supply_quality_frameB_nonstyria_locations.csv").write_text(loc_examples.to_csv(index=False), encoding="utf-8")  # private (free text)

    # SQ05 staleness
    upd = pd.to_datetime(gh.profile_updated, errors="coerce", utc=True); col = pd.Timestamp(json.loads((PROC / "supply_build_manifest.json").read_text())["collection_date"], tz="UTC")
    age_days = (col - upd).dt.days
    rows = []
    for name, sub, a in (("P_all", P_all, age_days[P_all.index]), ("P_data", P_data, age_days[P_data.index])):
        n = len(sub)
        rows.append({"population": name, "n": n, "profile_updated_within_12m": int((a <= 365).sum()), "share_updated_12m": round((a <= 365).mean(), 3) if n else None, "any_push_12m": int((sub.n_active_12m >= 1).sum()),
                     "share_push_12m": round((sub.n_active_12m >= 1).mean(), 3) if n else None, "no_push_3y": int(pd.to_datetime(sub.last_push, errors="coerce", utc=True).lt(col - pd.Timedelta(days=1095)).sum()),
                     "median_account_age_years": float(sub.account_age_years.median()) if n else None})
    write(pd.DataFrame(rows), "SQ05_staleness", "profile_updated changes with any account activity; a location string may be years old")

    # SQ06 taxonomy failures: bio contains a data word but no family assigned
    dw = re.compile(r"data|analy|machine learning|\bml\b|\bai\b|statist|\bbi\b|intelligence|quant", re.I)
    unmatched = P_all[P_all.has_bio & ~P_all.is_t1 & P_all.bio.map(lambda b: bool(dw.search(b or "")))]
    sq06 = pd.DataFrame([{"bios_with_data_word": int(P_all.bio.map(lambda b: bool(dw.search(b or ""))).sum()), "of_which_T1": int((P_all.is_t1 & P_all.bio.map(lambda b: bool(dw.search(b or "")))).sum()),
                          "unmatched": len(unmatched), "unmatched_share": round(len(unmatched) / max(1, int(P_all.bio.map(lambda b: bool(dw.search(b or ""))).sum())), 3),
                          "rule_provenance_T1": json.dumps(Counter(str(r).split(":")[0] for r in P_T1.bio_role_rule).most_common()), "after_transition_reclassified": int(P_T1.bio_role_rule.astype(str).str.startswith("after_transition").sum())}])
    write(sq06, "SQ06_taxonomy_coverage")
    # private review samples (bios are personal text → never exported)
    rs = pd.concat([P_T1.sample(min(60, len(P_T1)), random_state=1).assign(sample="T1"), unmatched.sample(min(40, len(unmatched)), random_state=1).assign(sample="unmatched")])
    rs[["sample", "candidate_id", "bio", "bio_role_family", "bio_normalized_title", "bio_role_rule", "seniority_bio", "state"]].to_csv(PROC / "supply_quality_bio_review_sample.csv", index=False)
    ps = p.sample(min(80, len(p)), random_state=1)[["project_id", "name", "description", "language", "topics", "data_reason", "is_educational", "archetype", "formats", "themes_ds_method", "themes_analytics_domain", "readme_chars"]]
    ps.to_csv(PROC / "supply_quality_repo_review_sample.csv", index=False)

    # SQ07 skill false-positive risk: skills whose evidence is almost only 'used' via repo names with short tokens
    risky = ["R", "Go", "C/C++", "Julia", "AI (generic)", "Cloud (generic)", "Data Visualization", "Streaming", "Data Modeling", "Statistics (general)", "Mathematics", "Excel", "SAS", "DAX/M", "Kafka", "Airflow"]
    rows = []
    for s in risky:
        sub = e[(e.skill == s) & e.candidate_id.isin(P_data.candidate_id)]
        rows.append({"skill": s, "candidates": int(sub.candidate_id.nunique()), "bio_mentions": int(sub.mentioned.sum()), "repo_meta_used": int(sub.used.sum()), "readme_demonstrated": int(sub.demonstrated.sum()),
                     "risk": "language-field only (reliable)" if s == "R" else "generic word (indicative only)" if "generic" in s or s in ("Data Visualization", "Statistics (general)", "Mathematics", "Data Modeling", "Streaming") else "check sample"})
    write(pd.DataFrame(rows), "SQ07_skill_false_positive_risk", "the Layer 1 vocabulary was designed for job ads; README prose can trigger generic entries more often; project_demonstrated counts are the conservative reading")

    # SQ08 project classification stats
    sq08 = pd.DataFrame([{"data_repos": len(p), "by_reason": json.dumps(Counter(r.split(":")[0] for r in p.data_reason).most_common()), "readme_fetched": int(p.readme_fetched.sum()), "readme_404_or_missing": int((p.readme_status != 200).sum()),
                          "tree_fetched": int(p.tree_entries.notna().sum()), "is_project": int(p.is_project.sum()), "documented": int(p.is_documented.sum()), "educational": int(p.is_educational.sum()), "substantive": int(p.is_substantive.sum()),
                          "archived": int(p.archived.sum()), "no_theme": int((p[["themes_analytics_domain", "themes_ds_method", "themes_engineering", "themes_ai"]].map(len).sum(axis=1) == 0).sum()),
                          "keyword_only_with_empty_readme": int(((p.data_reason.str.startswith("keyword")) & (p.readme_chars < 300)).sum())}])
    write(sq08, "SQ08_project_classification")

    # SQ09 frame comparison of key rates (selection effects)
    rows = []
    for fr in ("frame_a", "frame_b", "frame_c"):
        sub = P_all[P_all[fr]]; n = len(sub)
        rows.append({"frame": fr[-1].upper(), "n": n, "has_bio": round(sub.has_bio.mean(), 3) if n else None, "T1": round(sub.is_t1.mean(), 3) if n else None, "data_signal": round(sub.is_data.mean(), 3) if n else None,
                     "median_repos": float(sub.n_repos_owned.median()) if n else None, "push_12m": round((sub.n_active_12m >= 1).mean(), 3) if n else None, "student_T1": round((sub.is_t1 & sub.is_student).sum() / max(1, sub.is_t1.sum()), 3)})
    write(pd.DataFrame(rows), "SQ09_frame_selection_effects", "frame A over-represents accounts that write data words in bios; frame B is the population of Styrian accounts with ≥ 1 repo; frame C is a base-rate sample")

    # SQ10/SQ11 hand-labelled precision (private labels; no writer existed before 2026-09-30)
    write_precision_tables()

    out = {"generated": pd.Timestamp.now().isoformat(), "search": sq01.to_dict("records")[0], "duplicates": sq02.to_dict("records")[0], "geography": sq04.to_dict("records")[0], "staleness": rows, "taxonomy": sq06.to_dict("records")[0],
           "projects": sq08.to_dict("records")[0], "review_samples_private": ["data/processed/supply_quality_bio_review_sample.csv", "data/processed/supply_quality_repo_review_sample.csv"]}
    (OUT / "supply_data_quality.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"search": out["search"], "taxonomy": out["taxonomy"]}, indent=1)[:1500])


if __name__ == "__main__":
    main()
