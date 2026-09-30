"""Visual decision layer, Layer 1 (employer demand): BQ01-BQ19.

One business question per figure, asked in the first person because the project
exists to support one person's decisions (`config/profile.json`). Each builder
returns a `Spec` that carries the question, the answer sentence *computed from
the table* (never typed by hand, so it cannot drift from the data), the DSX
relationship and mark, and the documentation anchors the figure attaches to.

Chart selection: `references/chart-selection.md` (GSD-DSX) - name the
relationship, then take an admissible mark from the catalogue.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "viz"))

from engine import (  # noqa: E402
    AMS_SOURCE,
    BASE,
    DEMAND_SOURCE,
    DEMAND_VINTAGE,
    EUROSTAT_SOURCE,
    FOURTH,
    HILITE,
    MUTED,
    PRIMARY_BASIS,
    TABLES,
    THIRD,
    Spec,
    eur_k,
    finalise,
    label_bars,
    market_counts,
    new_figure,
    pct,
    save,
    spread_labels,
    styria_basis_note,
)

PROFILE = json.load(open(ROOT / "config" / "profile.json", encoding="utf-8"))
HAVE = set(PROFILE["have"])
DEVELOPING = set(PROFILE["developing"])
STRUCTURAL = set(PROFILE["structural"])

FAMILY_LABEL = {
    "data_engineering": "Data engineering",
    "data_science": "Data science",
    "business_analysis": "Business analysis",
    "data_analytics": "Data analytics",
    "bi": "BI",
    "data_governance": "Data governance",
    "marketing_analytics": "Marketing analytics",
    "product_analytics": "Product analytics",
}


def table(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLES / name)


def n_core() -> str:
    """'n = 720 core postings' from market_summary.json, never typed by hand (M81)."""
    return f"n = {market_counts()['core']} core postings"


def n_desc() -> str:
    return f"n = {market_counts()['core_with_description']} core postings with a description"


def profile_status(skill: str) -> str:
    if skill in HAVE:
        return "have"
    if skill in DEVELOPING:
        return "developing"
    if skill in STRUCTURAL:
        return "structural"
    return "unclassified"


# docs/limitations.md: a family cell under 30 postings is not ranked. Family-level charts
# still show those families - hiding them would misrepresent the market - but they are
# labelled as too small and never drive a headline number.
MIN_FAMILY_N = 30


def family_label_with_n(family: str, n: int) -> str:
    return FAMILY_LABEL.get(family, family) + ("" if n >= MIN_FAMILY_N else f" (n = {n})")


STATUS_COLOR = {"have": THIRD, "developing": BASE, "structural": FOURTH, "unclassified": MUTED}
STATUS_MARKER = {"have": "o", "developing": "s", "structural": "^", "unclassified": "x"}


# --------------------------------------------------------------------------------------------
# BQ01 - the reachable market
# --------------------------------------------------------------------------------------------
def bq01():
    # Bars use the primary state (T03a: Styria 54 in the 2026-09-16 run); the Graz breakdown
    # (T03c, graz_area_core) exists only on the any-listed-site basis (58), so it is quoted
    # against that total and never against the primary-state count (H11, OQ-19).
    st = table("T03a_state_counts.csv").sort_values("count")
    cities = table("T03c_styria_cities.csv")
    counts = market_counts()
    graz_area = counts["graz_area_any_site"]
    styria_any = counts["styria_any_site"]
    styria = int(st.loc[st.state == "Steiermark", "count"].iloc[0])
    vienna = int(st.loc[st.state == "Wien", "count"].iloc[0])
    total = int(st["count"].sum())
    graz_city = int(cities.loc[cities.city.str.contains("Graz", case=False, na=False), "count"].max())

    fig, ax = new_figure(height=5.2)
    colors = [HILITE if s == "Steiermark" else BASE for s in st.state]
    ax.barh(st.state, st["count"], color=colors)
    ax.set_xlim(0, st["count"].max() * 1.14)
    ax.set_xlabel("Open core data-role postings (one-day stock)")
    label_bars(ax, list(st["count"]), [f"{v} ({v / total:.0%})" for v in st["count"]])
    ax.annotate(
        f"{styria_any} ads list a Styrian site: {graz_city} in Graz city, {graz_area} inside the commuting area",
        xy=(styria, list(st.state).index("Steiermark")),
        xytext=(vienna * 0.34, list(st.state).index("Steiermark") - 1.9),
        fontsize=9, color=HILITE,
        arrowprops={"arrowstyle": "->", "color": HILITE, "lw": 1},
    )
    finalise(
        fig,
        title=f"Staying in Graz means competing for {styria} of {total} open Austrian data postings - "
              f"Vienna alone holds {vienna}",
        source=DEMAND_SOURCE,
        units="unique postings",
        n=f"n = {total} core postings; bars {PRIMARY_BASIS}",
        note=f"Multi-site ads count once, in their primary state. {styria_basis_note(counts)}; the Graz "
             "breakdown uses the second basis.",
    )
    # One basis per sentence (tests/test_manifest_values.py): the answer stays on the primary state; the
    # any-listed-site numbers (58 / 52) go to the caveat, labelled.
    graz_primary = counts["graz_area_primary_styria"]
    graz_clause = (f"; {graz_primary} of them are inside the Graz commuting area" if graz_primary is not None else "")
    return Spec(
        chart_id="BQ01_reachable_market",
        question="If I do not move from Graz, how much of the Austrian data market am I actually applying to?",
        answer=f"By primary state, Styria holds {styria} of {total} open core postings ({styria / total:.1%}){graz_clause}, "
               f"against {vienna} in Vienna ({vienna / total:.0%}).",
        relationship="comparison across categories",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["T03a_state_counts.csv", "T03c_styria_cities.csv"],
        units="unique postings",
        caveat="One-day stock of open advertisements, not yearly demand. The official yearly series (JB05) puts "
               "Styria higher, at 13.6 % of the national flow. Counting every ad that lists a Styrian site (the "
               f"location-flag basis of T02/T04a/T07e) Styria has {styria_any} postings, {graz_area} of them in the Graz "
               f"commuting area, and Vienna {counts['vienna_any_site']}.",
        anchors=[
            ("docs/market-guide.md", "after_match", "* Vienna holds **48 %** of core postings"),
            ("CAREER_DECISION_MAP.md", "after_match", "**Vienna: 48 % of open core data postings"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ02 - is the local market growing while I prepare?
# --------------------------------------------------------------------------------------------
def bq02():
    jb = table("JB01_yearly_counts_long.csv")
    ds = jb[jb.beruf.str.contains("Data Scientist", na=False)]
    wide = ds.pivot_table(index="year", columns="bundesland", values="ads", aggfunc="sum")
    keep = ["Österreich", "Wien", "Oberösterreich", "Steiermark"]
    wide = wide[keep]
    idx = wide / wide.iloc[0] * 100

    fig, ax = new_figure(height=5.2)
    styles = {"Steiermark": (HILITE, 2.6), "Österreich": (MUTED, 1.6), "Wien": (BASE, 1.6), "Oberösterreich": (THIRD, 1.6)}
    for col in keep:
        color, lw = styles[col]
        ax.plot(idx.index, idx[col], color=color, linewidth=lw, marker="o", markersize=4)
        ax.annotate(f" {col} {idx[col].iloc[-1]:.0f}", (idx.index[-1], idx[col].iloc[-1]),
                    color=color, fontsize=9, va="center", ha="left")
    ax.axhline(100, color=MUTED, linewidth=0.8, linestyle=":")
    ax.set_xlim(idx.index.min(), idx.index.max() + 1.6)
    ax.set_ylabel("Yearly ads, 2020 = 100")
    ax.set_xlabel("Year")
    sty_now, sty_2020, sty_peak = wide["Steiermark"].iloc[-1], wide["Steiermark"].iloc[0], wide["Steiermark"].max()
    vie_now, vie_peak = wide["Wien"].iloc[-1], wide["Wien"].max()
    at_now, at_2020 = wide["Österreich"].iloc[-1], wide["Österreich"].iloc[0]
    finalise(
        fig,
        title=f"Austria's data-ad flow fell {abs(at_now / at_2020 - 1):.0%} below 2020 and Vienna "
              f"{abs(vie_now / vie_peak - 1):.0%} below its peak - Styria is {sty_now / sty_2020 - 1:+.0%} above 2020",
        source=AMS_SOURCE,
        units="index, 2020 = 100 (yearly advertisement counts)",
        n=f"Styria {int(sty_2020)} (2020) → {int(sty_peak)} (peak) → {int(sty_now)} (2025)",
        note="AMS occupation class, coarser than this project's title taxonomy.",
    )
    return Spec(
        chart_id="BQ02_regional_trend",
        question="Is the Graz market growing or shrinking while I spend a year preparing?",
        answer=f"On the official yearly series Styria is {sty_now / sty_2020 - 1:+.0%} against 2020 "
               f"({int(sty_2020)} → {int(sty_now)} ads) while Austria is {at_now / at_2020 - 1:+.0%} and Vienna is "
               f"{vie_now / vie_peak - 1:+.0%} off its 2022 peak - the only large region holding its level.",
        relationship="trend over time",
        mark="multi_line",
        data_signature="bivariate-dual",
        tables=["JB01_yearly_counts_long.csv"],
        units="index, 2020 = 100",
        caveat="A coarse AMS occupation class ('Data Scientist (m/w)'), not this project's title taxonomy; "
               "counts advertisements, not hires.",
        anchors=[
            ("docs/market-guide.md", "after_heading", "## 12. Time dimension (T13, JB01)"),
            ("CAREER_DECISION_MAP.md", "after_match", "the only large region above its 2020 level"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ03 - should I time applications by season?
# --------------------------------------------------------------------------------------------
def bq03():
    s1 = table("S01_seasonal_index.csv")
    s1 = s1[s1["sample"] == "full"]
    s6 = table("S06_season_vs_cycle.csv")
    sectors = list(dict.fromkeys(s1.sector_label))
    colors = [BASE, THIRD, FOURTH, MUTED]
    markers = ["o", "s", "^", "D"]
    quarters = ["Q1", "Q2", "Q3", "Q4"]

    short = {label: label.split(" (")[0] for label in sectors}
    fig, ax = new_figure(height=5.0, width=10.4)
    right_edge = s1.ci_high.max() * 1.015
    for si, (sector, color, marker) in enumerate(zip(sectors, colors, markers)):
        sub = s1[s1.sector_label == sector].set_index("quarter").reindex(quarters)
        offset = (si - 1.5) * 0.17
        ypos = np.arange(len(quarters)) + offset
        ax.errorbar(
            sub.index_a_own_year_mean, ypos,
            xerr=[sub.index_a_own_year_mean - sub.ci_low, sub.ci_high - sub.index_a_own_year_mean],
            fmt=marker, color=color, ecolor=color, capsize=2, markersize=6, linewidth=1.2,
        )
        # Direct labels on the first row instead of a legend that would sit on the data.
        ax.text(right_edge, offset, short[sector], color=color, fontsize=8.5, va="center", ha="left")
    ax.set_xlim(right=right_edge * 1.16)
    ax.axvline(1.0, color="#222222", linewidth=0.9)
    ax.set_yticks(np.arange(len(quarters)))
    ax.set_yticklabels(quarters)
    ax.invert_yaxis()
    ax.set_xlabel("Vacancy index against the sector's own yearly mean (1.00 = an average quarter)")
    ratio = s6.ratio.min(), s6.ratio.max()
    q4 = s1[s1.quarter == "Q4"].index_a_own_year_mean
    finalise(
        fig,
        title=f"Q4 is the thinnest quarter in all four sectors - but by {1 - q4.max():.0%}-{1 - q4.min():.0%}, "
              f"while the business cycle moves vacancies {ratio[0]:.0f}-{ratio[1]:.0f} times more",
        source=EUROSTAT_SOURCE,
        units="index (quarter ÷ own-year mean), 95 % CI",
        n="n = 16-17 years per sector",
        note="Sectors are NACE aggregates B-F industry & construction, B-S total economy, G-N market services (incl. ICT, finance, professional), O-S public sector/education/health. No occupation or regional grain: this is all vacancies, not data roles.",
    )
    return Spec(
        chart_id="BQ03_seasonality",
        question="Should I time my applications by season, or does the cycle swamp the calendar?",
        answer=f"Q4 runs {1 - q4.max():.0%}-{1 - q4.min():.0%} below an average quarter in every sector and Q1 is "
               f"usually the strongest, but between-year swings are {ratio[0]:.0f}-{ratio[1]:.0f}× the seasonal "
               "swing - use Oct-Dec to build and be ready in January, do not wait for a month.",
        relationship="deviation from target",
        mark="error_bars",
        data_signature="interval-range",
        tables=["S01_seasonal_index.csv", "S06_season_vs_cycle.csv"],
        units="index (1.00 = average quarter)",
        caveat="Eurostat's Austrian vacancy series has no occupation or regional breakdown; market services (G-N) "
               "includes retail, accommodation and food service, so its Q3 peak is not data-job demand.",
        anchors=[
            ("docs/seasonality.md", "after_heading", "## 4. Results (S01, full sample 2009–2025)"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHEN IN THE YEAR SHOULD I APPLY, AND WHEN IS IT QUIET?"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ04 - who in Styria actually advertises
# --------------------------------------------------------------------------------------------
def bq04():
    # T04a carries two counts per employer: `postings` (all states) and `styria` (postings that
    # list a Styrian site). The question is about Styria, so ranking, bars and headline all use
    # `styria` (H10); the all-state column summed to 58 only by coincidence with styria_core.
    full = table("T04a_employers_styria.csv").sort_values(["styria", "postings"], ascending=False)
    emp = full.head(14).iloc[::-1]
    analyst_side = emp.families.fillna("").str.contains("data_analytics|bi|business_analysis")
    labels = [f"{name}{' *' if flag else ''}" for name, flag in zip(emp.example_company, analyst_side)]
    colors = [HILITE if flag else BASE for flag in analyst_side]

    fig, ax = new_figure(height=0.34 * len(emp) + 2.4)
    ax.barh(labels, emp.styria, color=colors)
    ax.set_xlim(left=0)
    ax.set_xlabel("Open core data postings listing a Styrian site")
    label_bars(ax, list(emp.styria), [str(int(v)) for v in emp.styria])
    counts = market_counts()
    total = int(full.styria.sum())
    styria_any = counts["styria_any_site"]
    unnamed = styria_any - total
    named = len(full)
    n_analyst = int(analyst_side.sum())
    lead = full.iloc[0]
    finalise(
        fig,
        title=f"{named} named employers hold {total} of Styria's {styria_any} data postings - {n_analyst} of the top "
              f"{len(emp)} advertise on the analytics/BI/business-analysis side I can enter (*)",
        source=DEMAND_SOURCE,
        units="open postings per employer that list a Styrian site",
        n=f"n = {total} Styrian postings with a named employer ({unnamed} further Styrian ads name none); "
          f"any-listed-site basis, {styria_basis_note(counts)}",
        note="* = the employer advertises at least one analytics, BI or business-analysis role.",
    )
    return Spec(
        chart_id="BQ04_styria_employers",
        question="Which Styrian employers actually advertise data roles - who is on my realistic target list?",
        answer=f"{named} named employers carry {total} of the {styria_any} ads that list a Styrian site; "
               f"{lead.example_company} leads with {int(lead.styria)}, and {n_analyst} of the largest {len(emp)} "
               "advertise analytics, BI or business-analysis roles rather than only engineering.",
        relationship="ranking",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["T04a_employers_styria.csv"],
        units="open postings",
        caveat=f"A one-day stock: an employer absent here is not an employer that does not hire. {unnamed} Styrian "
               "ads (AMS/EURES) name no employer at all. Counts are on the any-listed-site basis "
               f"({styria_any}), not the primary-state count ({counts['styria_primary']}).",
        anchors=[
            ("docs/market-guide.md", "after_heading", "## 4. Employers (T04, T04a, T04b)"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHERE ARE THEY? (Styria specifically)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ05 - which family to target
# --------------------------------------------------------------------------------------------
def bq05():
    d1 = table("D01_decision_matrix.csv")
    d1 = d1[d1.role_family.isin(FAMILY_LABEL)]

    # A 100 % overlap computed over a family with one posting is arithmetic, not evidence.
    # The project's own robustness rule is n >= 30 (docs/limitations.md), so the highlight
    # is chosen among families that clear it; the rest are drawn but marked small-sample.
    d1 = d1.copy()
    d1["viable"] = d1.V1_postings_at >= MIN_FAMILY_N
    best = d1[d1.viable].loc[d1[d1.viable].V5_profile_overlap_top15.idxmax(), "role_family"]

    fig, ax = new_figure(height=6.0, width=10.0)
    label_y = spread_labels(
        list(d1.V5_profile_overlap_top15), min_gap=0.075, lo=0.04, hi=1.0,
    )
    for (_, row), ly in zip(d1.iterrows(), label_y):
        color = HILITE if row.role_family == best else (BASE if row.viable else MUTED)
        ax.scatter(row.V1_postings_at, row.V5_profile_overlap_top15,
                   s=max(row.V2_postings_styria, 0.4) * 46, color=color, alpha=0.5,
                   edgecolor=color, linewidth=1.4, zorder=3)
        small = "" if row.viable else f"  (n < {MIN_FAMILY_N}: too small to rank)"
        lx = row.V1_postings_at + 9
        ax.plot([row.V1_postings_at, lx], [row.V5_profile_overlap_top15, ly],
                color=color, linewidth=0.6, alpha=0.5, zorder=2)
        ax.annotate(
            f"{FAMILY_LABEL[row.role_family]} · {int(row.V1_postings_at)} AT · "
            f"{int(row.V2_postings_styria)} Styria{small}",
            (lx, ly), fontsize=8.5, color=color, ha="left", va="center", zorder=4,
        )
    ax.set_xlabel("Open postings in Austria")
    ax.set_ylabel("Share of the family's 15 most-mentioned skills\nalready in my profile (have or developing)")
    ax.set_ylim(0, 1.08)
    ax.set_xlim(0, d1.V1_postings_at.max() * 1.85)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    row_best = d1[d1.role_family == best].iloc[0]
    row_big = d1.loc[d1.V1_postings_at.idxmax()]
    finalise(
        fig,
        title=f"{FAMILY_LABEL[best]} covers {row_best.V5_profile_overlap_top15:.0%} of its top-15 skills from what I "
              f"already have; {FAMILY_LABEL[row_big.role_family]} has the most openings and the largest gap",
        source=DEMAND_SOURCE + "; profile from config/profile.json",
        units="postings (x), share of top-15 skills in profile (y), bubble area scales with Styrian postings",
        n=f"{n_core()}; 15 top skills per family (D01)",
        note="Overlap counts self-declared skills, not demonstrated ones. Families under 30 postings are drawn in grey: their overlap is arithmetic, not evidence.",
    )
    return Spec(
        chart_id="BQ05_family_choice",
        question="Which role family gives me the most openings for the smallest structural gap?",
        answer=f"{FAMILY_LABEL[best]} has {row_best.V5_profile_overlap_top15:.0%} of its top-15 skills inside my "
               f"profile with {int(row_best.V1_postings_at)} Austrian and {int(row_best.V2_postings_styria)} Styrian "
               f"postings, while {FAMILY_LABEL[row_big.role_family]} offers {int(row_big.V1_postings_at)} postings at "
               f"only {row_big.V5_profile_overlap_top15:.0%} overlap.",
        relationship="correlation",
        mark="bubble",
        data_signature="trivariate",
        tables=["D01_decision_matrix.csv"],
        units="postings / share of top-15 skills",
        caveat="Overlap is computed against self-declared profile lists, and measures market size and fit, not ease "
               "of being hired. Families below 30 Austrian postings (product and marketing analytics) are shown but "
               "not ranked; every Styrian family count is below 30.",
        anchors=[
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHAT CAREER PATHS ARE SUPPORTED BY THE EVIDENCE?"),
            ("docs/decision-framework.md", "after_heading", "# Decision framework: how career paths are compared"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ06 - does Graz want a different kind of data person
# --------------------------------------------------------------------------------------------
def bq06():
    fam = table("T02_role_family_counts.csv")
    fam = fam[fam.role_family.isin(FAMILY_LABEL)].copy()
    fam["at_share"] = fam["count"] / fam["count"].sum()
    fam["sty_share"] = fam["styria_count"] / fam["styria_count"].sum()
    fam = fam.sort_values("sty_share")
    labels = [FAMILY_LABEL[f] for f in fam.role_family]
    y = np.arange(len(fam))

    fig, ax = new_figure(height=0.44 * len(fam) + 2.6)
    for i, (a, s) in enumerate(zip(fam.at_share, fam.sty_share)):
        ax.plot([a, s], [i, i], color=MUTED, linewidth=1.4, zorder=1)
    n_at, n_sty = int(fam["count"].sum()), int(fam["styria_count"].sum())
    ax.scatter(fam.at_share, y, color=BASE, s=70, zorder=2, label=f"Austria (n = {n_at})")
    ax.scatter(fam.sty_share, y, color=HILITE, s=70, marker="D", zorder=2,
               label=f"Styria (n = {n_sty}, any Styrian site)")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(left=0)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of the region's core postings")
    ax.legend(fontsize=9, loc="lower right")
    eng = fam[fam.role_family == "data_engineering"].iloc[0]
    ba = fam[fam.role_family == "business_analysis"].iloc[0]
    finalise(
        fig,
        title=f"Graz is engineering-heavy: data engineering is {eng.sty_share:.0%} of Styrian postings against "
              f"{eng.at_share:.0%} nationally, while business analysis drops from {ba.at_share:.0%} to {ba.sty_share:.0%}",
        source=DEMAND_SOURCE,
        units="share of the region's core postings",
        n=f"n = {n_at} Austria / {n_sty} Styria (ads listing a Styrian site; {market_counts()['styria_primary']} "
          f"{PRIMARY_BASIS})",
        note=f"Styrian cells are small: {n_sty} postings across eight families. Directional only.",
    )
    return Spec(
        chart_id="BQ06_styria_vs_austria_mix",
        question="Does Graz want a different kind of data person than Austria as a whole?",
        answer=f"Yes: data engineering is {eng.sty_share:.0%} of the {n_sty} postings that list a Styrian site against {eng.at_share:.0%} "
               f"nationally, business analysis falls from {ba.at_share:.0%} to {ba.sty_share:.0%}, and marketing "
               "and product analytics are absent from Styria entirely.",
        relationship="ranking",
        mark="dumbbell",
        data_signature="categorical-multi",
        tables=["T02_role_family_counts.csv"],
        units="share of postings",
        caveat=f"n = {n_sty} for Styria (ads listing a Styrian site; {market_counts()['styria_primary']} "
               f"{PRIMARY_BASIS}); every family cell is below 30, so differences are directional.",
        anchors=[
            ("docs/market-guide.md", "after_match", "Family mix in Styria (n = 58, indicative)"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHAT ROLES EXIST?"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ07 - is my ranking an artefact of the weights?
# --------------------------------------------------------------------------------------------
def bq07():
    d2 = table("D02_sensitivity.csv")
    weightings = [("rank_default", "Default"), ("rank_geography_first", "Geography first"),
                  ("rank_language_first", "Language first"), ("rank_equal", "Equal weights")]
    x = np.arange(len(weightings))

    fig, ax = new_figure(height=5.4)
    top3 = set(d2.sort_values("rank_default").role_family.head(3))
    for _, row in d2.iterrows():
        ranks = [row[c] for c, _ in weightings]
        highlight = row.role_family == "data_analytics"
        color = HILITE if highlight else (BASE if row.role_family in top3 else MUTED)
        ax.plot(x, ranks, marker="o", markersize=7, linewidth=2.6 if highlight else 1.6, color=color)
        ax.annotate(f" {FAMILY_LABEL[row.role_family]}", (x[-1], ranks[-1]), color=color,
                    fontsize=9, va="center", ha="left")
    ax.set_xticks(x)
    ax.set_xticklabels([label for _, label in weightings])
    ax.set_yticks(range(1, len(d2) + 1))
    ax.set_ylabel("Rank (1 = best under that weighting)")
    ax.invert_yaxis()
    ax.set_xlim(-0.3, len(weightings) - 0.3 + 1.5)
    ax.grid(axis="y")
    analytics_ranks = {label: int(d2.loc[d2.role_family == "data_analytics", col].iloc[0]) for col, label in weightings}
    stable = len(set(analytics_ranks.values())) == 1
    finalise(
        fig,
        title="The same three families lead under every weighting - data analytics holds rank "
              f"{analytics_ranks['Default']} whatever I weight" if stable else
              "The leading families are stable across weightings; only their order moves",
        source="D01/D02 decision matrix over " + DEMAND_SOURCE,
        units="rank (1 = best)",
        n="n = 7 families scored on 10 criteria under 4 weightings",
        note="The score measures market size, English openness and advertised floors - not ease of entry.",
    )
    return Spec(
        chart_id="BQ07_ranking_sensitivity",
        question="Is my family ranking a real signal, or an artefact of how I weighted the criteria?",
        answer=f"The top three (engineering, science, analytics) hold under all four weightings and data analytics "
               f"stays at rank {analytics_ranks['Default']}; only the order inside the top two moves, so the "
               "ordering is not a weighting artefact.",
        relationship="ranking",
        mark="bump",
        data_signature="categorical-multi",
        tables=["D02_sensitivity.csv", "D01_decision_matrix.csv"],
        units="rank",
        caveat="The matrix ranks market attractiveness, not probability of being hired; no Styrian family cell "
               "reaches n = 30, so no path is 'robust' under the project's own rule.",
        anchors=[
            ("CAREER_DECISION_MAP.md", "after_match", "The *ordering* of the top three"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ08 - what do employers actually name, and how sure can I be?
# --------------------------------------------------------------------------------------------
def bq08():
    sk = table("T05_skills_all_tech.csv").head(24).copy()
    sk["status"] = sk.skill.map(profile_status)
    sk = sk.sort_values("share")
    y = np.arange(len(sk))

    fig, ax = new_figure(height=0.34 * len(sk) + 2.8)
    for status in ["have", "developing", "structural", "unclassified"]:
        sub = sk[sk.status == status]
        if sub.empty:
            continue
        pos = [list(sk.skill).index(s) for s in sub.skill]
        ax.errorbar(
            sub.share, pos,
            xerr=[sub.share - sub.ci_low, sub.ci_high - sub.share],
            fmt=STATUS_MARKER[status], color=STATUS_COLOR[status], ecolor=STATUS_COLOR[status],
            capsize=2, markersize=7, linewidth=1.2, label=f"{status} (my profile)",
        )
    ax.set_yticks(y)
    ax.set_yticklabels(sk.skill)
    ax.set_xlim(left=0)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of core postings mentioning the item (Wilson 95 % CI)")
    ax.legend(fontsize=8.5, loc="lower right")
    top10 = table("T05_skills_all_tech.csv").head(10)
    covered = sum(profile_status(s) in {"have", "developing"} for s in top10.skill)
    lead = table("T05_skills_all_tech.csv").iloc[0]
    finalise(
        fig,
        title=f"{lead.skill} leads at {lead.share:.0%} of ads - and {covered} of the 10 most-named items are already "
              "in my have-or-developing lists",
        source=DEMAND_SOURCE,
        units="share of postings mentioning the item",
        n=f"n = {int(lead.n)} core postings with a description",
        note="A mention is not a requirement; rule-based extraction (docs/data-quality.md).",
    )
    return Spec(
        chart_id="BQ08_demanded_skills",
        question="Which tools do Austrian employers actually name - and how much of that list do I already hold?",
        answer=f"{lead.skill} ({lead.share:.0%}) and Python lead the list, and {covered} of the 10 most-mentioned "
               "items are already in my have-or-developing profile; the intervals separate the top tier cleanly "
               "from everything under 10 %.",
        relationship="ranking",
        mark="error_bars",
        data_signature="interval-range",
        tables=["T05_skills_all_tech.csv", "config/profile.json"],
        units="share of postings",
        caveat="Shares count ads that *mention* an item, never ads that require it; the profile status is "
               "self-declared, not demonstrated.",
        anchors=[
            ("docs/market-guide.md", "after_match", "Python libraries are almost never named"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHAT DO THEY REQUIRE?"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ09 - what should I learn next
# --------------------------------------------------------------------------------------------
def bq09():
    d4 = table("D04_learning_priorities.csv")
    order = {"NOW": 0, "NEXT": 1, "LATER": 2}
    sub = d4[d4.priority.isin(order)].copy()
    sub["rank"] = sub.priority.map(order)
    sub = sub.sort_values(["rank", "share"], ascending=[False, True])
    colors = {"NOW": HILITE, "NEXT": BASE, "LATER": MUTED}

    fig, ax = new_figure(height=0.42 * len(sub) + 2.8)
    ax.barh(sub.skill, sub.share, color=[colors[p] for p in sub.priority])
    ax.set_xlim(left=0)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of core postings mentioning the skill")
    label_bars(ax, list(sub.share),
               [f"{s:.0%} · top-15 skill in {int(f)} famil{'y' if f == 1 else 'ies'} · {p}" for s, f, p in
                zip(sub.share, sub["families_where_top(>=15%)"], sub.priority)])
    ax.set_xlim(right=sub.share.max() * 1.95)
    now = sub[sub.priority == "NOW"].sort_values("share", ascending=False)
    finalise(
        fig,
        title=f"The four NOW skills ({', '.join(now.skill)}) are named in {now.share.min():.0%}-{now.share.max():.0%} "
              "of ads and are top-15 skills in up to 7 of the 8 families",
        source=DEMAND_SOURCE + "; priority rule in src/analysis/build_decision_matrix.py",
        units="share of postings; number of families where the skill is top-15",
        n=n_desc(),
        note="Priority combines demand share, breadth across families and my current profile status.",
    )
    return Spec(
        chart_id="BQ09_learning_priorities",
        question="If I can only learn a few more things this year, which ones open the most doors?",
        answer=f"{', '.join(now.skill)} are the NOW set - each named in {now.share.min():.0%}-{now.share.max():.0%} "
               "of ads and each a top-15 skill in several families; Power BI, data modelling, GenAI and REST follow "
               "as NEXT.",
        relationship="ranking",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["D04_learning_priorities.csv"],
        units="share of postings",
        caveat="Priority is a demand-and-breadth heuristic, not evidence that learning the skill changes a hiring "
               "outcome.",
        anchors=[
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHAT SHOULD I LEARN?"),
            ("docs/career-map.md", "after_heading", "## 7. Learning roadmap (D04, evidence-derived)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ10 - which skills travel together
# --------------------------------------------------------------------------------------------
def bq10():
    pairs = table("T06_cooccurrence_pairs.csv")
    top = table("T05_skills_all_tech.csv").head(12).skill.tolist()
    mat = pd.DataFrame(np.nan, index=top, columns=top, dtype=float)
    for _, row in pairs.iterrows():
        if row.skill_a in top and row.skill_b in top:
            mat.loc[row.skill_a, row.skill_b] = row.p_b_given_a
            mat.loc[row.skill_b, row.skill_a] = row.p_a_given_b

    fig, ax = new_figure(height=7.2, width=9.6)
    data = mat.to_numpy(dtype=float)
    im = ax.imshow(np.ma.masked_invalid(data), cmap="viridis", vmin=0, vmax=1)
    ax.set_xticks(range(len(top)))
    ax.set_xticklabels(top, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top, fontsize=9)
    ax.set_ylabel("If an ad mentions this …")
    ax.set_xlabel("… how often does it also mention this?")
    ax.grid(False)
    for i in range(len(top)):
        for j in range(len(top)):
            v = data[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v * 100:.0f}", ha="center", va="center", fontsize=7.5,
                        color="white" if v < 0.62 else "#111111")
    fig.colorbar(im, ax=ax, shrink=0.72, label="P(column | row)")
    ml = pairs[(pairs.skill_a == "Machine Learning") & (pairs.skill_b == "Python")]
    ml_val = float(ml.p_a_given_b.iloc[0]) if not ml.empty else np.nan
    sql_py = pairs[(pairs.skill_a == "SQL") & (pairs.skill_b == "Python")].iloc[0]
    finalise(
        fig,
        title=f"The stacks are asymmetric: {sql_py.p_b_given_a:.0%} of SQL ads also name Python, and "
              f"{sql_py.p_a_given_b:.0%} of Python ads name SQL - SQL is the hub of the Austrian data stack",
        source=DEMAND_SOURCE,
        units="conditional probability, % of the row's ads that also mention the column",
        n=n_desc(),
        note="Diagonal blank by construction. Read rows, not columns: the matrix is not symmetric.",
    )
    return Spec(
        chart_id="BQ10_skill_cooccurrence",
        question="What is the minimum credible stack - which skills do employers ask for together?",
        answer=f"SQL is the hub: {sql_py.p_b_given_a:.0%} of SQL ads also name Python and {sql_py.p_a_given_b:.0%} of "
               "Python ads name SQL, while Power BI's strongest partner is reporting wording rather than Python - "
               "a SQL + Python + dashboard combination covers the densest part of the matrix.",
        relationship="correlation",
        mark="heatmap",
        data_signature="trivariate",
        tables=["T06_cooccurrence_pairs.csv", "T05_skills_all_tech.csv"],
        units="conditional probability",
        caveat="Co-mention in an advertisement, not a statement about how the tools are used together in the job.",
        anchors=[
            ("docs/market-guide.md", "after_match", "Power BI's strongest partner is reporting/visualisation wording"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHAT TECHNOLOGIES DO THEY REQUIRE?"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ11 - intern vs junior doors
# --------------------------------------------------------------------------------------------
def bq11():
    t17 = table("T17_skill_divergence_intern_vs_junior.csv").copy()
    t17 = t17.reindex(t17.junior_minus_intern_pp.abs().sort_values(ascending=False).index).head(14)
    t17 = t17.sort_values("junior_minus_intern_pp")
    colors = [BASE if v < 0 else HILITE for v in t17.junior_minus_intern_pp]

    fig, ax = new_figure(height=0.40 * len(t17) + 2.8)
    ax.barh(t17.skill, t17.junior_minus_intern_pp, color=colors)
    ax.axvline(0, color="#222222", linewidth=0.9)
    ax.set_xlabel("Percentage points: junior-ad share minus intern-ad share")
    span = t17.junior_minus_intern_pp.abs().max()
    ax.set_xlim(-span * 1.58, span * 1.58)
    for i, (skill, v, ic, jc) in enumerate(zip(t17.skill, t17.junior_minus_intern_pp, t17.intern_count, t17.junior_count)):
        ax.text(v + (1.2 if v >= 0 else -1.2), i, f"{v:+.0f} pp ({int(ic)}→{int(jc)} ads)",
                va="center", ha="left" if v >= 0 else "right", fontsize=8.5)
    ax.text(0.99, 0.03, "→ asked more in junior ads", transform=ax.transAxes, ha="right", fontsize=9, color=HILITE)
    ax.text(0.01, 0.03, "← asked more in intern ads", transform=ax.transAxes, ha="left", fontsize=9, color=BASE)
    top_j = t17.iloc[-1]
    top_i = t17.iloc[0]
    finalise(
        fig,
        title=f"The two entry doors ask for different things: {top_j.skill} is {top_j.junior_minus_intern_pp:+.0f} pp "
              f"more common in junior ads, {top_i.skill} {abs(top_i.junior_minus_intern_pp):.0f} pp more common in intern ads",
        source=DEMAND_SOURCE,
        units="percentage-point difference in mention share",
        n="n = 42 intern ads / 31 junior ads (descriptions)",
        note="Both denominators only just clear 30 - directional, not a second market.",
    )
    return Spec(
        chart_id="BQ11_intern_vs_junior",
        question="The two entry doors are intern and junior - do they ask for different things?",
        answer=f"Yes: junior ads lean to {top_j.skill} ({top_j.junior_minus_intern_pp:+.0f} pp) and ETL, intern ads to "
               f"{top_i.skill} and Excel; SQL is high in both, so it is the one skill that opens either door.",
        relationship="deviation from target",
        mark="diverging_bar",
        data_signature="categorical-value",
        tables=["T17_skill_divergence_intern_vs_junior.csv"],
        units="percentage points",
        caveat="n = 42 and n = 31: differences under roughly 15 pp are inside the noise of these cell sizes.",
        anchors=[
            ("docs/market-guide.md", "after_heading", "## 8b. Intern vs junior vs rest (T17, T04d, T05f, D04b)"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## INTERN VS JUNIOR VS THE REST (T17, T04d, T05f, D04b)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ12 - how much of the market does my German reach
# --------------------------------------------------------------------------------------------
def bq12():
    t7e = table("T07e_addressable_market_scenarios.csv")
    keep = ["Austria", "Vienna", "Styria", "Graz area",
            "family:data_science", "family:data_analytics", "family:bi"]
    sub = t7e[t7e.scope.isin(keep)].set_index("scope").reindex(keep)
    scope_label = {"family:data_science": "Data science", "family:data_analytics": "Data analytics",
                   "family:bi": "BI"}
    sub.index = [scope_label.get(s, s) for s in sub.index]
    scenarios = [
        ("english_posting_no_german_req", "English-written AND no stated German requirement", HILITE),
        ("no_explicit_german_requirement", "No explicit German requirement (silence included)", BASE),
        ("german_not_required_at_C1_or_above", "German not required at C1-equivalent", MUTED),
    ]
    x = np.arange(len(sub))
    width = 0.26

    fig, ax = new_figure(height=5.4)
    for k, (col, label, color) in enumerate(scenarios):
        vals = sub[col] / sub["n"]
        ax.bar(x + (k - 1) * width, vals, width, color=color, label=label)
        for xi, (v, c) in zip(x + (k - 1) * width, zip(vals, sub[col])):
            ax.text(xi, v + 0.012, f"{int(c)}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(sub.index)
    ax.axvline(3.5, color=MUTED, linewidth=0.8, linestyle=":")
    ax.text(3.58, 0.985, "by role family (Austria)", fontsize=8.5, color=MUTED, va="top")
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Share of the scope's postings")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.legend(fontsize=8.5, loc="upper left")
    sty = sub.loc["Styria"]
    finalise(
        fig,
        title=f"In Styria the answer is a range, not a number: {int(sty.english_posting_no_german_req)} of "
              f"{int(sty.n)} ads are English-written with no stated German requirement, "
              f"{int(sty.german_not_required_at_C1_or_above)} do not ask for C1",
        source=DEMAND_SOURCE,
        units="postings per scope (labels) and share of the scope (bars)",
        n="n = " + " / ".join(f"{int(v)} {k}" for k, v in sub["n"].items())
          + "; Vienna, Styria and Graz area = ads listing a site there",
        note="Three alternative readings of the same ads - they are scenarios, never summed or stacked.",
    )
    return Spec(
        chart_id="BQ12_german_addressable_market",
        question="With German at A2-B1, how many Graz jobs can I honestly apply to today?",
        answer=f"Between {int(sty.english_posting_no_german_req)} and "
               f"{int(sty.german_not_required_at_C1_or_above)} of the {int(sty.n)} open ads that list a Styrian site, depending on which "
               "reading you take; the strictest reading (English-written and silent on German) leaves "
               f"{int(sty.english_posting_no_german_req)} in Styria and "
               f"{int(sub.loc['Graz area', 'english_posting_no_german_req'])} in the Graz area.",
        relationship="comparison across categories",
        mark="grouped_bar",
        data_signature="bivariate-dual",
        tables=["T07e_addressable_market_scenarios.csv"],
        units="postings / share of scope",
        caveat="'English-written and silent on German' is not 'English-only': German may still be expected. "
               "Whether a stated requirement is negotiable is not measured anywhere in this project.",
        anchors=[
            ("docs/market-guide.md", "after_match", "**Addressable-market scenarios (T07e)**"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHAT LANGUAGES DO THEY REQUIRE?"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ13 - which family is most open to English
# --------------------------------------------------------------------------------------------
def bq13():
    lang = table("T07c_posting_language_by_family.csv")
    eng = lang[lang.posting_language == "en"].set_index("role_family")
    ger = table("T07_german_requirement_by_role_family.csv")
    req = ger[ger.german_requirement.isin(["required", "required_implied"])]
    req = req.groupby("role_family")["share"].sum()

    fams = [f for f in FAMILY_LABEL if f in eng.index and f in req.index]
    fig, ax = new_figure(height=5.8, width=10.0)
    label_y = spread_labels([float(req.loc[f]) for f in fams], min_gap=0.045, lo=0.05, hi=0.72)
    for fam, ly in zip(fams, label_y):
        x, y = eng.loc[fam, "share"], req.loc[fam]
        n = int(eng.loc[fam, "n"])
        color = HILITE if fam in {"data_analytics", "marketing_analytics"} else BASE
        ax.scatter(x, y, s=max(n, 8) * 2.4, color=color, alpha=0.55, edgecolor=color,
                   linewidth=1.4, zorder=3)
        lx = x + 0.035
        ax.plot([x, lx], [y, ly], color=color, linewidth=0.6, alpha=0.5, zorder=2)
        small = "" if n >= MIN_FAMILY_N else " — too small to rank"
        ax.annotate(f"{FAMILY_LABEL[fam]} · n = {n}{small}", (lx, ly), fontsize=8.5,
                    color=color, ha="left", va="center", zorder=4)
    ax.set_xlabel("Share of the family's ads written in English")
    ax.set_ylabel("Share stating a German requirement or level")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlim(0, max(eng.loc[fams, "share"]) * 1.72)
    ax.set_ylim(0, max(req[fams]) * 1.45)
    ax.annotate("more English, less stated German = more of this family open to me now",
                xy=(0.985, 0.03), xycoords="axes fraction", ha="right", va="bottom",
                fontsize=8.5, color=MUTED)
    best = max(fams, key=lambda f: eng.loc[f, "share"])
    worst = min(fams, key=lambda f: eng.loc[f, "share"])
    finalise(
        fig,
        title=f"{FAMILY_LABEL[best]} is the most English-open family ({eng.loc[best, 'share']:.0%} of its ads in "
              f"English, {req[best]:.0%} stating German); {FAMILY_LABEL[worst]} the least "
              f"({eng.loc[worst, 'share']:.0%} / {req[worst]:.0%})",
        source=DEMAND_SOURCE,
        units="share of the family's postings (bubble area scales with postings in the family)",
        n=n_desc(),
        note="A German-written ad that says nothing about German usually still implies it (T07d).",
    )
    return Spec(
        chart_id="BQ13_language_by_family",
        question="Which role family gives my English the most room and my German the least resistance?",
        answer=f"{FAMILY_LABEL[best]}: {eng.loc[best, 'share']:.0%} of its ads are written in English and "
               f"{req[best]:.0%} state a German requirement, against {FAMILY_LABEL[worst]} at "
               f"{eng.loc[worst, 'share']:.0%} English and {req[worst]:.0%} German - the language dimension moves "
               "more between families than the skill lists do.",
        relationship="correlation",
        mark="bubble",
        data_signature="trivariate",
        tables=["T07c_posting_language_by_family.csv", "T07_german_requirement_by_role_family.csv"],
        units="share of postings",
        caveat="Marketing analytics (n = 24) and product analytics (n = 1) carry cells too small to separate.",
        anchors=[
            ("docs/market-guide.md", "after_match", "**Posting language:**"),
            ("CAREER_DECISION_MAP.md", "after_match", "By family: BI 51 % German required/level-stated"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ14 - does the missing degree block me
# --------------------------------------------------------------------------------------------
def bq14():
    deg = table("T11e_degree_requirement_strength_by_family.csv")
    order = ["required", "preferred", "mentioned", "none"]
    colors = {"required": HILITE, "preferred": FOURTH, "mentioned": BASE, "none": MUTED}
    wide = deg.pivot_table(index="role_family", columns="degree_requirement", values="share").fillna(0)
    wide = wide.reindex(columns=order, fill_value=0).sort_values("required")
    family_n = deg.groupby("role_family")["n"].max()
    labels = [family_label_with_n(f, int(family_n.get(f, 0))) for f in wide.index]
    viable = [int(family_n.get(f, 0)) >= MIN_FAMILY_N for f in wide.index]

    fig, ax = new_figure(height=0.46 * len(wide) + 2.8)
    left = np.zeros(len(wide))
    for col in order:
        ax.barh(labels, wide[col], left=left, color=colors[col], label=col)
        for i, (v, l0) in enumerate(zip(wide[col], left)):
            if v > 0.06:
                ax.text(l0 + v / 2, i, f"{v:.0%}", ha="center", va="center", fontsize=8.5,
                        color="white" if col in {"required", "none"} else "#222222")
        left = left + wide[col].to_numpy()
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of the family's postings")
    ax.legend(fontsize=8.5, ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.30))
    req_share = wide.loc[viable, "required"]
    none_share = wide.loc[viable, "none"]
    finalise(
        fig,
        title=f"A degree is stated as a condition in {req_share.min():.0%}-{req_share.max():.0%} of ads depending on "
              f"the family - and never mentioned at all in {none_share.min():.0%}-{none_share.max():.0%}",
        source=DEMAND_SOURCE,
        units="share of the family's postings",
        n=n_desc(),
        note=f"Ranges are over families with at least {MIN_FAMILY_N} postings. Roughly a third of ads add "
             "'or equivalent experience' next to the degree wording.",
    )
    return Spec(
        chart_id="BQ14_degree_requirement",
        question="Does not holding a data/informatics degree close the door?",
        answer=f"It narrows it rather than closing it: {req_share.min():.0%}-{req_share.max():.0%} of ads state a "
               f"degree as a condition depending on the family, {none_share.min():.0%}-{none_share.max():.0%} never "
               "mention education at all, and a third of the conditional ads add 'or equivalent experience'.",
        relationship="part to whole",
        mark="stacked_bar",
        data_signature="categorical-multi",
        tables=["T11e_degree_requirement_strength_by_family.csv"],
        units="share of postings",
        caveat="Wording strength, not hiring practice: no evidence here on how degree wording is applied in "
               "screening.",
        anchors=[
            ("docs/market-guide.md", "after_heading", "## 11. Education and certifications (T11, T11e)"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHAT EDUCATION DO THEY REQUIRE?"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ15-BQ17 - advertised floors
# --------------------------------------------------------------------------------------------
def _salary_range_chart(df, label_col, *, label_map=None, highlight=None):
    """Median dot with a p25-p75 range bar: position on a common scale, not a length mark.

    Returns (fig, ax, sorted_df, axis_floor); the caller writes the takeaway and
    declares the axis floor in the note, which is what a non-zero baseline needs.
    """
    df = df.sort_values("min_median")
    labels = [label_map.get(v, v) if label_map else v for v in df[label_col]]
    y = np.arange(len(df))
    fig, ax = new_figure(height=0.44 * len(df) + 2.8)
    for i, row in enumerate(df.itertuples()):
        ax.plot([row.min_p25, row.min_p75], [i, i], color=MUTED, linewidth=3, alpha=0.45, solid_capstyle="butt")
    dot_colors = [HILITE if v == highlight else BASE for v in df[label_col]]
    ax.scatter(df.min_median, y, color=dot_colors, s=[105 if c == HILITE else 80 for c in dot_colors], zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    floor = np.floor(df.min_p25.min() / 5000) * 5000
    ax.set_xlim(floor, df.min_p75.max() * 1.10)
    ax.xaxis.set_major_formatter(lambda v, _: f"€{v / 1000:.0f}k")
    ax.set_xlabel("Advertised minimum, annual gross (median dot, p25-p75 bar)")
    for i, row in enumerate(df.itertuples()):
        ax.text(row.min_p75 + (df.min_p75.max() - floor) * 0.02, i,
                f"{eur_k(row.min_median)}  (n = {int(row.n)})", va="center", fontsize=8.5)
    return fig, ax, df, floor


def bq15():
    df = table("T09b_salary_by_role_family.csv")
    df = df[df.role_family.isin(FAMILY_LABEL) & (df.n >= 20)]
    fig, ax, df, floor = _salary_range_chart(df, "role_family", label_map=FAMILY_LABEL, highlight="data_analytics")
    ana = df[df.role_family == "data_analytics"].iloc[0]
    eng = df[df.role_family == "data_engineering"].iloc[0]
    finalise(
        fig,
        title=f"The family I can enter advertises the lowest floor: data analytics {eur_k(ana.min_median)} against "
              f"data engineering {eur_k(eng.min_median)} - a {eur_k(eng.min_median - ana.min_median)} gap at the door",
        source=DEMAND_SOURCE,
        units="euro, annual gross (monthly × 14)",
        n=f"n = {int(df.n.sum())} postings with a parsed figure, families with n ≥ 20",
        note=f"Axis starts at €{floor / 1000:.0f}k - these are collective-agreement floors, not offers.",
    )
    return Spec(
        chart_id="BQ15_salary_by_family",
        question="What do the families advertise as a floor, and what does entering through analytics cost me?",
        answer=f"Data analytics advertises a median minimum of {eur_k(ana.min_median)} against data engineering's "
               f"{eur_k(eng.min_median)} - a {eur_k(eng.min_median - ana.min_median)} difference at the entry door, "
               "with overlapping interquartile ranges.",
        relationship="ranking",
        mark="dot_plot",
        data_signature="categorical-value",
        tables=["T09b_salary_by_role_family.csv"],
        units="EUR, annual gross",
        caveat="81 % of parsed figures are a single collective-agreement minimum; 53 % of ads say they pay above it. "
               "These are legal floors, not offers and not pay.",
        anchors=[
            ("docs/market-guide.md", "after_match", "Median advertised **minimum** (annual gross, monthly × 14)"),
            ("CAREER_DECISION_MAP.md", "after_heading",
             "## WHAT DO THEY PAY? (advertised minimums, annual gross, monthly × 14)"),
        ],
    ), fig


def bq16():
    df = table("T09b_salary_by_seniority.csv")
    labels = {"intern_student": "Intern / student", "trainee_junior": "Junior / trainee",
              "unspecified": "No seniority word", "senior": "Senior", "lead_head": "Lead / head"}
    df = df[df.seniority.isin(labels)]
    fig, ax, df, floor = _salary_range_chart(df, "seniority", label_map=labels, highlight="unspecified")
    jun = df[df.seniority == "trainee_junior"].iloc[0]
    unl = df[df.seniority == "unspecified"].iloc[0]
    sen = df[df.seniority == "senior"].iloc[0]
    finalise(
        fig,
        title=f"Entering on a junior label costs {eur_k(unl.min_median - jun.min_median)} against an unlabelled ad and "
              f"{eur_k(sen.min_median - jun.min_median)} against a senior one",
        source=DEMAND_SOURCE,
        units="euro, annual gross (monthly × 14)",
        n=f"n = {int(df.n.sum())} postings with a parsed figure",
        note=f"Axis starts at €{floor / 1000:.0f}k. 57.5 % of ads carry no seniority word at all.",
    )
    return Spec(
        chart_id="BQ16_salary_by_seniority",
        question="What does entering on a junior label actually cost me, given 20 years of prior experience?",
        answer=f"The junior median floor is {eur_k(jun.min_median)} against {eur_k(unl.min_median)} for an unlabelled "
               f"ad and {eur_k(sen.min_median)} for a senior one - a {eur_k(unl.min_median - jun.min_median)} penalty "
               "for the label, which is why the 57.5 % of ads carrying no seniority word matter more than the junior "
               "ones.",
        relationship="ranking",
        mark="dot_plot",
        data_signature="categorical-value",
        tables=["T09b_salary_by_seniority.csv"],
        units="EUR, annual gross",
        caveat="Seniority is read from the advertisement's title, and the figure is an advertised floor, not an "
               "offer. Junior n = 22.",
        anchors=[
            ("docs/market-guide.md", "after_match", "By seniority label: intern"),
        ],
    ), fig


def bq17():
    df = table("T09d_salary_by_skill.csv")
    df = df[df.n >= 20].copy()
    df["status"] = df.skill.map(profile_status)
    fig, ax, df, floor = _salary_range_chart(df, "skill")
    for tick, status in zip(ax.get_yticklabels(), df.status):
        tick.set_color(STATUS_COLOR[status])
    top, bottom = df.iloc[-1], df.iloc[0]
    finalise(
        fig,
        title=f"Ads naming {top.skill} advertise {eur_k(top.min_median)} floors against {eur_k(bottom.min_median)} for "
              f"ads naming {bottom.skill} - a {eur_k(top.min_median - bottom.min_median)} spread across the same market",
        source=DEMAND_SOURCE,
        units="euro, annual gross (monthly × 14)",
        n=f"n = {int(table('T09d_salary_by_skill.csv').n.max())} ads maximum per skill; skills with n ≥ 20 shown",
        note=f"Axis starts at €{floor / 1000:.0f}k. Label colour = my profile status "
             "(green have, blue developing, orange structural).",
    )
    return Spec(
        chart_id="BQ17_salary_by_skill",
        question="Which skills sit in the better-paying ads - is the learning list also the earning list?",
        answer=f"Ads mentioning {top.skill} carry {eur_k(top.min_median)} floors against {eur_k(bottom.min_median)} "
               f"for {bottom.skill} ads - engineering and ML wording sits {eur_k(top.min_median - bottom.min_median)} "
               "above reporting and spreadsheet wording, so the NOW list and the pay list point the same way.",
        relationship="ranking",
        mark="dot_plot",
        data_signature="categorical-value",
        tables=["T09d_salary_by_skill.csv", "config/profile.json"],
        units="EUR, annual gross",
        caveat="This is the floor of the ads that *mention* a skill, confounded with seniority, family and employer "
               "size. It is not the price of the skill.",
        anchors=[
            ("docs/market-guide.md", "after_match", "By skill mentioned: Databricks"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ18 - work model
# --------------------------------------------------------------------------------------------
def bq18():
    rem = table("T10_remote_by_family.csv")
    order = ["remote", "hybrid", "hybrid_or_flexible", "on_site", "unknown"]
    colors = {"remote": HILITE, "hybrid": BASE, "hybrid_or_flexible": THIRD, "on_site": FOURTH, "unknown": MUTED}
    # The taxonomy keys are not self-explanatory: "hybrid" is an explicit pattern or a
    # stated number of days, "hybrid_or_flexible" a general home-office mention, and
    # "unknown" is silence in the advertisement - not evidence of on-site work.
    legend_label = {"remote": "fully remote", "hybrid": "hybrid (explicit pattern)",
                    "hybrid_or_flexible": "home office mentioned", "on_site": "on site",
                    "unknown": "not stated"}
    wide = rem.pivot_table(index="role_family", columns="remote_type", values="share").fillna(0)
    wide = wide.reindex(columns=order, fill_value=0)
    wide = wide.loc[[f for f in FAMILY_LABEL if f in wide.index]]
    wide = wide.sort_values("remote")
    family_n = rem.groupby("role_family")["n"].max()
    labels = [family_label_with_n(f, int(family_n.get(f, 0))) for f in wide.index]

    fig, ax = new_figure(height=0.46 * len(wide) + 3.0)
    left = np.zeros(len(wide))
    for col in order:
        ax.barh(labels, wide[col], left=left, color=colors[col], label=legend_label[col])
        for i, (v, l0) in enumerate(zip(wide[col], left)):
            if v > 0.07:
                ax.text(l0 + v / 2, i, f"{v:.0%}", ha="center", va="center", fontsize=8.5,
                        color="white" if col in {"unknown", "hybrid"} else "#222222")
        left = left + wide[col].to_numpy()
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of the family's postings")
    ax.legend(fontsize=8.5, ncol=5, loc="lower center", bbox_to_anchor=(0.5, -0.32))
    overall = table("T10_remote_overall.csv")
    rem_share = float(overall.loc[overall.remote_type == "remote", "share"].iloc[0])
    finalise(
        fig,
        title=f"Fully remote is {rem_share:.0%} of the market: chasing remote roles from Graz means competing for "
              f"{int(overall.loc[overall.remote_type == 'remote', 'count'].iloc[0])} of {int(overall.n.iloc[0])} ads",
        source=DEMAND_SOURCE,
        units="share of the family's postings",
        n=f"n = {int(overall.n.iloc[0])} core postings with a description",
        note="40 % of ads say nothing about the work model; silence is not evidence of on-site.",
    )
    return Spec(
        chart_id="BQ18_work_model",
        question="Is hybrid real, and is chasing fully-remote roles from Graz a trap?",
        answer=f"Fully remote is {rem_share:.0%} of ads "
               f"({int(overall.loc[overall.remote_type == 'remote', 'count'].iloc[0])} postings) - a trap as a "
               "strategy; hybrid or home-office wording covers about half the market, and Styria matches the "
               "national pattern, so commuting distance to Graz stays the binding constraint.",
        relationship="part to whole",
        mark="stacked_bar",
        data_signature="categorical-multi",
        tables=["T10_remote_by_family.csv", "T10_remote_overall.csv"],
        units="share of postings",
        caveat="Wording in the advertisement, not the arrangement actually offered; 40 % of ads are silent.",
        anchors=[
            ("docs/market-guide.md", "after_heading", "## 10. Work model (T10)"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHAT WORK MODE DO THEY OFFER?"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ19 - the side doors
# --------------------------------------------------------------------------------------------
def _sweep_date() -> str:
    """Collection date of the full-text sweep (outputs/adjacent_demand.json), else the demand snapshot date."""
    try:
        return str(json.load(open(ROOT / "outputs" / "adjacent_demand.json", encoding="utf-8"))["collected"])[:10]
    except (OSError, ValueError, KeyError):
        return DEMAND_VINTAGE


def bq19():
    adj = table("T16_adjacent_demand_by_region.csv")
    adj = adj[adj.tool.isin(["Python", "SQL", "Power BI", "Excel"])].copy()
    adj["key"] = adj.region + " · " + adj.tool
    adj = adj.sort_values(["region", "postings_mentioning"])
    y = np.arange(len(adj))

    fig, ax = new_figure(height=0.36 * len(adj) + 3.0)
    ax.barh(y, adj.in_core_data_title, color=BASE, label="under a core data title")
    ax.barh(y, adj.in_non_data_title, left=adj.in_core_data_title, color=HILITE, label="under a non-data title")
    ax.set_yticks(y)
    ax.set_yticklabels(adj.key, fontsize=9)
    ax.set_xlim(left=0)
    ax.set_xlabel("Postings in the AMS full-text sweep mentioning the tool")
    for i, row in enumerate(adj.itertuples()):
        ax.text(row.postings_mentioning * 1.01, i, f"{row.share_non_data_title:.0%} non-data",
                va="center", fontsize=8.5)
    ax.set_xlim(right=adj.postings_mentioning.max() * 1.28)
    ax.legend(fontsize=8.5, loc="lower right")
    sty_py = adj[(adj.region == "Steiermark") & (adj.tool == "Python")].iloc[0]
    finalise(
        fig,
        title=f"{sty_py.share_non_data_title:.0%} of Styrian ads that mention Python carry a non-data title - the "
              "entry doors are controlling, engineering and research jobs, not data titles",
        source=f"AMS/EURES full-text sweep of three regions, {_sweep_date()} (T16)",
        units="postings mentioning the tool",
        n=f"sweep n = {int(adj.sweep_postings_region.min()):,}-{int(adj.sweep_postings_region.max()):,} postings per region (full-text keyword retrieval)",
        note=f"A different retrieval from the {market_counts()['core']}-posting title census: these ads were found by "
             "tool keyword.",
    )
    return Spec(
        chart_id="BQ19_side_doors",
        question="Can I get into data work through a non-data title - do those jobs use the same tools?",
        answer=f"Yes, and it is the larger channel: {sty_py.share_non_data_title:.0%} of Styrian ads mentioning "
               f"Python and {adj[(adj.region == 'Steiermark') & (adj.tool == 'SQL')].iloc[0].share_non_data_title:.0%} "
               "of those mentioning SQL sit under non-data titles (controlling, engineering, research), so data "
               "skills are demanded far more widely than data titles are advertised.",
        relationship="part to whole",
        mark="stacked_bar",
        data_signature="categorical-multi",
        tables=["T16_adjacent_demand_by_region.csv"],
        units="postings",
        caveat="Covers only the AMS feed of three regions and retrieves by full-text keyword, so it is not "
               f"comparable to the {market_counts()['core']}-posting title census.",
        anchors=[
            ("docs/market-guide.md", "after_heading", "## 13. Adjacent demand (T16)"),
            ("docs/career-map.md", "after_heading", "## 5. Pathways supported by the evidence"),
        ],
    ), fig


BUILDERS = [bq01, bq02, bq03, bq04, bq05, bq06, bq07, bq08, bq09, bq10,
            bq11, bq12, bq13, bq14, bq15, bq16, bq17, bq18, bq19]
