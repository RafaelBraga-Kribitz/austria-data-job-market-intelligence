"""Layer 2 project / GitHub / README / portfolio analysis: tables C14–C21, C24 (marketing × data projects) and
outputs/supply_projects.json, supply_project_formats.json, supply_github.json, supply_linkedin.json.

Populations: P_data (observed data-signal candidates) for candidate-level shares; "projects" = data repositories meeting the
project definition (schemas/supply_schema.md) owned by P_data candidates; "documented projects" = README ≥ 1,000 chars.
All C14–C24 tables are GitHub evidence, so only `source == "github"` candidates enter them (LinkedIn slot rows carry no
repositories by construction). supply_linkedin.json holds the public tallies of the LinkedIn slot (supply_common).
Runs unchanged after src/pipeline/redact_supply_raw.py (uses has_blog, not the website text; README headings used ≥ 5 times survive).

Usage: python src/analysis/project_analysis.py
"""
from __future__ import annotations

import json
from collections import Counter

import pandas as pd

from supply_common import CAP, CFG, OUT, PROC, load_candidates, load_projects, public_linkedin_summary, share_table, wilson, write

SHARE_COLS = ["count", "n", "share", "ci_low", "ci_high"]  # columns share_table adds after the label


def bucket_count(k: int) -> str:
    return "0" if k == 0 else "1" if k == 1 else "2–3" if k <= 3 else "4–5" if k <= 5 else "6–10" if k <= 10 else "10+"


def push_bucket(m) -> str:
    if pd.isna(m):
        return "unknown"
    return "≤3 months" if m <= 3 else "4–12 months" if m <= 12 else "1–3 years" if m <= 36 else "> 3 years"


def stars_bucket(s) -> str:
    if pd.isna(s):
        return "unknown"
    return "0" if s == 0 else "1–2" if s <= 2 else "3–9" if s <= 9 else "10–49" if s <= 49 else "50+"


def wr(df: pd.DataFrame, name: str, note: str | None = None) -> pd.DataFrame:
    """write() and return the frame as written (with the note column), so the JSON exports reuse it instead of re-reading."""
    write(df, name, note)
    return df.assign(note=note) if note else df


def read_linkedin(path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False) if path.exists() else pd.DataFrame()


def main() -> None:
    c = load_candidates(); p = load_projects()
    c = c[c.source == "github"]
    P_data = c[c.is_data]; n_data = len(P_data)
    P_T1 = c[c.is_t1 & c.is_austria]; n_t1 = len(P_T1)
    fam = P_T1.set_index("candidate_id")["family"]
    p = p[p.candidate_id.isin(P_data.candidate_id)].copy()
    p["family"] = p.candidate_id.map(fam)
    proj = p[p.is_project]; docd = p[p.is_documented]; subst = p[p.is_substantive]
    n_p, n_d, n_s = len(proj), len(docd), len(subst)

    # ---------------- C14 GitHub evidence per candidate
    rows = []
    for name, sub in (("P_data", P_data), ("P_T1", P_T1)):
        n = len(sub)
        def sh(mask):
            k = int(mask.sum()); lo, hi = wilson(k, n); return k, round(k / n, 3) if n else None, lo, hi
        for lab, mask in (("≥1 owned non-fork repository", sub.n_repos_owned >= 1), ("≥1 data repository", sub.n_data_repos >= 1), ("≥1 project (definition)", sub.n_projects >= 1),
                          ("≥1 documented project (README ≥ 1k)", sub.n_documented_projects >= 1), ("≥1 substantive project (documented, not educational)", sub.n_substantive_projects >= 1),
                          ("≥1 educational/tutorial data repo", sub.n_educational_repos >= 1), ("any push in last 12 months", sub.n_active_12m >= 1), ("≥1 star on any owned repo", sub.max_stars >= 1),
                          ("≥10 stars on any owned repo", sub.max_stars >= 10), ("has forks of others' repos", sub.n_forks >= 1), ("bio present", sub.has_bio), ("company field present", sub.has_company),
                          ("available-for-hire flag", sub.hireable), ("website/blog field present", sub.has_blog)):
            k, s, lo, hi = sh(mask)
            rows.append({"population": name, "signal": lab, "count": k, "n": n, "share": s, "ci_low": lo, "ci_high": hi})
    c14 = pd.DataFrame(rows)
    write(c14, "C14_github_evidence", "GitHub presence is 100 % by construction (the frame is GitHub); the informative shares are those below 100 %")
    c14b = pd.DataFrame([{"population": name, "n": len(sub), "median_owned_repos": float(sub.n_repos_owned.median()), "median_data_repos": float(sub.n_data_repos.median()), "median_projects": float(sub.n_projects.median()),
                          "median_documented": float(sub.n_documented_projects.median()), "median_followers": float(sub.followers.median()), "median_stars_total": float(sub.stars_total.median()),
                          "median_account_age_years": float(sub.account_age_years.median()), "p90_projects": float(sub.n_projects.quantile(.9))} for name, sub in (("P_data", P_data), ("P_T1", P_T1))])
    write(c14b, "C14b_github_medians")
    arche_c = Counter(); arche_p = Counter(k for k in p.archetype)
    for d in P_data.archetypes:
        for k in (d or {}):
            arche_c[k] += 1
    c14c = pd.DataFrame([{"archetype": k, "projects": arche_p.get(k, 0), "share_of_data_repos": round(arche_p.get(k, 0) / len(p), 3) if len(p) else None, "candidates_with_≥1": arche_c.get(k, 0), "n_candidates": n_data,
                          "candidate_share": round(arche_c.get(k, 0) / n_data, 3) if n_data else None} for k in CFG["repo_archetypes"]["order"]])
    write(c14c, "C14c_repository_archetypes", "archetype assigned per data repository (config/supply_taxonomy.json repo_archetypes order)")
    act = share_table(p.months_since_push.map(push_bucket), len(p), "last_push", explode=False)
    write(act, "C14d_data_repo_activity", "population: all data repositories of P_data; 'unknown' = no push date recorded")
    write(share_table(p.stars.map(stars_bucket), len(p), "stars", explode=False), "C14e_data_repo_stars", "'unknown' = no star count recorded")

    # ---------------- C15 portfolio evidence (cross-platform)
    rows = []
    for name, sub in (("P_data", P_data), ("P_T1", P_T1)):
        n = len(sub); links = sub.links_any.map(set); fmts = sub.project_formats.map(lambda d: set((d or {}).keys()))
        for lab, mask in (("LinkedIn link on profile/READMEs", links.map(lambda s: "linkedin" in s)), ("Kaggle link", links.map(lambda s: "kaggle" in s)),
                          ("personal website (custom domain)", links.map(lambda s: "personal_site_custom" in s)), ("GitHub Pages site", links.map(lambda s: "personal_site_github_pages" in s)),
                          ("Medium/Substack/dev.to blog link", links.map(lambda s: "medium_blog" in s)), ("Tableau Public link", links.map(lambda s: "tableau_public" in s)),
                          ("Hugging Face link", links.map(lambda s: "huggingface" in s)), ("Streamlit/HF Space app link", links.map(lambda s: "streamlit_hf_space" in s)),
                          ("Google Scholar/ORCID/ResearchGate", links.map(lambda s: "scholar_orcid" in s)), ("X/Twitter", links.map(lambda s: "twitter_x" in s)), ("XING", links.map(lambda s: "xing" in s)),
                          ("≥1 notebook-format project", fmts.map(lambda s: "notebook" in s)), ("≥1 dashboard/BI-format project", fmts.map(lambda s: "dashboard_bi" in s)),
                          ("≥1 deployed app (Streamlit/Gradio/Shiny)", fmts.map(lambda s: "streamlit_gradio_app" in s)), ("≥1 API project", fmts.map(lambda s: "api" in s)),
                          ("≥1 project with tests", fmts.map(lambda s: "tests" in s)), ("≥1 project with CI", fmts.map(lambda s: "ci" in s)), ("≥1 project with Docker", fmts.map(lambda s: "docker" in s)),
                          ("≥1 academic paper/thesis repo", fmts.map(lambda s: "paper_academic" in s)), ("≥1 Kaggle/competition repo", fmts.map(lambda s: "competition_kaggle" in s)),
                          ("≥1 pipeline/dbt/Airflow project", fmts.map(lambda s: "pipeline_project" in s)), ("≥1 report/slides format", fmts.map(lambda s: "report_pdf_slides" in s))):
            k = int(mask.sum()); lo, hi = wilson(k, n)
            rows.append({"population": name, "evidence": lab, "count": k, "n": n, "share": round(k / n, 3) if n else None, "ci_low": lo, "ci_high": hi})
    c15 = wr(pd.DataFrame(rows), "C15_portfolio_evidence", "links are those visible on the GitHub profile (website field, social accounts) or in data-project READMEs; a candidate may have a LinkedIn profile without linking it")

    # ---------------- C16 project counts
    rows = []
    for name, sub in (("P_data", P_data), ("P_T1", P_T1)):
        for var in ("n_projects", "n_documented_projects", "n_substantive_projects", "n_data_repos"):
            t = share_table(sub[var].map(bucket_count), len(sub), "bucket", explode=False); t["population"] = name; t["variable"] = var
            t["bucket_order"] = t.bucket.map({"0": 0, "1": 1, "2–3": 2, "4–5": 3, "6–10": 4, "10+": 5}); rows.append(t.sort_values("bucket_order"))
    c16 = wr(pd.concat(rows, ignore_index=True), "C16_project_count_distribution", "project = owned non-fork data repository with README ≥ 300 chars, ≥ 1 star or a description; repositories ≠ projects")

    # ---------------- C17 formats
    c17 = share_table(proj.formats, n_p, "format"); c17["population"] = "projects"
    c17d = share_table(docd.formats, n_d, "format"); c17d["population"] = "documented projects"
    cand_f = share_table(P_data.project_formats.map(lambda d: list((d or {}).keys())), n_data, "format"); cand_f["population"] = "P_data candidates (≥1 project with format)"
    write(pd.concat([c17, c17d, cand_f], ignore_index=True), "C17_project_formats")
    combos = Counter()
    for f in proj.formats:
        key = " + ".join(sorted(x for x in f if x in ("notebook", "python_package_or_src", "streamlit_gradio_app", "web_app", "api", "dashboard_bi", "pipeline_project", "docker", "tests", "ci", "r_markdown_quarto"))) or "(none of the packaging formats)"
        combos[key] += 1
    write(pd.DataFrame([{"format_combination": k, "projects": v, "n": n_p, "share": round(v / n_p, 3)} for k, v in combos.most_common(30)]), "C17b_format_combinations")

    # ---------------- C18 topics
    parts = []
    for grp in ("analytics_domain", "ds_method", "engineering", "ai"):
        t = share_table(proj[f"themes_{grp}"], n_p, "theme"); t["group"] = grp; t["population"] = "projects"; parts.append(t)
        t2 = share_table(subst[f"themes_{grp}"], n_s, "theme"); t2["group"] = grp; t2["population"] = "substantive projects"; parts.append(t2)
        t3 = share_table(P_data.project_themes.map(lambda d: [k.split(":")[1] for k in (d or {}) if k.startswith(grp + ":")]), n_data, "theme"); t3["group"] = grp; t3["population"] = "P_data candidates (≥1 project)"; parts.append(t3)
    c18 = wr(pd.concat(parts, ignore_index=True), "C18_project_topics")
    fam_theme = []
    for f, sub in proj.dropna(subset=["family"]).groupby("family"):
        if len(sub) < 10:
            continue
        for grp in ("analytics_domain", "ds_method", "engineering", "ai"):
            t = share_table(sub[f"themes_{grp}"], len(sub), "theme", top=8); t["group"] = grp; t.insert(0, "family", f); fam_theme.append(t)
    write(pd.concat(fam_theme, ignore_index=True) if fam_theme else pd.DataFrame(columns=["family", "theme", *SHARE_COLS, "group"]),
          "C18b_project_topics_by_family", "projects owned by bio-declared candidates, by their family")
    no_theme = int((proj[["themes_analytics_domain", "themes_ds_method", "themes_engineering", "themes_ai"]].map(len).sum(axis=1) == 0).sum())
    c18c = wr(pd.DataFrame([{"projects": n_p, "documented": n_d, "substantive": n_s, "projects_without_any_theme": no_theme, "share_without_theme": round(no_theme / n_p, 3) if n_p else None,
                         "share_with_business_domain": round((proj.themes_analytics_domain.map(len) > 0).mean(), 3) if n_p else None, "share_with_ds_method": round((proj.themes_ds_method.map(len) > 0).mean(), 3) if n_p else None,
                         "share_with_engineering": round((proj.themes_engineering.map(len) > 0).mean(), 3) if n_p else None, "share_with_ai": round((proj.themes_ai.map(len) > 0).mean(), 3) if n_p else None}]), "C18c_project_theme_coverage")

    # ---------------- C19 README patterns
    hcols = [col for col in p.columns if col.startswith("rd_h_")]; ccols = [col for col in p.columns if col.startswith("rd_") and not col.startswith("rd_h_")]
    rows = []
    for name, sub in (("projects", proj), ("documented projects", docd), ("substantive projects", subst)):
        n = len(sub)
        for col in hcols + ccols:
            k = int(sub[col].fillna(False).sum()); lo, hi = wilson(k, n)
            rows.append({"population": name, "feature": col.replace("rd_h_", "section: ").replace("rd_", "content: "), "count": k, "n": n, "share": round(k / n, 3) if n else None, "ci_low": lo, "ci_high": hi})
    c19 = wr(pd.DataFrame(rows), "C19_readme_patterns")
    rows = []
    for name, sub in (("projects", proj), ("documented projects", docd)):
        t = share_table(sub.readme_length_bucket, len(sub), "readme_length", explode=False); t["population"] = name; rows.append(t)
    write(pd.concat(rows, ignore_index=True), "C19b_readme_length")
    nsec = docd[hcols].sum(axis=1)
    c19c = wr(pd.DataFrame([{"population": "documented projects", "n": n_d, "median_sections_detected": float(nsec.median()) if n_d else None, "share_≥4_sections": round((nsec >= 4).mean(), 3) if n_d else None,
                         "median_chars": float(docd.readme_chars.median()) if n_d else None, "median_words": float(docd.readme_words.median()) if n_d else None, "median_headings": float(docd.readme_headings.median()) if n_d else None,
                         "share_results_AND_method": round((docd.rd_h_results & docd.rd_h_methodology).mean(), 3) if n_d else None, "share_results_AND_limitations": round((docd.rd_h_results & docd.rd_h_limitations).mean(), 3) if n_d else None,
                         "share_business_context_OR_terms": round((docd.rd_h_business_context | docd.rd_mentions_business_terms).mean(), 3) if n_d else None,
                         "share_reproducibility_section_AND_cmd": round((docd.rd_h_reproducibility & docd.rd_mentions_reproduce_cmd).mean(), 3) if n_d else None}]), "C19c_readme_structure_summary")
    ra = []
    for a, sub in docd.groupby("archetype"):
        if len(sub) < 10:
            continue
        row = {"archetype": a, "n": len(sub)}
        for col in hcols + ["rd_has_image", "rd_mentions_metrics", "rd_mentions_business_terms", "rd_mentions_limitations", "rd_mentions_reproduce_cmd"]:
            row[col.replace("rd_h_", "").replace("rd_", "")] = round(sub[col].fillna(False).mean(), 2)
        ra.append(row)
    ra_cols = ["archetype", "n"] + [col.replace("rd_h_", "").replace("rd_", "") for col in hcols + ["rd_has_image", "rd_mentions_metrics", "rd_mentions_business_terms", "rd_mentions_limitations", "rd_mentions_reproduce_cmd"]]
    write(pd.DataFrame(ra, columns=ra_cols), "C19d_readme_patterns_by_archetype", "documented projects; archetypes with ≥ 10 projects")
    heads = Counter(h for l in docd.readme_heading_list for h in (l or []))
    c19e = wr(pd.DataFrame([{"heading": h, "projects": k, "n": n_d, "share": round(k / n_d, 3)} for h, k in heads.most_common(60) if k >= 5], columns=["heading", "projects", "n", "share"]),
              "C19e_common_readme_headings", "verbatim lower-cased headings used in ≥ 5 documented projects")

    # ---------------- C20 project technologies, C21 capabilities
    c20 = share_table(proj.skills, n_p, "skill", top=60); c20["population"] = "projects"
    c20s = share_table(subst.skills, n_s, "skill", top=60); c20s["population"] = "substantive projects"
    write(pd.concat([c20, c20s], ignore_index=True), "C20_project_technologies")
    by_arch = []
    for a, sub in proj.groupby("archetype"):
        if len(sub) < 10:
            continue
        t = share_table(sub.skills, len(sub), "skill", top=10); t.insert(0, "archetype", a); by_arch.append(t)
    write(pd.concat(by_arch, ignore_index=True) if by_arch else pd.DataFrame(columns=["archetype", "skill", *SHARE_COLS]), "C20b_project_technologies_by_archetype")
    rows = []
    for cap, spec in CAP.items():
        ds = set(spec["demand_skills"]); th = set(spec["project_themes"])
        def has(r):
            return bool(set(r["skills"]) & ds) or bool((set(r["themes_analytics_domain"]) | set(r["themes_ds_method"]) | set(r["themes_engineering"]) | set(r["themes_ai"]) | set(r["formats"])) & th)
        kp = int(proj.apply(has, axis=1).sum()) if n_p else 0; ks = int(subst.apply(has, axis=1).sum()) if n_s else 0
        cands = int(subst[subst.apply(has, axis=1)].candidate_id.nunique()) if n_s else 0
        rows.append({"capability": cap, "group": spec["group"], "projects": kp, "n_projects": n_p, "project_share": round(kp / n_p, 3) if n_p else None, "substantive_projects": ks, "n_substantive": n_s,
                     "substantive_share": round(ks / n_s, 3) if n_s else None, "candidates_with_substantive_evidence": cands, "n_candidates": n_data, "candidate_share": round(cands / n_data, 3) if n_data else None})
    c21 = pd.DataFrame(rows).sort_values("projects", ascending=False)
    write(c21, "C21_project_capabilities", "a project 'carries' a capability when any of its Layer 1 skills or Layer 2 themes/formats belongs to it (config/capability_map.json)")

    # ---------------- C24 marketing × data intersection (projects and candidates)
    mk_p = proj[proj.themes_analytics_domain.map(lambda l: "marketing" in l or "customer" in l or "ecommerce" in l)]
    mk_c = P_data[P_data.candidate_id.isin(mk_p.candidate_id)]
    c24 = pd.DataFrame([{"marketing/customer/e-commerce projects": len(mk_p), "share_of_projects": round(len(mk_p) / n_p, 3) if n_p else None, "substantive": int(mk_p.is_substantive.sum()),
                         "candidates_with_such_project": len(mk_c), "share_of_P_data": round(len(mk_c) / n_data, 3) if n_data else None,
                         "of_which_T1_bio_declared": int(mk_c.is_t1.sum()), "T1_families": json.dumps(mk_c.family.value_counts().to_dict()), "styria": int(mk_c.is_styria.sum()), "vienna": int(mk_c.is_vienna.sum()),
                         "methods_top": "; ".join(f"{k} ({v})" for k, v in Counter(x for l in mk_p.themes_ds_method for x in l).most_common(8)),
                         "formats_top": "; ".join(f"{k} ({v})" for k, v in Counter(x for l in mk_p.formats for x in l).most_common(8)),
                         "skills_top": "; ".join(f"{k} ({v})" for k, v in Counter(x for l in mk_p.skills for x in l).most_common(10)),
                         "with_experimentation_or_causal": int(mk_p.themes_ds_method.map(lambda l: "experimentation" in l or "causal_inference" in l).sum()),
                         "with_sql_and_python": int(mk_p.skills.map(lambda l: "SQL" in l and "Python" in l).sum()), "with_power_bi_or_tableau": int(mk_p.skills.map(lambda l: "Power BI" in l or "Tableau" in l).sum())}])
    write(c24, "C24_marketing_data_intersection")

    # ---------------- JSON
    man = json.loads((PROC / "supply_build_manifest.json").read_text(encoding="utf-8"))
    meta = {"generated": pd.Timestamp.now().isoformat(), "collection_date": man["collection_date"], "taxonomy_version": CFG["version"], "source_quality": "B",
            "populations": {"P_data": n_data, "P_T1": n_t1, "data_repos": len(p), "projects": n_p, "documented_projects": n_d, "substantive_projects": n_s}}
    (OUT / "supply_projects.json").write_text(json.dumps({**meta, "project_counts": c16.to_dict("records"), "topics": c18.to_dict("records"), "theme_coverage": c18c.to_dict("records")[0],
                                                          "archetypes": c14c.to_dict("records"), "capabilities": c21.to_dict("records"), "marketing_data_intersection": c24.to_dict("records")[0],
                                                          "project_definition": CFG["evidence_rules"]["project_definition"]}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "supply_project_formats.json").write_text(json.dumps({**meta, "formats": pd.concat([c17, c17d, cand_f]).to_dict("records"), "combinations": [{"format_combination": k, "projects": v} for k, v in combos.most_common(20)],
                                                                 "readme_patterns": c19.to_dict("records"), "readme_structure": c19c.to_dict("records")[0],
                                                                 "common_headings": c19e.to_dict("records")}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "supply_github.json").write_text(json.dumps({**meta, "evidence": c14.to_dict("records"), "medians": c14b.to_dict("records"), "archetypes": c14c.to_dict("records"), "activity": act.to_dict("records"),
                                                        "portfolio_evidence": c15.to_dict("records"), "project_technologies_top": c20.head(30).to_dict("records")}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    # LinkedIn slot: own collection dates, methods and quality grades; the GitHub vintage/quality apply only to the proxy share
    li = public_linkedin_summary(read_linkedin(PROC / "supply_linkedin_counts.csv"), read_linkedin(PROC / "supply_linkedin_profiles.csv"))
    (OUT / "supply_linkedin.json").write_text(json.dumps({"generated": meta["generated"], **li,
                                                          "observable_proxy": "share of GitHub data-signal candidates who link a LinkedIn profile (C15)",
                                                          "proxy_collection_date": meta["collection_date"], "proxy_source_quality": meta["source_quality"],
                                                          "linkedin_link_share": c15.query("evidence == 'LinkedIn link on profile/READMEs'").to_dict("records")}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(meta["populations"], indent=1))


if __name__ == "__main__":
    main()
