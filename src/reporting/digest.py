"""Compact digest of every figure quoted in the decision documents -> outputs/reports/digest.txt

Run after the pipeline (run_all.py runs it as the `digest` step):
    python src/reporting/digest.py               write outputs/reports/digest.txt (UTF-8, LF, atomic replace)
    python src/reporting/digest.py --stdout      ... and print the digest as well
    python src/reporting/digest.py --strict      exit code 1 if any input table is missing
    python src/reporting/digest.py --out PATH    write to another file

Every number in CAREER_DECISION_MAP.md / AGENT_CONTEXT.md / docs/market-guide.md should be traceable to a line
written here (which in turn names the table it comes from).

The file is written by this script itself (no shell redirect), so its encoding does not depend on the shell, and it is
built in memory and moved into place only when complete: a failure can never leave a truncated digest behind. A missing
table does not abort the run; the section that needs it says so, and every missing input is listed at the end.
Section headings take their vintages (snapshot dates, year ranges) from the data (market_summary.json,
supply_build_manifest.json or supply_summary.json, S04a, JB01) instead of hard-coded text.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "outputs" / "tables"
OUT = ROOT / "outputs"
PROC = ROOT / "data" / "processed"
DEFAULT_TARGET = OUT / "reports" / "digest.txt"
pd.set_option("display.width", 200); pd.set_option("display.max_colwidth", 90); pd.set_option("display.max_rows", 200)

MISSING: list[str] = []   # "<input> (section: <title>)" for every input that was absent
ERRORS: list[str] = []    # sections that failed for another reason (schema drift, unexpected values)


def sec(title, table):
    print(f"\n=== {title}  [{table}] ===")


def _rel(path) -> str:
    try:
        return Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
    except (TypeError, ValueError, OSError):
        return str(path)


@contextmanager
def section(title, table):
    """Print a section heading; a missing input or a failing statement ends only this section and is recorded."""
    sec(title, table)
    try:
        yield
    except FileNotFoundError as e:
        name = _rel(e.filename) if e.filename else str(e)
        MISSING.append(f"{name}  (section: {title})")
        print(f"(section incomplete - missing input: {name})")
    except Exception as e:  # noqa: BLE001 - listed at the end and turned into a non-zero exit code
        ERRORS.append(f"{title}: {type(e).__name__}: {e}")
        print(f"(section incomplete - {type(e).__name__}: {e})")


def csv(name: str) -> pd.DataFrame:
    return pd.read_csv(TAB / name)


def raw(name: str) -> str:
    return (TAB / name).read_text(encoding="utf-8")


def piv(f, idx, col, val="share"):
    d = pd.read_csv(TAB / f)
    return d.pivot_table(index=idx, columns=col, values=val).round(2)


def _json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _year_range(name: str, col: str = "year") -> str | None:
    try:
        y = pd.read_csv(TAB / name, usecols=[col])[col].dropna().astype(int)
    except (OSError, ValueError):
        return None
    return f"{y.min()}-{y.max()}" if len(y) else None


def vintages() -> dict[str, str]:
    """Snapshot dates and year ranges of every layer, read from the data ('unknown' where the source is absent)."""
    ms = _json(OUT / "market_summary.json") or {}
    rng = ms.get("collected_at_range") or {}
    lo, hi = str(rng.get("min") or "")[:10], str(rng.get("max") or "")[:10]
    man = _json(PROC / "supply_build_manifest.json") or _json(OUT / "supply_summary.json") or {}
    return {
        "demand": (lo if lo == hi else f"{lo}..{hi}") if lo else "unknown",
        "supply": man.get("collection_date") or "unknown",
        "eurostat_jvs": _year_range("S04a_levels_by_year.csv") or "unknown",
        "jobbarometer": _year_range("JB01_yearly_counts_long.csv") or "unknown",
    }


def layer1_digest(v: dict[str, str]):
    """Layer 1 (employer demand) figures quoted in CAREER_DECISION_MAP.md, docs/market-guide.md, AGENT_CONTEXT.md."""
    with section(f"Counts (demand snapshot collected {v['demand']})", "market_summary.json"):
        S = json.loads((OUT / "market_summary.json").read_text(encoding="utf-8"))
        print(json.dumps(S["counts"], indent=1)); print("posted:", S["posted_date_range"], "collected:", S["collected_at_range"])
    with section("Source coverage", "T01"):
        print(csv("T01_source_coverage.csv")[["source", "rows", "in_scope_rows", "adjacent_rows", "with_description", "in_scope_canonical"]].to_string(index=False))
    with section("Dedupe", "dedupe_summary / T01b"):
        print(csv("dedupe_summary.csv").to_string(index=False)); print(csv("T01b_source_overlap_in_scope.csv").head(10).to_string(index=False))
    with section("Families", "T02"):
        print(csv("T02_role_family_counts.csv").to_string(index=False)); print(csv("T02a_adjacent_family_counts.csv").to_string(index=False))
    with section("Normalized titles", "T02b"):
        print(csv("T02b_normalized_title_counts.csv").to_string(index=False))
    with section("States", "T03a/T03d"):
        print(csv("T03a_state_counts.csv").to_string(index=False)); print(csv("T03d_geo_summary.csv").to_string(index=False)); print(csv("T03c_styria_cities.csv").head(8).to_string(index=False))
    with section("Employers", "T04b/T04a/T04/T04d"):
        print(csv("T04b_employer_concentration.csv").to_string(index=False)); print(csv("T04a_employers_styria.csv")[["example_company", "styria", "families", "is_agency"]].head(20).to_string(index=False)); print(csv("T04_employers.csv")[["example_company", "postings", "states"]].head(15).to_string(index=False))
        if (TAB / "T04d_dual_track_summary.csv").exists():
            print("-- dual-track (intern AND junior)"); print(csv("T04d_dual_track_summary.csv").to_string(index=False))
            d4 = csv("T04d_dual_track_employers.csv")
            if len(d4):
                print(d4.head(20).to_string(index=False))
    with section("Tech skills overall", "T05_skills_all_tech"):
        print(csv("T05_skills_all_tech.csv")[["skill", "count", "n", "share", "ci_low", "ci_high"]].head(40).to_string(index=False))
    with section("Tech skills Styria vs rest", "T05_skills_all_tech_by_styria"):
        st = csv("T05_skills_all_tech_by_styria.csv"); top = csv("T05_skills_all_tech.csv").skill.head(25)
        print(st.groupby("styria_flag").n.first().to_dict()); print(st.pivot_table(index="skill", columns="styria_flag", values="share").reindex(top).round(2).to_string())
    with section("Top skills per family", "T14"):
        print(csv("T14_family_profiles.csv")[["role_family", "n_with_description", "top_tech_skills"]].to_string(index=False))
    with section("Business/soft/python/stats/BI/platform categories", "T05_skills_<cat>"):
        for c in ["business_domain", "soft_skills", "python_ecosystem", "statistics_methods", "bi_tools", "data_platforms", "cloud_platforms", "ml_ai", "certifications"]:
            d = csv(f"T05_skills_{c}.csv"); print(f"-- {c}: " + "; ".join(f"{r.skill} {r.share:.0%} ({r.count})" for r in d.head(12).itertuples()))
    with section("Stacks & pairs", "T06b/T06"):
        print(csv("T06b_top_stacks_size3.csv").head(10).to_string(index=False)); print(csv("T06_cooccurrence_pairs.csv")[["skill_a", "skill_b", "both", "share_of_postings", "p_b_given_a", "lift"]].head(12).to_string(index=False))
    with section("German requirement", "T07"):
        print(csv("T07_german_requirement_by_overall.csv").to_string(index=False)); print(piv("T07_german_requirement_by_role_family.csv", "role_family", "german_requirement").to_string()); print(piv("T07_german_requirement_by_source.csv", "source", "german_requirement").to_string()); print(piv("T07_german_requirement_by_styria_flag.csv", "styria_flag", "german_requirement").to_string()); print(piv("T07_german_requirement_by_seniority.csv", "seniority", "german_requirement").to_string())
    with section("German levels / English / posting language", "T07a/T07b/T07c/T07d"):
        print(csv("T07a_german_level_overall.csv").to_string(index=False)); print(csv("T07b_english_requirement.csv").to_string(index=False)); print(csv("T07c_posting_language.csv").to_string(index=False)); print(piv("T07c_posting_language_by_family.csv", "role_family", "posting_language").to_string()); print(piv("T07c_posting_language_by_styria.csv", "styria_flag", "posting_language").to_string()); print(raw("T07d_posting_language_x_german_req.csv"))
    with section("Addressable scenarios", "T07e"):
        print(csv("T07e_addressable_market_scenarios.csv").to_string(index=False))
    with section("Seniority & experience", "T08"):
        print(csv("T08_seniority_overall.csv").to_string(index=False)); print(piv("T08_seniority_by_family.csv", "role_family", "seniority").to_string()); print(csv("T08a_experience_years_by_seniority.csv").to_string(index=False)); print(csv("T08c_experience_coverage.csv").to_string(index=False)); print(raw("T08d_seniority_x_years.csv"))
    with section("Salary", "T09"):
        print(csv("T09_salary_coverage.csv").to_string(index=False)); print(raw("T09a_salary_basis_by_source.csv"))
        for g in ["role_family", "seniority", "state", "normalized_title", "source", "posting_language"]:
            print(f"-- by {g}"); print(csv(f"T09b_salary_by_{g}.csv")[[g, "n", "min_p25", "min_median", "min_p75", "max_median", "n_with_max"]].to_string(index=False))
        print(csv("T09c_salary_by_family_seniority.csv")[["role_family", "seniority", "n", "min_median", "max_median"]].to_string(index=False)); print(csv("T09d_salary_by_skill.csv").to_string(index=False))
    with section("Remote", "T10"):
        print(csv("T10_remote_overall.csv").to_string(index=False)); print(piv("T10_remote_by_family.csv", "role_family", "remote_type").to_string()); print(piv("T10_remote_by_styria.csv", "styria_flag", "remote_type").to_string()); print(piv("T10_remote_by_source.csv", "source", "remote_type").to_string()); print(csv("T10a_home_office_days.csv").to_string(index=False))
    with section("Education & certifications", "T11"):
        print(csv("T11_education_summary.csv").to_string(index=False)); print(csv("T11a_degree_levels.csv").to_string(index=False)); print(csv("T11b_degree_fields.csv").to_string(index=False)); d = csv("T11c_degree_required_by_family.csv"); print(d[d.degree_required == True][["role_family", "share", "n"]].to_string(index=False)); print(csv("T11d_certifications.csv").to_string(index=False))  # noqa: E712
    with section("Employment", "T12"):
        print(csv("T12_employment_type.csv").to_string(index=False)); print(csv("T12a_flags.csv").to_string(index=False))
    with section("Posting age", "T13b"):
        print(csv("T13b_posting_age_by_source.csv").to_string(index=False))
    with section("Clusters", "T15"):
        print(csv("T15_clusters_kmeans.csv")[["cluster", "n", "share", "defining_skills", "family_mix", "styria_share", "english_posting_share"]].to_string(index=False)); print(json.loads((OUT / "clusters.json").read_text(encoding="utf-8"))["silhouette"])
    with section("Adjacent demand", "T16"):
        print(csv("T16_adjacent_demand_by_region.csv").to_string(index=False))
    with section(f"JobBarometer (AMS yearly ads {v['jobbarometer']})", "JB05/JB03/JB04"):
        jb = csv("JB05_styria_vs_austria.csv"); print(jb[jb.is_data_occupation][["beruf", "austria", "styria", "vienna", "upper_austria", "styria_share", "austria_2020", "growth_2020_to_latest", "styria_2020", "styria_growth_2020_to_latest"]].to_string(index=False))
        L = csv("JB01_yearly_counts_long.csv"); print(L[L.beruf.str.contains("Data Scientist") & L.bl.isin(["AT", "AT22", "AT13", "AT31"])].pivot_table(index="year", columns="bundesland", values="ads").to_string())
        t = csv("JB03_trends.csv"); print(t[t.beruf.str.contains("Data Scientist|Datenbankentwickler|Data-Warehouse|Wirtschaftsinformatik|Systemanaly", regex=True, na=False) & t.bl.isin(["AT", "AT22"])][["beruf", "bundesland", "trend_3y", "share_label", "count_latest"]].to_string(index=False))
        c = csv("JB04_competencies.csv"); print(c[c.beruf.str.contains("Data Scientist")].to_string(index=False))
    with section("Decision matrix", "D01/D02/D04/D04b"):
        print(csv("D01_decision_matrix.csv")[["role_family", "V1_postings_at", "V2_postings_styria", "V3_english_posting_share", "V4_german_required_share", "V5_profile_overlap_top15", "V6_structural_gap_top15", "V7_median_min_salary", "V8_remote_or_hybrid_share", "V9_senior_entry_openness", "V10_degree_required_share", "score_default", "rank_default", "small_sample_flag"]].to_string(index=False)); print(csv("D02_sensitivity.csv").to_string(index=False)); print(csv("D04_learning_priorities.csv")[["skill", "share", "styria_share", "families_where_top(>=15%)", "profile_status", "priority"]].head(45).to_string(index=False))
        if (TAB / "D04b_learn_priority_topics.csv").exists():
            print("-- D04b topic learn-priority"); print(csv("D04b_learn_priority_topics.csv")[["skill", "share", "junior_share", "profile_status", "priority"]].head(40).to_string(index=False))
    if (TAB / "T05f_topic_demand.csv").exists():
        with section("Topic demand (additive slices)", "T05f"):
            print(csv("T05f_topic_demand.csv").to_string(index=False))
    if (TAB / "T17_skill_divergence_intern_vs_junior.csv").exists():
        with section("Intern vs junior skill divergence", "T17"):
            print(csv("T17_skill_divergence_intern_vs_junior.csv").head(25).to_string(index=False))
            print(csv("T17b_german_by_entry_track.csv").to_string(index=False))
            print(csv("T17c_family_mix_by_entry_track.csv").head(40).to_string(index=False))
    if (TAB / "T19_supplement_status.csv").exists():
        with section("Radar/Arbeitnow supplement", "T19"):
            print(csv("T19_supplement_status.csv").to_string(index=False))
            for name in ("T19_supplement_families.csv", "T19_supplement_sources.csv", "T19_supplement_states.csv"):
                if (TAB / name).exists():
                    print(csv(name).to_string(index=False))
            if (TAB / "T19_supplement_skills.csv").exists():
                sk = csv("T19_supplement_skills.csv")
                print(sk.head(25).to_string(index=False) if len(sk) else "(no skill mentions — hunter rows are mostly title-only)")
    with section("Data quality", "Q02/Q03a/Q04/Q05a"):
        print(csv("Q02_coverage_by_source_core.csv").to_string(index=False)); print(csv("Q03a_normalization_confidence.csv").to_string(index=False)); print(csv("Q04_duplicates.csv").to_string(index=False)); print(csv("Q05a_stale.csv").to_string(index=False))
    if (TAB / "S01_seasonal_index.csv").exists():
        with section(f"Seasonality (Eurostat JVS, quarterly {v['eurostat_jvs']})", "S01/S03/S06"):
            s1 = csv("S01_seasonal_index.csv")
            print(s1[s1["sample"] == "full"][["sector", "quarter", "n_years", "index_a_own_year_mean", "ci_low", "ci_high", "index_b_moving_average", "years_above_average"]].to_string(index=False))
            print(csv("S03_sensitivity_samples.csv").to_string(index=False))
            print(csv("S06_season_vs_cycle.csv").to_string(index=False))
            if (TAB / "S05_snapshot_age_distribution.csv").exists():
                print("-- why not from our own snapshot (S05)"); print(csv("S05_snapshot_age_distribution.csv").to_string(index=False))


def supply_digest(v: dict[str, str]):
    """Layer 2 / Layer 3 figures quoted in CAREER_SUPPLY_DEMAND_MAP.md, docs/supply-findings.md, AGENT_CONTEXT.md §22–24."""
    if not (TAB / "C04_role_family_distribution.csv").exists():
        print("\n(no Layer 2 tables)"); MISSING.append("outputs/tables/C04_role_family_distribution.csv  (all Layer 2/3 sections)"); return
    with section(f"Supply coverage & tiers (GitHub collection {v['supply']})", "C01/C01a"):
        print(csv("C01_candidate_source_coverage.csv")[["frame", "accounts", "austrian_location", "data_signal", "bio_declared", "data_signal_share", "share_with_bio"]].to_string(index=False)); print(csv("C01a_data_tier_distribution.csv")[["data_tier", "count", "n", "share"]].to_string(index=False))
    with section("Supply families / titles / concentration", "C04/C04a/C03/C04b"):
        print(csv("C04_role_family_distribution.csv")[["role_family", "count", "n", "share", "ci_low", "ci_high", "styria", "graz_area", "vienna", "students"]].to_string(index=False)); print(csv("C04a_adjacent_bio_families.csv")[["adjacent_family", "count", "n", "share", "of_which_repo_evidenced_T2"]].to_string(index=False)); print(csv("C03_normalized_title_distribution.csv")[["normalized_title", "count", "n", "share", "styria", "vienna"]].to_string(index=False)); print(csv("C04b_title_concentration.csv")[["measure", "raw_bio_titles", "normalized_titles"]].to_string(index=False))
    with section("Supply geography", "C05/C05a/C05c"):
        d = csv("C05_geography_by_state.csv"); print(d[d.population == "P_data"][["state", "count", "n", "share"]].to_string(index=False)); print(csv("C05a_geo_summary.csv").to_string(index=False)); print(csv("C05c_styria_complete_frame.csv").to_string(index=False))
    with section("Supply seniority / status", "C06/C06e"):
        d = csv("C06_seniority_distribution.csv"); print(d[["seniority", "count", "n", "share", "population"]].to_string(index=False)); print(csv("C06e_status_flags.csv").to_string(index=False))
    with section("Supply language presentation", "C07"):
        print(csv("C07_language_presentation.csv")[["population", "signal", "value", "count", "n", "share"]].to_string(index=False))
    with section("Supply education / certifications", "C08/C08b/C09/C09b"):
        print(csv("C08_education_levels.csv")[["education_level", "count", "n", "share", "population"]].to_string(index=False)); print(csv("C08b_education_fields.csv")[["education_field", "count", "n", "share"]].to_string(index=False)); print(csv("C09_certifications.csv")[["certification", "count", "n", "share"]].head(12).to_string(index=False)); print(csv("C09b_certifications_per_candidate.csv")[["certifications_per_candidate", "count", "n", "share"]].to_string(index=False))
    with section("Supply technologies (evidence strength)", "C10"):
        print(csv("C10_technologies_evidence.csv")[["skill", "any_evidence", "mentioned", "used", "demonstrated", "project_demonstrated", "n", "any_evidence_share", "project_demonstrated_share"]].head(40).to_string(index=False))
    with section("Supply capabilities", "C11"):
        print(csv("C11_capabilities_evidence.csv")[["capability", "group", "candidates_any", "candidates_project_demonstrated", "n", "share_any", "share_project_demonstrated"]].to_string(index=False))
    with section("GitHub evidence / medians / archetypes / activity", "C14/C14b/C14c/C14d/C14e"):
        d = csv("C14_github_evidence.csv"); print(d[d.population == "P_data"][["signal", "count", "n", "share"]].to_string(index=False)); print(csv("C14b_github_medians.csv").to_string(index=False)); print(csv("C14c_repository_archetypes.csv").to_string(index=False)); print(csv("C14d_data_repo_activity.csv")[["last_push", "count", "n", "share"]].to_string(index=False)); print(csv("C14e_data_repo_stars.csv")[["stars", "count", "n", "share"]].to_string(index=False))
    with section("Portfolio / cross-platform evidence", "C15"):
        d = csv("C15_portfolio_evidence.csv"); print(d[d.population == "P_data"][["evidence", "count", "n", "share"]].to_string(index=False))
    with section("Project counts", "C16"):
        d = csv("C16_project_count_distribution.csv"); print(d[["population", "variable", "bucket", "count", "n", "share"]].to_string(index=False))
    with section("Project formats", "C17/C17b"):
        d = csv("C17_project_formats.csv"); print(d[d.population == "projects"][["format", "count", "n", "share"]].to_string(index=False)); print(csv("C17b_format_combinations.csv").head(12).to_string(index=False))
    with section("Project topics", "C18/C18c"):
        d = csv("C18_project_topics.csv"); print(d[d.population == "projects"].sort_values("count", ascending=False)[["group", "theme", "count", "n", "share"]].head(35).to_string(index=False)); print(csv("C18c_project_theme_coverage.csv").to_string(index=False))
    with section("README patterns", "C19/C19c/C19e"):
        d = csv("C19_readme_patterns.csv"); print(d[d.population == "documented projects"][["feature", "count", "n", "share"]].to_string(index=False)); print(csv("C19c_readme_structure_summary.csv").to_string(index=False)); print(csv("C19e_common_readme_headings.csv").head(25).to_string(index=False))
    with section("Project technologies / capabilities", "C20/C21"):
        d = csv("C20_project_technologies.csv"); print(d[d.population == "projects"][["skill", "count", "n", "share"]].head(25).to_string(index=False)); print(csv("C21_project_capabilities.csv")[["capability", "projects", "n_projects", "project_share", "substantive_projects", "substantive_share", "candidates_with_substantive_evidence", "candidate_share"]].head(30).to_string(index=False))
    with section("Transitions / marketing bios / clusters", "C22/C22b/C22d/C23"):
        print(csv("C22_transition_signals.csv").iloc[:, :6].to_string(index=False)); print(csv("C22b_prior_domains.csv")[["prior_domain", "count", "n", "share", "population"]].to_string(index=False)); print(csv("C22d_marketing_named_bios.csv").to_string(index=False)); print(csv("C23_positioning_clusters.csv")[["cluster", "size", "share", "share_T1", "styria", "vienna", "students", "median_projects", "defining_features"]].to_string(index=False))
    with section("Marketing × data", "C24/DS12"):
        print(csv("C24_marketing_data_intersection.csv").T.to_string()); print(csv("DS12_marketing_x_data_intersection.csv").T.to_string())
    with section("Demand × supply: families / titles", "DS01/DS02"):
        print(csv("DS01_demand_supply_role_families.csv")[["category", "demand_count", "demand_share", "supply_count", "supply_share", "relative_representation", "candidate_density_T1_per_posting", "demand_styria", "supply_styria_T1", "density_styria", "demand_vienna", "supply_vienna_T1", "quadrant"]].to_string(index=False)); print(csv("DS02_demand_supply_titles.csv")[["category", "demand_count", "supply_count", "supply_share", "relative_representation", "demand_styria", "supply_styria_T1"]].to_string(index=False))
    with section("Demand × supply: skills", "DS03"):
        print(csv("DS03_demand_supply_skills.csv")[["category", "demand_share", "supply_share", "project_share", "difference_pp", "relative_representation", "evidence_gap_pp", "quadrant"]].head(45).to_string(index=False))
    with section("Demand × supply: capabilities", "DS10"):
        print(csv("DS10_demand_supply_capability_evidence.csv")[["category", "group", "demand_share", "supply_any_share", "supply_project_share", "evidence_gap_pp", "quadrant", "interpretation"]].to_string(index=False))
    with section("Demand × supply: geography / language / seniority / education", "DS05/DS05b/DS06/DS06b/DS07/DS08"):
        print(csv("DS05_demand_supply_geography.csv")[["category", "demand_count", "demand_share", "supply_count", "supply_share", "supply_T1", "candidate_density_data_per_posting", "candidate_density_T1_per_posting", "supply_frame"]].to_string(index=False)); print(csv("DS05b_family_by_region_demand_supply.csv").to_string(index=False)); print(csv("DS06_demand_supply_language.csv")[["region", "demand_english_share", "demand_german_req_share", "supply_n", "bio_classified", "bio_en", "bio_de", "readme_classified", "readme_any_de", "readme_en_only"]].to_string(index=False)); print(csv("DS06b_addressable_language_intersection.csv").iloc[:, :9].to_string(index=False)); print(csv("DS07_demand_supply_seniority.csv")[["category", "demand_count", "demand_share", "supply_count", "supply_share", "supply_styria_T1"]].to_string(index=False)); print(csv("DS08_demand_supply_education.csv")[["dimension", "category", "demand_count", "demand_share", "supply_count", "supply_n", "supply_share", "difference_pp"]].to_string(index=False))
    with section("Styria / Graz demand × supply", "DS13"):
        print(csv("DS13_styria_graz_demand_supply.csv").iloc[:, :2].to_string(index=False))
    with section("Supply data quality / precision", "SQ01/SQ02/SQ05/SQ09/SQ10/SQ11"):
        print(csv("SQ01_search_coverage_and_caps.csv").T.to_string()); print(csv("SQ05_staleness.csv").iloc[:, :8].to_string(index=False)); print(csv("SQ09_frame_selection_effects.csv").iloc[:, :8].to_string(index=False)); print(csv("SQ10_bio_classification_precision.csv").iloc[:, :6].to_string(index=False)); print(csv("SQ11_project_classification_precision.csv").iloc[:, :6].to_string(index=False))
    with section("Official / survey supply context", "O01/O02/O03/O04/O07"):
        o = csv("O01_graduates_by_field_level_at.csv"); print(o[o.level.isin(["Bachelor", "Master"])][["field", "level", "latest_year", "graduates_latest", "change_5y_pct"]].to_string(index=False)); print(csv("O02_employment_by_isco_at.csv").iloc[:, [0, 1, -5, -4, -3]].to_string(index=False)); print(csv("O03_ict_specialists_at.csv").tail(4).to_string(index=False)); print(csv("O04_so2025_at_devtype.csv")[["item", "count", "n", "share", "is_data_role"]].head(14).to_string(index=False)); print(csv("O07_so2025_at_experience.csv").to_string(index=False))


def salary_premium_digest():
    """D05: the skill premium that survives controlling for family, seniority and state."""
    path = TAB / "D05_skill_salary_premium.csv"
    if not path.exists():
        print("\n=== Skill salary premium, controlled  [D05] ===")
        print("not computed; run python src/analysis/salary_premium.py (needs the private per-posting file)")
        MISSING.append("outputs/tables/D05_skill_salary_premium.csv  (section: Skill salary premium)")
        return
    with section("Skill salary premium, controlled for family/seniority/state", "D05"):
        d = pd.read_csv(path)
        print(d[["skill", "ads_mentioning", "raw_difference_pct", "adjusted_premium_pct",
                 "ci_low_pct", "ci_high_pct", "clears_zero"]].to_string(index=False))
        print(f"model: {d.model.iloc[0]}")
        print(f"R2 = {d.model_r2.iloc[0]}; controls = {d.controls.iloc[0]}")


def visual_digest():
    """The visual decision layer (D-024): one business question per figure.

    Printed here so the numbers the figures put into the decision documents are
    traceable the same way every other quoted number is. The answer strings are
    computed from the named tables at render time by src/analysis/make_visual_layer.py.
    """
    contract = OUT / "visual_questions.json"
    if not contract.exists():
        print("\n=== Visual decision layer  [outputs/visual_questions.json] ===")
        print("not rendered; run python src/analysis/make_visual_layer.py")
        MISSING.append("outputs/visual_questions.json  (section: Visual decision layer)")
        return
    payload = json.loads(contract.read_text(encoding="utf-8"))
    with section(f"Visual decision layer ({len(payload['figures'])} figures, {payload['data_vintage']})",
                 "outputs/visual_questions.json"):
        for fig in payload["figures"]:
            print(f"\n{fig['chart_id']}  [{fig['mark']} | {fig['relationship']}]  tables: {', '.join(fig['tables'])}")
            print(f"  Q: {fig['question']}")
            print(f"  A: {fig['answer']}")
            print(f"  seal: {fig['svg_sha256']}")


def render() -> str:
    """The whole digest as text (nothing is written); fills MISSING and ERRORS."""
    MISSING.clear(); ERRORS.clear()
    v = vintages()
    buf = io.StringIO()
    with redirect_stdout(buf):
        print("Digest of the numbers quoted in the decision documents (src/reporting/digest.py; tables in outputs/tables/)")
        print(f"Vintages: demand snapshot {v['demand']} · supply collection {v['supply']} · "
              f"Eurostat JVS {v['eurostat_jvs']} · AMS JobBarometer {v['jobbarometer']}")
        layer1_digest(v)
        supply_digest(v)
        salary_premium_digest()
        visual_digest()
        sec("Completeness of this digest", "missing inputs / failed sections")
        if not MISSING and not ERRORS:
            print("all inputs present; every section complete")
        for m in MISSING:
            print(f"MISSING  {m}")
        for e in ERRORS:
            print(f"FAILED   {e}")
    return buf.getvalue()


def write_atomic(text: str, target: Path) -> None:
    """UTF-8 with LF line endings; written to a temporary file next to the target, then moved into place."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, target)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write the digest of quoted numbers to outputs/reports/digest.txt")
    ap.add_argument("--out", type=Path, default=DEFAULT_TARGET, help="target file (default: outputs/reports/digest.txt)")
    ap.add_argument("--stdout", action="store_true", help="also print the digest")
    ap.add_argument("--strict", action="store_true", help="exit code 1 when an input table is missing")
    a = ap.parse_args(argv)
    text = render()
    write_atomic(text, a.out)
    if a.stdout:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text)
    print(f"digest written: {_rel(a.out)} ({len(text.splitlines())} lines)", file=sys.stderr)
    for m in MISSING:
        print(f"digest: MISSING input {m}", file=sys.stderr)
    for e in ERRORS:
        print(f"digest: FAILED section {e}", file=sys.stderr)
    if ERRORS or (a.strict and MISSING):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
