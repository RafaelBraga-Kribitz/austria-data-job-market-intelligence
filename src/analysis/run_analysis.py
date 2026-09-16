"""Step 4: descriptive analysis -> outputs/tables/*.csv and outputs/*.json

All statistics are computed on the ANALYSIS SET:
    canonical rows (is_canonical) whose role_family is in CORE_FAMILIES.
Adjacent families (ai_software_engineering, other_data) are reported separately.
Every table carries its denominator (n) so that percentages are auditable.
Wilson 95% confidence intervals are attached to key proportions.
"""
from __future__ import annotations

import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
OUT = ROOT / "outputs"
TAB.mkdir(parents=True, exist_ok=True)

CORE_FAMILIES = ["data_analytics", "bi", "data_science", "data_engineering", "data_governance", "marketing_analytics", "product_analytics", "business_analysis"]
ADJACENT = ["ai_software_engineering", "other_data"]
SKILL_CATS = ["programming_languages", "bi_tools", "cloud_platforms", "data_platforms", "python_ecosystem", "data_engineering", "ml_ai", "statistics_methods", "business_domain", "soft_skills", "certifications", "work_model"]
AGENCY_RE = r"personal|recruit|staffing|hays\b|randstad|adecco|manpower|trenkwalder|epunkt|iventa|dis ag|robert half|michael page|page personnel|otti|jobs?\.at|karriere|talent|headhunt|consultants?\b.*(?:personal|hr)|hr consult|personalberat|arbeitskräfte|zeitarbeit|powerserv|hofmann personal|teamwork|jobmarkt|jobfinder|hill international|schulmeister|catro|dr\. pendl|stepstone|apex|xpertum|isg\b|leitner personal|hrm\b|hokify|worktoday|jobmatch|talentor|manpowergroup|experis|brunel|akkodis|modis|iro&partners"


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0, c - h), 3), round(min(1, c + h), 3))


def share_table(df: pd.DataFrame, col: str, name: str, groupcol: str | None = None, min_n: int = 1) -> pd.DataFrame:
    """Share of rows per category of `col` (list or scalar), optionally by group."""
    rows = []
    groups = [(None, df)] if groupcol is None else list(df.groupby(groupcol))
    for g, sub in groups:
        n = len(sub)
        if n < min_n:
            continue
        s = sub[col]
        if s.apply(lambda x: isinstance(x, list)).any():
            expl = s.explode().dropna()
        else:
            expl = s.dropna()
        for k, v in expl.value_counts().items():
            lo, hi = wilson(int(v), n)
            rows.append({**({groupcol: g} if groupcol else {}), name: k, "count": int(v), "n": n, "share": round(v / n, 3), "ci_low": lo, "ci_high": hi})
    return pd.DataFrame(rows)


def main():
    df = pd.read_json(PROC / "postings_dedup.jsonl", lines=True)
    for c in ["posted_date", "collected_at"]:
        df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
    df["is_agency"] = df["company"].fillna("").str.lower().str.contains(AGENCY_RE, regex=True)
    core = df[(df.is_canonical) & (df.role_family.isin(CORE_FAMILIES))].copy()
    adj = df[(df.is_canonical) & (df.role_family.isin(ADJACENT))].copy()
    allc = df[df.is_canonical & df.role_family.isin(CORE_FAMILIES + ADJACENT)].copy()
    core["geo_scope"] = np.select([core.is_graz_area, core.is_styria, core.is_vienna], ["Graz area", "Styria (other)", "Vienna"], default="Other Austria / unspecified")
    core["styria_flag"] = np.where(core.is_styria, "Styria", "Rest of Austria")
    core["has_desc"] = core.description_length > 300
    desc = core[core.has_desc].copy()  # denominator for text-derived features

    # ---------------- T01 source coverage
    t = df.groupby("source").agg(rows=("posting_uid", "count"), in_scope_rows=("role_family", lambda s: s.isin(CORE_FAMILIES).sum()),
                                 adjacent_rows=("role_family", lambda s: s.isin(ADJACENT).sum()),
                                 with_description=("description_length", lambda s: (s > 300).sum()),
                                 first_posted=("posted_date", "min"), last_posted=("posted_date", "max"),
                                 collected_from=("collected_at", "min"), collected_to=("collected_at", "max"))
    t["in_scope_canonical"] = core.groupby("source").size()
    t.reset_index().to_csv(TAB / "T01_source_coverage.csv", index=False)
    # source overlap among in-scope groups
    ov = df[df.role_family.isin(CORE_FAMILIES)].groupby("dedupe_group_id")["source"].apply(lambda s: ",".join(sorted(set(s)))).value_counts().reset_index()
    ov.columns = ["sources_in_group", "groups"]
    ov.to_csv(TAB / "T01b_source_overlap_in_scope.csv", index=False)

    # ---------------- T02 role families / titles
    fam = core.role_family.value_counts().reset_index(); fam.columns = ["role_family", "count"]; fam["n"] = len(core); fam["share"] = (fam["count"] / len(core)).round(3)
    fam["styria_count"] = fam.role_family.map(core[core.is_styria].role_family.value_counts()).fillna(0).astype(int)
    fam["graz_area_count"] = fam.role_family.map(core[core.is_graz_area].role_family.value_counts()).fillna(0).astype(int)
    fam["vienna_count"] = fam.role_family.map(core[core.is_vienna].role_family.value_counts()).fillna(0).astype(int)
    fam.to_csv(TAB / "T02_role_family_counts.csv", index=False)
    adjc = adj.role_family.value_counts().reset_index(); adjc.columns = ["role_family", "count"]; adjc.to_csv(TAB / "T02a_adjacent_family_counts.csv", index=False)
    nt = core.groupby(["role_family", "normalized_title"]).size().reset_index(name="count").sort_values("count", ascending=False)
    nt["styria"] = [len(core[(core.normalized_title == r.normalized_title) & core.is_styria]) for r in nt.itertuples()]
    nt.to_csv(TAB / "T02b_normalized_title_counts.csv", index=False)
    rt = core.groupby(["title_clean", "role_family"]).size().reset_index(name="count").sort_values("count", ascending=False).head(150)
    rt.to_csv(TAB / "T02c_top_raw_titles.csv", index=False)
    # ESCO occupation codes attached by AMS (EURES rows only)
    es = core[core.source == "eures"].esco_occupation_uris.explode().dropna().value_counts().head(40).reset_index(); es.columns = ["esco_uri", "count"]
    es.to_csv(TAB / "T02d_esco_occupations_eures.csv", index=False)

    # ---------------- T03 geography
    g = pd.crosstab(core.role_family, core.state.fillna("unspecified"), margins=True)
    g.to_csv(TAB / "T03_family_by_state.csv")
    gs = core.state.fillna("unspecified").value_counts().reset_index(); gs.columns = ["state", "count"]; gs["n"] = len(core); gs["share"] = (gs["count"] / len(core)).round(3)
    gs.to_csv(TAB / "T03a_state_counts.csv", index=False)
    geo = core.geo_scope.value_counts().reset_index(); geo.columns = ["geo_scope", "count"]; geo["share"] = (geo["count"] / len(core)).round(3)
    geo.to_csv(TAB / "T03b_geo_scope.csv", index=False)
    sty = core[core.is_styria]
    cs = sty.city.fillna("unspecified").value_counts().reset_index(); cs.columns = ["city", "count"]; cs.to_csv(TAB / "T03c_styria_cities.csv", index=False)
    pd.DataFrame({"metric": ["core_postings", "styria", "graz_area", "graz_city", "vienna", "austria_wide_flag", "multi_location", "location_unspecified"],
                  "count": [len(core), int(core.is_styria.sum()), int(core.is_graz_area.sum()), int(core.is_graz_city.sum()), int(core.is_vienna.sum()), int(core.is_austria_wide.sum()), int(core.multi_location.sum()), int(core.state.isna().sum())]}).to_csv(TAB / "T03d_geo_summary.csv", index=False)
    # state by source (platform geographic bias)
    pd.crosstab(core.source, core.state.fillna("unspecified")).to_csv(TAB / "T03e_state_by_source.csv")

    # ---------------- T04 employers
    emp = core[core.company_norm.notna()]
    e = emp.groupby("company_norm").agg(postings=("posting_uid", "count"), families=("role_family", lambda s: ",".join(sorted(set(s)))),
                                       states=("state", lambda s: ",".join(sorted(set(x for x in s if isinstance(x, str))))),
                                       styria=("is_styria", "sum"), graz_area=("is_graz_area", "sum"), is_agency=("is_agency", "max"),
                                       sources=("source", lambda s: ",".join(sorted(set(s)))), example_company=("company", "first")).sort_values("postings", ascending=False)
    e.reset_index().to_csv(TAB / "T04_employers.csv", index=False)
    e[e.styria > 0].sort_values("styria", ascending=False).reset_index().to_csv(TAB / "T04a_employers_styria.csv", index=False)
    top10 = e.postings.head(10).sum(); top25 = e.postings.head(25).sum()
    pd.DataFrame({"metric": ["core_postings_total", "postings_with_named_employer", "postings_without_named_employer", "unique_named_employers_austria", "unique_named_employers_styria", "unique_named_employers_graz_area",
                             "top10_share_of_named", "top25_share_of_named", "agency_share_of_named_postings", "eures_anonymised_employer_rows", "styria_postings_without_named_employer"],
                  "value": [len(core), len(emp), len(core) - len(emp), e.shape[0], int((e.styria > 0).sum()), int((e.graz_area > 0).sum()), round(top10 / len(emp), 3), round(top25 / len(emp), 3), round(emp.is_agency.mean(), 3),
                            int(core[(core.source == "eures") & core.company_norm.isna()].shape[0]), int(core[core.is_styria & core.company_norm.isna()].shape[0])]}).to_csv(TAB / "T04b_employer_concentration.csv", index=False)
    pd.crosstab(core.source, core.industry_raw.fillna("unspecified")).T.sort_values("linkedin", ascending=False).head(40).to_csv(TAB / "T04c_linkedin_industry_raw.csv")

    # ---------------- T05 skills
    for cat in SKILL_CATS:
        col = f"skills_{cat}"
        share_table(desc, col, "skill").sort_values("count", ascending=False).to_csv(TAB / f"T05_skills_{cat}.csv", index=False)
        share_table(desc, col, "skill", "role_family").to_csv(TAB / f"T05_skills_{cat}_by_family.csv", index=False)
        share_table(desc, col, "skill", "styria_flag").to_csv(TAB / f"T05_skills_{cat}_by_styria.csv", index=False)
    # all tech skills in one long table
    tech = ["programming_languages", "bi_tools", "cloud_platforms", "data_platforms", "python_ecosystem", "data_engineering", "ml_ai", "statistics_methods"]
    desc["skills_all_tech"] = desc[[f"skills_{c}" for c in tech]].apply(lambda r: sorted({x for l in r for x in (l if isinstance(l, list) else [])}), axis=1)
    st = share_table(desc, "skills_all_tech", "skill").sort_values("count", ascending=False)
    st.to_csv(TAB / "T05_skills_all_tech.csv", index=False)
    share_table(desc, "skills_all_tech", "skill", "role_family").to_csv(TAB / "T05_skills_all_tech_by_family.csv", index=False)
    share_table(desc, "skills_all_tech", "skill", "styria_flag").to_csv(TAB / "T05_skills_all_tech_by_styria.csv", index=False)
    share_table(desc, "skills_all_tech", "skill", "seniority").to_csv(TAB / "T05_skills_all_tech_by_seniority.csv", index=False)

    # ---------------- T06 co-occurrence
    top = [s for s in st.skill.head(30) if s not in ("Cloud (generic)", "AI (generic)", "Statistics (general)", "Data Visualization", "Machine Learning")]
    top = st.skill.head(30).tolist()
    rows = []
    sets = desc.skills_all_tech.apply(set)
    n = len(desc)
    for a, b in combinations(top, 2):
        both = int(sets.apply(lambda s: a in s and b in s).sum())
        na = int(sets.apply(lambda s: a in s).sum()); nb = int(sets.apply(lambda s: b in s).sum())
        if both == 0:
            continue
        rows.append({"skill_a": a, "skill_b": b, "both": both, "n": n, "share_of_postings": round(both / n, 3),
                     "p_b_given_a": round(both / na, 3), "p_a_given_b": round(both / nb, 3), "jaccard": round(both / (na + nb - both), 3),
                     "lift": round((both / n) / ((na / n) * (nb / n)), 2)})
    pd.DataFrame(rows).sort_values("both", ascending=False).to_csv(TAB / "T06_cooccurrence_pairs.csv", index=False)
    # recurring stacks: most frequent skill-set combinations of size 3 among top 15
    top15 = st.skill.head(15).tolist()
    combos = {}
    for s in sets:
        s2 = sorted(s & set(top15))
        for c in combinations(s2, 3):
            combos[c] = combos.get(c, 0) + 1
    pd.DataFrame([{"stack": " + ".join(k), "count": v, "n": n, "share": round(v / n, 3)} for k, v in combos.items()]).sort_values("count", ascending=False).head(40).to_csv(TAB / "T06b_top_stacks_size3.csv", index=False)

    # ---------------- T07 languages
    lang_base = desc
    for grp in [None, "role_family", "styria_flag", "state", "source", "seniority", "posting_language", "remote_type"]:
        name = "overall" if grp is None else grp
        share_table(lang_base, "german_requirement", "german_requirement", grp).to_csv(TAB / f"T07_german_requirement_by_{name}.csv", index=False)
    share_table(lang_base, "german_level_bucket", "german_level_bucket").to_csv(TAB / "T07a_german_level_overall.csv", index=False)
    share_table(lang_base, "german_level_bucket", "german_level_bucket", "role_family").to_csv(TAB / "T07a_german_level_by_family.csv", index=False)
    share_table(lang_base, "english_requirement", "english_requirement").to_csv(TAB / "T07b_english_requirement.csv", index=False)
    share_table(lang_base, "english_level_bucket", "english_level_bucket").to_csv(TAB / "T07b_english_level.csv", index=False)
    share_table(lang_base, "posting_language", "posting_language").to_csv(TAB / "T07c_posting_language.csv", index=False)
    share_table(lang_base, "posting_language", "posting_language", "role_family").to_csv(TAB / "T07c_posting_language_by_family.csv", index=False)
    share_table(lang_base, "posting_language", "posting_language", "styria_flag").to_csv(TAB / "T07c_posting_language_by_styria.csv", index=False)
    pd.crosstab(lang_base.posting_language, lang_base.german_requirement).to_csv(TAB / "T07d_posting_language_x_german_req.csv")
    # addressable-market scenarios (documented assumptions)
    def addressable(sub):
        n = len(sub)
        eng_only = sub[(sub.posting_language == "en") & (~sub.german_requirement.isin(["required", "required_implied", "german_or_english"]))]
        no_german_barrier = sub[~sub.german_requirement.isin(["required", "required_implied"])]
        b2_ok = sub[~((sub.german_requirement.isin(["required", "required_implied"])) & (sub.german_level_bucket.isin(["C1/fluent", "C2/native"])))]
        return {"n": n, "english_posting_no_german_req": len(eng_only), "no_explicit_german_requirement": len(no_german_barrier), "german_not_required_at_C1_or_above": len(b2_ok)}
    rows = []
    for name, sub in [("Austria", lang_base), ("Styria", lang_base[lang_base.is_styria]), ("Graz area", lang_base[lang_base.is_graz_area]), ("Vienna", lang_base[lang_base.is_vienna])]:
        rows.append({"scope": name, **addressable(sub)})
    for famname, sub in lang_base.groupby("role_family"):
        rows.append({"scope": f"family:{famname}", **addressable(sub)})
    pd.DataFrame(rows).to_csv(TAB / "T07e_addressable_market_scenarios.csv", index=False)

    # ---------------- T08 seniority & experience
    share_table(core, "seniority", "seniority").to_csv(TAB / "T08_seniority_overall.csv", index=False)
    share_table(core, "seniority", "seniority", "role_family").to_csv(TAB / "T08_seniority_by_family.csv", index=False)
    share_table(core, "seniority", "seniority", "styria_flag").to_csv(TAB / "T08_seniority_by_styria.csv", index=False)
    ex = desc[desc.experience_min_years.notna()]
    exs = ex.groupby("seniority").experience_min_years.describe()[["count", "mean", "25%", "50%", "75%"]].round(1).reset_index()
    exs.to_csv(TAB / "T08a_experience_years_by_seniority.csv", index=False)
    ex.groupby("role_family").experience_min_years.describe()[["count", "mean", "25%", "50%", "75%"]].round(1).reset_index().to_csv(TAB / "T08b_experience_years_by_family.csv", index=False)
    pd.DataFrame({"metric": ["with_description", "explicit_years_stated", "multi_year_phrase", "entry_level_phrase"],
                  "count": [len(desc), len(ex), int(desc.experience_multi_year_phrase.sum()), int(desc.experience_entry_level_phrase.sum())]}).to_csv(TAB / "T08c_experience_coverage.csv", index=False)
    pd.crosstab(desc.seniority, pd.cut(desc.experience_min_years, [-1, 0, 1, 2, 3, 5, 8, 30], labels=["0", "1", "2", "3", "4-5", "6-8", "9+"])).to_csv(TAB / "T08d_seniority_x_years.csv")

    # ---------------- T09 salary
    sal = core[core.salary_min_annual_eur.notna()].copy()
    cov = pd.DataFrame({"metric": ["core_postings", "with_salary_figure", "with_range", "kv_minimum_mention", "overpay_mention", "structured_source", "text_parsed",
                                   "all_in_mention", "bonus_or_variable_mention", "part_time_basis_risk_among_figures", "minimum_only_figures"],
                        "count": [len(core), len(sal), int((sal.salary_basis == "range").sum()), int(core.salary_kv_mention.sum()), int(core.salary_overpay_mention.sum()), int((sal.salary_source == "structured").sum()), int((sal.salary_source == "text").sum()),
                                  int(core.salary_all_in_mention.sum()), int(core.salary_bonus_mention.sum()), int(sal.salary_part_time_basis_risk.sum()), int((sal.salary_basis == "minimum_only").sum())]})
    cov.to_csv(TAB / "T09_salary_coverage.csv", index=False)
    pd.crosstab(core.source, core.salary_basis).to_csv(TAB / "T09a_salary_basis_by_source.csv")
    def sal_stats(g):
        return pd.Series({"n": len(g), "min_p25": g.salary_min_annual_eur.quantile(.25), "min_median": g.salary_min_annual_eur.median(), "min_p75": g.salary_min_annual_eur.quantile(.75),
                          "max_median": g.salary_max_annual_eur.median(), "n_with_max": g.salary_max_annual_eur.notna().sum(), "mean_min": g.salary_min_annual_eur.mean()})
    for grp in ["role_family", "seniority", "state", "styria_flag", "source", "normalized_title", "posting_language", "remote_type"]:
        sal.groupby(grp).apply(sal_stats).round(0).reset_index().to_csv(TAB / f"T09b_salary_by_{grp}.csv", index=False)
    sal.groupby(["role_family", "seniority"]).apply(sal_stats).round(0).reset_index().to_csv(TAB / "T09c_salary_by_family_seniority.csv", index=False)
    # salary by skill (top tech skills)
    rows = []
    sal_d = sal[sal.has_desc]
    for sk in st.skill.head(20):
        sub = sal_d[sal_d.skills_all_tech.apply(lambda l: sk in (l or []))] if "skills_all_tech" in sal_d else sal_d.iloc[0:0]
    sal_d = sal_d.merge(desc[["posting_uid", "skills_all_tech"]], on="posting_uid", how="left")
    for sk in st.skill.head(25):
        sub = sal_d[sal_d.skills_all_tech.apply(lambda l: isinstance(l, list) and sk in l)]
        if len(sub) >= 5:
            rows.append({"skill": sk, "n": len(sub), "min_median": sub.salary_min_annual_eur.median(), "min_p25": sub.salary_min_annual_eur.quantile(.25), "min_p75": sub.salary_min_annual_eur.quantile(.75)})
    pd.DataFrame(rows).round(0).to_csv(TAB / "T09d_salary_by_skill.csv", index=False)
    sal[["posting_uid", "source", "role_family", "normalized_title", "seniority", "state", "company", "salary_min_annual_eur", "salary_max_annual_eur", "salary_period", "salary_source", "salary_basis", "salary_kv_mention", "salary_overpay_mention", "salary_snippet", "source_url"]].to_csv(TAB / "T09e_salary_observations.csv", index=False)

    # ---------------- T10 remote
    share_table(desc, "remote_type", "remote_type").to_csv(TAB / "T10_remote_overall.csv", index=False)
    share_table(desc, "remote_type", "remote_type", "role_family").to_csv(TAB / "T10_remote_by_family.csv", index=False)
    share_table(desc, "remote_type", "remote_type", "styria_flag").to_csv(TAB / "T10_remote_by_styria.csv", index=False)
    share_table(desc, "remote_type", "remote_type", "source").to_csv(TAB / "T10_remote_by_source.csv", index=False)
    desc.home_office_days_per_week.value_counts().reset_index().to_csv(TAB / "T10a_home_office_days.csv", index=False)
    pd.DataFrame({"metric": ["with_description", "remote_austria_restricted_phrase"], "count": [len(desc), int(desc.remote_austria_restricted.sum())]}).to_csv(TAB / "T10b_remote_restrictions.csv", index=False)

    # ---------------- T11 education & certifications
    pd.DataFrame({"metric": ["with_description", "degree_required_phrase", "degree_or_equivalent_phrase", "any_degree_level_mention", "phd_mention", "master_mention", "bachelor_mention", "htl_matura_mention", "any_certification_mention"],
                  "count": [len(desc), int(desc.degree_required.sum()), int(desc.degree_or_equivalent.sum()), int(desc.degree_levels.apply(lambda l: len(l) > 0).sum()),
                            int(desc.degree_levels.apply(lambda l: "PhD" in l).sum()), int(desc.degree_levels.apply(lambda l: "Master" in l).sum()), int(desc.degree_levels.apply(lambda l: "Bachelor" in l).sum()), int(desc.degree_levels.apply(lambda l: "HTL/Matura" in l).sum()),
                            int(desc.skills_certifications.apply(lambda l: len(l) > 0).sum())]}).to_csv(TAB / "T11_education_summary.csv", index=False)
    share_table(desc, "degree_levels", "degree_level").to_csv(TAB / "T11a_degree_levels.csv", index=False)
    share_table(desc, "degree_levels", "degree_level", "role_family").to_csv(TAB / "T11a_degree_levels_by_family.csv", index=False)
    share_table(desc, "degree_fields", "degree_field").to_csv(TAB / "T11b_degree_fields.csv", index=False)
    share_table(desc, "degree_fields", "degree_field", "role_family").to_csv(TAB / "T11b_degree_fields_by_family.csv", index=False)
    share_table(desc, "degree_required", "degree_required", "role_family").to_csv(TAB / "T11c_degree_required_by_family.csv", index=False)
    # D-012: 4-way strength of the degree wording (required / preferred / mentioned / none)
    share_table(desc, "degree_requirement", "degree_requirement").to_csv(TAB / "T11e_degree_requirement_strength.csv", index=False)
    share_table(desc, "degree_requirement", "degree_requirement", "role_family").to_csv(TAB / "T11e_degree_requirement_strength_by_family.csv", index=False)
    share_table(desc, "skills_certifications", "certification").to_csv(TAB / "T11d_certifications.csv", index=False)
    share_table(desc, "skills_certifications", "certification", "role_family").to_csv(TAB / "T11d_certifications_by_family.csv", index=False)

    # ---------------- T12 employment
    share_table(core, "employment_type", "employment_type").to_csv(TAB / "T12_employment_type.csv", index=False)
    share_table(core, "employment_type", "employment_type", "role_family").to_csv(TAB / "T12_employment_type_by_family.csv", index=False)
    pd.DataFrame({"metric": ["core_postings", "internship_or_student", "temporary_or_contract", "academic_title"], "count": [len(core), int(core.is_internship_student.sum()), int(core.is_temporary_or_contract.sum()), int(core.is_academic.sum())]}).to_csv(TAB / "T12a_flags.csv", index=False)

    # ---------------- T13 temporal (snapshot)
    core["posted_week"] = core.posted_date.dt.to_period("W").astype(str)
    core.groupby(["posted_week"]).size().reset_index(name="count").to_csv(TAB / "T13_posted_by_week.csv", index=False)
    core.groupby(["source", core.posted_date.dt.to_period("M").astype(str)]).size().reset_index(name="count").to_csv(TAB / "T13a_posted_by_month_source.csv", index=False)
    age = (core.collected_at - core.posted_date).dt.days
    core.assign(age_days=age).groupby("source").age_days.describe()[["count", "mean", "25%", "50%", "75%", "max"]].round(0).reset_index().to_csv(TAB / "T13b_posting_age_by_source.csv", index=False)

    # ---------------- T14 family profiles (top skills per family)
    prof = []
    for famname, sub in desc.groupby("role_family"):
        n_f = len(sub)
        vc = sub.skills_all_tech.explode().dropna().value_counts().head(15)
        prof.append({"role_family": famname, "n_with_description": n_f, "top_tech_skills": "; ".join(f"{k} ({v / n_f:.0%})" for k, v in vc.items()),
                     "top_business": "; ".join(f"{k} ({v / n_f:.0%})" for k, v in sub.skills_business_domain.explode().dropna().value_counts().head(8).items()),
                     "top_soft": "; ".join(f"{k} ({v / n_f:.0%})" for k, v in sub.skills_soft_skills.explode().dropna().value_counts().head(6).items()),
                     "german_required_share": round(sub.german_requirement.isin(["required", "required_implied"]).mean(), 2),
                     "english_posting_share": round((sub.posting_language == "en").mean(), 2),
                     "degree_required_share": round(sub.degree_required.mean(), 2),
                     "median_min_salary": sub.salary_min_annual_eur.median(), "n_salary": int(sub.salary_min_annual_eur.notna().sum()),
                     "styria_share": round(sub.is_styria.mean(), 2), "senior_or_lead_share": round(sub.seniority.isin(["senior", "lead_head"]).mean(), 2)})
    pd.DataFrame(prof).to_csv(TAB / "T14_family_profiles.csv", index=False)

    # ---------------- machine-readable summary
    summary = {
        "generated_from": "data/processed/postings_dedup.jsonl", "analysis_set_definition": "canonical rows with role_family in CORE_FAMILIES",
        "core_families": CORE_FAMILIES, "adjacent_families": ADJACENT,
        "counts": {"raw_rows_all_sources": int(len(df)), "canonical_groups_all": int(df.is_canonical.sum()), "core_canonical": int(len(core)), "core_with_description": int(len(desc)),
                   "adjacent_canonical": int(len(adj)), "styria_core": int(core.is_styria.sum()), "graz_area_core": int(core.is_graz_area.sum()), "vienna_core": int(core.is_vienna.sum()),
                   "unique_employers_core": int(e.shape[0]), "unique_employers_styria": int((e.styria > 0).sum())},
        "posted_date_range": {"min": str(core.posted_date.min().date()) if core.posted_date.notna().any() else None, "max": str(core.posted_date.max().date()) if core.posted_date.notna().any() else None},
        "collected_at_range": {"min": str(df.collected_at.min()), "max": str(df.collected_at.max())},
        "sources": t.reset_index().astype(str).to_dict(orient="records"),
    }
    json.dump(summary, open(OUT / "market_summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
    print(json.dumps(summary["counts"], indent=1))
    print("tables written:", len(list(TAB.glob("T*.csv"))))


if __name__ == "__main__":
    main()
