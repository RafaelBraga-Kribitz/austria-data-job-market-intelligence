"""Adjacent demand: data tools requested in postings whose TITLE is not a data title.

Input: data/raw/eures_textsearch/<date>/listings.jsonl (EURES full-text sweep per region)
Output: outputs/tables/T16_adjacent_demand_by_region.csv, T16a_adjacent_titles_styria.csv, outputs/adjacent_demand.json

For each region (Styria, Vienna, Upper Austria) and each tool keyword we count unique
postings whose description actually contains the tool (regex from config/skills_taxonomy.json),
split by whether the title is a core data title (role_family in CORE) or not. This shows
how much of the demand for e.g. Python/Power BI sits in controller, engineer, marketing
or research roles -> possible entry channels for a domain expert.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "pipeline"))
import normalize as N  # noqa: E402

RAW = ROOT / "data" / "raw" / "eures_textsearch"
TAB = ROOT / "outputs" / "tables"
CORE = ["data_analytics", "bi", "data_science", "data_engineering", "data_governance", "marketing_analytics", "product_analytics", "business_analysis"]
REGION = {"at22": "Steiermark", "at13": "Wien", "at31": "Oberösterreich"}
TOOLS = {"Python": r"python", "SQL": r"\bsql\b", "Power BI": r"power ?bi", "Tableau": r"tableau", "Excel": r"\bexcel\b", "Machine Learning": r"machine ?learning|maschinelles lernen",
         "Statistics": r"statisti", "Data analytics (word)": r"data analytics|datenanaly", "Dashboard/Reporting": r"dashboard", "Business Intelligence": r"business intelligence|\bbi\b", "Data Science (word)": r"data science", "R (language)": r"\br\b\s*(?:/|,|und|and|oder|or)\s*python|python\s*(?:/|,|und|and|oder|or)\s*r\b|r-?studio"}


def strip(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or ""))


def main():
    runs = sorted(p for p in RAW.iterdir() if p.is_dir())
    rows = {}
    for line in open(runs[-1] / "listings.jsonl", encoding="utf-8"):
        e = json.loads(line); r = e["record"]; reg = e.get("region")
        key = (r["id"], reg)
        if key in rows:
            continue
        lang = (r.get("availableLanguages") or ["de"])[0]
        tr = (r.get("translations") or {}).get(lang) or {}
        title = tr.get("title") or r.get("title") or ""
        desc = strip(tr.get("description"))
        tc, _ = N.clean_title(title)
        fam = N.classify_role(tc)["role_family"]
        rows[key] = {"id": r["id"], "region": REGION.get(reg, reg), "title": title, "role_family": fam, "is_core": fam in CORE, "text": (title + "\n" + desc).lower(),
                     "employer": (r.get("employer") or {}).get("name")}
    df = pd.DataFrame(rows.values())
    out = []
    for reg, g in df.groupby("region"):
        for tool, pat in TOOLS.items():
            has = g.text.str.contains(pat, regex=True)
            sub = g[has]
            out.append({"region": reg, "tool": tool, "postings_mentioning": int(has.sum()), "in_core_data_title": int(sub.is_core.sum()), "in_non_data_title": int((~sub.is_core).sum()),
                        "share_non_data_title": round((~sub.is_core).mean(), 3) if len(sub) else None,
                        "top_non_data_families": "; ".join(f"{k} {v}" for k, v in sub[~sub.is_core].role_family.value_counts().head(3).items()),
                        "sweep_postings_region": len(g)})
    T = pd.DataFrame(out)
    T.to_csv(TAB / "T16_adjacent_demand_by_region.csv", index=False)
    sty = df[(df.region == "Steiermark") & (~df.is_core) & df.text.str.contains(r"python|\bsql\b|power ?bi|tableau", regex=True)]
    sty[["id", "title", "role_family", "employer"]].assign(url=lambda d: "https://europa.eu/eures/portal/jv-se/jv-details/" + d.id + "?lang=en").to_csv(TAB / "T16a_adjacent_titles_styria.csv", index=False)
    json.dump({"note": "EURES full-text sweep (AMS feed) restricted by NUTS-2 region; keyword search is token-based so the sweep is a superset; counts here require the tool regex to match the ad text. Not merged with the core posting set.",
               "collected": runs[-1].name, "by_region": json.loads(T.to_json(orient="records")), "styria_non_data_titles_with_tools": json.loads(sty[["title", "role_family", "employer"]].head(80).to_json(orient="records"))},
              open(ROOT / "outputs" / "adjacent_demand.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(T[T.region == "Steiermark"].to_string())


if __name__ == "__main__":
    main()
