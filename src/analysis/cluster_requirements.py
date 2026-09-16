"""Step 5: requirement clusters (exploratory, NOT a claim that clusters are 'real professions').

Method: binary skill matrix (tech + statistics + business vocabulary present in
description) for core canonical postings with a description; TF-IDF-like
weighting is unnecessary for binary indicators, so we use k-means on
L2-normalised binary vectors, k chosen by silhouette over 4..10, plus NMF (k=6)
for interpretable additive topics. Each cluster is characterised by its most
over-represented skills (lift vs. the whole set) and its family/geography mix.
Limitations: sensitive to vocabulary coverage; postings without descriptions
are excluded; k is a heuristic choice.
Output: outputs/tables/T15_clusters_*.csv, data/processed/cluster_assignments.csv
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import NMF
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
CORE = ["data_analytics", "bi", "data_science", "data_engineering", "data_governance", "marketing_analytics", "product_analytics", "business_analysis"]
CATS = ["programming_languages", "bi_tools", "cloud_platforms", "data_platforms", "python_ecosystem", "data_engineering", "ml_ai", "statistics_methods", "business_domain"]
EXCLUDE = {"Cloud (generic)", "AI (generic)", "Statistics (general)", "Data Visualization", "Mathematics", "Consulting", "Project Management", "SAP (ERP)"}


def main():
    df = pd.read_json(PROC / "postings_dedup.jsonl", lines=True)
    d = df[df.is_canonical & df.role_family.isin(CORE) & (df.description_length > 300)].copy()
    bags = d[[f"skills_{c}" for c in CATS]].apply(lambda r: sorted({x for l in r for x in (l if isinstance(l, list) else []) if x not in EXCLUDE}), axis=1)
    vocab = sorted({x for b in bags for x in b})
    freq = pd.Series([x for b in bags for x in b]).value_counts()
    vocab = [v for v in vocab if freq[v] >= 8]  # drop ultra-rare
    idx = {v: i for i, v in enumerate(vocab)}
    X = np.zeros((len(d), len(vocab)))
    for i, b in enumerate(bags):
        for x in b:
            if x in idx:
                X[i, idx[x]] = 1
    keep = X.sum(1) >= 2
    d = d[keep].copy(); X = X[keep]
    Xn = normalize(X)
    print(f"{len(d)} postings x {len(vocab)} skills")
    best = None
    for k in range(4, 11):
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(Xn)
        s = silhouette_score(Xn, km.labels_)
        print(f"k={k} silhouette={s:.3f}")
        if best is None or s > best[1]:
            best = (k, s, km)
    k, s, km = best
    d["cluster"] = km.labels_
    base = X.mean(0)
    rows = []
    for c in range(k):
        m = X[km.labels_ == c].mean(0)
        lift = (m + 1e-9) / (base + 1e-9)
        top = sorted([(vocab[j], m[j], lift[j]) for j in range(len(vocab)) if m[j] >= 0.25], key=lambda t: -t[2])[:12]
        sub = d[d.cluster == c]
        rows.append({"cluster": c, "n": len(sub), "share": round(len(sub) / len(d), 3),
                     "defining_skills": "; ".join(f"{n} ({p:.0%}, lift {l:.1f})" for n, p, l in top),
                     "family_mix": "; ".join(f"{f} {v}" for f, v in sub.role_family.value_counts().head(4).items()),
                     "styria_share": round(sub.is_styria.mean(), 2), "english_posting_share": round((sub.posting_language == "en").mean(), 2),
                     "german_required_share": round(sub.german_requirement.isin(["required", "required_implied"]).mean(), 2),
                     "median_min_salary": sub.salary_min_annual_eur.median(), "n_salary": int(sub.salary_min_annual_eur.notna().sum()),
                     "example_titles": " | ".join(sub.title.head(5).astype(str))})
    pd.DataFrame(rows).to_csv(TAB / "T15_clusters_kmeans.csv", index=False)
    # NMF topics
    nmf = NMF(n_components=6, random_state=42, max_iter=500).fit(X)
    trows = []
    for t, comp in enumerate(nmf.components_):
        top = np.argsort(comp)[::-1][:10]
        trows.append({"topic": t, "top_skills": "; ".join(f"{vocab[j]} ({comp[j]:.2f})" for j in top)})
    pd.DataFrame(trows).to_csv(TAB / "T15_nmf_topics.csv", index=False)
    d[["posting_uid", "source", "title", "role_family", "state", "cluster"]].to_csv(PROC / "cluster_assignments.csv", index=False)
    json.dump({"k": k, "silhouette": round(float(s), 3), "n_postings": int(len(d)), "n_skills": len(vocab), "clusters": rows}, open(ROOT / "outputs" / "clusters.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(pd.DataFrame(rows)[["cluster", "n", "defining_skills"]].to_string())


if __name__ == "__main__":
    main()
