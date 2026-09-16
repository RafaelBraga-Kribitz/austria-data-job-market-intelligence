"""Step 8: decision matrix per role family for the profile in config/profile.json
-> outputs/tables/D01_decision_matrix.csv, D02_sensitivity.csv, D03_skill_gap_by_family.csv,
   D04_learning_priorities.csv, outputs/career_paths.json
See docs/decision-framework.md for variable definitions, weights and sensitivity rules.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "outputs" / "tables"
OUT = ROOT / "outputs"
PROF = json.load(open(ROOT / "config" / "profile.json", encoding="utf-8"))
HAVE, DEV, STRUCT = set(PROF["have"]), set(PROF["developing"]), set(PROF["structural"])
FAMS = ["data_analytics", "bi", "marketing_analytics", "product_analytics", "business_analysis", "data_science", "data_engineering", "data_governance"]
WEIGHTS = {"default": {"V1": .15, "V2": .15, "V3": .10, "V4": .10, "V5": .15, "V6": .10, "V7": .05, "V8": .05, "V9": .10, "V10": .05},
           "geography_first": {"V1": .10, "V2": .35, "V3": .10, "V4": .10, "V5": .10, "V6": .05, "V7": .05, "V8": .05, "V9": .05, "V10": .05},
           "language_first": {"V1": .10, "V2": .10, "V3": .20, "V4": .20, "V5": .10, "V6": .05, "V7": .05, "V8": .05, "V9": .10, "V10": .05},
           "equal": {f"V{i}": .1 for i in range(1, 11)}}
BETTER_HIGH = {"V1": True, "V2": True, "V3": True, "V4": False, "V5": True, "V6": False, "V7": True, "V8": True, "V9": True, "V10": False}
GENERIC = {"Cloud (generic)", "AI (generic)", "Statistics (general)", "Data Visualization", "Machine Learning"}


def share_of(df, keycol, key, valcol, val, fam):
    sub = df[(df.role_family == fam) & (df[keycol] == key)] if keycol else df[df.role_family == fam]
    return sub


def main():
    fam = pd.read_csv(TAB / "T02_role_family_counts.csv").set_index("role_family")
    sk = pd.read_csv(TAB / "T05_skills_all_tech_by_family.csv")
    skb = pd.read_csv(TAB / "T05_skills_business_domain_by_family.csv")
    pl = pd.read_csv(TAB / "T07c_posting_language_by_family.csv")
    ge = pd.read_csv(TAB / "T07_german_requirement_by_role_family.csv")
    sal = pd.read_csv(TAB / "T09b_salary_by_role_family.csv").set_index("role_family")
    rem = pd.read_csv(TAB / "T10_remote_by_family.csv")
    sen = pd.read_csv(TAB / "T08_seniority_by_family.csv")
    exp = pd.read_csv(TAB / "T08b_experience_years_by_family.csv").set_index("role_family")
    deg = pd.read_csv(TAB / "T11c_degree_required_by_family.csv")
    rows, gaps = [], []
    for f in FAMS:
        if f not in fam.index:
            continue
        top = sk[sk.role_family == f].sort_values("count", ascending=False)
        top = top[~top.skill.isin(GENERIC)].head(15)
        n_desc = int(top.n.iloc[0]) if len(top) else 0
        have = [s for s in top.skill if s in HAVE or s in DEV]
        struct = [s for s in top.skill if s in STRUCT]
        unknown = [s for s in top.skill if s not in HAVE | DEV | STRUCT]
        for r in top.itertuples():
            status = "have" if r.skill in HAVE else "developing" if r.skill in DEV else "structural" if r.skill in STRUCT else "unclassified"
            gaps.append({"role_family": f, "skill": r.skill, "share_in_family": r.share, "count": r.count, "n": r.n, "profile_status": status})
        g = ge[ge.role_family == f]
        v4 = float(g[g.german_requirement.isin(["required", "required_implied"])].share.sum()) if len(g) else None
        p = pl[pl.role_family == f]
        v3 = float(p[p.posting_language == "en"].share.sum()) if len(p) else None
        r_ = rem[rem.role_family == f]
        v8 = float(r_[r_.remote_type.isin(["remote", "hybrid", "hybrid_or_flexible"])].share.sum()) if len(r_) else None
        s_ = sen[sen.role_family == f]
        junior_like = float(s_[s_.seniority.isin(["intern_student", "trainee_junior"])].share.sum()) if len(s_) else 0
        med_exp = float(exp.loc[f, "50%"]) if f in exp.index else None
        v9 = (1 - junior_like) * (1 if (med_exp is None or med_exp <= 5) else 0.5)
        d_ = deg[deg.role_family == f]
        v10 = float(d_[d_.degree_required == True].share.sum()) if len(d_) else None
        rows.append({"role_family": f, "V1_postings_at": int(fam.loc[f, "count"]), "V2_postings_styria": int(fam.loc[f, "styria_count"]), "V2b_graz_area": int(fam.loc[f, "graz_area_count"]),
                     "V3_english_posting_share": v3, "V4_german_required_share": v4, "V5_profile_overlap_top15": round(len(have) / max(len(top), 1), 2),
                     "V6_structural_gap_top15": round(len(struct) / max(len(top), 1), 2), "V7_median_min_salary": float(sal.loc[f, "min_median"]) if f in sal.index else None, "V7_n_salary": int(sal.loc[f, "n"]) if f in sal.index else 0,
                     "V8_remote_or_hybrid_share": v8, "V9_senior_entry_openness": round(v9, 2), "V9_median_years_stated": med_exp, "V10_degree_required_share": v10,
                     "n_with_description": n_desc, "top15_skills": "; ".join(top.skill), "overlap_skills": "; ".join(have), "structural_skills": "; ".join(struct), "unclassified_skills": "; ".join(unknown),
                     "small_sample_flag": bool(fam.loc[f, "count"] < 30 or fam.loc[f, "styria_count"] < 10)})
    D = pd.DataFrame(rows).set_index("role_family")
    # families with fewer than 20 Austrian postings are reported but not ranked (no stable percentages)
    small = D[D.V1_postings_at < 20].copy(); D = D[D.V1_postings_at >= 20]
    vcols = {"V1": "V1_postings_at", "V2": "V2_postings_styria", "V3": "V3_english_posting_share", "V4": "V4_german_required_share", "V5": "V5_profile_overlap_top15", "V6": "V6_structural_gap_top15", "V7": "V7_median_min_salary", "V8": "V8_remote_or_hybrid_share", "V9": "V9_senior_entry_openness", "V10": "V10_degree_required_share"}
    N = pd.DataFrame(index=D.index)
    for v, c in vcols.items():
        x = D[c].astype(float)
        rng = x.max() - x.min()
        n = (x - x.min()) / rng if rng and rng > 0 else pd.Series(0.5, index=x.index)
        N[v] = n if BETTER_HIGH[v] else 1 - n
        N[v] = N[v].fillna(0.5)
    sens = pd.DataFrame(index=D.index)
    for name, w in WEIGHTS.items():
        sens[f"score_{name}"] = sum(N[v] * w[v] for v in w)
        sens[f"rank_{name}"] = sens[f"score_{name}"].rank(ascending=False).astype(int)
    D = D.join(sens[["score_default", "rank_default"]])
    D["robust_top3"] = (sens.filter(like="rank_").le(3).all(axis=1)) & (D.V1_postings_at >= 30) & (D.V2_postings_styria >= 30)
    D["tentative_top3"] = (sens.filter(like="rank_").le(3).all(axis=1)) & ~D.robust_top3
    D = pd.concat([D, small.assign(score_default=None, rank_default=None, robust_top3=False, tentative_top3=False)])
    D.sort_values("score_default", ascending=False).reset_index().to_csv(TAB / "D01_decision_matrix.csv", index=False)
    sens.round(3).reset_index().to_csv(TAB / "D02_sensitivity.csv", index=False)
    G = pd.DataFrame(gaps)
    G.to_csv(TAB / "D03_skill_gap_by_family.csv", index=False)
    # learning priorities: skill demand across target families weighted by family size, split by profile status
    allsk = pd.read_csv(TAB / "T05_skills_all_tech.csv")
    allsk = allsk[~allsk.skill.isin(GENERIC)]
    sty = pd.read_csv(TAB / "T05_skills_all_tech_by_styria.csv")
    sty = sty[sty.styria_flag == "Styria"].set_index("skill").share
    famcount = fam["count"]
    unlock = sk[~sk.skill.isin(GENERIC)].groupby("skill").apply(lambda g: int((g.share >= 0.15).sum()))
    L = allsk[["skill", "count", "n", "share", "ci_low", "ci_high"]].copy()
    L["styria_share"] = L.skill.map(sty)
    L["families_where_top(>=15%)"] = L.skill.map(unlock).fillna(0).astype(int)
    L["profile_status"] = L.skill.map(lambda s: "have" if s in HAVE else "developing" if s in DEV else "structural" if s in STRUCT else "unclassified")
    def prio(r):
        if r.profile_status == "have":
            return "already have (demonstrate)"
        if r.share >= 0.20 and r.profile_status == "developing":
            return "NOW"
        if r.share >= 0.10 and r.profile_status == "developing":
            return "NEXT"
        if r.share >= 0.20 and r.profile_status == "structural":
            return "LATER (structural, high demand)"
        if r.share >= 0.08:
            return "LATER"
        return "do not prioritise (low evidence)"
    L["priority"] = L.apply(prio, axis=1)
    L.sort_values("share", ascending=False).to_csv(TAB / "D04_learning_priorities.csv", index=False)
    json.dump({"note": "Scores are a transparent weighted sum of min-max-normalised variables (docs/decision-framework.md). Not a hiring probability.",
               "profile": PROF["summary"], "weights": WEIGHTS, "matrix": json.loads(D.reset_index().to_json(orient="records")),
               "sensitivity": json.loads(sens.round(3).reset_index().to_json(orient="records")),
               "learning_priorities": json.loads(L.sort_values("share", ascending=False).head(60).to_json(orient="records"))},
              open(OUT / "career_paths.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(D[["V1_postings_at", "V2_postings_styria", "V3_english_posting_share", "V4_german_required_share", "V5_profile_overlap_top15", "V6_structural_gap_top15", "score_default", "rank_default", "robust_top3"]].sort_values("score_default", ascending=False).to_string())
    print(sens.filter(like="rank_").to_string())


if __name__ == "__main__":
    main()
