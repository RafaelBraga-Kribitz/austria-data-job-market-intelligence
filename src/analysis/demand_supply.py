"""Layer 3: join Layer 1 employer demand (aggregated T* tables; capability shares recomputed from the private posting file
when present) with Layer 2 observed candidate supply (private candidate/project tables) on shared dimensions.
Tables DS01–DS13 and outputs/demand_supply_*.json.

Reading rules (docs/demand-supply-methodology.md): demand share = share of core postings (n from market_summary.json:
core_canonical / core_with_description) that MENTION an item; supply share = share of observed data-signal GitHub candidates (P_data) or bio-declared candidates
(P_T1) with the item; the two populations are different universes (advertisements vs public accounts), so the tables report
both shares, their difference in percentage points and their ratio, never a single score. Quadrants use the medians of the
joined set as thresholds and are labels for market structure, not judgements.

Regional bases (OQ-19). Demand: DS01/DS05b/DS13 Styria and Vienna columns come from T02 (ads listing at least one site
in the region, market_summary styria_core); DS05 comes from T03a (primary state). Supply: the canonical Styrian
denominators are location-resolved (every account whose resolved location is Styria: P_T1 56 / P_data 248 / all 2,033
in the 2026-09-17 collection); the frame-B complete-Styria subset (52 / 247 / 2,023) is reported in DS13 under that label.

Usage: python src/analysis/demand_supply.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter

import numpy as np
import pandas as pd

from supply_common import CAP, CFG, CORE_FAMILIES, FAMILY_LABELS, OUT, PROC, ROOT, TAB, load_candidates, load_evidence, load_projects, wilson, write

L1 = lambda name: pd.read_csv(TAB / f"{name}.csv")  # noqa: E731


def quadrant(d: float, s: float, td: float, ts: float) -> str:
    if d >= td and s >= ts:
        return "A: high demand / high observed supply"
    if d >= td:
        return "B: high demand / lower observed supply"
    if s >= ts:
        return "C: lower demand / high observed supply"
    return "D: lower demand / lower observed supply"


def demand_capability_shares() -> tuple[dict, int, str]:
    """Exact posting-level capability shares from the private processed file; fallback = max of member-skill shares."""
    f = PROC / "postings_dedup.parquet"
    t05 = L1("T05_skills_all_tech").set_index("skill")["share"].to_dict()
    n = int(L1("T05_skills_all_tech")["n"].iloc[0])
    if f.exists():
        df = pd.read_parquet(f)
        core = df[(df["is_canonical"] == True) & (df["role_family"].isin(CORE_FAMILIES))]  # noqa: E712
        # same denominator as run_analysis (stored length, so a later text redaction cannot move it)
        length = core["description_length"] if "description_length" in core.columns else core["description_text"].fillna("").str.len()
        core = core[length > 300]
        skill_cols = [c for c in core.columns if c.startswith("skills_")]
        sets, bad_cells, bad_rows = [], 0, 0
        for _, r in core[skill_cols].iterrows():
            s, bad = set(), False
            for c in skill_cols:
                v = r[c]
                if isinstance(v, str):
                    try:
                        v = json.loads(v)
                    except json.JSONDecodeError:
                        v = []; bad_cells += 1; bad = True
                s |= set(v or [])
            sets.append(s); bad_rows += bad
        if bad_cells:
            print(f"WARNING: {bad_cells} skills cell(s) in {bad_rows} posting(s) could not be parsed and count as no skill "
                  "(capability demand shares are lower bounds for those rows)", file=sys.stderr)
        out = {}
        for cap, spec in CAP.items():
            ds = set(spec["demand_skills"])
            out[cap] = round(sum(1 for s in sets if s & ds) / len(sets), 3)
        return out, len(sets), "exact (private posting file)" + (f"; {bad_rows} posting(s) with unparsable skills cells" if bad_rows else "")
    print(f"WARNING: {f.relative_to(ROOT)} not found - capability demand shares fall back to the max of member-skill "
          "shares (T05), a lower bound of the union; DS09/DS10 demand_method records this", file=sys.stderr)
    return {cap: round(max([t05.get(s, 0) for s in spec["demand_skills"]] or [0]), 3) for cap, spec in CAP.items()}, n, "approximate (max of member-skill shares; union not available publicly)"


def main() -> None:
    c = load_candidates(); e = load_evidence(); p = load_projects()
    P_data = c[c.is_data]; P_T1 = c[c.is_t1 & c.is_austria]; n_data, n_t1 = len(P_data), len(P_T1)
    sty_T1 = P_T1[P_T1.is_styria]; vie_T1 = P_T1[P_T1.is_vienna]
    sty_data = P_data[P_data.is_styria]; vie_data = P_data[P_data.is_vienna]
    ev = e[e.candidate_id.isin(P_data.candidate_id)]
    sup_any = ev.groupby("skill")["candidate_id"].nunique(); sup_proj = ev[ev.project_demonstrated].groupby("skill")["candidate_id"].nunique()
    sup_men = ev[ev.mentioned].groupby("skill")["candidate_id"].nunique()
    all_rows = []

    # ---------------- DS01 role families
    t02 = L1("T02_role_family_counts"); n_dem = int(t02.n.iloc[0])
    fam_sup = P_T1.family.value_counts(); fam_sty = sty_T1.family.value_counts(); fam_vie = vie_T1.family.value_counts()
    off = json.loads((OUT / "supply_official.json").read_text(encoding="utf-8")) if (OUT / "supply_official.json").exists() else {}
    so = off.get("stackoverflow") or off.get("stackoverflow_2025") or {}
    so_fam = so.get("data_families", {}) if so.get("available") else {}
    if not so_fam:
        print("NOTICE: Stack Overflow survey block unavailable in outputs/supply_official.json - DS01 so2025_at_respondents "
              "is empty (not refreshed)", file=sys.stderr)
    rows = []
    for fam in CORE_FAMILIES:
        d = t02[t02.role_family == fam].iloc[0] if (t02.role_family == fam).any() else None
        dc = int(d["count"]) if d is not None else 0; ds = dc / n_dem
        sc = int(fam_sup.get(fam, 0)); ss = sc / n_t1 if n_t1 else 0
        lo, hi = wilson(sc, n_t1)
        rows.append({"dimension": "role_family", "category": fam, "label": FAMILY_LABELS[fam], "demand_count": dc, "demand_n": n_dem, "demand_share": round(ds, 3), "supply_count": sc, "supply_n": n_t1, "supply_share": round(ss, 3),
                     "supply_ci_low": lo, "supply_ci_high": hi, "difference_pp": round(100 * (ss - ds), 1), "relative_representation": round(ss / ds, 2) if ds else None,
                     "candidate_density_T1_per_posting": round(sc / dc, 2) if dc else None, "demand_styria": int(d["styria_count"]) if d is not None else 0, "supply_styria_T1": int(fam_sty.get(fam, 0)),
                     "density_styria": round(fam_sty.get(fam, 0) / d["styria_count"], 2) if d is not None and d["styria_count"] else None, "demand_vienna": int(d["vienna_count"]) if d is not None else 0,
                     "supply_vienna_T1": int(fam_vie.get(fam, 0)), "so2025_at_respondents": so_fam.get(fam), "demand_table": "T02", "supply_population": "P_T1 (bio-declared)", "source_quality": "A/B (postings) × B (GitHub)"})
    ds01 = pd.DataFrame(rows)
    td, ts = ds01.demand_share.median(), ds01.supply_share.median()
    ds01["quadrant"] = [quadrant(d, s, td, ts) for d, s in zip(ds01.demand_share, ds01.supply_share)]
    ds01["interpretation"] = ds01.apply(lambda r: ("bio-declared supply concentrated relative to advertised demand" if r.relative_representation and r.relative_representation > 1.5 else "bio-declared supply thin relative to advertised demand" if r.relative_representation is not None and r.relative_representation < 0.67 else "supply and demand shares of similar order"), axis=1)
    write(ds01, "DS01_demand_supply_role_families", f"quadrant thresholds = medians: demand {td:.3f}, supply {ts:.3f}; demand_styria/demand_vienna = ads listing a site in the region (T02, any-site basis; T03a/DS05 give the primary-state counts); "
          "supply_styria_T1 = location-resolved bio-declared accounts (canonical Styrian denominator); Styrian supply is a complete GitHub frame (frame B), Vienna is a keyword+base-rate sample (lower bound)"
          + ("" if so_fam else "; so2025_at_respondents NOT refreshed (survey extract unavailable)"))
    all_rows += ds01.to_dict("records")

    # ---------------- DS02 titles
    t02b = L1("T02b_normalized_title_counts"); tit_sup = P_T1.bio_normalized_title.value_counts(); tit_sty = sty_T1.bio_normalized_title.value_counts()
    rows = []
    for t in sorted(set(t02b.normalized_title) | set(tit_sup.index)):
        d = t02b[t02b.normalized_title == t]; dc = int(d["count"].iloc[0]) if len(d) else 0; dsty = int(d["styria"].iloc[0]) if len(d) else 0
        sc = int(tit_sup.get(t, 0)); lo, hi = wilson(sc, n_t1)
        rows.append({"dimension": "normalized_title", "category": t, "demand_count": dc, "demand_n": n_dem, "demand_share": round(dc / n_dem, 3), "supply_count": sc, "supply_n": n_t1, "supply_share": round(sc / n_t1, 3) if n_t1 else None,
                     "supply_ci_low": lo, "supply_ci_high": hi, "difference_pp": round(100 * (sc / n_t1 - dc / n_dem), 1) if n_t1 else None, "relative_representation": round((sc / n_t1) / (dc / n_dem), 2) if n_t1 and dc else None,
                     "demand_styria": dsty, "supply_styria_T1": int(tit_sty.get(t, 0)), "demand_table": "T02b", "supply_population": "P_T1"})
    ds02 = pd.DataFrame(rows).sort_values("demand_count", ascending=False)
    write(ds02, "DS02_demand_supply_titles")
    all_rows += ds02.to_dict("records")

    # ---------------- DS03 skills (all Layer 1 tech skills) and DS04 technologies subset
    t05 = L1("T05_skills_all_tech"); n_t05 = int(t05.n.iloc[0])
    with open(ROOT / "config" / "skills_taxonomy.json", encoding="utf-8") as fh:
        taxonomy = json.load(fh)
    cat_of = {name: cat for cat, names in taxonomy.items() if not cat.startswith("_") for name in names}
    # Styrian demand share per skill (ads listing a Styrian site, with a description), from the by-styria table
    by_sty = L1("T05_skills_all_tech_by_styria")
    by_sty = by_sty[by_sty.styria_flag == "Styria"].set_index("skill")
    n_sty_desc = int(by_sty.n.iloc[0]) if len(by_sty) else 0
    rows = []
    for _, r in t05.iterrows():
        s = r["skill"]; sc = int(sup_any.get(s, 0)); pc = int(sup_proj.get(s, 0)); mc = int(sup_men.get(s, 0))
        lo, hi = wilson(sc, n_data)
        rows.append({"dimension": "skill", "category": s, "skill_category": cat_of.get(s), "demand_count": int(r["count"]), "demand_n": n_t05, "demand_share": float(r["share"]), "demand_ci_low": r.get("ci_low"), "demand_ci_high": r.get("ci_high"),
                     "demand_styria_count": int(by_sty.at[s, "count"]) if s in by_sty.index else 0, "demand_styria_n": n_sty_desc,
                     "demand_styria_share": float(by_sty.at[s, "share"]) if s in by_sty.index else 0.0,
                     "supply_count": sc, "supply_n": n_data, "supply_share": round(sc / n_data, 3) if n_data else None, "supply_ci_low": lo, "supply_ci_high": hi, "supply_mentioned_bio": mc,
                     "project_count": pc, "project_n": n_data, "project_share": round(pc / n_data, 3) if n_data else None,
                     "difference_pp": round(100 * (sc / n_data - r["share"]), 1) if n_data else None, "relative_representation": round((sc / n_data) / r["share"], 2) if n_data and r["share"] else None,
                     "evidence_gap_pp": round(100 * (r["share"] - pc / n_data), 1) if n_data else None, "demand_table": "T05", "supply_population": "P_data (any evidence) / project_demonstrated"})
    ds03 = pd.DataFrame(rows)
    sub = ds03[ds03.demand_count >= 5]
    td, ts = sub.demand_share.median(), sub.supply_share.median()
    ds03["quadrant"] = [quadrant(d, s, td, ts) if (s is not None) else None for d, s in zip(ds03.demand_share, ds03.supply_share)]
    ds03["threshold_demand"] = td; ds03["threshold_supply"] = ts
    write(ds03.sort_values("demand_count", ascending=False), "DS03_demand_supply_skills", "supply share counts any evidence (bio, repo metadata, README); project_share counts substantive-project evidence only; "
          f"demand_styria_* = ads listing a Styrian site with a description (T05 by styria, n = {n_sty_desc}; cells are small, directional only)")
    all_rows += ds03.to_dict("records")
    tech_cats = {"programming_languages", "bi_tools", "cloud_platforms", "data_platforms", "python_ecosystem", "data_engineering"}
    ds04 = ds03[ds03.skill_category.isin(tech_cats)].sort_values("demand_count", ascending=False)
    write(ds04, "DS04_demand_supply_technologies")

    # ---------------- DS05 geography
    t03 = L1("T03a_state_counts"); n_geo = int(t03.n.iloc[0])
    st_all = c[c.is_austria].region.value_counts(); st_data = P_data.region.value_counts(); st_t1 = P_T1.region.value_counts()
    rows = []
    for _, r in t03.iterrows():
        st = r["state"]; key = "unspecified (Austria)" if st == "unspecified" else st
        sc = int(st_data.get(key, 0)); tc = int(st_t1.get(key, 0)); ac = int(st_all.get(key, 0))
        frame = "complete (frame B)" if key == "Steiermark" else "keyword + base-rate sample (lower bound)"
        rows.append({"dimension": "state", "category": st, "demand_count": int(r["count"]), "demand_n": n_geo, "demand_share": float(r["share"]), "supply_all_accounts": ac, "supply_count": sc, "supply_n": n_data,
                     "supply_share": round(sc / n_data, 3) if n_data else None, "supply_T1": tc, "supply_T1_share": round(tc / n_t1, 3) if n_t1 else None,
                     "difference_pp": round(100 * (sc / n_data - r["share"]), 1) if n_data else None, "candidate_density_data_per_posting": round(sc / r["count"], 2) if r["count"] else None,
                     "candidate_density_T1_per_posting": round(tc / r["count"], 2) if r["count"] else None, "supply_frame": frame, "demand_table": "T03a"})
    ds05 = pd.DataFrame(rows)
    write(ds05, "DS05_demand_supply_geography", "demand = primary state (T03a; one state per ad); supply_T1/supply_count = location-resolved accounts; supply shares across states are NOT comparable with each other (frames differ); "
          "densities are comparable only for Styria (complete) vs the sampled states as lower bounds")
    all_rows += ds05.to_dict("records")
    fam_geo = []
    for fam in CORE_FAMILIES:
        d = t02[t02.role_family == fam].iloc[0]
        fam_geo.append({"family": fam, "label": FAMILY_LABELS[fam], "demand_AT": int(d["count"]), "demand_styria": int(d["styria_count"]), "demand_graz_area": int(d["graz_area_count"]), "demand_vienna": int(d["vienna_count"]),
                        "supply_T1_AT": int(fam_sup.get(fam, 0)), "supply_T1_styria": int(fam_sty.get(fam, 0)), "supply_T1_graz_area": int(sty_T1[sty_T1.is_graz_area].family.value_counts().get(fam, 0)), "supply_T1_vienna": int(fam_vie.get(fam, 0)),
                        "density_styria_T1_per_posting": round(fam_sty.get(fam, 0) / d["styria_count"], 2) if d["styria_count"] else None, "density_vienna_T1_per_posting_lower_bound": round(fam_vie.get(fam, 0) / d["vienna_count"], 2) if d["vienna_count"] else None})
    write(pd.DataFrame(fam_geo), "DS05b_family_by_region_demand_supply")

    # ---------------- DS06 language
    t07 = L1("T07_german_requirement_by_overall").set_index("german_requirement"); n_lang = int(t07.n.iloc[0])
    t07c = L1("T07c_posting_language").set_index("posting_language")
    t07e = L1("T07e_addressable_market_scenarios") if (TAB / "T07e_addressable_market_scenarios.csv").exists() else None
    def lang_side(sub):
        bl = sub.bio_language.dropna(); rl = sub.readme_languages.map(lambda d: d or {})
        n_b = len(bl); n_r = int((rl.map(len) > 0).sum())
        return {"bio_classified": n_b, "bio_en": int((bl == "en").sum()), "bio_de": int((bl == "de").sum()), "readme_classified": n_r, "readme_any_de": int(rl.map(lambda d: d.get("de", 0) > 0).sum()), "readme_en_only": int(rl.map(lambda d: d.get("en", 0) > 0 and d.get("de", 0) == 0).sum())}
    rows = []
    for reg, sub_d, dem_en, dem_gr, dem_n in (("Austria", P_data, int(t07c.loc["en", "count"]), int(t07.loc["required", "count"] + t07.loc["required_implied", "count"]), n_lang),
                                             ("Steiermark", sty_data, None, None, None), ("Wien", vie_data, None, None, None)):
        ls = lang_side(sub_d)
        rows.append({"dimension": "language", "region": reg, "demand_english_written_ads": dem_en, "demand_german_required_or_level_stated": dem_gr, "demand_n": dem_n,
                     "demand_english_share": round(dem_en / dem_n, 3) if dem_n else None, "demand_german_req_share": round(dem_gr / dem_n, 3) if dem_n else None, "supply_n": len(sub_d), **ls,
                     "supply_bio_en_share": round(ls["bio_en"] / ls["bio_classified"], 3) if ls["bio_classified"] else None, "supply_readme_en_only_share": round(ls["readme_en_only"] / ls["readme_classified"], 3) if ls["readme_classified"] else None,
                     "demand_table": "T07/T07c/T07e", "supply_population": "P_data", "note": "supply side measures the language candidates WRITE in, not proficiency; regional demand figures are in T07 by-state tables"})
    ds06 = pd.DataFrame(rows)
    write(ds06, "DS06_demand_supply_language")
    all_rows += ds06.to_dict("records")
    if t07e is not None:
        write(t07e.assign(supply_english_presenting_styria=int((sty_data.bio_language == "en").sum()), supply_styria_data_candidates=len(sty_data), supply_english_presenting_vienna=int((vie_data.bio_language == "en").sum()), supply_vienna_data_candidates=len(vie_data)),
              "DS06b_addressable_language_intersection", "demand scenarios from T07e vs English-presenting (bio) candidates by region; an English bio does not imply lack of German")

    # ---------------- DS07 seniority
    t08 = L1("T08_seniority_overall").set_index("seniority"); n_sen = int(t08.n.iloc[0])
    map_sup = {"intern_student": "student", "trainee_junior": "junior", "unspecified": "unlabelled", "senior": "senior", "lead_head": "lead_head"}
    sen_sup = P_T1.seniority_bio.value_counts(); sen_sty = sty_T1.seniority_bio.value_counts()
    rows = []
    for dl, sl in map_sup.items():
        dc = int(t08.loc[dl, "count"]) if dl in t08.index else 0; sc = int(sen_sup.get(sl, 0)); lo, hi = wilson(sc, n_t1)
        rows.append({"dimension": "seniority", "category": f"{dl} ↔ {sl}", "demand_count": dc, "demand_n": n_sen, "demand_share": round(dc / n_sen, 3), "supply_count": sc, "supply_n": n_t1, "supply_share": round(sc / n_t1, 3) if n_t1 else None,
                     "supply_ci_low": lo, "supply_ci_high": hi, "difference_pp": round(100 * (sc / n_t1 - dc / n_sen), 1) if n_t1 else None, "supply_styria_T1": int(sen_sty.get(sl, 0)), "demand_table": "T08", "supply_population": "P_T1",
                     "note": "demand = seniority word in the ad title; supply = seniority word in the bio; 'unspecified/unlabelled' dominate both sides"})
    ds07 = pd.DataFrame(rows)
    write(ds07, "DS07_demand_supply_seniority")
    all_rows += ds07.to_dict("records")
    acc = P_T1.groupby("seniority_bio").agg(n=("candidate_id", "size"), median_account_age_years=("account_age_years", "median"), median_projects=("n_projects", "median"), share_student=("is_student", "mean")).round(2).reset_index()
    write(acc, "DS07b_seniority_signals_supply", "title-to-experience mismatch is not measurable on GitHub (no years of experience); account age and project counts are the only tenure-like signals")

    # ---------------- DS08 education
    t11a = L1("T11a_degree_levels").set_index("degree_level"); n_ed = int(t11a.n.iloc[0]); t11b = L1("T11b_degree_fields").set_index("degree_field"); t11e = L1("T11e_degree_requirement_strength").set_index("degree_requirement")
    lv_sup = Counter(x for l in P_data.edu_levels_any for x in l); lv_t1 = Counter(x for l in P_T1.edu_levels_any for x in l)
    rows = []
    for lvl in ("Master", "Bachelor", "PhD", "HTL/Matura", "Degree (generic)"):
        dc = int(t11a.loc[lvl, "count"]) if lvl in t11a.index else 0; sc = int(lv_sup.get(lvl, 0)); tc = int(lv_t1.get(lvl, 0)); lo, hi = wilson(sc, n_data)
        rows.append({"dimension": "education_level", "category": lvl, "demand_count": dc, "demand_n": n_ed, "demand_share": round(dc / n_ed, 3), "supply_count": sc, "supply_n": n_data, "supply_share": round(sc / n_data, 3) if n_data else None,
                     "supply_ci_low": lo, "supply_ci_high": hi, "supply_T1": tc, "supply_T1_share": round(tc / n_t1, 3) if n_t1 else None, "difference_pp": round(100 * (sc / n_data - dc / n_ed), 1) if n_data else None,
                     "demand_table": "T11a", "supply_population": "P_data", "note": "demand = level named in the ad (often 'or equivalent'); supply = level wording in bio/READMEs (absence ≠ no degree)"})
    for extra, dc in (("degree wording required (T11e)", int(t11e.loc["required", "count"])), ("any degree wording (T11e required+preferred+mentioned)", int(t11e.loc[["required", "preferred", "mentioned"], "count"].sum()))):
        sc = int((P_data.edu_levels_any.map(len) > 0).sum())
        rows.append({"dimension": "education_level", "category": extra, "demand_count": dc, "demand_n": n_ed, "demand_share": round(dc / n_ed, 3), "supply_count": sc, "supply_n": n_data, "supply_share": round(sc / n_data, 3) if n_data else None,
                     "supply_ci_low": wilson(sc, n_data)[0], "supply_ci_high": wilson(sc, n_data)[1], "supply_T1": int((P_T1.edu_levels_any.map(len) > 0).sum()), "supply_T1_share": round((P_T1.edu_levels_any.map(len) > 0).mean(), 3) if n_t1 else None,
                     "difference_pp": None, "demand_table": "T11e", "supply_population": "P_data", "note": "supply = any education wording observable"})
    fd_sup = Counter(x for l in P_T1.edu_fields_any for x in l)
    for fld in t11b.index:
        sc = int(fd_sup.get(fld.replace("Field: ", ""), 0) or fd_sup.get(fld, 0)); dc = int(t11b.loc[fld, "count"]); lo, hi = wilson(sc, n_t1)
        rows.append({"dimension": "education_field", "category": fld, "demand_count": dc, "demand_n": n_ed, "demand_share": round(dc / n_ed, 3), "supply_count": sc, "supply_n": n_t1, "supply_share": round(sc / n_t1, 3) if n_t1 else None,
                     "supply_ci_low": lo, "supply_ci_high": hi, "supply_T1": sc, "supply_T1_share": round(sc / n_t1, 3) if n_t1 else None, "difference_pp": round(100 * (sc / n_t1 - dc / n_ed), 1) if n_t1 else None,
                     "demand_table": "T11b", "supply_population": "P_T1", "note": "field wording in bios only"})
    t11d = L1("T11d_certifications").set_index("certification")
    cert_sup = Counter(x for l in P_data.certifications_any for x in l)
    for cert in t11d.index:
        dc = int(t11d.loc[cert, "count"]); sc = int(cert_sup.get(cert, 0)); lo, hi = wilson(sc, n_data)
        rows.append({"dimension": "certification", "category": cert, "demand_count": dc, "demand_n": n_ed, "demand_share": round(dc / n_ed, 3), "supply_count": sc, "supply_n": n_data, "supply_share": round(sc / n_data, 3) if n_data else None,
                     "supply_ci_low": lo, "supply_ci_high": hi, "supply_T1": int(Counter(x for l in P_T1.certifications_any for x in l).get(cert, 0)), "supply_T1_share": None, "difference_pp": round(100 * (sc / n_data - dc / n_ed), 1) if n_data else None,
                     "demand_table": "T11d", "supply_population": "P_data", "note": "candidate-side certificate wording incl. capstone repositories"})
    for cert, sc in cert_sup.most_common():
        if cert not in t11d.index:
            rows.append({"dimension": "certification", "category": cert, "demand_count": 0, "demand_n": n_ed, "demand_share": 0.0, "supply_count": int(sc), "supply_n": n_data, "supply_share": round(sc / n_data, 3), "supply_ci_low": wilson(sc, n_data)[0], "supply_ci_high": wilson(sc, n_data)[1],
                         "supply_T1": None, "supply_T1_share": None, "difference_pp": round(100 * sc / n_data, 1), "demand_table": "T11d (not requested in any ad)", "supply_population": "P_data", "note": "candidate-side only"})
    ds08 = pd.DataFrame(rows)
    write(ds08, "DS08_demand_supply_education")
    all_rows += ds08.to_dict("records")

    # ---------------- DS09/DS10 capabilities × evidence
    dem_cap, n_cap, method = demand_capability_shares()
    sk_any = P_data.skills_any.map(set); sk_dem = P_data.skills_project_demonstrated.map(set); sk_men = P_data.bio_skills.map(set); sk_used = P_data.skills_used.map(set)
    themes = P_data.project_themes.map(lambda d: {k.split(":")[1] for k in (d or {})}); fmts = P_data.project_formats.map(lambda d: set((d or {}).keys()))
    s_themes = P_data.subst_themes.map(lambda d: {k.split(":")[1] for k in (d or {})}); s_fmts = P_data.subst_formats.map(lambda d: set((d or {}).keys()))
    projs = p[p.candidate_id.isin(P_data.candidate_id) & p.is_substantive]
    rows = []
    for cap, spec in CAP.items():
        ds = set(spec["demand_skills"]); th = set(spec["project_themes"])
        anyc = int((sk_any.map(lambda s: bool(s & ds)) | themes.map(lambda t: bool(t & th)) | fmts.map(lambda f: bool(f & th))).sum())
        men = int(sk_men.map(lambda s: bool(s & ds)).sum()); used = int(sk_used.map(lambda s: bool(s & ds)).sum())
        dem = int((sk_dem.map(lambda s: bool(s & ds)) | s_themes.map(lambda t: bool(t & th)) | s_fmts.map(lambda f: bool(f & th))).sum())
        nproj = int(projs.apply(lambda r: bool(set(r["skills"]) & ds) or bool((set(r["themes_analytics_domain"]) | set(r["themes_ds_method"]) | set(r["themes_engineering"]) | set(r["themes_ai"]) | set(r["formats"])) & th), axis=1).sum()) if len(projs) else 0
        d = dem_cap.get(cap, 0.0); lo, hi = wilson(anyc, n_data)
        obs = "not observable on GitHub (soft-skill wording)" if cap == "Stakeholder / communication" else "true by construction on GitHub" if cap == "Git" else "observable"
        rows.append({"dimension": "capability", "category": cap, "group": spec["group"], "observability": obs, "demand_share": d, "demand_n": n_cap, "supply_any_count": anyc, "supply_n": n_data, "supply_any_share": round(anyc / n_data, 3) if n_data else None,
                     "supply_ci_low": lo, "supply_ci_high": hi, "supply_mentioned_bio": men, "supply_used_repo_meta": used, "supply_project_demonstrated": dem, "supply_project_share": round(dem / n_data, 3) if n_data else None,
                     "substantive_projects_carrying": nproj, "n_substantive_projects": int(len(projs)), "difference_pp": round(100 * (anyc / n_data - d), 1) if n_data else None, "relative_representation": round((anyc / n_data) / d, 2) if n_data and d else None,
                     "evidence_gap_pp": round(100 * (d - dem / n_data), 1) if n_data else None, "professional_evidence": "not observable on GitHub", "demand_method": method})
    ds10 = pd.DataFrame(rows)
    td, ts = ds10.demand_share.median(), ds10.supply_any_share.median()
    ds10["quadrant"] = [quadrant(d, s, td, ts) for d, s in zip(ds10.demand_share, ds10.supply_any_share)]
    def label(r):
        if r.demand_share >= td and r.supply_project_share is not None and r.supply_project_share < 0.5 * r.demand_share:
            return "demanded, rarely project-demonstrated (demonstration opportunity candidate)"
        if r.demand_share >= td and r.supply_any_share >= ts:
            return "core market capability: demanded and commonly evidenced"
        if r.demand_share < td and r.supply_any_share >= ts:
            return "commonly evidenced, less demanded (not differentiating)"
        if r.demand_share >= td:
            return "demanded, less commonly evidenced"
        return "smaller on both sides"
    ds10["interpretation"] = ds10.apply(label, axis=1)
    ds10["threshold_demand"] = td; ds10["threshold_supply"] = ts
    write(ds10.sort_values("demand_share", ascending=False), "DS10_demand_supply_capability_evidence", "demand share = share of core postings (with description) mentioning any skill of the capability; supply = P_data candidates by evidence strength")
    all_rows += ds10.to_dict("records")
    ds09 = ds10[["category", "group", "demand_share", "supply_any_share", "supply_project_share", "substantive_projects_carrying", "n_substantive_projects", "evidence_gap_pp", "interpretation"]].rename(columns={"category": "capability"})
    ds09["project_carry_share"] = (ds09.substantive_projects_carrying / ds09.n_substantive_projects).round(3) if len(projs) else None
    write(ds09.sort_values("demand_share", ascending=False), "DS09_demand_supply_project_evidence")

    # ---------------- DS11 candidate positioning clusters vs demand
    c23 = L1("C23_positioning_clusters") if (TAB / "C23_positioning_clusters.csv").exists() else pd.DataFrame()
    t05_share = t05.set_index("skill")["share"].to_dict()
    rows = []
    for _, r in c23.iterrows():
        feats = [f.split(" ")[0] for f in str(r.get("defining_features", "")).split("; ") if f]
        skills = [f for f in feats if f in t05_share]
        rows.append({"cluster": int(r["cluster"]), "size": int(r["size"]), "share_of_P_data": r["share"], "defining_features": r["defining_features"], "families_T1": r["families_T1"], "styria": r["styria"], "vienna": r["vienna"],
                     "mean_demand_share_of_defining_skills": round(float(np.mean([t05_share[s] for s in skills])), 3) if skills else None, "max_demand_share_of_defining_skills": round(float(max(t05_share[s] for s in skills)), 3) if skills else None,
                     "median_projects": r["median_projects"], "share_any_cert": r["share_any_cert"], "top_titles": r["top_titles"]})
    write(pd.DataFrame(rows), "DS11_demand_supply_positioning_clusters", "cluster defining features from C23 scored against Layer 1 mention shares (T05)")

    # ---------------- DS12 marketing × data
    t05b = L1("T05_skills_business_domain").set_index("skill")["share"].to_dict() if (TAB / "T05_skills_business_domain.csv").exists() else {}
    t05s = {**t05_share, **t05b}
    mk_dem = {"marketing_analytics_postings": int(t02[t02.role_family == "marketing_analytics"]["count"].iloc[0]), "marketing_analytics_styria": int(t02[t02.role_family == "marketing_analytics"]["styria_count"].iloc[0]),
              "marketing_wording_share_T05": t05s.get("Marketing"), "crm_share": t05s.get("CRM"), "customer_analytics_share": t05s.get("Customer Analytics"), "web_analytics_share": t05s.get("Web/Digital Analytics"),
              "ab_testing_share": t05s.get("A/B Testing / Experimentation"), "causal_inference_share": t05s.get("Causal Inference"), "ecommerce_share": t05s.get("E-Commerce")}
    mk_sup = {"T1_marketing_analytics_family": int(fam_sup.get("marketing_analytics", 0)), "T1_bios_naming_marketing": int(P_T1.prior_domains.map(lambda l: "marketing" in l).sum()),
              "P_data_marketing_capability_any": int(sk_any.map(lambda s: bool(s & set(CAP["Marketing / CRM / web analytics"]["demand_skills"]))).sum() + 0),
              "P_data_marketing_theme_projects": int(themes.map(lambda t: bool(t & {"marketing", "customer", "ecommerce"})).sum()),
              "P_data_experimentation_projects": int(themes.map(lambda t: "experimentation" in t).sum()), "P_data_causal_projects": int(themes.map(lambda t: "causal_inference" in t).sum()),
              "P_data_marketing_AND_python_sql": int((themes.map(lambda t: bool(t & {"marketing", "customer", "ecommerce"})) & sk_any.map(lambda s: "Python" in s and "SQL" in s)).sum()),
              "P_data_marketing_AND_experimentation": int((themes.map(lambda t: bool(t & {"marketing", "customer", "ecommerce"})) & themes.map(lambda t: bool(t & {"experimentation", "causal_inference"}))).sum()),
              "styria_marketing_theme_candidates": int(themes[P_data.is_styria.values].map(lambda t: bool(t & {"marketing", "customer", "ecommerce"})).sum())}
    ds12 = pd.DataFrame([{"side": "demand", **{k: v for k, v in mk_dem.items()}, "n": n_dem, "table": "T02/T05"}, {"side": "supply", **{k: v for k, v in mk_sup.items()}, "n": n_data, "table": "C22d/C24"}])
    write(ds12, "DS12_marketing_x_data_intersection")

    # ---------------- DS13 Styria / Graz focus
    sty_all = c[c.frame_b & c.is_austria]            # frame-B complete-Styria subset
    sty_loc = c[c.is_austria & c.is_styria]          # location-resolved (canonical, OQ-19)
    sty_primary = int(t03[t03.state == "Steiermark"]["count"].iloc[0]) if (t03.state == "Steiermark").any() else 0
    t07e_sty = t07e[t07e.scope == "Styria"].iloc[0] if t07e is not None and (t07e.scope == "Styria").any() else None
    ds13 = pd.DataFrame([{"measure": "core data postings listing a Styrian site (T02, any-site basis)", "value": int(t02.styria_count.sum())},
                         {"measure": "core data postings with Styria as primary state (T03a)", "value": sty_primary},
                         {"measure": "core data postings, Graz area (T02, any-site basis)", "value": int(t02.graz_area_count.sum())},
                         {"measure": "Styrian GitHub accounts, location-resolved (canonical)", "value": len(sty_loc)},
                         {"measure": "  of which data-signal (T1+T2), location-resolved", "value": len(sty_data)},
                         {"measure": "  of which bio-declared data role (T1), location-resolved (canonical)", "value": len(sty_T1)},
                         {"measure": "  of which T1 in Graz area, location-resolved", "value": int(sty_T1.is_graz_area.sum())},
                         {"measure": "Styrian GitHub accounts with ≥1 public repo (frame-B complete-Styria subset)", "value": len(sty_all)}, {"measure": "  of which data-signal (T1+T2), frame-B subset", "value": int(sty_all.is_data.sum())},
                         {"measure": "  of which bio-declared data role (T1), frame-B subset", "value": int(sty_all.is_t1.sum())}, {"measure": "  of which T1 in Graz area, frame-B subset", "value": int((sty_all.is_t1 & sty_all.is_graz_area).sum())},
                         {"measure": "  T1 students, frame-B subset", "value": int((sty_all.is_t1 & sty_all.is_student).sum())}, {"measure": "  T1 with ≥1 documented project, frame-B subset", "value": int((sty_all.is_t1 & (sty_all.n_documented_projects >= 1)).sum())},
                         {"measure": "  data-signal with any push in 12 months, frame-B subset", "value": int((sty_all.is_data & (sty_all.n_active_12m >= 1)).sum())}, {"measure": "  data-signal with English bio, frame-B subset", "value": int((sty_all.is_data & (sty_all.bio_language == "en")).sum())},
                         {"measure": "  data-signal with hireable flag, frame-B subset", "value": int((sty_all.is_data & sty_all.hireable).sum())},
                         {"measure": "T1 candidates (location-resolved) per core posting listing a Styrian site", "value": round(len(sty_T1) / int(t02.styria_count.sum()), 2) if t02.styria_count.sum() else None},
                         {"measure": "data-signal candidates (location-resolved) per core posting listing a Styrian site", "value": round(len(sty_data) / int(t02.styria_count.sum()), 2) if t02.styria_count.sum() else None},
                         {"measure": "English-written Styrian ads without stated German requirement (T07e, any-site basis)",
                          "value": f"{int(t07e_sty.english_posting_no_german_req)} of {int(t07e_sty.n)} (Layer 1)" if t07e_sty is not None else None},
                         {"measure": "Vienna: core postings (T03a) / T1 candidates in sample (lower bound)", "value": f"{int(t03[t03.state == 'Wien']['count'].iloc[0])} / {int(st_t1.get('Wien', 0))}"}])
    jb = L1("JB01_yearly_counts_long") if (TAB / "JB01_yearly_counts_long.csv").exists() else None
    flow = ""
    if jb is not None:
        jb_sty = jb[(jb.bundesland == "Steiermark") & jb.beruf.str.contains("Data Scientist", na=False)].groupby("year")["ads"].sum()
        if len(jb_sty) and t02.styria_count.sum():
            flow = (f"; the yearly flow of Styrian ads (AMS JobBarometer 'Data Scientist': {int(jb_sty.iloc[-1])} in {int(jb_sty.index[-1])}) "
                    f"is ~{jb_sty.iloc[-1] / t02.styria_count.sum():.0f}× the one-day stock")
    write(ds13, "DS13_styria_graz_demand_supply", "Styrian supply is the only complete GitHub frame; canonical Styrian supply denominators are location-resolved, "
          "the frame-B complete-Styria subset is shown separately" + flow)

    # ---------------- JSON exports
    ms = json.loads((OUT / "market_summary.json").read_text(encoding="utf-8"))
    meta = {"generated": pd.Timestamp.now().isoformat(),
            "demand_vintage": f"{str(ms['collected_at_range']['min'])[:10]} (Layer 1 snapshot, {ms['counts']['core_canonical']} core postings)",
            "supply_vintage": json.loads((PROC / "supply_build_manifest.json").read_text())["collection_date"],
            "supply_populations": {"P_data": n_data, "P_T1": n_t1, "styria_location_resolved_accounts": len(sty_loc), "styria_T1_location_resolved": len(sty_T1),
                                   "styria_frame_B_accounts": len(sty_all), "styria_T1_frame_B_subset": int(sty_all.is_t1.sum())}, "taxonomy_version": CFG["version"],
            "reading_rules": ["demand share = share of postings mentioning an item", "supply share = share of observed GitHub data-signal candidates with evidence", "different universes: compare orders of magnitude and rankings, not exact percentages",
                              "quadrant thresholds are medians of the joined set", "no single composite score is computed"]}
    (OUT / "demand_supply_matrix.json").write_text(json.dumps({**meta, "rows": all_rows}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "demand_supply_capabilities.json").write_text(json.dumps({**meta, "capabilities": ds10.to_dict("records"), "demand_method": method}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "demand_supply_geography.json").write_text(json.dumps({**meta, "by_state": ds05.to_dict("records"), "family_by_region": fam_geo, "styria": ds13.to_dict("records")}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "demand_supply_language.json").write_text(json.dumps({**meta, "rows": ds06.to_dict("records"), "addressable_scenarios": t07e.to_dict("records") if t07e is not None else None, "styria_english_presenting_data_candidates": int((sty_data.bio_language == "en").sum()), "styria_data_candidates": len(sty_data)}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "demand_supply_seniority.json").write_text(json.dumps({**meta, "rows": ds07.to_dict("records"), "supply_signals": acc.to_dict("records")}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "demand_supply_education.json").write_text(json.dumps({**meta, "rows": ds08.to_dict("records")}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"families": ds01[["category", "demand_count", "supply_count", "relative_representation", "quadrant"]].to_dict("records"), "capability_method": method}, indent=1))


if __name__ == "__main__":
    main()
