"""Collect the Austrian Job Vacancy Statistics (JVS) quarterly series from the Eurostat API.

Why this source exists in a job-postings project: the posting snapshot in data/raw is a single day and
therefore cannot measure seasonality (see docs/seasonality.md §1). Eurostat's JVS is the only openly
licensed Austrian vacancy series with a within-year time grain and enough years to separate season
from trend.

Dataset : jvs_q_nace2 — "Job vacancy statistics by NACE Rev. 2 activity - quarterly data"
Source  : Statistik Austria (Offene-Stellen-Erhebung) via Eurostat; compiled under Regulation (EU) 2019/2152.
Access  : documented public REST API, no key, no restriction on automated access; Eurostat content is
          reusable under the Commission's reuse policy (Decision 2011/833/EU) with attribution.
Grain   : quarter × NACE aggregate (B-F industry & construction, G-N market services, O-S public/
          education/health, B-N, B-S), non-seasonally-adjusted, 2009-Q1 onwards.

Usage: python src/acquisition/collect_eurostat_jvs.py
Writes: data/raw/eurostat_jvs/<today>/jvs_q_nace2_at.jsonl  (one envelope per indicator)
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from common import RawWriter, now_iso

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/jvs_q_nace2"
INDICATORS = ("JOBVAC", "JOBRATE")  # number of job vacancies; job vacancy rate (%)
GEO = "AT"
ADJ = "NSA"  # non-seasonally-adjusted: required, seasonally adjusted data would erase the signal


def fetch(indicator: str) -> dict:
    q = urllib.parse.urlencode({"geo": GEO, "s_adj": ADJ, "indic_em": indicator, "format": "JSON", "lang": "EN"})
    url = f"{BASE}?{q}"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "austria-data-job-market-intelligence/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8")), url


def decode(doc: dict) -> list[dict]:
    """Flatten a JSON-stat 2.0 response into records. Last dimension varies fastest."""
    if "value" not in doc or "dimension" not in doc:
        return []
    order, size, dim = doc["id"], doc["size"], doc["dimension"]
    labels = {k: {i: c for c, i in dim[k]["category"]["index"].items()} for k in order}
    values = doc["value"]
    items = values.items() if isinstance(values, dict) else enumerate(values)
    rows = []
    for flat, val in items:
        if val is None:
            continue
        f = int(flat)
        rec = {}
        for k, s in zip(reversed(order), reversed(size)):
            code = labels[k].get(f % s)
            if code is None:  # defensive: malformed index
                rec = None
                break
            rec[k] = code
            f //= s
        if rec is not None:
            rec["value"] = val
            rows.append(rec)
    return rows


def main() -> None:
    w = RawWriter("eurostat_jvs")
    total = 0
    for ind in INDICATORS:
        doc, url = fetch(ind)
        rows = decode(doc)
        w.write("jvs_q_nace2_at", {"indicator": ind, "url": url, "label": doc.get("label"),
                                   "updated": doc.get("updated"), "n_rows": len(rows), "rows": rows},
                indicator=ind)
        w.log_query(ts=now_iso(), dataset="jvs_q_nace2", indicator=ind, geo=GEO, s_adj=ADJ, returned=len(rows))
        print(f"[eurostat] {ind}: {len(rows)} observations")
        total += len(rows)
    w.close()
    print(f"done. {total} observations written to {w.dir}")


if __name__ == "__main__":
    main()
