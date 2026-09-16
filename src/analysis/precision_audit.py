"""Q03c: manual precision audit of the role taxonomy (2026-09-16 audit, DECISION_LOG D-012).

A random sample of 25 canonical core titles per family (seed 11) was drawn from the run of 2026-09-16
BEFORE the D-012 rule changes and labelled by hand:
  TP         = the title is a member of the family as defined in docs/role-taxonomy.md
  FP         = not a data role of that family (e.g. SAP supply-chain consultant under "bi")
  borderline = defensible either way (e.g. master-data maintenance under "data_governance")
The script re-classifies the same titles with the CURRENT rules so that the effect of the rule change is
measured on the same sample. Labels are stored inline below (they are judgements, not extraction output).

Usage: python src/analysis/precision_audit.py  [path to the pre-D-012 postings_dedup.parquet]
Output: outputs/tables/Q03c_manual_precision_audit.csv and Q03c_precision_summary.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "pipeline"))
import normalize as N  # noqa: E402

CORE = {"data_analytics", "bi", "data_science", "data_engineering", "data_governance", "marketing_analytics", "product_analytics", "business_analysis"}
# 1-based positions in the seed-11 sample, per family (see docstring)
LABELS = {
    "bi": {"FP": {2, 4, 6, 9, 11, 14, 15, 16, 19, 21}, "borderline": {23}},
    "business_analysis": {"FP": {4, 8, 10, 23, 24}, "borderline": {11, 12, 13, 22}},
    "data_analytics": {"FP": {3, 9}, "borderline": {11, 23}},
    "data_engineering": {"FP": {5}, "borderline": {15, 25}},
    "data_governance": {"FP": {8, 20, 21, 24}, "borderline": {2, 5, 12, 14, 19, 22, 25}},
    "data_science": {"FP": {11, 15, 25}, "borderline": {6, 18, 21, 23}},
    "marketing_analytics": {"FP": {6, 18}, "borderline": {13, 16}},
    "product_analytics": {"FP": {1, 3}, "borderline": set()},
}


def main(src: str) -> None:
    d = pd.read_parquet(src)
    c = d[d.is_canonical & d.role_family.isin(CORE)]
    rows = []
    for fam, g in c.groupby("role_family"):
        s = g.sample(min(25, len(g)), random_state=11)
        for i, (uid, title, nt) in enumerate(zip(s.posting_uid, s.title, s.normalized_title), start=1):
            lab = "FP" if i in LABELS[fam]["FP"] else "borderline" if i in LABELS[fam]["borderline"] else "TP"
            r = N.classify_role(N.clean_title(title)[0], title)
            rows.append({"family_before": fam, "sample_pos": i, "posting_uid": uid, "title": title.replace("\n", " ").strip(),
                         "normalized_title_before": nt, "manual_label": lab,
                         "family_after": r["role_family"], "normalized_title_after": r["normalized_title"],
                         "kept_in_family_after": r["role_family"] == fam})
    out = pd.DataFrame(rows)
    (ROOT / "outputs" / "tables").mkdir(parents=True, exist_ok=True)
    out.to_csv(ROOT / "outputs" / "tables" / "Q03c_manual_precision_audit.csv", index=False)
    summ = []
    for fam, g in out.groupby("family_before"):
        kept = g[g.kept_in_family_after]
        summ.append({"family": fam, "n_sampled": len(g), "TP": int((g.manual_label == "TP").sum()), "borderline": int((g.manual_label == "borderline").sum()),
                     "FP": int((g.manual_label == "FP").sum()),
                     "precision_before_strict": round((g.manual_label == "TP").mean(), 2),
                     "precision_before_lenient": round((g.manual_label != "FP").mean(), 2),
                     "n_kept_after": len(kept),
                     "precision_after_strict": round((kept.manual_label == "TP").mean(), 2) if len(kept) else None,
                     "precision_after_lenient": round((kept.manual_label != "FP").mean(), 2) if len(kept) else None,
                     "FP_removed": int(((g.manual_label == "FP") & ~g.kept_in_family_after).sum()),
                     "TP_lost": int(((g.manual_label == "TP") & ~g.kept_in_family_after).sum())})
    S = pd.DataFrame(summ)
    tot = {"family": "ALL", "n_sampled": len(out), "TP": int((out.manual_label == "TP").sum()), "borderline": int((out.manual_label == "borderline").sum()), "FP": int((out.manual_label == "FP").sum()),
           "precision_before_strict": round((out.manual_label == "TP").mean(), 2), "precision_before_lenient": round((out.manual_label != "FP").mean(), 2),
           "n_kept_after": int(out.kept_in_family_after.sum()),
           "precision_after_strict": round((out[out.kept_in_family_after].manual_label == "TP").mean(), 2),
           "precision_after_lenient": round((out[out.kept_in_family_after].manual_label != "FP").mean(), 2),
           "FP_removed": int(((out.manual_label == "FP") & ~out.kept_in_family_after).sum()), "TP_lost": int(((out.manual_label == "TP") & ~out.kept_in_family_after).sum())}
    S = pd.concat([S, pd.DataFrame([tot])], ignore_index=True)
    S.to_csv(ROOT / "outputs" / "tables" / "Q03c_precision_summary.csv", index=False)
    print(S.to_string())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "processed" / "postings_dedup.parquet"))
