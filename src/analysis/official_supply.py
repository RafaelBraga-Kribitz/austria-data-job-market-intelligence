"""Layer 2 census-type supply context: Eurostat (graduates by field, employment by occupation, ICT specialists) and the
Stack Overflow Developer Survey (Austrian respondents; 2025 by default). Produces the O* tables and
outputs/supply_official.json.

These are population-level or survey-level measures, NOT the public-profile sample: they answer "how large is the yearly
flow of degree-holders in data-relevant fields" and "how do Austrian developers who answer the survey describe their
stack, education and work model", with n and source on every table.

Usage: python src/analysis/official_supply.py [--so-year YYYY]
  --so-year picks data/external/stackoverflow_survey/<YYYY>/ (written by the ingest's --year); default is the newest
  year folder that holds survey_results_austria.csv, else 2025. The survey tables are named O04_so<YYYY>_... and the
  JSON block `stackoverflow_<YYYY>` (mirrored under the year-free key `stackoverflow`).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "outputs" / "tables"
RAW = ROOT / "data" / "raw" / "eurostat_supply"
SO_ROOT = ROOT / "data" / "external" / "stackoverflow_survey"
SO_DEFAULT_YEAR = "2025"


def so_year_default() -> str:
    """Newest year folder with an Austrian extract; 2025 when none exists (the folder is git-ignored)."""
    years = sorted(p.name for p in SO_ROOT.glob("[0-9][0-9][0-9][0-9]") if (p / "survey_results_austria.csv").exists()) \
        if SO_ROOT.exists() else []
    return years[-1] if years else SO_DEFAULT_YEAR


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round((c - h) / d, 3), round((c + h) / d, 3)


def load_eurostat(ds: str) -> pd.DataFrame:
    folder = sorted(RAW.iterdir())[-1]
    rows = []
    for l in open(folder / f"{ds}.jsonl", encoding="utf-8"):
        rec = json.loads(l)
        for r in rec["rows"]:
            r["updated"] = rec["updated"]; rows.append(r)
    return pd.DataFrame(rows), folder.name


FIELD_GROUPS = {
    "ICT (F06)": "F06", "  software & applications development (F0613)": "F0613", "  database & network design (F0612)": "F0612",
    "Mathematics & statistics (F054)": "F054", "  statistics (F0542)": "F0542", "  mathematics (F0541)": "F0541",
    "Business & administration (F041)": "F041", "  marketing & advertising (F0414)": "F0414", "  management & administration (F0413)": "F0413",
    "  finance, banking, insurance (F0412)": "F0412", "Economics (F0311)": "F0311", "Engineering & engineering trades (F071)": "F071",
    "Physical sciences (F053)": "F053", "  physics (F0533)": "F0533", "Psychology (F0313)": "F0313", "Sociology & cultural studies (F0314)": "F0314",
    "All fields (TOTAL)": "TOTAL",
}
LEVELS = {"ED6": "Bachelor", "ED7": "Master", "ED8": "Doctoral", "ED5-8": "All tertiary"}


def eurostat_tables() -> dict:
    g, vintage = load_eurostat("educ_uoe_grad02")
    g["value"] = pd.to_numeric(g["value"], errors="coerce")
    latest = g.groupby("iscedf13")["time"].max().min()
    rows = []
    for lab, code in FIELD_GROUPS.items():
        for lvl, lname in LEVELS.items():
            s = g[(g.iscedf13 == code) & (g.isced11 == lvl)].sort_values("time")
            if s.empty:
                continue
            by = dict(zip(s.time, s.value))
            yrs = sorted(by)
            rows.append({"field": lab.strip(), "field_code": code, "level": lname, "latest_year": yrs[-1], "graduates_latest": by[yrs[-1]],
                         "graduates_5y_before": by.get(str(int(yrs[-1]) - 5)), "change_5y_pct": round(100 * (by[yrs[-1]] / by[str(int(yrs[-1]) - 5)] - 1), 1) if by.get(str(int(yrs[-1]) - 5)) else None,
                         "mean_last_3y": round(sum(by[y] for y in yrs[-3:]) / min(3, len(yrs)), 0), "years_available": f"{yrs[0]}–{yrs[-1]}", "source": "Eurostat educ_uoe_grad02 (AT)", "source_quality": "A"})
    o01 = pd.DataFrame(rows)
    o01.to_csv(TAB / "O01_graduates_by_field_level_at.csv", index=False)
    long = g[["isced11", "iscedf13", "iscedf13_label", "time", "value", "status"]].rename(columns={"isced11": "level_code", "iscedf13": "field_code", "iscedf13_label": "field", "time": "year", "value": "graduates"})
    long["level"] = long.level_code.map(LEVELS)
    long.to_csv(TAB / "O01a_graduates_long_at.csv", index=False)

    e, _ = load_eurostat("lfsa_egai2d")
    e["value"] = pd.to_numeric(e["value"], errors="coerce")
    o02 = e.pivot_table(index=["isco08", "isco08_label"], columns="time", values="value").reset_index()
    o02.columns = [str(c) for c in o02.columns]
    yrs = [c for c in o02.columns if c.isdigit()]
    o02["change_since_" + yrs[0] + "_pct"] = ((o02[yrs[-1]] / o02[yrs[0]] - 1) * 100).round(1)
    o02["unit"] = "thousand persons employed, 15–64"; o02["source"] = "Eurostat lfsa_egai2d (AT)"; o02["source_quality"] = "A"
    o02.to_csv(TAB / "O02_employment_by_isco_at.csv", index=False)

    i, _ = load_eurostat("isoc_sks_itspt")
    i["value"] = pd.to_numeric(i["value"], errors="coerce")
    o03 = i.pivot_table(index="time", columns="unit", values="value").reset_index().rename(columns={"time": "year", "THS_PER": "ict_specialists_thousand", "PC_EMP": "ict_specialists_pct_of_employment"})
    o03["source"] = "Eurostat isoc_sks_itspt (AT)"; o03["source_quality"] = "A"
    o03.to_csv(TAB / "O03_ict_specialists_at.csv", index=False)
    summary = {
        "vintage_collected": vintage,
        "graduates": {r["field"] + " / " + r["level"]: {"latest_year": r["latest_year"], "graduates": r["graduates_latest"], "change_5y_pct": r["change_5y_pct"]} for r in rows if r["level"] in ("Master", "Bachelor", "All tertiary")},
        "employment_isco_latest": {f"{r['isco08']} {r['isco08_label']}": {"year": yrs[-1], "thousand": r[yrs[-1]], "change_pct_since_" + yrs[0]: r["change_since_" + yrs[0] + "_pct"]} for _, r in o02.iterrows()},
        "ict_specialists": o03.tail(3).to_dict("records"),
    }
    return summary


# --------------------------------------------------------------------------- Stack Overflow survey (Austria)
DATA_ROLES = {"Data scientist": "data_science", "Data engineer": "data_engineering", "Data or business analyst": "data_analytics",
              "AI/ML engineer": "data_science", "Applied scientist": "data_science", "Database administrator or engineer": "data_engineering"}
MULTI = ["LanguageHaveWorkedWith", "DatabaseHaveWorkedWith", "PlatformHaveWorkedWith", "ToolsTechHaveWorkedWith", "MiscTechHaveWorkedWith", "WebframeHaveWorkedWith", "AIModelsHaveWorkedWith"]


def explode_counts(df: pd.DataFrame, col: str, n_label: str) -> pd.DataFrame:
    s = df[col].dropna().astype(str).str.split(";").explode().str.strip()
    n = int(df[col].notna().sum())
    vc = s.value_counts().reset_index(); vc.columns = ["item", "count"]
    vc["n"] = n; vc["share"] = (vc["count"] / n).round(3); vc["population"] = n_label
    return vc


def so_tables(year: str = SO_DEFAULT_YEAR) -> dict:
    SO = SO_ROOT / year
    tag, label = f"so{year}", f"Stack Overflow Developer Survey {year}"
    where = SO.relative_to(ROOT).as_posix() if SO.is_relative_to(ROOT) else SO.as_posix()
    if not (SO / "survey_results_austria.csv").exists():
        # L118: the extract is private/git-ignored; say so instead of skipping silently
        print(f"NOTICE: {where}/survey_results_austria.csv not found - O04-O08 ({tag}) NOT refreshed; "
              "any existing O04-O08 files and the DS01 so2025 column are from an earlier run", file=sys.stderr)
        return {"available": False, "survey_year": year, "reason": f"{where}/survey_results_austria.csv missing",
                "tables_not_refreshed": [f"O04_{tag}_at_devtype", f"O05_{tag}_at_technologies", f"O06_{tag}_at_profile_distributions",
                                         f"O07_{tag}_at_experience", f"O08_{tag}_at_compensation"]}
    at = pd.read_csv(SO / "survey_results_austria.csv", low_memory=False)
    man = json.loads((SO / "manifest.json").read_text(encoding="utf-8"))
    at["devtypes"] = at["DevType"].fillna("").str.split(";")
    at["is_data_role"] = at["devtypes"].map(lambda l: any(d.strip() in DATA_ROLES for d in l))
    at["data_family"] = at["devtypes"].map(lambda l: sorted({DATA_ROLES[d.strip()] for d in l if d.strip() in DATA_ROLES}))
    prof = at[at["MainBranch"].fillna("").str.startswith("I am a developer by profession")]
    data = at[at["is_data_role"]]
    # O04 role distribution
    dv = explode_counts(at, "DevType", "Austria respondents with DevType")
    dv["is_data_role"] = dv["item"].isin(DATA_ROLES)
    dv["ci_low"], dv["ci_high"] = zip(*[wilson(int(k), int(n)) for k, n in zip(dv["count"], dv["n"])])
    dv["source"] = f"{label}, Country == Austria"; dv["source_quality"] = "B"
    dv.to_csv(TAB / f"O04_{tag}_at_devtype.csv", index=False)
    # O05 technologies: data-role respondents vs all AT respondents
    parts = []
    for col in MULTI:
        if col not in at.columns:
            continue
        a = explode_counts(at, col, "all AT respondents").rename(columns={"count": "count_all", "n": "n_all", "share": "share_all"}).drop(columns="population")
        d = explode_counts(data, col, "AT data-role respondents").rename(columns={"count": "count_data", "n": "n_data", "share": "share_data"}).drop(columns="population")
        m = a.merge(d, on="item", how="outer").fillna({"count_all": 0, "count_data": 0})
        m["n_all"] = int(at[col].notna().sum()); m["n_data"] = int(data[col].notna().sum())
        m["share_all"] = (m["count_all"] / m["n_all"]).round(3); m["share_data"] = (m["count_data"] / m["n_data"]).round(3) if m["n_data"].iloc[0] else None
        m["question"] = col; parts.append(m)
    o05 = pd.concat(parts, ignore_index=True).sort_values(["question", "count_all"], ascending=[True, False])
    o05["source"] = f"{label} (AT)"; o05["source_quality"] = "B"
    o05.to_csv(TAB / f"O05_{tag}_at_technologies.csv", index=False)
    # O06 education, experience, employment, remote, age, org size
    rows = []
    for col in ["EdLevel", "Employment", "RemoteWork", "Age", "OrgSize", "Industry", "ICorPM", "AISelect"]:
        if col not in at.columns:
            continue
        for pop, sub in (("all AT respondents", at), ("AT data-role respondents", data)):  # `label` is the survey label
            s = sub[col].dropna().astype(str)
            if col == "Employment":
                s = s.str.split(";").explode().str.strip()
            n = int(sub[col].notna().sum())
            for k, v in s.value_counts().items():
                lo, hi = wilson(int(v), n)
                rows.append({"question": col, "answer": k, "population": pop, "count": int(v), "n": n, "share": round(v / n, 3), "ci_low": lo, "ci_high": hi})
    o06 = pd.DataFrame(rows); o06["source"] = f"{label} (AT)"; o06["source_quality"] = "B"
    o06.to_csv(TAB / f"O06_{tag}_at_profile_distributions.csv", index=False)
    # O07 experience
    def yrs(s):
        return pd.to_numeric(s.replace({"Less than 1 year": 0.5, "More than 50 years": 51}), errors="coerce")
    rows = []
    for col in ["YearsCode", "YearsCodePro", "WorkExp"]:
        if col not in at.columns:
            continue
        for pop, sub in (("all AT respondents", at), ("AT data-role respondents", data), ("AT professional developers", prof)):
            v = yrs(sub[col]).dropna()
            if len(v):
                rows.append({"variable": col, "population": pop, "n": int(len(v)), "median": float(v.median()), "q1": float(v.quantile(.25)), "q3": float(v.quantile(.75)), "mean": round(float(v.mean()), 1)})
    o07 = pd.DataFrame(rows); o07["source"] = f"{label} (AT)"; o07["source_quality"] = "B"
    o07.to_csv(TAB / f"O07_{tag}_at_experience.csv", index=False)
    # O08 compensation (self-reported, converted yearly USD by SO) — data roles too few to report by role
    comp = at["ConvertedCompYearly"].dropna() if "ConvertedCompYearly" in at.columns else pd.Series(dtype=float)
    o08 = pd.DataFrame([{"population": "all AT respondents reporting compensation", "n": int(len(comp)), "median_usd": float(comp.median()) if len(comp) else None,
                         "q1_usd": float(comp.quantile(.25)) if len(comp) else None, "q3_usd": float(comp.quantile(.75)) if len(comp) else None,
                         "note": "self-reported, SO conversion to USD; data-role subgroup not reported (n < 30)", "source": f"{label} (AT)", "source_quality": "B"}])
    o08.to_csv(TAB / f"O08_{tag}_at_compensation.csv", index=False)
    n_data = int(at["is_data_role"].sum())
    lo, hi = wilson(n_data, len(at))
    fam = pd.Series([f for l in at["data_family"] for f in l]).value_counts().to_dict()
    top_lang_data = o05[(o05.question == "LanguageHaveWorkedWith")].sort_values("count_data", ascending=False).head(8)[["item", "count_data", "n_data", "share_data"]].to_dict("records")
    return {"available": True, "survey_year": year, "rows_total_survey": man["rows_total"], "rows_austria": int(len(at)), "austria_data_role_respondents": n_data,
            "austria_data_role_share": round(n_data / len(at), 3), "austria_data_role_share_ci": [lo, hi], "data_families": fam,
            "professional_developers_austria": int(len(prof)), "top_languages_data_roles": top_lang_data, "licence": man["licence"], "source_quality": "B",
            "caveat": "data-role subgroup n ≈ 20: report as indicative only; survey is self-selected, English-language, developer-centric"}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Eurostat and Stack Overflow supply context (O* tables)")
    ap.add_argument("--so-year", default=None, help="Stack Overflow survey year folder (default: newest available, else 2025)")
    year = ap.parse_args(argv).so_year or so_year_default()
    TAB.mkdir(parents=True, exist_ok=True)
    so = so_tables(year)
    # the year-keyed block keeps existing readers (stackoverflow_2025) working; `stackoverflow` is year-free
    out = {"generated": pd.Timestamp.now().isoformat(), "eurostat": eurostat_tables(), f"stackoverflow_{year}": so, "stackoverflow": so}
    (ROOT / "outputs" / "supply_official.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: (v if k != "eurostat" else {kk: (vv if kk != "graduates" else {x: y for x, y in list(vv.items())[:6]}) for kk, vv in v.items()}) for k, v in out.items()}, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()
