"""Data-quality metrics -> outputs/tables/Q*.csv and outputs/data_quality.json

Q01 missingness per field per source (all rows and core rows)
Q02 coverage: description, salary, language, location, date, by source
Q03 title normalization confidence: share per family/source; other_data + no-rule shares; sample audit file
Q04 duplicate/overlap: group sizes, cross-source overlap, within-source repost signals (same company+title, different ids)
Q05 stale postings: age distribution per source; evergreen (>180 days)
Q06 inaccessible postings: detail fetch status != 200
Q07 salary format audit: period detection source, implausible count, snippets sample
Q08 remote ambiguity: share unknown/hybrid_or_flexible
Q09 skill extraction spot-check sample (for manual audit)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
OUT = ROOT / "outputs"
CORE = ["data_analytics", "bi", "data_science", "data_engineering", "data_governance", "marketing_analytics", "product_analytics", "business_analysis"]
FIELDS = ["title", "company", "location_text", "state", "city", "posted_date", "description_text", "employment_type_raw", "salary_min_annual_eur", "german_requirement", "seniority", "remote_type", "industry_raw"]


def main():
    df = pd.read_json(PROC / "postings_dedup.jsonl", lines=True)
    df["posted_date"] = pd.to_datetime(df.posted_date, errors="coerce", utc=True)
    df["collected_at"] = pd.to_datetime(df.collected_at, errors="coerce", utc=True)
    core = df[df.role_family.isin(CORE)]
    # Q01 missingness
    rows = []
    for name, sub in [("all", df), ("core", core)]:
        for src, g in sub.groupby("source"):
            for f in FIELDS:
                s = g[f]
                miss = s.isna() | (s.astype(str).str.strip().isin(["", "unknown", "unspecified", "not_mentioned", "none", "None"]))
                rows.append({"set": name, "source": src, "field": f, "n": len(g), "missing": int(miss.sum()), "missing_share": round(miss.mean(), 3)})
    pd.DataFrame(rows).to_csv(TAB / "Q01_missingness.csv", index=False)
    # Q02 coverage by source (core)
    cov = core.groupby("source").agg(n=("posting_uid", "count"), description_gt300=("description_length", lambda s: (s > 300).mean()),
                                     salary_figure=("salary_min_annual_eur", lambda s: s.notna().mean()), salary_range=("salary_basis", lambda s: (s == "range").mean()),
                                     german_mentioned=("german_requirement", lambda s: (s != "not_mentioned").mean()), state_known=("state", lambda s: s.notna().mean()),
                                     city_known=("city", lambda s: s.notna().mean()), date_known=("posted_date", lambda s: s.notna().mean()),
                                     seniority_in_title=("seniority", lambda s: (s != "unspecified").mean()), remote_known=("remote_type", lambda s: (s != "unknown").mean())).round(3)
    cov.reset_index().to_csv(TAB / "Q02_coverage_by_source_core.csv", index=False)
    # Q03 normalization confidence
    can = df[df.is_canonical]
    q3 = pd.crosstab(can.source, can.role_family)
    q3.to_csv(TAB / "Q03_family_by_source_canonical.csv")
    conf = pd.DataFrame({"metric": ["canonical_rows", "core", "other_data (data-ish but unmatched)", "ai_software_engineering", "out_of_scope", "out_of_scope_no_rule", "out_of_scope_soft_override", "out_of_scope_hard_override", "location_confidence_high_core", "location_confidence_none_core", "seniority_unspecified_core"],
                         "count": [len(can), int(can.role_family.isin(CORE).sum()), int((can.role_family == "other_data").sum()), int((can.role_family == "ai_software_engineering").sum()), int((can.role_family == "out_of_scope").sum()),
                                   int(((can.role_family == "out_of_scope") & (can.role_oos_reason == "no_rule_matched")).sum()), int(((can.role_family == "out_of_scope") & (can.role_oos_reason != "no_rule_matched") & can.role_family_prelim.notna()).sum()),
                                   int(((can.role_family == "out_of_scope") & can.role_oos_reason.astype(str).str.contains("cent|entry|erfass|eingabe|typist", regex=True)).sum()),
                                   int((can[can.role_family.isin(CORE)].location_confidence == "high").sum()), int((can[can.role_family.isin(CORE)].location_confidence == "none").sum()), int((can[can.role_family.isin(CORE)].seniority == "unspecified").sum())]})
    conf.to_csv(TAB / "Q03a_normalization_confidence.csv", index=False)
    rng = np.random.default_rng(7)
    aud = []
    for famname in CORE + ["other_data", "ai_software_engineering"]:
        sub = can[can.role_family == famname]
        aud.append(sub.sample(min(15, len(sub)), random_state=7)[["posting_uid", "title", "title_clean", "role_family", "normalized_title", "role_rule", "source"]])
    oos = can[(can.role_family == "out_of_scope") & can.title_clean.str.contains("data|daten|analy|\\bbi\\b|intelligence|\\bki\\b|\\bai\\b", regex=True, na=False)]
    aud.append(oos.sample(min(40, len(oos)), random_state=7)[["posting_uid", "title", "title_clean", "role_family", "normalized_title", "role_rule", "source"]].assign(role_rule=oos.role_oos_reason))
    pd.concat(aud).to_csv(TAB / "Q03b_title_audit_sample.csv", index=False)
    # Q04 duplicates
    g = df.groupby("dedupe_group_id").agg(size=("posting_uid", "count"), sources=("source", lambda s: ",".join(sorted(set(s)))), in_scope=("role_family", lambda s: s.isin(CORE).any()))
    q4 = pd.DataFrame({"metric": ["groups_all", "groups_size>1", "rows_in_multi_groups", "core_groups", "core_groups_size>1", "core_rows", "core_duplicate_rate", "cross_source_groups_core"],
                       "value": [len(g), int((g["size"] > 1).sum()), int(g[g["size"] > 1]["size"].sum()), int(g.in_scope.sum()), int(((g["size"] > 1) & g.in_scope).sum()), int(len(core)), round(1 - g.in_scope.sum() / max(len(core), 1), 3), int((g.in_scope & g.sources.str.contains(",")).sum())]})
    q4.to_csv(TAB / "Q04_duplicates.csv", index=False)
    # within-source repost signal: same company_norm + title_clean, different source_id (already grouped, but count)
    rep = core.groupby(["source", "company_norm", "title_clean"]).source_id.nunique()
    pd.DataFrame({"metric": ["core_company_title_pairs", "pairs_with_multiple_ids_same_source"], "value": [len(rep), int((rep > 1).sum())]}).to_csv(TAB / "Q04a_reposts.csv", index=False)
    # Q05 stale postings
    core2 = core.assign(age_days=(core.collected_at - core.posted_date).dt.days)
    core2.groupby("source").age_days.describe()[["count", "mean", "25%", "50%", "75%", "max"]].round(0).reset_index().to_csv(TAB / "Q05_posting_age_by_source.csv", index=False)
    pd.DataFrame({"metric": ["core_with_date", "older_than_60d", "older_than_180d", "older_than_365d"], "count": [int(core2.age_days.notna().sum()), int((core2.age_days > 60).sum()), int((core2.age_days > 180).sum()), int((core2.age_days > 365).sum())]}).to_csv(TAB / "Q05a_stale.csv", index=False)
    # Q06 inaccessible
    if "detail_status" in df:
        q6 = df.groupby("source").detail_status.value_counts(dropna=False).reset_index(name="count")
        q6.to_csv(TAB / "Q06_detail_fetch_status.csv", index=False)
    # Q07 salary audit
    s = core[core.salary_min_annual_eur.notna() | (core.salary_basis == "implausible")]
    pd.crosstab(s.source, [s.salary_source.fillna("none"), s.salary_period.fillna("none")]).to_csv(TAB / "Q07_salary_period_source.csv")
    core[core.salary_min_annual_eur.notna()].sample(min(40, int(core.salary_min_annual_eur.notna().sum())), random_state=7)[["posting_uid", "source", "salary_min_annual_eur", "salary_max_annual_eur", "salary_period", "salary_source", "salary_snippet"]].to_csv(TAB / "Q07a_salary_audit_sample.csv", index=False)
    core[core.salary_basis == "implausible"][["posting_uid", "source", "salary_snippet"]].to_csv(TAB / "Q07b_salary_implausible.csv", index=False)
    # Q08 remote ambiguity
    core.remote_type.value_counts().reset_index().to_csv(TAB / "Q08_remote_ambiguity.csv", index=False)
    # Q09 skill spot-check sample
    d = core[core.description_length > 300].sample(min(30, int((core.description_length > 300).sum())), random_state=7)
    d[["posting_uid", "source_url", "title", "skills_programming_languages", "skills_bi_tools", "skills_cloud_platforms", "skills_data_platforms", "skills_ml_ai", "german_requirement", "german_snippet", "salary_snippet", "remote_type"]].to_csv(TAB / "Q09_skill_spotcheck_sample.csv", index=False)
    # summary json
    js = {"missingness": rows, "coverage_by_source_core": json.loads(cov.reset_index().to_json(orient="records")), "normalization_confidence": json.loads(conf.to_json(orient="records")),
          "duplicates": json.loads(q4.to_json(orient="records")), "stale": {"older_than_180d": int((core2.age_days > 180).sum()), "core_with_date": int(core2.age_days.notna().sum())}}
    json.dump(js, open(OUT / "data_quality.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(cov.to_string()); print(conf.to_string()); print(q4.to_string())


if __name__ == "__main__":
    main()
