"""Layer 2 candidate-supply analysis: tables C01–C13 (coverage, titles, families, geography, seniority, languages,
education, certifications, technologies, capabilities, co-occurrence), C22 transitions, C23 positioning clusters,
and outputs/supply_*.json. Every table carries n; shares are shares of the stated population.

Populations (docs/supply-methodology.md §4):
  P_all   GitHub accounts with an Austrian location signal (state or country named)              — the sampled frame
  P_data  P_all ∩ data-signal (tier T1 bio-declared or T2 repo-evidenced)                       — "observed data-signal candidates"
  P_T1    P_all ∩ T1 (bio declares a data role; the only rows with a role family)                — "bio-declared candidates"

Usage: python src/analysis/supply_analysis.py
"""
from __future__ import annotations

import itertools
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from supply_common import (CAP, CFG, CORE_FAMILIES, FAMILY_LABELS, OUT, PROC, REGIONS, ROOT, concentration, load_candidates, load_evidence,
                           load_projects, share_table, wilson, write)


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


C23_COLUMNS = ["cluster", "size", "share", "defining_features", "families_T1", "share_T1", "styria", "vienna", "students", "median_projects",
               "median_documented", "share_edu_wording", "share_any_cert", "top_titles", "silhouette_k"]


def by_group(df: pd.DataFrame, col_list: str, group: str, n_label: str, min_n: int = 5, top: int = 25) -> pd.DataFrame:
    parts = []
    for g, sub in df.groupby(group):
        if len(sub) < min_n:
            continue
        t = share_table(sub[col_list], len(sub), "item", top=top)
        t.insert(0, group, g)
        parts.append(t)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


RAW_TITLE_SPLIT = re.compile(r"\s*(?:\||•|·|—|–|\s-\s|,|;|/|\bat\b|\b@\b|\bbei\b|\bfor\b|\bwith\b|\(|\n)\s*", re.I)


def raw_bio_title(bio: str) -> str | None:
    if not bio:
        return None
    first = RAW_TITLE_SPLIT.split(bio.strip(), maxsplit=1)[0].strip(" .:!👋🚀")
    first = re.sub(r"^(?:i am|i'm|im|ich bin|hi,? i am|hello,? i am|a|an)\s+", "", first, flags=re.I).strip()
    if 2 < len(first) <= 60:
        return first.lower()
    return None


def main() -> None:
    c = load_candidates(); refuse_if_redacted(c); p = load_projects(); e = load_evidence()
    P_all = c[c["is_austria"]]; P_data = c[c["is_data"]]; P_T1 = c[c["is_t1"] & c["is_austria"]]
    n_all, n_data, n_t1 = len(P_all), len(P_data), len(P_T1)
    man = json.loads((PROC / "supply_build_manifest.json").read_text(encoding="utf-8"))

    # ---------------- C01 source coverage
    rows = []
    for fr in ("A", "B", "C"):
        sub = c[c[f"frame_{fr.lower()}"]]
        rows.append({"frame": fr, "description": {"A": "bio keyword × Austrian location token", "B": "complete Styrian population (≥1 public repo)", "C": "base-rate sample, other regions (≥1 public repo, capped per created-year slice)"}[fr],
                     "accounts": len(sub), "austrian_location": int(sub["is_austria"].sum()), "data_signal": int(sub["is_data"].sum()), "bio_declared": int((sub["is_t1"] & sub["is_austria"]).sum()),
                     "data_signal_share": round(sub["is_data"].mean(), 3) if len(sub) else None, "share_with_bio": round(sub["has_bio"].mean(), 3) if len(sub) else None})
    rows.append({"frame": "all", "description": "union of frames", "accounts": len(c[c.source == "github"]), "austrian_location": n_all, "data_signal": n_data, "bio_declared": n_t1,
                 "data_signal_share": round(n_data / n_all, 3) if n_all else None, "share_with_bio": round(P_all["has_bio"].mean(), 3) if n_all else None})
    c01 = pd.DataFrame(rows)
    c01["source"] = "GitHub REST API"; c01["source_quality"] = "B"; c01["collection_date"] = man["collection_date"]
    c01["n_search_rows"] = man["n_search_rows"]; c01["n_repos_listed"] = man["n_repos_listed"]; c01["n_data_repos"] = man["n_data_repos"]; c01["n_readmes_fetched"] = man["n_readmes_fetched"]
    c01["linkedin_manual_records"] = man.get("n_candidates_linkedin_manual", 0)
    write(c01, "C01_candidate_source_coverage")
    tiers = share_table(P_all["data_tier"], n_all, "data_tier", explode=False)
    write(tiers, "C01a_data_tier_distribution", "population: P_all (Austrian-located GitHub accounts across all frames; frame mix is not a random sample of Austria)")
    tier_frame = P_all.groupby(["data_tier"]).agg(n=("candidate_id", "size"), frame_a=("frame_a", "sum"), frame_b=("frame_b", "sum"), frame_c=("frame_c", "sum")).reset_index()
    write(tier_frame, "C01b_tier_by_frame")

    # ---------------- C02 raw bio titles (aggregate; only phrases used by >= 3 accounts are written)
    P_T1 = P_T1.assign(raw_title=P_T1["bio"].map(raw_bio_title))
    c02 = share_table(P_T1["raw_title"], n_t1, "raw_bio_title", min_count=3, explode=False)
    write(c02, "C02_raw_bio_title_distribution", "population: P_T1; first segment of the bio, lower-cased; phrases with < 3 accounts suppressed")
    conc_raw = concentration(P_T1["raw_title"].value_counts())
    # ---------------- C03 normalised titles, C04 families
    c03 = share_table(P_T1["bio_normalized_title"], n_t1, "normalized_title", explode=False)
    c03["styria"] = [int((P_T1[P_T1.bio_normalized_title == t]["is_styria"]).sum()) for t in c03.normalized_title]
    c03["vienna"] = [int((P_T1[P_T1.bio_normalized_title == t]["is_vienna"]).sum()) for t in c03.normalized_title]
    c03["family"] = [P_T1[P_T1.bio_normalized_title == t]["family"].iloc[0] for t in c03.normalized_title]
    write(c03, "C03_normalized_title_distribution", "population: P_T1 (bio-declared); title = Layer 1 normalized title assigned from the bio")
    conc_norm = concentration(P_T1["bio_normalized_title"].value_counts())
    c04 = share_table(P_T1["family"], n_t1, "role_family", explode=False)
    c04["family_label"] = c04.role_family.map(FAMILY_LABELS)
    for reg, flag in (("styria", "is_styria"), ("graz_area", "is_graz_area"), ("vienna", "is_vienna")):
        c04[reg] = [int(P_T1[(P_T1.family == f)][flag].sum()) for f in c04.role_family]
    c04["students"] = [int(P_T1[(P_T1.family == f)]["is_student"].sum()) for f in c04.role_family]
    c04["academic"] = [int(P_T1[(P_T1.family == f)]["is_academic"].sum()) for f in c04.role_family]
    write(c04, "C04_role_family_distribution", "population: P_T1; families from Layer 1 taxonomy applied to bios; T2 candidates have no family")
    adj = P_all[P_all.is_bio_adjacent]
    c04a = share_table(adj["bio_role_family"], len(P_all), "adjacent_family", explode=False); c04a["family_label"] = c04a.adjacent_family.map(FAMILY_LABELS)
    c04a["of_which_repo_evidenced_T2"] = [int((adj[adj.bio_role_family == f].data_tier == "T2_repo_evidenced").sum()) for f in c04a.adjacent_family]
    write(c04a, "C04a_adjacent_bio_families", "population: P_all; bios with generic ML/AI/data wording or AI-software/other-data titles are ADJACENT, not declared data roles; they count as data-signal only via repository evidence (T2)")
    c04b = pd.DataFrame([{"measure": k, "raw_bio_titles": conc_raw[k], "normalized_titles": conc_norm[k]} for k in conc_raw])
    write(c04b, "C04b_title_concentration", "population: P_T1; entropy in bits; HHI = sum of squared shares")

    # ---------------- C05 geography
    c05 = share_table(P_all["region"], n_all, "state", explode=False); c05["population"] = "P_all"
    c05d = share_table(P_data["region"], n_data, "state", explode=False); c05d["population"] = "P_data"
    c05t = share_table(P_T1["region"], n_t1, "state", explode=False); c05t["population"] = "P_T1"
    write(pd.concat([c05, c05d, c05t], ignore_index=True), "C05_geography_by_state", "frames are not proportional to population: Styria is complete (frame B), Vienna/others are keyword + base-rate samples; compare within-frame shares, not across states")
    geo_rows = []
    for name, sub in (("P_all", P_all), ("P_data", P_data), ("P_T1", P_T1)):
        n = len(sub)
        geo_rows.append({"population": name, "n": n, "vienna": int(sub.is_vienna.sum()), "styria": int(sub.is_styria.sum()), "graz_area": int(sub.is_graz_area.sum()), "graz_city": int(sub.is_graz_city.sum()),
                         "austria_only": int((sub.geo_confidence == "austria_only").sum()), "multi_location": int(sub.multi_location.sum()), "foreign_place_also_named": int(sub.foreign_place_named.sum()),
                         "hireable_flag": int(sub.hireable.sum()), "hireable_share": round(sub.hireable.mean(), 3) if n else None})
    write(pd.DataFrame(geo_rows), "C05a_geo_summary", "styria / graz_area = location-resolved accounts (resolved location in Styria): the canonical Styrian "
          "denominators (OQ-19); the frame-B complete-Styria subset is C05c")
    fam_region = P_T1.assign(region_group=P_T1.region.map(lambda s: s if s in ("Wien", "Steiermark", "Oberösterreich", "Salzburg", "Tirol") else ("unspecified (Austria)" if s == "unspecified (Austria)" else "other Bundesland")))
    c05b = fam_region.groupby(["family", "region_group"]).size().unstack(fill_value=0).reset_index()
    c05b["family_label"] = c05b.family.map(FAMILY_LABELS); c05b["total"] = c05b[[col for col in c05b.columns if col not in ("family", "family_label")]].sum(axis=1)
    write(c05b, "C05b_family_by_region", "population: P_T1 counts (not shares): frame B makes Styria complete, other regions are samples")
    # Styria complete-frame detail: data-signal share among all Styrian accounts with >= 1 repo
    sty = c[c.frame_b & c.is_austria]
    c05c = pd.DataFrame([{"population": "Styrian accounts, frame-B complete-Styria subset (≥1 public repo)", "n": len(sty), "with_bio": int(sty.has_bio.sum()), "T1_bio_declared": int(sty.is_t1.sum()),
                          "T2_repo_evidenced": int((sty.data_tier == "T2_repo_evidenced").sum()), "T3_weak": int((sty.data_tier == "T3_weak_repo_signal").sum()),
                          "data_signal_share": round(sty.is_data.mean(), 3) if len(sty) else None, "graz_area": int(sty.is_graz_area.sum()), "students_among_T1": int((sty.is_t1 & sty.is_student).sum()),
                          "hireable": int(sty.hireable.sum()), "active_12m_share": round((sty.n_active_12m > 0).mean(), 3) if len(sty) else None}])
    write(c05c, "C05c_styria_complete_frame", "frame-B complete-Styria subset: accounts found by the Styrian place-name search with ≥1 public repo; "
          "the canonical location-resolved Styrian counts (all accounts, P_data, P_T1) are in C05a")

    # ---------------- C06 seniority
    c06 = share_table(P_T1["seniority_bio"], n_t1, "seniority", explode=False); c06["population"] = "P_T1"
    c06d = share_table(P_data["seniority_bio"], n_data, "seniority", explode=False); c06d["population"] = "P_data"
    write(pd.concat([c06, c06d], ignore_index=True), "C06_seniority_distribution", "explicit bio wording only; 'unlabelled' = bio without a seniority word; 'unknown' = no bio")
    c06b = P_T1.groupby(["family", "seniority_bio"]).size().unstack(fill_value=0).reset_index(); c06b["family_label"] = c06b.family.map(FAMILY_LABELS)
    write(c06b, "C06b_seniority_by_family")
    c06c = P_T1.assign(reg=P_T1.region.map(lambda s: s if s in ("Wien", "Steiermark") else "other/unspecified")).groupby(["reg", "seniority_bio"]).size().unstack(fill_value=0).reset_index()
    write(c06c, "C06c_seniority_by_region")
    c06d2 = P_T1.groupby("seniority_bio").agg(n=("candidate_id", "size"), median_account_age_years=("account_age_years", "median"), median_public_repos=("public_repos", "median"),
                                              median_followers=("followers", "median"), share_hireable=("hireable", "mean"), share_student=("is_student", "mean"), share_academic=("is_academic", "mean")).round(3).reset_index()
    write(c06d2, "C06d_seniority_vs_account_signals", "account age is tenure on GitHub, not years of experience")
    flags = pd.DataFrame([{"population": "P_T1", "n": n_t1, "student": int(P_T1.is_student.sum()), "academic": int(P_T1.is_academic.sum()), "hireable": int(P_T1.hireable.sum()),
                           "has_company": int(P_T1.has_company.sum()), "transition_explicit": int(P_T1.transition_explicit.sum())}])
    write(flags, "C06e_status_flags")

    # ---------------- C07 language (presentation language only)
    rows = []
    for name, sub in (("P_all", P_all), ("P_data", P_data), ("P_T1", P_T1)):
        bl = sub["bio_language"].dropna(); n = len(bl)
        for lang in ("en", "de", "mixed"):
            k = int((bl == lang).sum()); lo, hi = wilson(k, n)
            rows.append({"population": name, "signal": "bio language (bios > 40 chars)", "value": lang, "count": k, "n": n, "share": round(k / n, 3) if n else None, "ci_low": lo, "ci_high": hi})
        rl = sub["readme_languages"].map(lambda d: d or {})
        n2 = int((rl.map(len) > 0).sum())
        any_de = int(rl.map(lambda d: d.get("de", 0) > 0).sum()); only_en = int(rl.map(lambda d: d.get("en", 0) > 0 and d.get("de", 0) == 0).sum())
        rows.append({"population": name, "signal": "README language (candidates with ≥1 classified README)", "value": "any German README", "count": any_de, "n": n2, "share": round(any_de / n2, 3) if n2 else None, **dict(zip(("ci_low", "ci_high"), wilson(any_de, n2)))})
        rows.append({"population": name, "signal": "README language (candidates with ≥1 classified README)", "value": "English-only READMEs", "count": only_en, "n": n2, "share": round(only_en / n2, 3) if n2 else None, **dict(zip(("ci_low", "ci_high"), wilson(only_en, n2)))})
    c07 = pd.DataFrame(rows)
    write(c07, "C07_language_presentation", "GitHub does not expose language proficiency; this measures the language candidates WRITE in (bio, README). CEFR-type supply is NOT observable here (docs/supply-methodology.md §6)")

    # ---------------- C08 education
    c08 = share_table(P_data["edu_levels_any"], n_data, "education_level"); c08["population"] = "P_data"
    c08t = share_table(P_T1["edu_levels_any"], n_t1, "education_level"); c08t["population"] = "P_T1"
    none_d = int((P_data["edu_levels_any"].map(len) == 0).sum()); none_t = int((P_T1["edu_levels_any"].map(len) == 0).sum())
    extra = pd.DataFrame([{"education_level": "no education wording observable", "count": none_d, "n": n_data, "share": round(none_d / n_data, 3) if n_data else None, "population": "P_data", **dict(zip(("ci_low", "ci_high"), wilson(none_d, n_data)))},
                          {"education_level": "no education wording observable", "count": none_t, "n": n_t1, "share": round(none_t / n_t1, 3) if n_t1 else None, "population": "P_T1", **dict(zip(("ci_low", "ci_high"), wilson(none_t, n_t1)))}])
    write(pd.concat([c08, c08t, extra], ignore_index=True), "C08_education_levels", "wording in bios and project READMEs; absence ≠ no degree")
    write(share_table(P_T1["edu_fields_any"], n_t1, "education_field"), "C08b_education_fields", "population: P_T1; field wording in bios")
    write(share_table(P_data["edu_institutions_any"], n_data, "institution", min_count=3), "C08c_institutions_named", "population: P_data; Austrian institutions named in bios/READMEs (count ≥ 3)")
    write(by_group(P_T1, "edu_levels_any", "family", "P_T1"), "C08d_education_by_family")
    write(by_group(P_T1.assign(reg=P_T1.region.map(lambda s: s if s in ("Wien", "Steiermark") else "other/unspecified")), "edu_levels_any", "reg", "P_T1"), "C08e_education_by_region")

    # ---------------- C09 certifications
    c09 = share_table(P_data["certifications_any"], n_data, "certification"); c09["population"] = "P_data"
    write(c09, "C09_certifications", "population: P_data; wording in bios, repo names/descriptions and READMEs (e.g. capstone repositories)")
    per = P_data["certifications_any"].map(lambda l: len([x for x in l if x != "Certification (any mention)"]))
    c09b = share_table(per.map(lambda k: "0" if k == 0 else "1" if k == 1 else "2" if k == 2 else "3+"), n_data, "certifications_per_candidate", explode=False)
    write(c09b, "C09b_certifications_per_candidate")
    write(by_group(P_T1, "certifications_any", "family", "P_T1"), "C09c_certifications_by_family")
    write(by_group(P_T1, "certifications_any", "seniority_bio", "P_T1"), "C09d_certifications_by_seniority")

    # ---------------- C10 technologies with evidence strength
    ev = e[e.candidate_id.isin(P_data.candidate_id)]
    agg = ev.groupby("skill").agg(category=("category", "first"), any_evidence=("candidate_id", "nunique"), mentioned=("mentioned", "sum"), used=("used", "sum"),
                                  demonstrated=("demonstrated", "sum"), project_demonstrated=("project_demonstrated", "sum")).reset_index()
    agg["n"] = n_data
    for col in ("any_evidence", "mentioned", "used", "demonstrated", "project_demonstrated"):
        agg[col + "_share"] = (agg[col] / n_data).round(3)
    ci = [wilson(int(k), n_data) for k in agg.any_evidence]; agg["ci_low"] = [x[0] for x in ci]; agg["ci_high"] = [x[1] for x in ci]
    agg = agg.sort_values("any_evidence", ascending=False)
    agg["rank"] = range(1, len(agg) + 1)
    write(agg, "C10_technologies_evidence", "population: P_data; mentioned = bio; used = repo metadata/primary language; demonstrated = README of a documented project; project_demonstrated = and not educational")
    write(by_group(P_T1, "skills_any", "family", "P_T1", top=20), "C10b_technologies_by_family")
    write(by_group(P_data.assign(reg=P_data.region.map(lambda s: s if s in ("Wien", "Steiermark") else "other/unspecified")), "skills_any", "reg", "P_data", top=25), "C10c_technologies_by_region")
    write(by_group(P_T1, "skills_any", "seniority_bio", "P_T1", top=20), "C10d_technologies_by_seniority")
    write(by_group(P_data, "skills_any", "data_tier", "P_data", top=25), "C10e_technologies_by_tier")

    # ---------------- C11 capabilities
    rows = []
    sk_any = P_data["skills_any"].map(set); sk_dem = P_data["skills_project_demonstrated"].map(set); sk_men = P_data["bio_skills"].map(set)
    themes = P_data["project_themes"].map(lambda d: {k.split(":")[1] for k in (d or {})})
    fmts = P_data["project_formats"].map(lambda d: set((d or {}).keys()))
    s_themes = P_data["subst_themes"].map(lambda d: {k.split(":")[1] for k in (d or {})})
    s_fmts = P_data["subst_formats"].map(lambda d: set((d or {}).keys()))
    for cap, spec in CAP.items():
        ds = set(spec["demand_skills"]); th = set(spec["project_themes"])
        anyc = int((sk_any.map(lambda s: bool(s & ds)) | themes.map(lambda t: bool(t & th)) | fmts.map(lambda f: bool(f & th))).sum())
        men = int(sk_men.map(lambda s: bool(s & ds)).sum())
        dem = int((sk_dem.map(lambda s: bool(s & ds)) | s_themes.map(lambda t: bool(t & th)) | s_fmts.map(lambda f: bool(f & th))).sum())
        lo, hi = wilson(anyc, n_data)
        rows.append({"capability": cap, "group": spec["group"], "candidates_any": anyc, "candidates_mentioned_bio": men, "candidates_project_demonstrated": dem, "n": n_data,
                     "share_any": round(anyc / n_data, 3) if n_data else None, "share_project_demonstrated": round(dem / n_data, 3) if n_data else None, "ci_low": lo, "ci_high": hi})
    c11 = pd.DataFrame(rows).sort_values("candidates_any", ascending=False)
    write(c11, "C11_capabilities_evidence", "population: P_data; capability = any of its skills/themes (config/capability_map.json)")

    # ---------------- C12/C13 co-occurrence
    top = agg.head(25).skill.tolist()
    pairs = Counter(); single = Counter()
    for s in sk_any:
        t = [x for x in s if x in top]
        for x in t:
            single[x] += 1
        for a, b in itertools.combinations(sorted(t), 2):
            pairs[(a, b)] += 1
    rows = [{"skill_a": a, "skill_b": b, "both": k, "n": n_data, "share_both": round(k / n_data, 3), "share_of_a": round(k / single[a], 3), "share_of_b": round(k / single[b], 3),
             "lift": round((k / n_data) / ((single[a] / n_data) * (single[b] / n_data)), 2)} for (a, b), k in pairs.most_common(150)]
    write(pd.DataFrame(rows), "C12_technology_cooccurrence", "population: P_data; skills_any")
    capsets = []
    for s, t, f in zip(sk_any, themes, fmts):
        capsets.append({cap for cap, spec in CAP.items() if (s & set(spec["demand_skills"])) or (t & set(spec["project_themes"])) or (f & set(spec["project_themes"]))})
    cp = Counter(); cs = Counter()
    for st in capsets:
        for x in st:
            cs[x] += 1
        for a, b in itertools.combinations(sorted(st), 2):
            cp[(a, b)] += 1
    c13_rows = [{"capability_a": a, "capability_b": b, "both": k, "n": n_data, "share_both": round(k / n_data, 3), "lift": round((k / n_data) / ((cs[a] / n_data) * (cs[b] / n_data)), 2)} for (a, b), k in cp.most_common(120)]
    write(pd.DataFrame(c13_rows), "C13_capability_cooccurrence")

    # ---------------- C22 transitions
    tr = P_T1[P_T1.transition_explicit | (P_T1.prior_domains.map(len) > 0)]
    c22 = pd.DataFrame([{"population": "P_T1", "n": n_t1, "explicit_transition_wording": int(P_T1.transition_explicit.sum()), "share_explicit": round(P_T1.transition_explicit.mean(), 3) if n_t1 else None,
                         "any_prior_domain_named": int((P_T1.prior_domains.map(len) > 0).sum()), "share_prior_domain": round((P_T1.prior_domains.map(len) > 0).mean(), 3) if n_t1 else None}])
    write(c22, "C22_transition_signals", "prior domain named in the same bio as a data role is a weak signal (it may be the current domain, not a former one); explicit wording ('former', 'turned', 'career change') is the strong signal")
    pd_counts = share_table(P_T1["prior_domains"], n_t1, "prior_domain"); pd_counts["population"] = "P_T1"
    pd_expl = share_table(P_T1[P_T1.transition_explicit]["prior_domains"], int(P_T1.transition_explicit.sum()), "prior_domain"); pd_expl["population"] = "P_T1 with explicit transition wording"
    write(pd.concat([pd_counts, pd_expl], ignore_index=True), "C22b_prior_domains")
    dest = P_T1.explode("prior_domains").dropna(subset=["prior_domains"]).groupby(["prior_domains", "family"]).size().unstack(fill_value=0).reset_index()
    write(dest, "C22c_prior_domain_by_destination_family", "counts of P_T1 bios naming a prior domain, by the data family the bio maps to")
    mk = P_T1[P_T1.prior_domains.map(lambda l: "marketing" in l)]
    c22d = pd.DataFrame([{"population": "P_T1 bios naming marketing", "n": len(mk), "explicit_transition": int(mk.transition_explicit.sum()), "families": json.dumps(mk.family.value_counts().to_dict()),
                          "seniority": json.dumps(mk.seniority_bio.value_counts().to_dict()), "regions": json.dumps(mk.region.value_counts().to_dict()), "median_projects": float(mk.n_projects.median()) if len(mk) else None,
                          "top_skills": "; ".join(f"{k} ({v})" for k, v in Counter(x for l in mk.skills_any for x in l).most_common(10))}])
    write(c22d, "C22d_marketing_named_bios")

    # ---------------- C23 positioning clusters (k-means on binary skill/theme/format matrix)
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, silhouette_score
    feats = sorted(set(agg.head(35).skill) | {f"theme:{k}" for k in ("marketing", "customer", "finance", "sales", "operations", "healthcare", "sustainability", "public_policy", "classification", "regression", "forecasting", "nlp", "computer_vision", "clustering", "experimentation", "causal_inference", "optimization", "bayesian", "llm_app", "rag", "agents", "etl_pipeline", "warehouse_modelling", "orchestration", "api_serving", "infrastructure")} | {f"fmt:{k}" for k in ("notebook", "dashboard_bi", "streamlit_gradio_app", "docker", "tests", "ci", "api", "pipeline_project", "web_app")})
    X = np.zeros((n_data, len(feats)), dtype=float)
    for i, (s, t, f) in enumerate(zip(sk_any, themes, fmts)):
        for j, name in enumerate(feats):
            if name.startswith("theme:"):
                X[i, j] = name[6:] in t
            elif name.startswith("fmt:"):
                X[i, j] = name[4:] in f
            else:
                X[i, j] = name in s
    rows = []
    c23_note = "k-means on binary skill/theme/format indicators over P_data; descriptive archetypes, not a classification of people"
    if n_data >= 60:
        k = 8 if n_data >= 300 else 5
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
        lab = km.labels_
        # L116: k is a fixed rule, not a selected optimum; record how good and how stable it is
        sil = {kk: round(float(silhouette_score(X, KMeans(n_clusters=kk, n_init=10, random_state=0).fit_predict(X))), 3)
               for kk in range(max(2, k - 3), k + 3) if kk != k}
        sil[k] = round(float(silhouette_score(X, lab)), 3)
        ari = [adjusted_rand_score(lab, KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(X)) for seed in (1, 2, 3, 4)]
        c23_note += (f"; k = {k} fixed by rule (8 if n >= 300 else 5), not chosen by fit: silhouette at k = {k} is {sil[k]} "
                     f"(scan {', '.join(f'k={kk}: {v}' for kk, v in sorted(sil.items()))}); stability across 4 other seeds "
                     f"mean ARI {np.mean(ari):.2f} (min {min(ari):.2f})")
        base = X.mean(axis=0)
        for cl in range(k):
            idx = lab == cl; m = X[idx].mean(axis=0)
            lift = [(feats[j], round(m[j], 2), round(m[j] / base[j], 1) if base[j] > 0 else None) for j in np.argsort(-(m - base))[:8] if m[j] >= 0.15]
            sub = P_data[idx]
            rows.append({"cluster": cl, "size": int(idx.sum()), "share": round(idx.mean(), 3), "defining_features": "; ".join(f"{f} {v:.0%} (×{l})" for f, v, l in lift),
                         "families_T1": json.dumps(sub.family.value_counts().head(4).to_dict()), "share_T1": round(sub.is_t1.mean(), 2), "styria": int(sub.is_styria.sum()), "vienna": int(sub.is_vienna.sum()),
                         "students": int(sub.is_student.sum()), "median_projects": float(sub.n_projects.median()), "median_documented": float(sub.n_documented_projects.median()),
                         "share_edu_wording": round((sub.edu_levels_any.map(len) > 0).mean(), 2), "share_any_cert": round((sub.certifications_any.map(len) > 0).mean(), 2),
                         "top_titles": json.dumps(sub.bio_normalized_title.value_counts().head(3).to_dict()), "silhouette_k": sil[k]})
        P_data = P_data.assign(cluster=lab)
    else:
        c23_note += f"; not computed: n = {n_data} < 60"
    # L105: an empty run still writes the header, so readers (demand_supply DS11, exports) can parse it
    write(pd.DataFrame(rows, columns=C23_COLUMNS), "C23_positioning_clusters", c23_note)

    # ---------------- JSON outputs
    def tbl(df: pd.DataFrame, cols: list[str], top: int | None = None) -> list[dict]:
        d = df[cols]
        return (d.head(top) if top else d).to_dict("records")
    meta = {"generated": pd.Timestamp.now().isoformat(), "collection_date": man["collection_date"], "taxonomy_version": CFG["version"], "source": "GitHub REST API (profiles, repositories, READMEs)",
            "source_quality": "B", "populations": {"P_all": n_all, "P_data": n_data, "P_T1": n_t1}, "unit": "public GitHub account with an Austrian location signal; not a census of the Austrian workforce"}
    (OUT / "supply_summary.json").write_text(json.dumps({**meta, "coverage": c01.to_dict("records"), "tiers": tbl(tiers, ["data_tier", "count", "n", "share"]), "families": tbl(c04, ["role_family", "count", "n", "share", "ci_low", "ci_high", "styria", "vienna", "students"]),
                                                          "geo_summary": geo_rows, "styria_complete_frame": c05c.to_dict("records")[0], "seniority_T1": tbl(c06, ["seniority", "count", "n", "share"]),
                                                          "top_technologies": tbl(agg, ["skill", "any_evidence", "project_demonstrated", "n", "any_evidence_share", "project_demonstrated_share"], 30),
                                                          "capabilities": tbl(c11, ["capability", "group", "candidates_any", "candidates_project_demonstrated", "n", "share_any", "share_project_demonstrated"]),
                                                          "transitions": c22.to_dict("records")[0], "concentration": {"raw_titles": conc_raw, "normalized_titles": conc_norm}}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "supply_titles.json").write_text(json.dumps({**meta, "raw_bio_titles_min3": tbl(c02, ["raw_bio_title", "count", "n", "share"]), "normalized_titles": tbl(c03, ["normalized_title", "family", "count", "n", "share", "ci_low", "ci_high", "styria", "vienna"]), "concentration": {"raw": conc_raw, "normalized": conc_norm}}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "supply_skills.json").write_text(json.dumps({**meta, "capabilities": c11.to_dict("records"), "capability_cooccurrence_top": c13_rows[:40]}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "supply_technologies.json").write_text(json.dumps({**meta, "technologies": agg.to_dict("records"), "cooccurrence_top": tbl(pd.DataFrame([{"skill_a": a, "skill_b": b, "both": k} for (a, b), k in pairs.most_common(40)]), ["skill_a", "skill_b", "both"]) if pairs else []}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "supply_seniority.json").write_text(json.dumps({**meta, "distribution_T1": tbl(c06, ["seniority", "count", "n", "share", "ci_low", "ci_high"]), "by_family": c06b.to_dict("records"), "by_region": c06c.to_dict("records"), "vs_account_signals": c06d2.to_dict("records"), "flags": flags.to_dict("records")[0]}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "supply_geography.json").write_text(json.dumps({**meta, "by_state": pd.concat([c05, c05d, c05t]).to_dict("records"), "summary": geo_rows, "family_by_region_T1": c05b.to_dict("records"), "styria_complete_frame": c05c.to_dict("records")[0]}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "supply_languages.json").write_text(json.dumps({**meta, "presentation_language": c07.to_dict("records"), "proficiency_note": "CEFR-type language proficiency is not observable on GitHub; see docs/supply-methodology.md §6 and the manual LinkedIn slot"}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "supply_education.json").write_text(json.dumps({**meta, "levels": pd.concat([c08, c08t, extra]).to_dict("records"), "fields_T1": share_table(P_T1["edu_fields_any"], n_t1, "education_field").to_dict("records"), "institutions_min3": share_table(P_data["edu_institutions_any"], n_data, "institution", min_count=3).to_dict("records")}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "supply_certifications.json").write_text(json.dumps({**meta, "certifications": c09.to_dict("records"), "per_candidate": c09b.to_dict("records")}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"P_all": n_all, "P_data": n_data, "P_T1": n_t1, "families": c04[["role_family", "count"]].to_dict("records")}, indent=1))


if __name__ == "__main__":
    main()
