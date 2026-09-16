"""Tier-1 official series: AMS JobBarometer -> outputs/tables/JB_*.csv, outputs/jobbarometer.json

Input: data/raw/jobbarometer/<date>/details.jsonl (parsed HTML pages).
Produces:
  JB01_yearly_counts_long.csv   beruf x bundesland x year -> online ads (2020-2025)
  JB02_latest_by_beruf_bl.csv   wide table latest year, all Bundesländer
  JB03_trends.csv               3-year trend rating + share label per beruf x bl
  JB04_competencies.csv         top competencies (Austria-wide) per beruf
  JB05_styria_vs_austria.csv    Styria share of national ads per relevant beruf
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "jobbarometer"
TAB = ROOT / "outputs" / "tables"
OUT = ROOT / "outputs"
BL_NAME = {"AT": "Österreich", "AT11": "Burgenland", "AT12": "Niederösterreich", "AT13": "Wien", "AT21": "Kärnten", "AT22": "Steiermark", "AT31": "Oberösterreich", "AT32": "Salzburg", "AT33": "Tirol", "AT34": "Vorarlberg"}
DATA_BERUFE_RE = re.compile(r"^(?!.*sicherheit)(?!.*biomedizin).*(data|daten|statist|business.?intelligence|analy|wirtschaftsinformatik|informatik|mathemat|marktforsch)", re.I)


def val(x):
    if isinstance(x, dict) and "lt" in x:
        return None  # "<20": censored
    return x


def main():
    runs = sorted(p for p in RAW.iterdir() if p.is_dir())
    # re-parse from the stored HTML so that parser fixes apply without re-crawling
    import sys
    sys.path.insert(0, str(ROOT / "src" / "acquisition"))
    from collect_jobbarometer import parse_detail
    recs = []
    for line in open(runs[-1] / "details.jsonl", encoding="utf-8"):
        r = json.loads(line)["record"]
        html_ = r.pop("html", None)
        if html_:
            parsed = parse_detail(html_)
            parsed.update({k: r[k] for k in ("group_id", "beruf_id", "beruf_name_catalogue", "bl", "url")})
            r = parsed
        recs.append(r)
    print(len(recs), "pages parsed")
    long = []
    for r in recs:
        for y, c in (r.get("yearly_counts") or {}).items():
            long.append({"group_id": r["group_id"], "beruf_id": r["beruf_id"], "beruf": r.get("beruf_name") or r["beruf_name_catalogue"], "bl": r["bl"], "bundesland": BL_NAME.get(r["bl"], r["bl"]), "year": int(y), "ads": val(c), "censored_lt20": isinstance(c, dict)})
    L = pd.DataFrame(long)
    L.to_csv(TAB / "JB01_yearly_counts_long.csv", index=False)
    latest = L[L.year == L.year.max()].pivot_table(index=["beruf", "group_id", "beruf_id"], columns="bundesland", values="ads", aggfunc="first").reset_index()
    latest.to_csv(TAB / "JB02_latest_by_beruf_bl.csv", index=False)
    tr = pd.DataFrame([{"beruf": r.get("beruf_name") or r["beruf_name_catalogue"], "bl": r["bl"], "bundesland": BL_NAME.get(r["bl"]), "trend_3y": r.get("trend_3y"), "trend_window": r.get("trend_window"), "share_label": r.get("share_label"), "count_year": r.get("count_year"), "count_latest": val(r.get("count_latest")), "group_id": r["group_id"], "beruf_id": r["beruf_id"]} for r in recs])
    tr.to_csv(TAB / "JB03_trends.csv", index=False)
    comp = []
    for r in recs:
        if r["bl"] != "AT":
            continue
        for name, pct in (r.get("top_competencies_pct") or []):
            comp.append({"beruf": r.get("beruf_name") or r["beruf_name_catalogue"], "competency": name, "avg_share_2022_2025_pct": pct, "kind": "top"})
        for name, pp in (r.get("growing_competencies_pp") or []):
            comp.append({"beruf": r.get("beruf_name") or r["beruf_name_catalogue"], "competency": name, "growth_pp": pp, "kind": "growing"})
    pd.DataFrame(comp).to_csv(TAB / "JB04_competencies.csv", index=False)
    # Styria vs Austria for latest year
    at = L[(L.bl == "AT") & (L.year == L.year.max())].set_index("beruf").ads
    st = L[(L.bl == "AT22") & (L.year == L.year.max())].set_index("beruf").ads
    wi = L[(L.bl == "AT13") & (L.year == L.year.max())].set_index("beruf").ads
    oo = L[(L.bl == "AT31") & (L.year == L.year.max())].set_index("beruf").ads
    sv = pd.DataFrame({"austria": at, "styria": st, "vienna": wi, "upper_austria": oo})
    sv["styria_share"] = (sv.styria / sv.austria).round(3)
    sv["vienna_share"] = (sv.vienna / sv.austria).round(3)
    sv["is_data_occupation"] = sv.index.to_series().str.contains(DATA_BERUFE_RE)
    # growth 2020->latest
    y0 = L[(L.bl == "AT") & (L.year == 2020)].set_index("beruf").ads
    sv["austria_2020"] = y0
    sv["growth_2020_to_latest"] = ((sv.austria / sv.austria_2020) - 1).round(2)
    s0 = L[(L.bl == "AT22") & (L.year == 2020)].set_index("beruf").ads
    sv["styria_2020"] = s0
    sv["styria_growth_2020_to_latest"] = ((sv.styria / sv.styria_2020) - 1).round(2)
    sv = sv.sort_values("austria", ascending=False)
    sv.reset_index().to_csv(TAB / "JB05_styria_vs_austria.csv", index=False)
    js = {"source": "AMS JobBarometer (jobbarometer.ams.at), 'Inserate aus dem Internet' = online job ads per year, AMS occupation classification",
          "collected": str(runs[-1].name), "latest_year": int(L.year.max()), "note": "Counts '<20' are censored by AMS and stored as null. Occupation = AMS Berufsuntergruppe, which is coarser than job titles.",
          "data_occupations": sv[sv.is_data_occupation].reset_index().to_dict(orient="records"),
          "yearly_austria": L[L.bl == "AT"].pivot_table(index="beruf", columns="year", values="ads", aggfunc="first").reset_index().to_dict(orient="records")}
    json.dump(js, open(OUT / "jobbarometer.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(sv[sv.is_data_occupation][["austria", "styria", "vienna", "styria_share", "growth_2020_to_latest"]].to_string())


if __name__ == "__main__":
    main()
