"""Step 3: duplicate detection across and within sources.

Input : data/processed/postings_normalized.jsonl
Output: data/processed/postings_dedup.jsonl (+ .parquet)   – all rows, with
        dedupe_group_id, dedupe_group_size, is_canonical, dedupe_method
        outputs/tables/dedupe_summary.csv

Method (documented in docs/methodology.md):
  Two postings are duplicates when
    (a) same source & same source_id            (already collapsed in step 1), or
    (b) same company_norm + same title_clean + same state (exact key), or
    (c) same title_clean + same state + description fingerprint equal
        (first 400 chars of description after whitespace/case normalisation), or
    (d) same company_norm + same title_clean and one side has no state.
  Groups are formed with union-find. The canonical row per group is the one
  with the longest description; ties -> source priority
  karriere > linkedin > eures > willhaben > jobsat (richer structured fields first).
  EURES rows with anonymised employer ("siehe Beschreibung") can only match via (c).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
TAB.mkdir(parents=True, exist_ok=True)
PRIORITY = {"karriere": 0, "linkedin": 1, "eures": 2, "willhaben": 3, "jobsat": 4}


class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def fingerprint(desc: str | None) -> str | None:
    if not desc or len(desc) < 200:
        return None
    s = re.sub(r"[^a-z0-9äöüß]+", " ", desc.lower())
    s = re.sub(r"\s+", " ", s).strip()
    # skip boilerplate starts (company intro) by using chars 200-600 too
    return s[:400]


def main():
    df = pd.read_json(PROC / "postings_normalized.jsonl", lines=True)
    n = len(df)
    uf = UF(n)
    method = [None] * n
    # (b) company + title + state
    key_b = defaultdict(list)
    key_c = defaultdict(list)
    key_d = defaultdict(list)
    for i, r in df.iterrows():
        tc = r.get("title_clean") or ""
        cn = r.get("company_norm")
        st = r.get("state")
        if tc and cn:
            key_b[(cn, tc, st)].append(i)
            key_d[(cn, tc)].append(i)
        fp = fingerprint(r.get("description_text"))
        if tc and fp:
            key_c[(tc, st, fp)].append(i)
            key_c[(tc, None, fp)].append(i)  # allow state-agnostic fingerprint match
    for k, idxs in key_b.items():
        for j in idxs[1:]:
            uf.union(idxs[0], j); method[j] = method[j] or "company_title_state"
    for k, idxs in key_c.items():
        for j in idxs[1:]:
            uf.union(idxs[0], j); method[j] = method[j] or "title_state_fingerprint"
    for k, idxs in key_d.items():
        sts = {df.at[i, "state"] for i in idxs}
        if None in sts or any(pd.isna(s) for s in sts):
            for j in idxs[1:]:
                uf.union(idxs[0], j); method[j] = method[j] or "company_title_nostate"
    groups = defaultdict(list)
    for i in range(n):
        groups[uf.find(i)].append(i)
    gid = [None] * n; gsize = [0] * n; canon = [False] * n
    for g, idxs in groups.items():
        best = sorted(idxs, key=lambda i: (-(len(df.at[i, "description_text"]) if isinstance(df.at[i, "description_text"], str) else 0), PRIORITY.get(df.at[i, "source"], 9)))[0]
        for i in idxs:
            gid[i] = f"g{g}"; gsize[i] = len(idxs)
        canon[best] = True
    df["dedupe_group_id"] = gid
    df["dedupe_group_size"] = gsize
    df["is_canonical"] = canon
    df["dedupe_method"] = [m if m else ("unique" if s == 1 else "group_root") for m, s in zip(method, gsize)]
    df["sources_in_group"] = df.groupby("dedupe_group_id")["source"].transform(lambda s: ",".join(sorted(set(s))))
    df.to_json(PROC / "postings_dedup.jsonl", orient="records", lines=True, force_ascii=False)
    df2 = df.copy()
    for c in df2.columns:
        if df2[c].apply(lambda x: isinstance(x, (list, dict))).any():
            df2[c] = df2[c].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else x)
    df2.to_parquet(PROC / "postings_dedup.parquet", index=False)
    ins = df[df.role_family != "out_of_scope"]
    summ = pd.DataFrame({
        "rows_total": [n], "rows_in_scope": [len(ins)],
        "unique_groups_total": [df.dedupe_group_id.nunique()],
        "unique_groups_in_scope": [ins.dedupe_group_id.nunique()],
        "duplicate_rate_in_scope": [round(1 - ins.dedupe_group_id.nunique() / max(len(ins), 1), 3)],
    })
    summ.to_csv(TAB / "dedupe_summary.csv", index=False)
    print(summ.to_string(index=False))
    print(ins.groupby("sources_in_group").size().sort_values(ascending=False).head(12))


if __name__ == "__main__":
    main()
