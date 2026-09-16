"""Step 7: machine-readable summaries for AI agents -> outputs/{skills,roles,locations,languages,salaries}.json

Each file states its denominator and vintage. career_paths.json is written by hand
(docs/career-map.md is the source) because it encodes judgement, not just counts.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "outputs" / "tables"
OUT = ROOT / "outputs"
S = json.load(open(OUT / "market_summary.json", encoding="utf-8"))
META = {"vintage": S["collected_at_range"], "posted_date_range": S["posted_date_range"], "analysis_set": S["analysis_set_definition"], "note": "Derived from outputs/tables; regenerate with src/analysis/export_agent_json.py after re-running the pipeline."}


def rec(df, n=None):
    return json.loads(df.head(n).to_json(orient="records")) if n else json.loads(df.to_json(orient="records"))


def main():
    # skills
    st = pd.read_csv(TAB / "T05_skills_all_tech.csv")
    fam = pd.read_csv(TAB / "T05_skills_all_tech_by_family.csv")
    sty = pd.read_csv(TAB / "T05_skills_all_tech_by_styria.csv")
    co = pd.read_csv(TAB / "T06_cooccurrence_pairs.csv")
    cats = {}
    for c in ["programming_languages", "bi_tools", "cloud_platforms", "data_platforms", "python_ecosystem", "data_engineering", "ml_ai", "statistics_methods", "business_domain", "soft_skills", "certifications"]:
        cats[c] = rec(pd.read_csv(TAB / f"T05_skills_{c}.csv"), 25)
    by_fam = {f: rec(g.sort_values("count", ascending=False), 20) for f, g in fam.groupby("role_family")}
    json.dump({**META, "denominator": int(st.n.iloc[0]) if len(st) else None, "top_tech_overall": rec(st, 40), "by_category": cats, "by_family_top20": by_fam,
               "styria_vs_rest": rec(sty), "top_cooccurrence_pairs": rec(co, 40)}, open(OUT / "skills.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # roles
    json.dump({**META, "families": rec(pd.read_csv(TAB / "T02_role_family_counts.csv")), "adjacent_families": rec(pd.read_csv(TAB / "T02a_adjacent_family_counts.csv")),
               "normalized_titles": rec(pd.read_csv(TAB / "T02b_normalized_title_counts.csv")), "top_raw_titles": rec(pd.read_csv(TAB / "T02c_top_raw_titles.csv"), 60),
               "family_profiles": rec(pd.read_csv(TAB / "T14_family_profiles.csv")), "seniority": rec(pd.read_csv(TAB / "T08_seniority_overall.csv")),
               "seniority_by_family": rec(pd.read_csv(TAB / "T08_seniority_by_family.csv")), "experience_years_by_seniority": rec(pd.read_csv(TAB / "T08a_experience_years_by_seniority.csv"))},
              open(OUT / "roles.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # locations
    fb = pd.read_csv(TAB / "T03_family_by_state.csv")
    json.dump({**META, "summary": rec(pd.read_csv(TAB / "T03d_geo_summary.csv")), "states": rec(pd.read_csv(TAB / "T03a_state_counts.csv")), "geo_scope": rec(pd.read_csv(TAB / "T03b_geo_scope.csv")),
               "family_by_state": json.loads(fb.to_json(orient="records")), "styria_cities": rec(pd.read_csv(TAB / "T03c_styria_cities.csv")),
               "employers_styria_top": rec(pd.read_csv(TAB / "T04a_employers_styria.csv"), 40), "employers_top": rec(pd.read_csv(TAB / "T04_employers.csv"), 40),
               "employer_concentration": rec(pd.read_csv(TAB / "T04b_employer_concentration.csv")),
               "remote_overall": rec(pd.read_csv(TAB / "T10_remote_overall.csv")), "remote_by_family": rec(pd.read_csv(TAB / "T10_remote_by_family.csv")), "remote_by_styria": rec(pd.read_csv(TAB / "T10_remote_by_styria.csv"))},
              open(OUT / "locations.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # languages
    json.dump({**META, "german_overall": rec(pd.read_csv(TAB / "T07_german_requirement_by_overall.csv")), "german_by_family": rec(pd.read_csv(TAB / "T07_german_requirement_by_role_family.csv")),
               "german_by_styria": rec(pd.read_csv(TAB / "T07_german_requirement_by_styria_flag.csv")), "german_by_source": rec(pd.read_csv(TAB / "T07_german_requirement_by_source.csv")),
               "german_levels": rec(pd.read_csv(TAB / "T07a_german_level_overall.csv")), "english": rec(pd.read_csv(TAB / "T07b_english_requirement.csv")),
               "posting_language": rec(pd.read_csv(TAB / "T07c_posting_language.csv")), "posting_language_by_family": rec(pd.read_csv(TAB / "T07c_posting_language_by_family.csv")),
               "addressable_market_scenarios": rec(pd.read_csv(TAB / "T07e_addressable_market_scenarios.csv")),
               "definitions": {"required": "explicit requirement word near the language mention", "required_implied": "a level (CEFR or descriptor) is stated without 'preferred' wording", "preferred": "von Vorteil / wünschenswert / plus / ideally", "mentioned": "language mentioned without level or requirement wording", "german_or_english": "either language accepted", "explicitly_not_required": "ad states German is not required or English is the working language", "not_mentioned": "no German mention in the ad text"}},
              open(OUT / "languages.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # salaries
    json.dump({**META, "coverage": rec(pd.read_csv(TAB / "T09_salary_coverage.csv")), "basis_by_source": json.loads(pd.read_csv(TAB / "T09a_salary_basis_by_source.csv").to_json(orient="records")),
               "by_family": rec(pd.read_csv(TAB / "T09b_salary_by_role_family.csv")), "by_seniority": rec(pd.read_csv(TAB / "T09b_salary_by_seniority.csv")), "by_state": rec(pd.read_csv(TAB / "T09b_salary_by_state.csv")),
               "by_family_seniority": rec(pd.read_csv(TAB / "T09c_salary_by_family_seniority.csv")), "by_skill": rec(pd.read_csv(TAB / "T09d_salary_by_skill.csv")),
               "definitions": {"salary_min_annual_eur": "advertised MINIMUM gross annual salary in EUR; monthly figures ×14 (Austrian convention); mostly collective-agreement floors, not offers", "salary_max_annual_eur": "upper end when a range was advertised", "third_party_surveys": "NOT included here; see docs/salary-context.md"}},
              open(OUT / "salaries.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote skills/roles/locations/languages/salaries json")


if __name__ == "__main__":
    main()
