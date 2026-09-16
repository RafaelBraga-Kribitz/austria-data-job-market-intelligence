"""Seasonality of Austrian labour demand -> outputs/tables/S*.csv, outputs/seasonality.json, figure F13.

Two separate questions, two separate evidence layers:

 A. "In which part of the year are most vacancies open?"  -> Eurostat Job Vacancy Statistics (jvs_q_nace2),
    Austria, quarterly, non-seasonally-adjusted, 2009-Q1..2025-Q4, NACE aggregates. This is the ONLY
    openly licensed Austrian vacancy series with a within-year grain and enough years to separate the
    seasonal pattern from the trend.

 B. "Can our own posting snapshot answer it?"  -> No, and S05 quantifies why: a one-day snapshot observes
    a posting only if it is still open, so the distribution of first-publish dates is the survival curve,
    not the posting calendar. Reported as negative evidence so the claim is checkable.

Seasonal index, two independent methods (reported side by side; agreement = robustness):
  Method A "ratio to own-year mean": each quarter's value divided by the mean of its own calendar year.
           Removes any between-year level/trend by construction; leaks a little within-year trend.
  Method B "ratio to centred moving average": classical multiplicative decomposition, value divided by
           the centred 4-term moving average. Standard method; handles within-year trend; loses the
           first and last two quarters of the series.
Index 1.00 = an average quarter. Confidence intervals are t-based across years (n = number of years).

Inputs : data/raw/eurostat_jvs/<date>/jvs_q_nace2_at.jsonl, data/processed/postings_dedup.parquet
Outputs: S01 seasonal index by sector x quarter (both methods, both samples)
         S02 per-year quarter ratios (the raw material of S01; shows stability year by year)
         S03 sensitivity: full sample vs excluding 2020-2021 vs 2015+ only
         S04 level context: mean vacancies per quarter and sector, and the trend by year
         S05 why the posting snapshot cannot answer this (age/first-publish distribution)
         outputs/seasonality.json, outputs/figures/F13_seasonality.png
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "eurostat_jvs"
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
OUT = ROOT / "outputs"

SECTOR_LABEL = {
    "B-F": "Industry & construction (NACE B-F)",
    "G-N": "Market services incl. ICT, finance, professional (NACE G-N)",
    "O-S": "Public sector, education, health (NACE O-S)",
    "B-N": "Business economy (NACE B-N)",
    "B-S": "Total economy (NACE B-S)",
}
# the two aggregates that contain most Austrian data roles, plus the total
FOCUS = ["G-N", "B-F", "O-S", "B-S"]
COVID = {2020, 2021}


def load_jvs() -> pd.DataFrame:
    files = sorted(glob.glob(str(RAW / "*" / "jvs_q_nace2_at.jsonl")))
    if not files:
        raise SystemExit("no Eurostat raw file; run: python src/acquisition/collect_eurostat_jvs.py")
    rows = []
    for line in open(files[-1], encoding="utf-8"):
        rec = json.loads(line)["record"]
        if rec["indicator"] != "JOBVAC":
            continue
        rows.extend(rec["rows"])
    df = pd.DataFrame(rows)
    df["year"] = df.time.str[:4].astype(int)
    df["quarter"] = df.time.str[-1].astype(int)
    df["value"] = pd.to_numeric(df.value)
    return df.sort_values(["nace_r2", "year", "quarter"]).reset_index(drop=True)


def ratio_own_year(g: pd.DataFrame) -> pd.DataFrame:
    """Method A: value / mean of the same calendar year (complete years only)."""
    full = g.groupby("year").quarter.count()
    keep = full[full == 4].index
    g = g[g.year.isin(keep)].copy()
    g["year_mean"] = g.groupby("year").value.transform("mean")
    g["ratio_a"] = g.value / g.year_mean
    return g


def ratio_moving_average(g: pd.DataFrame) -> pd.DataFrame:
    """Method B: value / centred 4-term moving average (classical multiplicative decomposition).

    The 2x4 centred moving average for quarterly data is
        CMA_t = (0.5*x_{t-2} + x_{t-1} + x_t + x_{t+1} + 0.5*x_{t+2}) / 4
    computed explicitly here so the weights are visible. Quarters are re-indexed on a complete
    time grid first, so a gap in the series produces NaN rather than a silently wrong average.
    """
    g = g.sort_values(["year", "quarter"]).copy()
    g["t"] = g.year * 4 + (g.quarter - 1)
    full = pd.DataFrame({"t": range(int(g.t.min()), int(g.t.max()) + 1)}).merge(g, on="t", how="left")
    x = full.value
    cma = (0.5 * x.shift(2) + x.shift(1) + x + x.shift(-1) + 0.5 * x.shift(-2)) / 4
    full["cma"] = cma
    full["ratio_b"] = full.value / full.cma
    return full.dropna(subset=["year"]).assign(year=lambda d: d.year.astype(int), quarter=lambda d: d.quarter.astype(int))


def t_ci(x: pd.Series) -> tuple[float, float, float]:
    x = x.dropna()
    n = len(x)
    if n < 2:
        return (float(x.mean()) if n else np.nan, np.nan, np.nan)
    from scipy import stats
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(n)
    lo, hi = stats.t.interval(0.95, n - 1, loc=m, scale=se) if se > 0 else (m, m)
    return float(m), float(lo), float(hi)


def seasonal_table(df: pd.DataFrame, sample: str) -> pd.DataFrame:
    rows = []
    for nace, g0 in df.groupby("nace_r2"):
        if nace not in FOCUS:
            continue
        g = g0.copy()
        if sample == "excl_covid":
            g = g[~g.year.isin(COVID)]
        elif sample == "from_2015":
            g = g[g.year >= 2015]
        if g.year.nunique() < 4:
            continue
        a = ratio_own_year(g)
        b = ratio_moving_average(g)
        for q in (1, 2, 3, 4):
            qa, qb = a[a.quarter == q].ratio_a, b[b.quarter == q].ratio_b
            ma, lo, hi = t_ci(qa)
            mb, _, _ = t_ci(qb)
            rows.append({
                "sector": nace, "sector_label": SECTOR_LABEL[nace], "sample": sample, "quarter": f"Q{q}",
                "n_years": int(qa.notna().sum()),
                "index_a_own_year_mean": round(ma, 3), "ci_low": round(lo, 3), "ci_high": round(hi, 3),
                "index_b_moving_average": round(mb, 3) if not np.isnan(mb) else None,
                "years_above_average": int((qa > 1).sum()),
                "pct_years_above_average": round(float((qa > 1).mean()), 2),
            })
    return pd.DataFrame(rows)


def snapshot_negative_evidence() -> tuple[pd.DataFrame, dict]:
    """S05: show that the one-day snapshot's first-publish dates are a survival curve, not a calendar."""
    p = PROC / "postings_dedup.parquet"
    if not p.exists():
        return pd.DataFrame(), {"note": "processed postings not available (public repository)"}
    d = pd.read_parquet(p)
    core = {"data_analytics", "bi", "data_science", "data_engineering", "data_governance",
            "marketing_analytics", "product_analytics", "business_analysis"}
    c = d[d.is_canonical & d.role_family.isin(core)].copy()
    c["posted"] = pd.to_datetime(c.posted_date, errors="coerce", utc=True).dt.tz_localize(None)
    snap = c.collected_at.astype(str).str[:10].max()
    snap_ts = pd.Timestamp(snap)
    c["age_days"] = (snap_ts - c.posted).dt.days
    rows = []
    for n in (7, 14, 30, 60, 90, 180, 365):
        rows.append({"within_days": n, "postings": int((c.age_days <= n).sum()),
                     "share_of_core": round(float((c.age_days <= n).mean()), 3)})
    tbl = pd.DataFrame(rows)
    bym = c.posted.dt.month.value_counts().sort_index()
    meta = {
        "snapshot_date": snap,
        "core_postings": int(len(c)),
        "posted_in_collection_month": int(bym.get(snap_ts.month, 0)),
        "share_posted_in_collection_month": round(float(bym.get(snap_ts.month, 0) / len(c)), 3),
        "share_within_90_days": round(float((c.age_days <= 90).mean()), 3),
        "median_age_days_by_source": {k: float(v) for k, v in c.groupby("source").age_days.median().items()},
        "conclusion": ("The month distribution of first-publish dates in a one-day snapshot is the product of "
                       "posting volume and the probability that an advertisement is still open. With 90% of the "
                       "core set published within 90 days of collection, the observed pattern is survival decay; "
                       "seasonality is not identifiable from it."),
    }
    return tbl, meta


def make_figure(s01: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    full = s01[s01["sample"] == "full"]
    sectors = [s for s in FOCUS if s in set(full.sector)]
    labels = ["Q1 Jan-Mar", "Q2 Apr-Jun", "Q3 Jul-Sep", "Q4 Oct-Dec"]
    colours = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    x = np.arange(4)
    # Two panels on purpose: bars from zero encode magnitude honestly (the effect IS small);
    # the dot panel zooms in so the pattern is legible without misusing bar length.
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.4), gridspec_kw={"width_ratios": [1, 1.15]})
    width = 0.8 / max(len(sectors), 1)
    for i, s in enumerate(sectors):
        g = full[full.sector == s].sort_values("quarter")
        ax1.bar(x + i * width, g.index_a_own_year_mean, width, color=colours[i % len(colours)],
                label=f"{s} — {SECTOR_LABEL[s].split('(')[0].strip()}")
    ax1.axhline(1.0, color="black", lw=1, ls="--")
    ax1.set_xticks(x + width * (len(sectors) - 1) / 2)
    ax1.set_xticklabels(labels, fontsize=8)
    ax1.set_ylabel("seasonal index (1.00 = average quarter)")
    ax1.set_title("Magnitude: axis from 0\nthe seasonal effect is 5-14% end to end", fontsize=9)

    for i, s in enumerate(sectors):
        g = full[full.sector == s].sort_values("quarter")
        err = np.vstack([g.index_a_own_year_mean - g.ci_low, g.ci_high - g.index_a_own_year_mean])
        ax2.errorbar(x + (i - (len(sectors) - 1) / 2) * 0.16, g.index_a_own_year_mean, yerr=err,
                     fmt="o", capsize=3, ms=5, color=colours[i % len(colours)],
                     label=f"{s} — {SECTOR_LABEL[s].split('(')[0].strip()}")
    ax2.axhline(1.0, color="black", lw=1, ls="--")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8)
    ax2.set_xlim(-0.5, 3.5)
    ax2.grid(axis="y", alpha=0.3)
    ax2.set_title("Pattern: zoomed axis, 95% CI across the 17 years\n"
                  "Q4 is the weakest quarter in every aggregate", fontsize=9)
    ax2.legend(fontsize=7, loc="lower left")

    fig.suptitle("Austria: seasonality of open job vacancies, 2009-2025 (n = 17 years)\n"
                 "Eurostat JVS jvs_q_nace2, non-seasonally-adjusted; index = quarter / own-year mean. "
                 "No occupation or regional detail: not specific to data roles or to Styria.", fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(FIG / "F13_seasonality.png", dpi=150)
    plt.close(fig)


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    df = load_jvs()

    s01 = pd.concat([seasonal_table(df, s) for s in ("full", "excl_covid", "from_2015")], ignore_index=True)
    s01.to_csv(TAB / "S01_seasonal_index.csv", index=False)

    per_year = []
    for nace, g0 in df.groupby("nace_r2"):
        if nace not in FOCUS:
            continue
        a = ratio_own_year(g0)
        b = ratio_moving_average(g0)[["year", "quarter", "ratio_b", "cma"]]
        m = a.merge(b, on=["year", "quarter"], how="left")
        for _, r in m.iterrows():
            per_year.append({"sector": nace, "year": int(r.year), "quarter": f"Q{int(r.quarter)}",
                             "vacancies": int(r.value), "year_mean": round(float(r.year_mean), 1),
                             "ratio_own_year_mean": round(float(r.ratio_a), 3),
                             "ratio_moving_average": round(float(r.ratio_b), 3) if pd.notna(r.ratio_b) else None})
    pd.DataFrame(per_year).to_csv(TAB / "S02_quarter_ratios_by_year.csv", index=False)

    piv = s01.pivot_table(index=["sector", "quarter"], columns="sample", values="index_a_own_year_mean").reset_index()
    piv.to_csv(TAB / "S03_sensitivity_samples.csv", index=False)

    lvl = df[df.nace_r2.isin(FOCUS)].groupby(["nace_r2", "quarter"]).value.agg(["count", "mean", "median"]).round(0).reset_index()
    lvl.columns = ["sector", "quarter", "n_quarters", "mean_vacancies", "median_vacancies"]
    yr = df[df.nace_r2.isin(FOCUS)].groupby(["nace_r2", "year"]).value.mean().round(0).reset_index()
    yr.columns = ["sector", "year", "mean_vacancies"]
    lvl.to_csv(TAB / "S04_levels_by_quarter.csv", index=False)
    yr.to_csv(TAB / "S04a_levels_by_year.csv", index=False)

    s05, s05_meta = snapshot_negative_evidence()
    if not s05.empty:
        s05.to_csv(TAB / "S05_snapshot_age_distribution.csv", index=False)

    make_figure(s01)

    full = s01[s01["sample"] == "full"]
    summary = {}
    for s in FOCUS:
        g = full[full.sector == s].sort_values("index_a_own_year_mean", ascending=False)
        if g.empty:
            continue
        summary[s] = {
            "label": SECTOR_LABEL[s],
            "strongest_quarter": g.iloc[0].quarter, "strongest_index": g.iloc[0].index_a_own_year_mean,
            "weakest_quarter": g.iloc[-1].quarter, "weakest_index": g.iloc[-1].index_a_own_year_mean,
            "spread_pct": round(float((g.iloc[0].index_a_own_year_mean / g.iloc[-1].index_a_own_year_mean - 1) * 100), 1),
            "by_quarter": {r.quarter: {"index": r.index_a_own_year_mean, "ci": [r.ci_low, r.ci_high],
                                       "moving_average_index": r.index_b_moving_average,
                                       "years_above_average": f"{r.years_above_average}/{r.n_years}"}
                           for r in full[full.sector == s].itertuples()},
        }
    payload = {
        "question": "In which part of the year are most job vacancies open in Austria?",
        "source": "Eurostat Job Vacancy Statistics jvs_q_nace2 (Statistik Austria Offene-Stellen-Erhebung), "
                  "geo=AT, non-seasonally-adjusted, 2009-Q1..2025-Q4",
        "unit": "stock of open vacancies reported for the quarter; NOT the number of new postings and NOT hires",
        "grain": "quarter x NACE aggregate; no occupation detail, no regional detail (Styria not separable)",
        "method": "seasonal index = quarter value / own-year mean, averaged across years (95% t-CI); "
                  "cross-checked with ratio to centred 4-term moving average",
        "years": int(df.year.nunique()),
        "sectors": summary,
        "why_not_from_our_postings": s05_meta,
        "generated_from": "src/analysis/seasonality.py",
    }
    (OUT / "seasonality.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(full.sort_values(["sector", "quarter"]).to_string(index=False))
    print("\nsummary:", json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "by_quarter"} for k, v in summary.items()}, indent=1))


if __name__ == "__main__":
    main()
