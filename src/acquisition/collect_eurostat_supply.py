"""Layer 2 official supply context from Eurostat (open, documented API; reuse permitted with attribution).

Three series for Austria, stored verbatim (JSON-stat) under data/raw/eurostat_supply/<date>/ — PUBLIC, like the
Eurostat vacancy series of Layer 1 (DECISION_LOG D-015):

  educ_uoe_grad02  graduates by ISCED level (ED6 bachelor, ED7 master, ED8 doctoral) and detailed field of
                   education (ISCED-F 2013), sexes total — the yearly flow of new degree-holders in
                   ICT (F06, F0612 database/network, F0613 software/applications), mathematics & statistics
                   (F054, F0541, F0542), business & administration (F041, F0414 marketing), economics (F0311),
                   engineering (F071), physical sciences (F053) and totals.
  lfsa_egai2d      employed persons by ISCO-08 two-digit occupation, 15–64, thousands — stock of ICT
                   professionals (OC25), science & engineering professionals (OC21), business & administration
                   professionals (OC24) and associate professionals (OC33, OC35), total.
  isoc_sks_itspt   employed ICT specialists, thousands and % of total employment.

Usage: python src/acquisition/collect_eurostat_supply.py [--date YYYY-MM-DD]
  --date defaults to today in Europe/Vienna. Each dataset file is rewritten whole, and only when every
  request for it succeeded; otherwise the earlier file is kept and the run exits non-zero.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Session, cli, is_transient, status_of, today  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
UA = "austria-data-job-market-intelligence (non-commercial labour-market research)"

QUERIES = {
    "educ_uoe_grad02": [
        {"geo": "AT", "unit": "NR", "sex": "T", "isced11": lvl, "iscedf13": f, "lang": "EN"}
        for lvl in ("ED6", "ED7", "ED8", "ED5-8")
        for f in ("TOTAL", "F06", "F061", "F0612", "F0613", "F05", "F054", "F0541", "F0542", "F04", "F041", "F0414", "F0410", "F0413", "F0412", "F0411", "F03", "F0311", "F07", "F071", "F053", "F0533", "F0313", "F0314", "F01", "F02", "F09")
    ],
    "lfsa_egai2d": [
        {"geo": "AT", "unit": "THS_PER", "sex": "T", "age": "Y15-64", "isco08": oc, "lang": "EN"}
        for oc in ("TOTAL", "OC2", "OC21", "OC24", "OC25", "OC33", "OC35", "OC1", "OC3")
    ],
    "isoc_sks_itspt": [
        {"geo": "AT", "unit": u, "lang": "EN"} for u in ("THS_PER", "PC_EMP")
    ],
}


def flatten(js: dict) -> list[dict]:
    """JSON-stat 2.0 single-value-per-cell flattening."""
    ids = js["id"]; size = js["size"]
    cats = {d: js["dimension"][d]["category"] for d in ids}
    labels = {d: cats[d].get("label", {}) for d in ids}
    idx = {d: sorted(cats[d]["index"], key=lambda k: cats[d]["index"][k]) for d in ids}
    rows = []
    for k, v in js.get("value", {}).items():
        n = int(k); coords = []
        for d, s in zip(reversed(ids), reversed(size)):
            coords.append(n % s); n //= s
        coords = list(reversed(coords))
        row = {}
        for d, ci in zip(ids, coords):
            code = idx[d][ci]
            row[d] = code
            row[d + "_label"] = labels[d].get(code, code)
        row["value"] = v
        row["status"] = (js.get("status") or {}).get(k)
        rows.append(row)
    return rows


def main() -> None:
    a = cli(__doc__)
    date = a.date or today()
    out = ROOT / "data" / "raw" / "eurostat_supply" / date
    out.mkdir(parents=True, exist_ok=True)
    s = Session(delay=0.3, headers={"User-Agent": UA})
    failed = []
    with open(out / "query_log.jsonl", "a", encoding="utf-8") as log:
        for ds, qs in QUERIES.items():
            recs, errors = [], 0
            for q in qs:
                r = s.get(BASE + ds, params=q, timeout=60)
                js = None
                if r is not None and r.status_code == 200:
                    try:
                        js = r.json()
                    except ValueError:
                        pass
                log.write(json.dumps({"t": dt.datetime.now(dt.timezone.utc).isoformat(), "dataset": ds, "params": q,
                                      "status": status_of(r), "url": r.url if r is not None else None,
                                      **({"error": "nojson"} if r is not None and r.status_code == 200 and js is None else {})}) + "\n")
                if is_transient(status_of(r)) or (r.status_code == 200 and js is None):
                    errors += 1
                    continue
                if r.status_code != 200 or "value" not in js:  # definitive: no such cell combination
                    continue
                recs.append({"dataset": ds, "params": q, "label": js.get("label"), "updated": js.get("updated"), "source": js.get("source"),
                             "rows": flatten(js), "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat()})
            n = sum(len(rec["rows"]) for rec in recs)
            if errors:  # keep an earlier complete file rather than overwrite it with a partial one
                failed.append(ds)
                print(f"{ds}: {errors} request(s) failed; {ds}.jsonl left unchanged, re-run with --date {date}")
                continue
            with open(out / f"{ds}.jsonl", "w", encoding="utf-8") as f:
                for rec in recs:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"{ds}: {n} cells")
    print(f"done. {s.summary()}")
    if failed:
        raise SystemExit(f"incomplete datasets: {', '.join(failed)}")


if __name__ == "__main__":
    main()
