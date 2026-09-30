"""Visual decision layer, Layers 2-3 (observed supply, demand × supply): BQ20-BQ26.

These figures join two different universes - advertisements and public GitHub
accounts - so every one of them carries the same warning in its note line:
rankings and orders of magnitude, never exact ratios. A low supply share for a
tool that leaves no public code trace (Power BI, Excel, SAP) measures GitHub's
blindness, not the candidates; the charts encode that distinction rather than
hiding it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "viz"))
sys.path.insert(0, str(ROOT / "src" / "analysis"))

from engine import (  # noqa: E402
    BASE,
    DEMAND_SOURCE,
    FOURTH,
    HILITE,
    MUTED,
    SUPPLY_SOURCE,
    THIRD,
    Spec,
    finalise,
    label_bars,
    market_counts,
    new_figure,
    spread_labels,
)
from visual_questions_demand import FAMILY_LABEL, table  # noqa: E402

JOINT_SOURCE = f"{DEMAND_SOURCE}; {SUPPLY_SOURCE}"
JOINT_NOTE = ("Two different universes joined on shared taxonomies - read rankings and orders of magnitude, "
              "never exact ratios.")


# --------------------------------------------------------------------------------------------
# BQ20 - how crowded is each family
# --------------------------------------------------------------------------------------------
def bq20():
    ds1 = table("DS01_demand_supply_role_families.csv")
    ds1 = ds1[ds1.category.isin(FAMILY_LABEL) & (ds1.demand_count >= 20)].copy()
    ds1 = ds1.sort_values("candidate_density_T1_per_posting")
    y = np.arange(len(ds1))

    fig, ax = new_figure(height=0.56 * len(ds1) + 3.0)
    sty = ds1.density_styria.replace(0, np.nan)
    for i, (a, s) in enumerate(zip(ds1.candidate_density_T1_per_posting, sty)):
        if not np.isnan(s):
            ax.plot([min(a, s), max(a, s)], [i, i], color=MUTED, linewidth=1.3, zorder=1)
    ax.scatter(ds1.candidate_density_T1_per_posting, y, color=BASE, s=85, zorder=3)
    ax.scatter(sty, y, color=HILITE, s=85, marker="D", zorder=3)
    ax.axvline(1.0, color="#222222", linewidth=0.9, linestyle="--")
    ax.text(1.04, len(ds1) - 0.45, "one declared candidate\nper posting",
            fontsize=8.5, color="#222222", va="top")
    ax.set_xscale("log")
    ax.set_yticks(y)
    ax.set_yticklabels([FAMILY_LABEL[c] for c in ds1.category])
    ax.set_xlabel("Bio-declared GitHub candidates per open posting (log scale)")
    # Direct labels instead of a legend, on the top row only (DSX: a legend a label can replace).
    top = len(ds1) - 1
    ax.annotate("Austria", (ds1.candidate_density_T1_per_posting.iloc[top], top), textcoords="offset points",
                xytext=(0, 14), ha="center", fontsize=9, color=BASE)
    if not np.isnan(sty.iloc[top]):
        ax.annotate("Styria", (sty.iloc[top], top), textcoords="offset points",
                    xytext=(0, 14), ha="center", fontsize=9, color=HILITE)
    for i, row in enumerate(ds1.itertuples()):
        anchor = np.nanmax([row.candidate_density_T1_per_posting, row.density_styria or np.nan])
        ax.text(anchor * 1.14, i,
                f"AT {row.candidate_density_T1_per_posting:.2f} · {int(row.supply_count)} bios / {int(row.demand_count)} ads",
                va="center", fontsize=8)
    ax.set_xlim(right=ds1.candidate_density_T1_per_posting.max() * 9)
    sci = ds1[ds1.category == "data_science"].iloc[0]
    eng = ds1[ds1.category == "data_engineering"].iloc[0]
    ana = ds1[ds1.category == "data_analytics"].iloc[0]
    finalise(
        fig,
        title=f"Visible competition is {sci.candidate_density_T1_per_posting:.1f} declared data scientists per data-science "
              f"posting but {eng.candidate_density_T1_per_posting:.2f} engineers per engineering posting - the label I "
              "pick decides the crowd I stand in",
        source=JOINT_SOURCE,
        units="bio-declared candidates per open posting",
        n=f"n = {int(ds1.demand_n.max())} postings / {int(ds1.supply_n.max())} bio-declared GitHub accounts "
          f"(Styria: {int(ds1.demand_styria.sum())} postings listing a Styrian site / "
          f"{int(ds1.supply_styria_T1.sum())} location-resolved accounts across these families)",
        note=JOINT_NOTE + " GitHub cannot see BI, Excel or SAP practitioners; the Styrian marker is omitted where no bio-declared candidate was observed (marketing analytics).",
    )
    return Spec(
        chart_id="BQ20_competition_density",
        question="How many visible candidates am I standing next to per opening, depending on the label I choose?",
        answer=f"Data science shows {sci.candidate_density_T1_per_posting:.1f} declared candidates per posting "
               f"({sci.density_styria:.1f} in Styria) against {eng.candidate_density_T1_per_posting:.2f} for "
               f"engineering and {ana.candidate_density_T1_per_posting:.2f} for analytics - calling myself a data "
               "scientist puts me in the densest queue on the board.",
        relationship="ranking",
        mark="dot_plot",
        data_signature="categorical-value",
        tables=["DS01_demand_supply_role_families.csv"],
        units="candidates per posting",
        caveat="GitHub over-represents engineers, researchers and students and is blind to BI/Excel/SAP work, so a "
               "low density is partly real scarcity and partly invisibility. Vienna counts are lower bounds.",
        anchors=[
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_heading", "## 4. Where do they diverge? (DS01, DS02, DS03)"),
            ("docs/supply-findings.md", "after_heading", "## 2. Titles and families (C02, C03, C04, C04b, DS01, DS02)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ21 - the flagship: where is portfolio effort worth most
# --------------------------------------------------------------------------------------------
def bq21():
    ds10 = table("DS10_demand_supply_capability_evidence.csv").copy()
    # Below 10 % of ads a capability cannot carry a portfolio decision; the cut keeps
    # the figure readable and is declared in the note.
    ds10 = ds10[ds10.demand_share >= 0.10].copy()
    ds10["observable"] = ds10.observability.str.startswith("observable")
    ds10["gap"] = ds10.demand_share - ds10.supply_project_share

    fig, ax = new_figure(height=7.4, width=10.4)
    lim = max(ds10.demand_share.max(), ds10.supply_project_share.max()) * 1.14
    ax.plot([0, lim], [0, lim], color=MUTED, linewidth=1, linestyle=":")
    ax.annotate("shown as often as it is asked for", xy=(lim * 0.70, lim * 0.72), fontsize=8.5,
                color=MUTED, rotation=41, ha="center", rotation_mode="anchor")

    def point_color(row):
        if not row.observable:
            return MUTED
        return HILITE if row.gap > 0.15 else BASE

    ds10 = ds10.sort_values("supply_project_share")
    # Label the points a decision turns on; the rest stay as dots so the labelled ones
    # have room to be read.
    ds10["labelled"] = (
        (ds10.gap > 0.12) | (~ds10.observable)
        | (ds10.supply_project_share >= 0.15) | (ds10.demand_share >= 0.30)
    )
    for _, row in ds10[~ds10.labelled].iterrows():
        ax.scatter(row.demand_share, row.supply_project_share, s=52, color=point_color(row),
                   marker="o", alpha=0.55, zorder=3)
    shown = ds10[ds10.labelled].copy()
    # Two label columns - one reading right from the left-hand points, one reading left
    # from the right-hand points. Spreading each column on its own halves the crowding,
    # which is what keeps the leader lines short.
    shown["to_right"] = shown.demand_share < lim * 0.52
    for side in (True, False):
        group = shown[shown.to_right == side]
        if group.empty:
            continue
        # min_gap is one label height in data units: 8.5 pt over the axes height,
        # with a quarter of a line of air. Spacing labels further than that is what
        # turns leader lines into long diagonals.
        label_height = (8.5 / 72) / (fig.get_size_inches()[1] * 0.62) * lim
        label_y = spread_labels(list(group.supply_project_share), min_gap=label_height * 1.25,
                                lo=0.0, hi=lim * 0.94)
        for (_, row), ly in zip(group.iterrows(), label_y):
            color = point_color(row)
            ax.scatter(row.demand_share, row.supply_project_share, s=80, color=color,
                       marker="o" if row.observable else "X", alpha=0.95, zorder=3)
            lx = row.demand_share + (lim * 0.04 if side else -lim * 0.04)
            ax.plot([row.demand_share, lx], [row.supply_project_share, ly],
                    color=color, linewidth=0.6, alpha=0.5, zorder=2)
            ax.annotate(row.category, (lx, ly), fontsize=8.5, color=color,
                        ha="left" if side else "right", va="center", zorder=4)
    ax.set_xlim(0, lim)
    ax.set_ylim(-lim * 0.10, lim)
    ax.set_xlabel("Share of Austrian ads mentioning the capability")
    ax.set_ylabel("Share of candidates with project evidence")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.scatter([], [], color=HILITE, label="demanded, rarely demonstrated, and visible on GitHub")
    ax.scatter([], [], color=BASE, label="observable on GitHub, smaller gap")
    ax.scatter([], [], color=MUTED, marker="x", label="not observable on GitHub (Power BI, Excel, SAP, soft skills)")
    ax.legend(fontsize=8.5, loc="upper left")
    sql = ds10[ds10.category == "SQL"].iloc[0]
    finalise(
        fig,
        title=f"SQL is named in {sql.demand_share:.0%} of ads and demonstrated in a project by "
              f"{sql.supply_project_share:.0%} of observed candidates - the largest gap that a portfolio can actually close",
        source=JOINT_SOURCE,
        units="share of ads (x) and share of candidates with project evidence (y)",
        n=f"n = {int(ds10.demand_n.max())} postings with description / {int(ds10.supply_n.max()):,} data-signal "
          f"candidates / {int(ds10.n_substantive_projects.max()):,} substantive projects",
        note=JOINT_NOTE + " Capabilities mentioned in under 10 % of ads are omitted. Crosses are capabilities GitHub cannot see - their low position is blindness, not absence.",
    )
    return Spec(
        chart_id="BQ21_evidence_gap",
        question="Where is a month of portfolio work worth most - what is demanded often and demonstrated rarely?",
        answer=f"SQL ({sql.demand_share:.0%} of ads vs {sql.supply_project_share:.0%} of candidates with project "
               "evidence), data quality/validation, dimensional modelling and Azure pipelines sit furthest below the "
               "diagonal among the capabilities GitHub can actually see - and business framing sits with them. Power "
               "BI, Excel and SAP are equally demanded but cannot be closed with public code.",
        relationship="correlation",
        mark="scatter",
        data_signature="bivariate-simple",
        tables=["DS10_demand_supply_capability_evidence.csv"],
        units="share of ads / share of candidates",
        caveat="Two universes, one taxonomy: the axes are not the same denominator and the diagonal is a reading "
               "aid, not an identity. A capability marked not-observable is invisible to this measurement.",
        anchors=[
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_heading",
             "## 6. Which capabilities are demanded but less publicly demonstrated? "
             "(DS10 label \"demanded, rarely project-demonstrated\": demand ≥ median and project-demonstrated share "
             "< ½ demand share)"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHAT SHOULD I BUILD?"),
            ("docs/project-evidence-map.md", "after_heading", "# Project evidence map (portfolio architecture from evidence)"),
            ("docs/supply-findings.md", "after_heading", "## 7. Capabilities and evidence strength (C11, DS10)"),
            ("docs/career-map.md", "after_heading", "## 8. Project-selection intelligence (what ads actually ask for)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ22 - what is crowded vs scarce
# --------------------------------------------------------------------------------------------
def bq22():
    ds3 = table("DS03_demand_supply_skills.csv").rename(columns={"category": "skill"}).copy()
    ds3 = ds3[(ds3.demand_share >= 0.04) | (ds3.supply_share >= 0.15)]
    ds3 = ds3.reindex(ds3.difference_pp.abs().sort_values(ascending=False).index).head(18)
    ds3 = ds3.sort_values("difference_pp")
    colors = [HILITE if v < 0 else BASE for v in ds3.difference_pp]

    fig, ax = new_figure(height=0.42 * len(ds3) + 3.0)
    ax.barh(ds3.skill, ds3.difference_pp, color=colors)
    ax.axvline(0, color="#222222", linewidth=0.9)
    span = ds3.difference_pp.abs().max()
    ax.set_xlim(-span * 1.62, span * 1.62)
    ax.set_xlabel("Percentage points: share of candidates with evidence minus share of ads mentioning it")
    for i, row in enumerate(ds3.itertuples()):
        ax.text(row.difference_pp + (1.3 if row.difference_pp >= 0 else -1.3), i,
                f"ads {row.demand_share:.0%} · candidates {row.supply_share:.0%}",
                va="center", ha="left" if row.difference_pp >= 0 else "right", fontsize=8)
    ax.text(0.99, 0.03, "→ abundant in portfolios", transform=ax.transAxes, ha="right", fontsize=9, color=BASE)
    ax.text(0.01, 0.03, "← scarce in portfolios", transform=ax.transAxes, ha="left", fontsize=9, color=HILITE)
    scarce = ds3.iloc[0]
    abundant = ds3.iloc[-1]
    finalise(
        fig,
        title=f"{abundant.skill} is {abundant.difference_pp:+.0f} pp more common in portfolios than in ads, while "
              f"{scarce.skill} is {scarce.difference_pp:.0f} pp scarcer - the public pool is not building what is advertised",
        source=JOINT_SOURCE,
        units="percentage points (candidate evidence share minus ad mention share)",
        n=f"n = {int(ds3.demand_n.max())} postings with description / {int(ds3.supply_n.max()):,} data-signal "
          "candidates",
        note=JOINT_NOTE,
    )
    return Spec(
        chart_id="BQ22_crowded_vs_scarce",
        question="Which skills is everyone already showing, and which ones would actually distinguish me?",
        answer=f"{abundant.skill}, notebooks and deep-learning frameworks run far ahead of demand "
               f"({abundant.difference_pp:+.0f} pp), while {scarce.skill}, Power BI, Azure and data modelling run far "
               "behind it - a portfolio built only of notebooks competes in the densest part of the pool.",
        relationship="deviation from target",
        mark="diverging_bar",
        data_signature="categorical-value",
        tables=["DS03_demand_supply_skills.csv"],
        units="percentage points",
        caveat="Supply shares come from public code and profiles; tools that leave no code trace are understated by "
               "construction.",
        anchors=[
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_heading",
             "## 7. Which technologies are common but not differentiating? (DS10 quadrant C)"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHAT SHOULD I STOP SPENDING TIME ON?"),
            ("docs/supply-findings.md", "after_heading", "## 6. Technologies (C10, C10b–e, C12, DS03, DS04)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ23 - what does a public portfolio contain
# --------------------------------------------------------------------------------------------
def bq23():
    fmt = table("C17_project_formats.csv")
    fmt = fmt[fmt.population == "projects"]
    demand_mapped = {"sql_files", "dashboard_bi", "pipeline_project", "tests", "ci", "docs_folder"}
    # The 16 most common formats, plus every demand-mapped format even when it is rare -
    # the contrast between the two sets is the whole point of the figure.
    keep = set(fmt.sort_values("share").tail(16)["format"]) | demand_mapped
    fmt = fmt[fmt["format"].isin(keep)].sort_values("share")
    colors = [HILITE if f in demand_mapped else BASE for f in fmt["format"]]

    fig, ax = new_figure(height=0.36 * len(fmt) + 3.0)
    ax.barh(fmt["format"].str.replace("_", " "), fmt.share, color=colors)
    ax.set_xlim(left=0, right=fmt.share.max() * 1.32)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of public Austrian data projects carrying the format")
    label_bars(ax, list(fmt.share), [f"{s:.1%} ({int(c):,})" for s, c in zip(fmt.share, fmt["count"])])
    nb = fmt[fmt["format"] == "notebook"].iloc[0]
    sqlf = fmt[fmt["format"] == "sql_files"].iloc[0]
    finalise(
        fig,
        title=f"Notebooks are {nb.share:.0%} of public Austrian data projects and SQL files {sqlf.share:.1%} - the "
              "format employers name most often is the one almost nobody publishes",
        source=SUPPLY_SOURCE,
        units="share of projects",
        n=f"n = {int(nb.n):,} public projects by data-signal accounts",
        note="Highlighted formats are the ones that map onto demanded capabilities (SQL, dashboards, pipelines, tests, CI).",
    )
    return Spec(
        chart_id="BQ23_project_formats",
        question="What does a normal public portfolio in Austria actually contain - and what would stand out?",
        answer=f"Notebooks ({nb.share:.0%}) and Python packages dominate, while SQL files ({sqlf.share:.1%}), "
               "dashboards, pipelines, tests and CI are rare - the packaging that maps onto advertised work is "
               "precisely the packaging almost nobody publishes.",
        relationship="ranking",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["C17_project_formats.csv"],
        units="share of projects",
        caveat="Format detection is rule-based over repository file trees; a private or client project leaves no "
               "trace here.",
        anchors=[
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_heading", "## 17. Which project formats are common? (C17, C17b)"),
            ("docs/supply-findings.md", "after_heading", "## 11. Formats and packaging (C17, C17b)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ24 - what a README says vs what a decision needs
# --------------------------------------------------------------------------------------------
def bq24():
    rd = table("C19_readme_patterns.csv")
    rd = rd[(rd.population == "documented projects") & rd.feature.str.startswith("section:")].copy()
    rd["label"] = rd.feature.str.replace("section: ", "", regex=False).str.replace("_", " ")
    rd = rd.sort_values("share")
    analysis_sections = {"results", "limitations", "business context"}
    colors = [HILITE if lab in analysis_sections else BASE for lab in rd.label]

    fig, ax = new_figure(height=0.40 * len(rd) + 3.0)
    ax.barh(rd.label, rd.share, color=colors)
    ax.errorbar(rd.share, np.arange(len(rd)),
                xerr=[rd.share - rd.ci_low, rd.ci_high - rd.share],
                fmt="none", ecolor="#444444", capsize=2, linewidth=0.9)
    ax.set_xlim(left=0, right=rd.share.max() * 1.30)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of documented READMEs carrying the section (Wilson 95 % CI)")
    # Label beyond the interval, not beyond the bar: otherwise the whisker strikes the text.
    for i, row in enumerate(rd.itertuples()):
        ax.text(row.ci_high + rd.share.max() * 0.022, i, f"{row.share:.0%}",
                va="center", fontsize=9, color="#222222")
    run = rd[rd.label == "reproducibility"].iloc[0]
    biz = rd[rd.label == "business context"].iloc[0]
    res = rd[rd.label == "results"].iloc[0]
    finalise(
        fig,
        title=f"{run.share:.0%} of documented READMEs explain how to run the code; {res.share:.0%} state a result and "
              f"{biz.share:.0%} a business question - the analysis README is the minority pattern",
        source=SUPPLY_SOURCE,
        units="share of documented READMEs",
        n=f"n = {int(run.n):,} documented projects",
        note="Section detection is heading- and keyword-based; a README can carry the content without the heading.",
    )
    return Spec(
        chart_id="BQ24_readme_anatomy",
        question="If a hiring manager opens one of my repositories, what does the average one give them - and what is missing?",
        answer=f"Public READMEs are software READMEs: {run.share:.0%} say how to run the code, but only "
               f"{res.share:.0%} state a result, {rd[rd.label == 'limitations'].iloc[0].share:.0%} state limitations "
               f"and {biz.share:.0%} state a business question - question → data → method → result → limitation → "
               "decision is the rarest structure in the pool and the one my 20 years of marketing work can write "
               "without learning anything new.",
        relationship="ranking",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["C19_readme_patterns.csv"],
        units="share of documented READMEs",
        caveat="Detects headings and keywords, not quality; a README with the section can still be empty of "
               "substance.",
        anchors=[
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_heading", "## 16. What do candidate READMEs look like? (C19, C19c, C19e)"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHAT SHOULD MY GITHUB DEMONSTRATE?"),
            ("docs/supply-findings.md", "after_heading", "## 12. READMEs (C19, C19b–e)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ25 - seniority mismatch
# --------------------------------------------------------------------------------------------
def bq25():
    ds7 = table("DS07_demand_supply_seniority.csv").copy()
    # DS07 carries the raw taxonomy keys on both sides ("intern_student ↔ student");
    # the figure is read by a human, so it gets the human name.
    readable = {
        "intern_student ↔ student": "Intern or student",
        "trainee_junior ↔ junior": "Junior or trainee",
        "unspecified ↔ unlabelled": "No seniority word",
        "senior ↔ senior": "Senior",
        "lead_head ↔ lead_head": "Lead or head",
    }
    ds7["label"] = ds7.category.map(readable).fillna(ds7.category)
    ds7 = ds7.sort_values("demand_share")
    y = np.arange(len(ds7))

    fig, ax = new_figure(height=0.52 * len(ds7) + 3.0)
    for i, row in enumerate(ds7.itertuples()):
        ax.plot([row.demand_share, row.supply_share], [i, i], color=MUTED, linewidth=1.5, zorder=1)
    ax.scatter(ds7.demand_share, y, color=BASE, s=90, zorder=3, label="share of advertisements (title)")
    ax.scatter(ds7.supply_share, y, color=HILITE, s=90, marker="D", zorder=3, label="share of public profiles (bio)")
    ax.set_yticks(y)
    ax.set_yticklabels(ds7.label)
    ax.set_xlim(0, max(ds7.demand_share.max(), ds7.supply_share.max()) * 1.18)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of the side's population")
    ax.legend(fontsize=8.5, loc="lower right")
    for i, row in enumerate(ds7.itertuples()):
        ax.text(max(row.demand_share, row.supply_share) + 0.02, i,
                f"{row.difference_pp:+.0f} pp", va="center", fontsize=8.5)
    student = ds7[ds7.category.str.contains("student")].iloc[0]
    senior = ds7[ds7.category.str.contains("senior")].iloc[0]
    # Senior and lead are separate rows in DS07; the decision documents quote them together.
    lead = ds7[ds7.category.str.contains("lead")].iloc[0]
    demand_top = senior.demand_share + lead.demand_share
    supply_top = senior.supply_share + lead.supply_share
    finalise(
        fig,
        title=f"Senior or lead wording is in {demand_top:.0%} of ads but {supply_top:.0%} of public profiles, while "
              f"{student.supply_share:.0%} of profiles are students - experience is the scarce side of the visible pool",
        source=JOINT_SOURCE,
        units="share of the side's population",
        n=f"n = {int(ds7.demand_n.max())} postings / {int(ds7.supply_n.max())} bio-declared accounts",
        note=JOINT_NOTE + " Unlabelled dominates both sides (57.5 % of ads, 68 % of bios).",
    )
    return Spec(
        chart_id="BQ25_seniority_mismatch",
        question="Ads keep asking for seniors - am I actually competing with seniors?",
        answer=f"Not in the visible pool: {demand_top:.0%} of ads carry senior or lead wording (senior alone "
               f"{senior.demand_share:.0%}) against {supply_top:.0%} of public profiles, and "
               f"{student.supply_share:.0%} of profiles are students - so twenty years of business experience plus "
               "documented projects is an unusual combination where the portfolios are, even though the ads ask "
               "for it.",
        relationship="deviation from target",
        mark="dumbbell",
        data_signature="categorical-multi",
        tables=["DS07_demand_supply_seniority.csv"],
        units="share of population",
        caveat="Seniority read from ad titles and bio wording; years of experience are not observable on either "
               "side, and senior practitioners publish less.",
        anchors=[
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_heading", "## 11. How does seniority alter the picture? (DS07, DS07b)"),
            ("docs/supply-findings.md", "after_heading", "## 4. Seniority and status (C06, C06b–e, DS07, DS07b)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ26 - does marketing + data exist as a space
# --------------------------------------------------------------------------------------------
def bq26():
    ds12 = table("DS12_marketing_x_data_intersection.csv")
    supply = ds12[ds12.side == "supply"].iloc[0]
    demand = ds12[ds12.side == "demand"].iloc[0]
    steps = [
        ("Data-signal candidates observed", supply.n),
        ("… naming any marketing/customer capability", supply.P_data_marketing_capability_any),
        ("… with a marketing-themed project", supply.P_data_marketing_theme_projects),
        ("… and Python + SQL in it", supply.P_data_marketing_AND_python_sql),
        ("… and experimentation or causal work", supply.P_data_marketing_AND_experimentation),
    ]
    labels = [s[0] for s in steps][::-1]
    values = [float(s[1]) for s in steps][::-1]
    colors = [HILITE if i == 0 else BASE for i in range(len(values))]

    fig, ax = new_figure(height=0.60 * len(values) + 3.2, width=10.0)
    ax.barh(labels, values, color=colors)
    # Linear, not log: these are bars, and length has to stay proportional. The last bar
    # being almost invisible against the first one is the finding, not a rendering problem.
    ax.set_xlim(0, max(values) * 1.24)
    ax.set_xlabel("Public Austrian accounts with this evidence")
    for i, v in enumerate(values):
        share = v / max(values)
        text = f"{int(v):,}" if v == max(values) else f"{int(v):,}  ({share:.1%} of the pool)"
        ax.text(v + max(values) * 0.012, i, text, va="center", fontsize=9.5)
    finalise(
        fig,
        title=f"Fewer than {int(supply.P_data_marketing_AND_experimentation) + 2} public Austrian accounts combine "
              f"marketing data with experimentation - against {int(demand.marketing_analytics_postings)} "
              f"marketing-analytics ads nationally and {int(demand.marketing_analytics_styria)} in Styria",
        source=JOINT_SOURCE,
        units="public accounts (linear scale, zero baseline)",
        n=f"n = {int(supply.n):,} data-signal accounts; demand n = {market_counts()['core']} postings",
        note=JOINT_NOTE + " The demand side of this intersection is 24 ads - a rare space on both sides.",
    )
    return Spec(
        chart_id="BQ26_marketing_x_data",
        question="My 20 years are in marketing - does the marketing × data intersection actually exist as a space I can own?",
        answer=f"It exists in projects, not in titles: {int(supply.P_data_marketing_theme_projects)} of "
               f"{int(supply.n):,} observed candidates have a marketing-themed project, "
               f"{int(supply.P_data_marketing_AND_python_sql)} pair it with Python and SQL and only "
               f"{int(supply.P_data_marketing_AND_experimentation)} add experimentation or causal work - but demand "
               f"is only {int(demand.marketing_analytics_postings)} marketing-analytics ads nationally and "
               f"{int(demand.marketing_analytics_styria)} in Styria, so it is a differentiator inside analyst "
               "applications, not a local job title.",
        relationship="ranking",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["DS12_marketing_x_data_intersection.csv", "C24_marketing_data_intersection.csv"],
        units="accounts",
        caveat="Each step is a subset of the one above it. Public GitHub does not narrate career changes (3.4 % "
               "explicit, marketing 0), so transitioners are invisible here rather than absent.",
        anchors=[
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_heading",
             "## 19. What does the marketing + data intersection look like? (C22d, C24, DS12)"),
            ("CAREER_DECISION_MAP.md", "after_match",
             "**Marketing/CRM/web analytics (domain angle).**"),
            ("docs/supply-findings.md", "after_heading", "## 10. Project topics (C18, C18b, C18c, C24)"),
        ],
    ), fig


BUILDERS = [bq20, bq21, bq22, bq23, bq24, bq25, bq26]
