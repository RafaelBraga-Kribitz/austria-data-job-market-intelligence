"""Print a compact digest of all figures quoted in the decision documents.
Run after the pipeline: python src/reporting/digest.py > outputs/reports/digest.txt
Every number in CAREER_DECISION_MAP.md / AGENT_CONTEXT.md / docs/market-guide.md should be
traceable to a line printed here (which in turn names the table it comes from).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "outputs" / "tables"
OUT = ROOT / "outputs"
pd.set_option("display.width", 200); pd.set_option("display.max_colwidth", 90); pd.set_option("display.max_rows", 200)


def sec(title, table):
    print(f"\n=== {title}  [{table}] ===")


def piv(f, idx, col, val="share"):
    d = pd.read_csv(TAB / f)
    return d.pivot_table(index=idx, columns=col, values=val).round(2)


def main():
    S = json.load(open(OUT / "market_summary.json", encoding="utf-8"))
    sec("Counts", "market_summary.json"); print(json.dumps(S["counts"], indent=1)); print("posted:", S["posted_date_range"], "collected:", S["collected_at_range"])
    sec("Source coverage", "T01"); print(pd.read_csv(TAB / "T01_source_coverage.csv")[["source", "rows", "in_scope_rows", "adjacent_rows", "with_description", "in_scope_canonical"]].to_string(index=False))
    sec("Dedupe", "dedupe_summary / T01b"); print(pd.read_csv(TAB / "dedupe_summary.csv").to_string(index=False)); print(pd.read_csv(TAB / "T01b_source_overlap_in_scope.csv").head(10).to_string(index=False))
    sec("Families", "T02"); print(pd.read_csv(TAB / "T02_role_family_counts.csv").to_string(index=False)); print(pd.read_csv(TAB / "T02a_adjacent_family_counts.csv").to_string(index=False))
    sec("Normalized titles", "T02b"); print(pd.read_csv(TAB / "T02b_normalized_title_counts.csv").to_string(index=False))
    sec("States", "T03a/T03d"); print(pd.read_csv(TAB / "T03a_state_counts.csv").to_string(index=False)); print(pd.read_csv(TAB / "T03d_geo_summary.csv").to_string(index=False)); print(pd.read_csv(TAB / "T03c_styria_cities.csv").head(8).to_string(index=False))
    sec("Employers", "T04b/T04a/T04"); print(pd.read_csv(TAB / "T04b_employer_concentration.csv").to_string(index=False)); print(pd.read_csv(TAB / "T04a_employers_styria.csv")[["example_company", "styria", "families", "is_agency"]].head(20).to_string(index=False)); print(pd.read_csv(TAB / "T04_employers.csv")[["example_company", "postings", "states"]].head(15).to_string(index=False))
    sec("Tech skills overall", "T05_skills_all_tech"); print(pd.read_csv(TAB / "T05_skills_all_tech.csv")[["skill", "count", "n", "share", "ci_low", "ci_high"]].head(40).to_string(index=False))
    st = pd.read_csv(TAB / "T05_skills_all_tech_by_styria.csv"); top = pd.read_csv(TAB / "T05_skills_all_tech.csv").skill.head(25)
    sec("Tech skills Styria vs rest", "T05_skills_all_tech_by_styria"); print(st.groupby("styria_flag").n.first().to_dict()); print(st.pivot_table(index="skill", columns="styria_flag", values="share").reindex(top).round(2).to_string())
    sec("Top skills per family", "T14"); print(pd.read_csv(TAB / "T14_family_profiles.csv")[["role_family", "n_with_description", "top_tech_skills"]].to_string(index=False))
    sec("Business/soft/python/stats/BI/platform categories", "T05_skills_<cat>")
    for c in ["business_domain", "soft_skills", "python_ecosystem", "statistics_methods", "bi_tools", "data_platforms", "cloud_platforms", "ml_ai", "certifications"]:
        d = pd.read_csv(TAB / f"T05_skills_{c}.csv"); print(f"-- {c}: " + "; ".join(f"{r.skill} {r.share:.0%} ({r.count})" for r in d.head(12).itertuples()))
    sec("Stacks & pairs", "T06b/T06"); print(pd.read_csv(TAB / "T06b_top_stacks_size3.csv").head(10).to_string(index=False)); print(pd.read_csv(TAB / "T06_cooccurrence_pairs.csv")[["skill_a", "skill_b", "both", "share_of_postings", "p_b_given_a", "lift"]].head(12).to_string(index=False))
    sec("German requirement", "T07"); print(pd.read_csv(TAB / "T07_german_requirement_by_overall.csv").to_string(index=False)); print(piv("T07_german_requirement_by_role_family.csv", "role_family", "german_requirement").to_string()); print(piv("T07_german_requirement_by_source.csv", "source", "german_requirement").to_string()); print(piv("T07_german_requirement_by_styria_flag.csv", "styria_flag", "german_requirement").to_string()); print(piv("T07_german_requirement_by_seniority.csv", "seniority", "german_requirement").to_string())
    sec("German levels / English / posting language", "T07a/T07b/T07c/T07d"); print(pd.read_csv(TAB / "T07a_german_level_overall.csv").to_string(index=False)); print(pd.read_csv(TAB / "T07b_english_requirement.csv").to_string(index=False)); print(pd.read_csv(TAB / "T07c_posting_language.csv").to_string(index=False)); print(piv("T07c_posting_language_by_family.csv", "role_family", "posting_language").to_string()); print(piv("T07c_posting_language_by_styria.csv", "styria_flag", "posting_language").to_string()); print(open(TAB / "T07d_posting_language_x_german_req.csv").read())
    sec("Addressable scenarios", "T07e"); print(pd.read_csv(TAB / "T07e_addressable_market_scenarios.csv").to_string(index=False))
    sec("Seniority & experience", "T08"); print(pd.read_csv(TAB / "T08_seniority_overall.csv").to_string(index=False)); print(piv("T08_seniority_by_family.csv", "role_family", "seniority").to_string()); print(pd.read_csv(TAB / "T08a_experience_years_by_seniority.csv").to_string(index=False)); print(pd.read_csv(TAB / "T08c_experience_coverage.csv").to_string(index=False)); print(open(TAB / "T08d_seniority_x_years.csv").read())
    sec("Salary", "T09"); print(pd.read_csv(TAB / "T09_salary_coverage.csv").to_string(index=False)); print(open(TAB / "T09a_salary_basis_by_source.csv").read())
    for g in ["role_family", "seniority", "state", "normalized_title", "source", "posting_language"]:
        print(f"-- by {g}"); print(pd.read_csv(TAB / f"T09b_salary_by_{g}.csv")[[g, "n", "min_p25", "min_median", "min_p75", "max_median", "n_with_max"]].to_string(index=False))
    print(pd.read_csv(TAB / "T09c_salary_by_family_seniority.csv")[["role_family", "seniority", "n", "min_median", "max_median"]].to_string(index=False)); print(pd.read_csv(TAB / "T09d_salary_by_skill.csv").to_string(index=False))
    sec("Remote", "T10"); print(pd.read_csv(TAB / "T10_remote_overall.csv").to_string(index=False)); print(piv("T10_remote_by_family.csv", "role_family", "remote_type").to_string()); print(piv("T10_remote_by_styria.csv", "styria_flag", "remote_type").to_string()); print(piv("T10_remote_by_source.csv", "source", "remote_type").to_string()); print(pd.read_csv(TAB / "T10a_home_office_days.csv").to_string(index=False))
    sec("Education & certifications", "T11"); print(pd.read_csv(TAB / "T11_education_summary.csv").to_string(index=False)); print(pd.read_csv(TAB / "T11a_degree_levels.csv").to_string(index=False)); print(pd.read_csv(TAB / "T11b_degree_fields.csv").to_string(index=False)); d = pd.read_csv(TAB / "T11c_degree_required_by_family.csv"); print(d[d.degree_required == True][["role_family", "share", "n"]].to_string(index=False)); print(pd.read_csv(TAB / "T11d_certifications.csv").to_string(index=False))
    sec("Employment", "T12"); print(pd.read_csv(TAB / "T12_employment_type.csv").to_string(index=False)); print(pd.read_csv(TAB / "T12a_flags.csv").to_string(index=False))
    sec("Posting age", "T13b"); print(pd.read_csv(TAB / "T13b_posting_age_by_source.csv").to_string(index=False))
    sec("Clusters", "T15"); print(pd.read_csv(TAB / "T15_clusters_kmeans.csv")[["cluster", "n", "share", "defining_skills", "family_mix", "styria_share", "english_posting_share"]].to_string(index=False)); print(json.load(open(OUT / "clusters.json", encoding="utf-8"))["silhouette"])
    sec("Adjacent demand", "T16"); print(pd.read_csv(TAB / "T16_adjacent_demand_by_region.csv").to_string(index=False))
    sec("JobBarometer", "JB05/JB03/JB04"); jb = pd.read_csv(TAB / "JB05_styria_vs_austria.csv"); print(jb[jb.is_data_occupation][["beruf", "austria", "styria", "vienna", "upper_austria", "styria_share", "austria_2020", "growth_2020_to_latest", "styria_2020", "styria_growth_2020_to_latest"]].to_string(index=False))
    L = pd.read_csv(TAB / "JB01_yearly_counts_long.csv"); print(L[L.beruf.str.contains("Data Scientist") & L.bl.isin(["AT", "AT22", "AT13", "AT31"])].pivot_table(index="year", columns="bundesland", values="ads").to_string())
    t = pd.read_csv(TAB / "JB03_trends.csv"); print(t[t.beruf.str.contains("Data Scientist|Datenbankentwickler|Data-Warehouse|Wirtschaftsinformatik|Systemanaly", regex=True, na=False) & t.bl.isin(["AT", "AT22"])][["beruf", "bundesland", "trend_3y", "share_label", "count_latest"]].to_string(index=False))
    c = pd.read_csv(TAB / "JB04_competencies.csv"); print(c[c.beruf.str.contains("Data Scientist")].to_string(index=False))
    sec("Decision matrix", "D01/D02/D04"); print(pd.read_csv(TAB / "D01_decision_matrix.csv")[["role_family", "V1_postings_at", "V2_postings_styria", "V3_english_posting_share", "V4_german_required_share", "V5_profile_overlap_top15", "V6_structural_gap_top15", "V7_median_min_salary", "V8_remote_or_hybrid_share", "V9_senior_entry_openness", "V10_degree_required_share", "score_default", "rank_default", "small_sample_flag"]].to_string(index=False)); print(pd.read_csv(TAB / "D02_sensitivity.csv").to_string(index=False)); print(pd.read_csv(TAB / "D04_learning_priorities.csv")[["skill", "share", "styria_share", "families_where_top(>=15%)", "profile_status", "priority"]].head(45).to_string(index=False))
    sec("Data quality", "Q02/Q03a/Q04/Q05a"); print(pd.read_csv(TAB / "Q02_coverage_by_source_core.csv").to_string(index=False)); print(pd.read_csv(TAB / "Q03a_normalization_confidence.csv").to_string(index=False)); print(pd.read_csv(TAB / "Q04_duplicates.csv").to_string(index=False)); print(pd.read_csv(TAB / "Q05a_stale.csv").to_string(index=False))
    if (TAB / "S01_seasonal_index.csv").exists():
        sec("Seasonality (Eurostat JVS, quarterly 2009-2025)", "S01/S03/S06")
        s1 = pd.read_csv(TAB / "S01_seasonal_index.csv")
        print(s1[s1["sample"] == "full"][["sector", "quarter", "n_years", "index_a_own_year_mean", "ci_low", "ci_high", "index_b_moving_average", "years_above_average"]].to_string(index=False))
        print(pd.read_csv(TAB / "S03_sensitivity_samples.csv").to_string(index=False))
        print(pd.read_csv(TAB / "S06_season_vs_cycle.csv").to_string(index=False))
        if (TAB / "S05_snapshot_age_distribution.csv").exists():
            print("-- why not from our own snapshot (S05)"); print(pd.read_csv(TAB / "S05_snapshot_age_distribution.csv").to_string(index=False))


if __name__ == "__main__":
    main()
