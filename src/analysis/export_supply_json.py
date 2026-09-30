"""Machine-readable decision-layer exports for future agents (public):
  outputs/project_evidence_map.json      per target role family: employer requirements × candidate supply × project evidence
  outputs/operational_career_context.json consolidated Layer 1 / 2 / 3 context: definitions, vintages, key metrics, evidence gaps,
                                          vocabulary bridge, Styria and marketing×data summaries, limitations, open questions.
Reads only aggregated tables/JSON already in outputs/ (runs in the public repository).

Usage: python src/analysis/export_supply_json.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "outputs" / "tables"; OUT = ROOT / "outputs"
T = lambda n: pd.read_csv(TAB / f"{n}.csv")  # noqa: E731
J = lambda n: json.loads((OUT / f"{n}.json").read_text(encoding="utf-8"))  # noqa: E731


def demand_meta() -> tuple[str, int]:
    """Layer 1 vintage and core n from market_summary.json, so a refresh cannot leave stale literals (M81)."""
    try:
        ms = J("market_summary")
        return str(ms["collected_at_range"]["max"])[:10], int(ms["counts"]["core_canonical"])
    except (FileNotFoundError, KeyError, ValueError):
        return "2026-09-16", 720


FAMILIES = ["data_analytics", "data_science", "data_engineering", "bi", "business_analysis", "data_governance", "marketing_analytics", "product_analytics"]
LABEL = {"data_analytics": "Data analytics", "bi": "BI", "data_science": "Data science", "data_engineering": "Data engineering", "data_governance": "Data governance",
         "marketing_analytics": "Marketing analytics", "product_analytics": "Product analytics", "business_analysis": "Business analysis"}
# what kind of public evidence would make a capability legible (used only to phrase 'suggested evidence categories'; not a ranking)
EVIDENCE_TYPE = {"SQL": "queries over a modelled schema (star schema, window functions) with results in the README", "Python": "a repository with modules, tests and a README that states the question and the result",
                 "Power BI": "a published report or screenshots plus the data model and DAX in the repo (Power BI itself leaves no code trace)", "Excel": "not worth a project; mention as a tool",
                 "Data warehouse / modelling": "a dimensional model (dbt or SQL) with documentation of grain, facts and dimensions", "ETL / data pipelines": "an ingestion pipeline with scheduling, data checks and a run log",
                 "Data quality / governance": "explicit validation rules, data-quality tests (e.g. Great Expectations/dbt tests) and a lineage note", "Statistics": "a README results section with intervals, effect sizes and stated assumptions",
                 "Experimentation / A/B testing": "an A/B or quasi-experiment readout: design, power, result, decision", "Causal inference": "a DiD/propensity/synthetic-control analysis with identification assumptions written out",
                 "Forecasting / time series": "a forecast with backtesting, error metrics and a decision use", "Machine learning": "a model with baseline comparison, evaluation and a leakage note",
                 "GenAI / LLM": "a RAG or agent application over business documents with an evaluation set", "Data visualisation / dashboards": "a deployed dashboard or app (Streamlit/Power BI) with a screenshot and the questions it answers",
                 "Azure": "a pipeline or model deployed on Azure with infrastructure notes", "Databricks/Spark": "a notebook/pipeline on Databricks or PySpark with cluster/cost notes", "CI/CD & tests": "GitHub Actions running tests on every push",
                 "Docker": "a Dockerfile/compose that reproduces the project", "REST / APIs": "a FastAPI/Flask endpoint serving a model or data product", "Git": "commit history and branches on every project (visible by construction)",
                 "Marketing / CRM / web analytics": "a marketing/customer dataset project: attribution, segmentation, CLV or campaign analysis with business framing", "Product analytics": "funnel/retention/cohort analysis with a product decision",
                 "Finance / controlling / risk": "a controlling/forecast or risk dataset project with KPI definitions", "Stakeholder / communication": "READMEs with a business-context section, a one-page summary, a case study",
                 "Requirements / business analysis": "a requirements/case-study document alongside the code", "Airflow/orchestration": "a DAG with retries, schedules and logging", "dbt": "a dbt project with tests and docs",
                 "Snowflake/BigQuery/Redshift": "a warehouse project on a free tier with cost notes", "Cloud (any)": "any cloud-deployed component with an architecture diagram"}


def project_evidence_map() -> dict:
    t14 = T("T14_family_profiles").set_index("role_family"); t02 = T("T02_role_family_counts").set_index("role_family")
    c04 = T("C04_role_family_distribution").set_index("role_family"); c10b = T("C10b_technologies_by_family"); c06b = T("C06b_seniority_by_family").set_index("family")
    c08d = T("C08d_education_by_family"); c09c = T("C09c_certifications_by_family"); c18b = T("C18b_project_topics_by_family"); c17 = T("C17_project_formats"); c15 = T("C15_portfolio_evidence")
    ds10 = T("DS10_demand_supply_capability_evidence"); ds01 = T("DS01_demand_supply_role_families").set_index("category")
    fmt_proj = c17[c17.population == "projects"].set_index("format")["share"].to_dict()
    common_formats = [f"{k} ({v:.0%})" for k, v in sorted(fmt_proj.items(), key=lambda x: -x[1]) if v >= 0.25]
    rare_formats = [f"{k} ({v:.0%})" for k, v in sorted(fmt_proj.items(), key=lambda x: x[1]) if v < 0.10]
    gaps = ds10[ds10.interpretation.str.startswith("demanded, rarely")].sort_values("demand_share", ascending=False)
    out = {"generated": pd.Timestamp.now().isoformat(), "demand_vintage": demand_meta()[0], "supply_vintage": J("supply_summary")["collection_date"],
           "reading": "per family: what ads mention (Layer 1), what bio-declared candidates show (Layer 2), what projects commonly/rarely contain, and which demanded capabilities are rarely project-demonstrated. No number of projects is prescribed.",
           "families": {}}
    for fam in FAMILIES:
        req = t14.loc[fam] if fam in t14.index else None
        sup_sk = c10b[c10b.family == fam].sort_values("count", ascending=False)
        top_dem = [s.strip() for s in str(req.top_tech_skills).split(";")] if req is not None else []
        dem_names = [re.sub(r"\s*\(\d+%\)$", "", s) for s in top_dem]
        fam_gaps = [{"capability": r.category, "demand_share": r.demand_share, "supply_any_share": r.supply_any_share, "project_share": r.supply_project_share, "evidence_gap_pp": r.evidence_gap_pp,
                     "suggested_evidence": EVIDENCE_TYPE.get(r.category)} for _, r in gaps.iterrows()]
        out["families"][fam] = {
            "label": LABEL[fam],
            "employer_requirements": {"open_postings_AT": int(t02.loc[fam, "count"]) if fam in t02.index else 0, "styria": int(t02.loc[fam, "styria_count"]) if fam in t02.index else 0,
                                      "top_tech_skills": top_dem, "top_business_context": [s.strip() for s in str(req.top_business).split(";")] if req is not None else [],
                                      "german_required_share": float(req.german_required_share) if req is not None else None, "english_posting_share": float(req.english_posting_share) if req is not None else None,
                                      "degree_required_share": float(req.degree_required_share) if req is not None else None, "median_advertised_min_salary_eur": float(req.median_min_salary) if req is not None else None, "source": "T14/T02"},
            "candidate_supply": {"bio_declared_candidates": int(c04.loc[fam, "count"]) if fam in c04.index else 0, "share_of_bio_declared": float(c04.loc[fam, "share"]) if fam in c04.index else 0,
                                 "styria": int(c04.loc[fam, "styria"]) if fam in c04.index else 0, "vienna": int(c04.loc[fam, "vienna"]) if fam in c04.index else 0, "students": int(c04.loc[fam, "students"]) if fam in c04.index else 0,
                                 "relative_representation_vs_demand": float(ds01.loc[fam, "relative_representation"]) if fam in ds01.index and pd.notna(ds01.loc[fam, "relative_representation"]) else None,
                                 "top_skills_any_evidence": [f"{r['item']} ({r.share:.0%})" for _, r in sup_sk.head(12).iterrows()],
                                 "seniority_wording": {k: int(v) for k, v in c06b.loc[fam].drop("family_label", errors="ignore").items()} if fam in c06b.index else {},
                                 "education_wording": [f"{r['item']} ({r.share:.0%})" for _, r in c08d[c08d.family == fam].head(6).iterrows()], "certification_wording": [f"{r['item']} ({r.share:.0%})" for _, r in c09c[c09c.family == fam].head(6).iterrows()],
                                 "source": "C04/C10b/C06b/C08d/C09c"},
            "common_candidate_evidence": {"project_topics_by_family": [f"{r.group}:{r.theme} ({r.share:.0%})" for _, r in c18b[c18b.family == fam].sort_values("count", ascending=False).head(10).iterrows()],
                                          "formats_all_projects": common_formats, "source": "C18b/C17"},
            "rare_candidate_evidence": {"formats_under_10pct": rare_formats, "capabilities_rarely_project_demonstrated": [g["capability"] for g in fam_gaps if g["capability"] in dem_names or g["demand_share"] >= 0.15], "source": "C17/DS10"},
            "potential_evidence_gaps_for_this_family": [g for g in fam_gaps if g["capability"] in dem_names or any(d.lower() in g["capability"].lower() for d in dem_names)],
            "suggested_evidence_categories": sorted({EVIDENCE_TYPE[k] for k in EVIDENCE_TYPE if any(k.lower() in d.lower() or d.lower() in k.lower() for d in dem_names)})[:8],
        }
    out["cross_family"] = {"demanded_rarely_project_demonstrated": gaps[["category", "group", "demand_share", "supply_any_share", "supply_project_share", "evidence_gap_pp"]].to_dict("records"),
                           "core_market_capabilities": ds10[ds10.interpretation.str.startswith("core market")].sort_values("demand_share", ascending=False)[["category", "demand_share", "supply_any_share", "supply_project_share"]].to_dict("records"),
                           "commonly_evidenced_less_demanded": ds10[ds10.interpretation.str.startswith("commonly evidenced")].sort_values("supply_any_share", ascending=False)[["category", "demand_share", "supply_any_share"]].to_dict("records"),
                           "portfolio_evidence_prevalence": c15[c15.population == "P_data"][["evidence", "count", "n", "share"]].to_dict("records")}
    (OUT / "project_evidence_map.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return out


def linkedin_status(li: dict) -> str:
    """Status line of the LinkedIn slot; tolerates summaries written before the key contract (supply_common.public_linkedin_summary)."""
    return li.get("status") or "LinkedIn slot: status not recorded in supply_linkedin.json (re-run src/analysis/project_analysis.py)"


def linkedin_open_question(li: dict) -> str:
    """Unresolved-question wording derived from the slot tallies instead of a hard-coded 'empty'."""
    n_p = int(li.get("profiles_recorded", li.get("manual_profiles_recorded", 0)) or 0)
    n_c = int(li.get("search_counts_recorded", li.get("manual_search_counts_recorded", 0)) or 0)
    if not n_p and not n_c:
        return "how large is the non-GitHub candidate supply (LinkedIn slot empty)"
    dates = ", ".join(li.get("linkedin_collection_dates") or []) or "date not recorded"
    return (f"how large is the non-GitHub candidate supply (LinkedIn slot: {n_p} coded profiles and {n_c} search counts, {dates}; "
            "a systematic sample of visible profiles and result indices, not a census)")


def operational_context() -> None:
    ss = J("supply_summary"); dsc = J("demand_supply_capabilities"); geo = J("demand_supply_geography"); lang = J("demand_supply_language"); off = J("supply_official")
    pf = J("supply_project_formats"); gh = J("supply_github"); li = J("supply_linkedin"); dq = J("supply_data_quality")
    t02b = T("T02b_normalized_title_counts"); t05 = T("T05_skills_all_tech"); c02 = T("C02_raw_bio_title_distribution"); c10 = T("C10_technologies_evidence"); c24 = T("C24_marketing_data_intersection")
    ds10 = pd.DataFrame(dsc["capabilities"])
    vocab = {"employer_titles_top": [f"{r.normalized_title} ({r['count']})" for _, r in t02b.head(12).iterrows()],
             "candidate_raw_bio_phrases_top": [f"{r.raw_bio_title} ({r['count']})" for _, r in c02.head(20).iterrows()],
             "employer_skill_words_top": [f"{r.skill} ({r.share:.0%})" for _, r in t05.head(20).iterrows()],
             "candidate_skill_evidence_top": [f"{r.skill} ({r.any_evidence_share:.0%} any / {r.project_demonstrated_share:.0%} project)" for _, r in c10.head(20).iterrows()],
             "high_demand_high_supply_terms": [r.category for _, r in ds10[ds10.quadrant.str.startswith("A")].sort_values("demand_share", ascending=False).iterrows()],
             "high_demand_low_supply_terms": [r.category for _, r in ds10[ds10.quadrant.str.startswith("B")].sort_values("demand_share", ascending=False).iterrows()],
             "low_demand_high_supply_terms": [r.category for _, r in ds10[ds10.quadrant.str.startswith("C")].sort_values("supply_any_share", ascending=False).iterrows()],
             "high_demand_low_project_evidence_terms": [r.category for _, r in ds10[ds10.interpretation.str.startswith("demanded, rarely")].sort_values("demand_share", ascending=False).iterrows()]}
    readme = {r["feature"]: r["share"] for r in pf["readme_patterns"] if r["population"] == "documented projects"}
    ctx = {"generated": pd.Timestamp.now().isoformat(),
           "layers": {"layer_1_demand": {"what": "open data-role advertisements, Austria, one-day stock", "vintage": demand_meta()[0], "n_core_postings": demand_meta()[1], "context": "AGENT_CONTEXT.md, outputs/market_summary.json"},
                      "layer_2_supply": {"what": "public GitHub accounts with an Austrian location signal and a data signal; Stack Overflow 2025 Austrian respondents; Eurostat graduates/occupations", "vintage": ss["collection_date"], "populations": ss["populations"],
                                         "unit": ss["unit"], "linkedin": linkedin_status(li)},
                      "layer_3_demand_x_supply": {"what": "shares side by side on shared dimensions; quadrants by medians; evidence gaps; no composite score", "tables": "DS01–DS13", "method": "docs/demand-supply-methodology.md"}},
           "key_supply_metrics": {"families_bio_declared": ss["families"], "tiers": ss["tiers"], "styria_complete_frame": ss["styria_complete_frame"], "seniority_T1": ss["seniority_T1"], "top_technologies": ss["top_technologies"][:15],
                                  "transitions": ss["transitions"], "title_concentration": ss["concentration"], "github_medians": gh["medians"], "readme_documented_share_by_feature": readme,
                                  "project_formats_projects": [r for r in pf["formats"] if r["population"] == "projects"][:12], "common_headings": pf["common_headings"][:15]},
           "demand_x_supply": {"capabilities": dsc["capabilities"], "geography": geo["by_state"], "styria": geo["styria"], "language": lang["rows"], "styria_english_presenting_data_candidates": lang.get("styria_english_presenting_data_candidates")},
           "official_context": {"eurostat": off.get("eurostat", {}), "stackoverflow_2025": {k: v for k, v in off.get("stackoverflow_2025", {}).items() if k != "top_languages_data_roles"}},
           "vocabulary_bridge": vocab,
           "marketing_x_data": c24.to_dict("records")[0],
           "project_evidence_map_ref": "outputs/project_evidence_map.json",
           "interpretation_rules": ["supply share = share of observed GitHub data-signal candidates, not of the workforce", "a low supply share for a proprietary tool (Power BI, SAP, Excel) mostly reflects GitHub's blindness, not a supply gap",
                                    "Styrian counts are complete for GitHub; Vienna counts are lower bounds", "evidence gap = demand share − project-demonstrated share; validate demand before acting",
                                    "language: only presentation language is observed; never infer proficiency", "no individual is ranked or scored; clusters are descriptive archetypes"],
           "data_quality": {"search": dq["search"], "taxonomy": dq["taxonomy"], "projects": dq["projects"]},
           "unresolved_questions": [linkedin_open_question(li), "how much of the Vienna supply the keyword + base-rate frames miss", "whether stated German requirements in ads are negotiable for English-presenting candidates",
                                    "hiring outcomes: none observed on either side", "precision of bio→family classification (review sample in data/processed, private)"],
           "how_to_refresh": "docs/supply-methodology.md §8; never merge snapshots of different dates; compare table-to-table"}
    (OUT / "operational_career_context.json").write_text(json.dumps(ctx, indent=1, ensure_ascii=False, default=str), encoding="utf-8")


if __name__ == "__main__":
    project_evidence_map()
    operational_context()
    print("written: project_evidence_map.json, operational_career_context.json")
