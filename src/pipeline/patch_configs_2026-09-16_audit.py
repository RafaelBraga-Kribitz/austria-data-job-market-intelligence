"""One-off config patch applied during the 2026-09-16 publication/completeness audit (DECISION_LOG D-012).

Run once from the repository root: python src/pipeline/patch_configs_2026-09-16_audit.py
Idempotent: re-running produces the same configs. Kept in the repository so that the rule change is reproducible.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROLE = ROOT / "config" / "role_taxonomy.json"
SKILLS = ROOT / "config" / "skills_taxonomy.json"


def patch_roles() -> None:
    t = json.loads(ROLE.read_text(encoding="utf-8"))
    rules = t["rules"]
    by_norm = {r["normalized"]: r for r in rules}

    # 1. Product Analyst: exclude product owners and laboratory product analysts (hard OOS also covers labor/HPLC)
    by_norm["Product Analyst"]["patterns"] = [
        r"product(?!.*owner).{0,15}analy(?!.*business)", r"produkt(?!.*(?:labor|qualit|chemi)).{0,15}analy(?!st für)",
        r"product data scien", r"\bux.{0,10}analy", r"user.{0,10}analy", r"app analy", r"game analy"]

    # 2. Statisticians stay; actuaries/mathematicians move to an adjacent (non-core) rule
    by_norm["Statistician / Biostatistician"]["patterns"] = [r"statisti(?:ker|ker:in|cian|kerin)", r"biostatist", r"biometri"]

    # 3. Data Scientist: generic "künstliche intelligenz"/"KI-Experte" titles are AI titles, not data science
    ds = by_norm["Data Scientist"]["patterns"]
    by_norm["Data Scientist"]["patterns"] = [p for p in ds if p not in (r"künstliche intelligenz", r"\bki[- ]?(?:scientist|expert)")]

    # 4. AI Engineer titles are kept with ML Engineer but the label says so
    by_norm["Machine Learning Engineer"]["normalized"] = "Machine Learning / AI Engineer"

    # 5. Data governance split: operational master/product-data roles get their own normalized title
    gov = by_norm["Data Governance / Data Steward / Data Manager"]
    gov["normalized"] = "Data Governance / Data Steward / Data Manager"
    gov["patterns"] = [r"data steward", r"data governance", r"data quality", r"datenqualität", r"data catalog", r"\bcdo\b", r"chief data",
                       r"data owner", r"data product (?:manager|owner)", r"data platform (?:manager|owner)", r"(?:head|lead) of data",
                       r"data manager", r"datenmanager", r"data management", r"datenmanagement", r"data & vendor"]
    master = {"family": "data_governance", "normalized": "Master / Product Data Management (operational)",
              "patterns": [r"master data", r"stammdaten", r"product data", r"produktdaten", r"\bpim\b", r"engineering data", r"geodaten",
                           r"fahrplandaten", r"produktionsdaten", r"materialstammdaten", r"artikelstammdaten"]}

    # 6. BI consultant: require a data/analytics/BI word; AI/KI consultants go to ai_software_engineering
    by_norm["BI Consultant / Analytics Consultant"]["patterns"] = [
        r"\bbi[- ]?(?:consultant|berater)", r"business intelligence.{0,10}(?:consultant|berater)", r"power ?bi.{0,15}(?:consultant|berater)",
        r"analytics.{0,10}(?:consultant|berater)", r"\bdata.{0,10}(?:consultant|berater)", r"daten.{0,10}(?:consultant|berater)",
        r"consultant.{0,20}(?:\bdata\b|analytics|\bbi\b|business intelligence|\bbw\b|datasphere|\bsac\b)",
        r"berater.{0,20}(?:\bdata\b|analytics|\bbi\b|business intelligence|\bbw\b)", r"sap (?:bw|bi|analytics|sac|datasphere)"]

    # 7. BI analyst: bare "bi" must not match hyphenated compounds such as "Bi-Static"
    bia = by_norm["BI Analyst"]["patterns"]
    by_norm["BI Analyst"]["patterns"] = [r"(?<![\w-])bi(?![\w-])(?!.*(?:engineer|developer|consultant))" if p == r"\bbi\b(?!.*(?:engineer|developer|consultant))" else p for p in bia]

    # 8. BI developer: "reporting specialist" only with a data/BI word (regulatory/financial reporting is hard OOS)
    bid = by_norm["BI Developer / BI Engineer"]["patterns"]
    by_norm["BI Developer / BI Engineer"]["patterns"] = [p for p in bid if p not in (r"reporting specialist",)]

    # 9. Business analyst: drop generic process-manager / IT-business-applications / digital-business patterns
    ba = by_norm["Business Analyst"]["patterns"]
    drop = {r"process (?:analyst|manager)", r"it[- ]?business", r"digital business"}
    by_norm["Business Analyst"]["patterns"] = [p for p in ba if p not in drop] + [r"process analyst", r"business process (?:analyst|manager|owner)", r"it[- ]?business analy"]

    # 10. Financial/risk analyst: market research only as an analyst title; no generic "quantitative"
    fa = by_norm["Financial / Risk / Controlling Analyst (data-heavy)"]["patterns"]
    drop = {r"quantitative", r"market research", r"marktforsch"}
    by_norm["Financial / Risk / Controlling Analyst (data-heavy)"]["patterns"] = [p for p in fa if p not in drop] + [r"quantitative (?:analyst|risk|research)", r"market research analy", r"marktforschungsanaly"]

    # 11. New adjacent rule (other_data family) for actuaries/mathematicians, inserted before the generic other_data rule
    actuary = {"family": "other_data", "normalized": "Actuary / Mathematician (adjacent)",
               "patterns": [r"aktuar", r"actuar", r"versicherungsmathemat", r"mathematiker", r"quantitative"]}

    new_rules = []
    for r in rules:
        if r["normalized"] == "Data Governance / Data Steward / Data Manager":
            new_rules.append(master)
        if r["normalized"] == "Other data / analytics role":
            new_rules.append(actuary)
        new_rules.append(r)
    t["rules"] = new_rules
    t["_audit_note"] = ("2026-09-16 audit (D-012): rules tightened after a 25-title-per-family manual precision review "
                        "(outputs/tables/Q03c_manual_precision_audit.csv). See DECISION_LOG.md.")
    ROLE.write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")


def patch_skills() -> None:
    t = json.loads(SKILLS.read_text(encoding="utf-8"))
    pl = t["programming_languages"]
    if r"sql ?server" not in pl["SQL"]:
        pl["SQL"] = [p for p in pl["SQL"] if p != r"sql(?!\s*server)"] + [r"\bsql\b", r"sql ?server", r"t-sql", r"pl/sql", r"postgresql", r"mysql"]
        pl["SQL"] = list(dict.fromkeys(pl["SQL"]))
    dp = t["data_platforms"]
    if r"\bms sql\b" not in dp["SQL Server"]:
        dp["SQL Server"] = dp["SQL Server"] + [r"\bms sql\b", r"microsoft sql"]
    bi = t["bi_tools"]
    bi["Power BI"] = list(dict.fromkeys(bi["Power BI"] + [r"microsoft power ?bi", r"power ?query"]))
    c = t["certifications"]
    c["Azure cert"] = list(dict.fromkeys(c["Azure cert"] + [r"\b(?:dp|az|ai)-\d{3}\b", r"pl-?300"]))
    c["Google cert"] = list(dict.fromkeys(c["Google cert"] + [r"google (?:cloud|professional) (?:data|certif)", r"google (?:data analytics|advanced data analytics) (?:professional )?certif"]))
    c["Data-management cert (CDMP/DAMA)"] = [r"\bcdmp\b", r"dama[- ]?dmbok", r"\bdmbok\b"]
    c["Requirements/BA cert (IREB/IIBA/CBAP)"] = [r"\bireb\b", r"\biiba\b", r"\bcbap\b", r"\bcpre\b", r"\bccba\b"]
    c["Scrum/PM cert"] = list(dict.fromkeys(c["Scrum/PM cert"] + [r"\bpma\b(?=.{0,60}zertif)", r"scrum[- ]?(?:certif|zertifi)", r"\bsafe\b.{0,20}(?:certif|zertifi)"]))
    c["Databricks cert"] = list(dict.fromkeys(c["Databricks cert"] + [r"databricks certified"]))
    c["AWS cert"] = list(dict.fromkeys(c["AWS cert"] + [r"aws certified"]))
    t["_audit_note"] = "2026-09-16 audit (D-012): SQL now counts SQL Server mentions; 'MS SQL' alias; certification exam codes and DAMA/IREB/IIBA added."
    SKILLS.write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    patch_roles()
    patch_skills()
    print("configs patched")
