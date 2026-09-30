"""Visual decision layer, evidence quality: BQ27-BQ33.

The first follow-up brief asked a set of sceptical questions about the evidence
itself rather than about the market: what does a percentage's denominator
actually contain, how much of the corpus is duplicate or stale, how accurate is
the classification, how small are the Styrian cells, what is a salary figure
really, and how much of the market is invisible. Those answers existed in the
Q*/T* tables and in prose; they had no picture. These seven give them one, so a
reader can calibrate every other figure in the board before trusting it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "viz"))
sys.path.insert(0, str(ROOT / "src" / "analysis"))

from engine import (  # noqa: E402
    BASE,
    DEMAND_SOURCE,
    FOURTH,
    HILITE,
    MUTED,
    PRIMARY_BASIS,
    THIRD,
    Spec,
    finalise,
    label_bars,
    market_counts,
    new_figure,
    styria_basis_note,
)
from visual_questions_demand import FAMILY_LABEL, MIN_FAMILY_N, table  # noqa: E402


# --------------------------------------------------------------------------------------------
# BQ27 - what is behind the denominator
# --------------------------------------------------------------------------------------------
def bq27():
    summary = json.load(open(ROOT / "outputs" / "market_summary.json", encoding="utf-8"))["counts"]
    counts = market_counts()
    dup = table("Q04_duplicates.csv").set_index("metric")["value"]
    steps = [
        ("Raw rows collected from 5 boards", summary["raw_rows_all_sources"]),
        ("Unique postings after deduplication", summary["canonical_groups_all"]),
        ("Core data-role titles (the study set)", summary["core_canonical"]),
        ("… with a description over 300 characters", summary["core_with_description"]),
        ("… listing a Styrian site", summary["styria_core"]),
        ("… inside the Graz commuting area", summary["graz_area_core"]),
    ]
    labels = [s[0] for s in steps][::-1]
    values = [float(s[1]) for s in steps][::-1]
    colors = [HILITE if i < 2 else BASE for i in range(len(values))]

    fig, ax = new_figure(height=0.62 * len(values) + 3.2, width=10.4)
    ax.barh(labels, values, color=colors)
    ax.set_xlim(0, max(values) * 1.24)
    ax.set_xlabel("Postings (linear scale, zero baseline)")
    top = max(values)
    for i, v in enumerate(values):
        text = f"{int(v):,}" if v == top else f"{int(v):,}  ({v / top:.1%} of collected rows)"
        ax.text(v + top * 0.012, i, text, va="center", fontsize=9.5)
    finalise(
        fig,
        title=f"Every share in this project is a share of {summary['core_canonical']} postings, not of the "
              f"{summary['raw_rows_all_sources']:,} rows collected - and the Styrian claims rest on "
              f"{summary['styria_core']}",
        source=DEMAND_SOURCE,
        units="postings (each step is a subset of the one above)",
        n=f"in-scope duplicate rate before deduplication {float(dup['core_duplicate_rate']):.0%} "
          f"({int(dup['core_rows'])} rows → {int(dup['core_groups'])} groups)",
        note="Rows outside the eight data-role families are dropped at step 3; that cut, not the collection, is "
             f"what makes the study set small. {styria_basis_note(counts)}; the Styria and Graz steps count every "
             "ad that lists a site there.",
    )
    return Spec(
        chart_id="BQ27_population_funnel",
        question="When I read '40 % of ads', 40 % of what exactly - and how did 12,429 rows become that denominator?",
        answer=f"{summary['raw_rows_all_sources']:,} raw rows deduplicate to {summary['canonical_groups_all']:,} "
               f"unique postings, of which {summary['core_canonical']} carry a core data-role title - that is the "
               f"denominator behind almost every share in the project, and only {summary['styria_core']} of them "
               f"list a Styrian site ({summary['graz_area_core']} of those in the Graz commuting area).",
        relationship="part to whole",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["outputs/market_summary.json", "Q04_duplicates.csv", "T01_source_coverage.csv"],
        units="postings",
        caveat="Each bar is a subset of the one above it, so the bars must never be summed. Text-derived shares use "
               f"the {counts['core_with_description']} postings with a description, not all {counts['core']}. The Styria "
               f"steps count every ad that lists a Styrian site; {PRIMARY_BASIS} Styria has {counts['styria_primary']}.",
        anchors=[
            ("docs/data-quality.md", "after_heading", "## 1. What was collected"),
            ("docs/methodology.md", "after_heading", "## 5. Analysis sets and denominators"),
            ("docs/market-guide.md", "after_heading", "## 1. Size and sources (T01, T01b, dedupe_summary, market_summary.json)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ28 - how much is mislabelled
# --------------------------------------------------------------------------------------------
def bq28():
    prec = table("Q03c_precision_summary.csv")
    prec = prec[prec.family != "ALL"].copy() if "ALL" in set(prec.family) else prec.copy()
    prec = prec.sort_values("precision_after_strict")
    y = np.arange(len(prec))

    fig, ax = new_figure(height=0.50 * len(prec) + 3.2, width=10.0)
    for i, row in enumerate(prec.itertuples()):
        ax.plot([row.precision_before_strict, row.precision_after_strict], [i, i],
                color=MUTED, linewidth=1.4, zorder=1)
    ax.scatter(prec.precision_before_strict, y, color=MUTED, s=70, zorder=2)
    ax.scatter(prec.precision_after_strict, y, color=BASE, s=85, zorder=3)
    ax.scatter(prec.precision_after_lenient, y, color=THIRD, s=85, marker="D", zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels([FAMILY_LABEL.get(f, f) for f in prec.family])
    ax.set_xlim(0.4, 1.12)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Hand-labelled precision of the title classifier (25 titles sampled per family)")
    top = len(prec) - 1
    for x, text, color in [(prec.precision_before_strict.iloc[top], "before the audit", MUTED),
                           (prec.precision_after_strict.iloc[top], "after (strict)", BASE),
                           (prec.precision_after_lenient.iloc[top], "after (lenient)", THIRD)]:
        ax.annotate(text, (x, top), textcoords="offset points", xytext=(0, 15),
                    ha="center", fontsize=8.5, color=color)
    worst = prec.iloc[0]
    best = prec.iloc[-1]
    fig.canvas.draw()
    finalise(
        fig,
        title=f"After the taxonomy audit the weakest family is {FAMILY_LABEL.get(worst.family, worst.family)} at "
              f"{worst.precision_after_strict:.0%} strict precision, the strongest "
              f"{FAMILY_LABEL.get(best.family, best.family)} at {best.precision_after_strict:.0%}",
        source="Hand-labelled sample of 177 advertised titles, 25 per family (Q03c, DECISION_LOG D-012)",
        units="share of sampled titles judged correctly classified",
        n="n = 25 sampled titles per family",
        note="Precision only: recall was never measured, so a family can still be missing postings it should hold. "
             "Lenient counts borderline titles as correct.",
    )
    return Spec(
        chart_id="BQ28_classification_precision",
        question="How much of what I am reading is in the wrong family - can I trust the role labels at all?",
        answer=f"After the D-012 audit, strict precision runs from {worst.precision_after_strict:.0%} "
               f"({FAMILY_LABEL.get(worst.family, worst.family)}, where IT-analyst and process-owner titles leak in) "
               f"to {best.precision_after_strict:.0%}, lenient from "
               f"{prec.precision_after_lenient.min():.0%} to {prec.precision_after_lenient.max():.0%} - good enough "
               "for ranking families, not for quoting a single family's count to the posting.",
        relationship="deviation from target",
        mark="dumbbell",
        data_signature="categorical-multi",
        tables=["Q03c_precision_summary.csv"],
        units="share of sampled titles",
        caveat="25 titles per family is a small audit sample, and recall is unmeasured: this bounds false positives "
               "only, never false negatives.",
        anchors=[
            ("docs/data-quality.md", "after_heading", "## 4. Title normalization confidence (Q03a, Q03b, Q03c)"),
            ("docs/market-guide.md", "after_match", "**Measured precision.**"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ29 - which Styrian numbers are too small
# --------------------------------------------------------------------------------------------
def bq29():
    fam = table("T02_role_family_counts.csv")
    fam = fam[fam.role_family.isin(FAMILY_LABEL)].sort_values("styria_count")
    labels = [FAMILY_LABEL[f] for f in fam.role_family]
    colors = [THIRD if c >= MIN_FAMILY_N else HILITE for c in fam.styria_count]

    fig, ax = new_figure(height=0.44 * len(fam) + 3.0, width=10.0)
    ax.barh(labels, fam.styria_count, color=colors)
    ax.axvline(MIN_FAMILY_N, color="#222222", linewidth=1.1, linestyle="--")
    ax.text(MIN_FAMILY_N + 0.6, len(fam) - 0.6,
            f"n = {MIN_FAMILY_N}: the project's own threshold\nfor calling a finding robust",
            fontsize=8.5, va="top")
    ax.set_xlim(0, max(fam.styria_count.max(), MIN_FAMILY_N) * 1.55)
    ax.set_xlabel("Open Styrian postings in the family")
    label_bars(ax, list(fam.styria_count),
               [f"{int(v)} of {int(fam.styria_count.sum())}" for v in fam.styria_count])
    finalise(
        fig,
        title=f"No Styrian family reaches {MIN_FAMILY_N} postings - every Styrian statement in this project is "
              "directional, and the correct way to quote it is a count",
        source=DEMAND_SOURCE,
        units="postings",
        n=f"n = {int(fam.styria_count.sum())} Styrian core postings (ads listing a Styrian site) across "
          f"{len(fam)} families",
        note="A percentage over a cell this small moves by several points when one advertisement is added or removed.",
    )
    return Spec(
        chart_id="BQ29_styria_sample_sizes",
        question="Which of my Styrian conclusions are actually too small to carry a decision?",
        answer=f"All of them, by the project's own rule: the largest Styrian family cell is "
               f"{int(fam.styria_count.max())} postings against a robustness threshold of {MIN_FAMILY_N}, and four "
               "families sit at five or fewer - so Styrian findings are read as counts and directions, never as "
               "percentages.",
        relationship="comparison across categories",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["T02_role_family_counts.csv"],
        units="postings",
        caveat="The official yearly series (JB05) puts Styria at 13.6 % of the national flow against "
               f"{market_counts()['styria_primary'] / market_counts()['core']:.1%} here ({PRIMARY_BASIS}; "
               f"{market_counts()['styria_any_site'] / market_counts()['core']:.1%} counting every ad with a Styrian "
               "site), so this snapshot may also understate Styrian volume, not only measure it imprecisely.",
        anchors=[
            ("docs/limitations.md", "after_heading", "## Robust vs. tentative conclusions"),
            ("CAREER_DECISION_MAP.md", "after_match", "**All Styrian figures are tentative"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ30 - what the dataset cannot see
# --------------------------------------------------------------------------------------------
def bq30():
    src = table("T01_source_coverage.csv").sort_values("in_scope_canonical")
    names = {"eures": "EURES / AMS", "jobsat": "jobs.at", "karriere": "karriere.at",
             "linkedin": "LinkedIn", "willhaben": "willhaben"}
    labels = [names.get(s, s) for s in src.source]
    y = np.arange(len(src))

    fig, ax = new_figure(height=0.52 * len(src) + 3.4, width=10.2)
    ax.barh(y, src.rows, color=MUTED, label="rows collected from the source")
    ax.barh(y, src.in_scope_canonical, color=BASE, label="core data-role postings contributed")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, src.rows.max() * 1.30)
    ax.set_xlabel("Rows / postings")
    for i, row in enumerate(src.itertuples()):
        ax.text(row.rows + src.rows.max() * 0.012, i,
                f"{int(row.rows):,} collected → {int(row.in_scope_canonical)} core "
                f"({row.in_scope_canonical / row.rows:.1%})", va="center", fontsize=8.5)
    ax.legend(fontsize=8.5, loc="lower right")
    missing = "StepStone.at, Indeed.at (HTTP 403), hokify, Glassdoor, company career pages, university job portals"
    ax.annotate(f"Not collected at all: {missing}",
                xy=(0.01, 0.02), xycoords="axes fraction", fontsize=8.5, color=HILITE, va="bottom")
    finalise(
        fig,
        title=f"Five boards contributed the {int(src.in_scope_canonical.sum())} core postings - and the two largest "
              "corporate boards in Austria contributed none",
        source=DEMAND_SOURCE,
        units="rows collected and core postings contributed",
        n=f"n = {int(src.rows.sum()):,} raw rows → {int(src.in_scope_canonical.sum())} core canonical postings",
        note="The invisible share cannot be quantified from inside this dataset: what StepStone, Indeed and company "
             "career pages hold is unmeasured, not measured as zero.",
    )
    return Spec(
        chart_id="BQ30_source_coverage",
        question="How much of the Austrian market can this dataset simply not see?",
        answer=f"LinkedIn and EURES/AMS carry most of the {int(src.in_scope_canonical.sum())} core postings, and the "
               "corporate white-collar segment is missing entirely: StepStone.at and Indeed.at returned HTTP 403, "
               "and company career pages, university portals and hokify were never collected - so the corporate "
               "share of Austrian data demand is an unmeasured gap, not a measured absence.",
        relationship="comparison across categories",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["T01_source_coverage.csv", "T01b_source_overlap_in_scope.csv"],
        units="rows / postings",
        caveat="Only 20 % of core postings were seen on more than one source, so the boards are largely disjoint "
               "universes; a missing board is a missing slice, not a redundant one.",
        anchors=[
            ("docs/limitations.md", "after_heading", "## Invisible market: what this dataset plausibly cannot see"),
            ("docs/data-sources.md", "after_heading", "## Tier 2 · job platforms"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ31 - how fresh is the snapshot
# --------------------------------------------------------------------------------------------
def bq31():
    # The percentile columns are named "25%"/"50%"/"75%", which itertuples would expose as
    # positional _4/_5/_6; rename them so the code says what it reads.
    age = table("T13b_posting_age_by_source.csv").rename(
        columns={"25%": "p25", "50%": "median", "75%": "p75"}).sort_values("median")
    names = {"eures": "EURES / AMS", "jobsat": "jobs.at", "karriere": "karriere.at",
             "linkedin": "LinkedIn", "willhaben": "willhaben"}
    labels = [names.get(s, s) for s in age.source]
    y = np.arange(len(age))

    fig, ax = new_figure(height=0.52 * len(age) + 3.2, width=10.0)
    for i, row in enumerate(age.itertuples()):
        ax.plot([row.p25, row.p75], [i, i], color=MUTED, linewidth=3, alpha=0.45, solid_capstyle="butt")
    ax.scatter(age["median"], y, color=BASE, s=85, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, age["p75"].max() * 1.35)
    ax.set_xlabel("Days between first publication and collection (median dot, p25-p75 bar)")
    for i, row in enumerate(age.itertuples()):
        ax.text(row.p75 + age["p75"].max() * 0.03, i,
                f"median {int(row.median)} days  (n = {int(row.count)})", va="center", fontsize=8.5)
    finalise(
        fig,
        title=f"karriere.at ads are a median {int(age['median'].min())} days old and AMS ads "
              f"{int(age['median'].max())} - the same snapshot mixes this week's market with last quarter's",
        source=DEMAND_SOURCE,
        units="days since first publication",
        n=f"n = {int(age['count'].sum())} core postings with a publication date",
        note="karriere.at refreshes its posted date, so its low median partly measures the board's behaviour rather "
             "than genuine freshness.",
    )
    return Spec(
        chart_id="BQ31_posting_freshness",
        question="How fresh is the market I am reading - am I looking at this week or at leftovers?",
        answer=f"It depends entirely on the board: karriere.at shows a median age of {int(age['median'].min())} days "
               f"and EURES/AMS {int(age['median'].max())} days, with 34 core postings older than 180 days - so the "
               "snapshot is a mixture of fresh demand and evergreen advertisements, and source mix drives apparent "
               "freshness.",
        relationship="distribution",
        mark="dot_plot",
        data_signature="categorical-value",
        tables=["T13b_posting_age_by_source.csv", "Q05a_stale.csv"],
        units="days",
        caveat="Publication dates are board-reported and some boards refresh them; age is a lower bound on how long "
               "a vacancy has really been open.",
        anchors=[
            ("docs/data-quality.md", "after_heading", "## 6. Stale postings (Q05, T13b)"),
            ("docs/market-guide.md", "after_heading", "## 12. Time dimension (T13, JB01)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ32 - what a salary figure actually is
# --------------------------------------------------------------------------------------------
def bq32():
    cov = table("T09_salary_coverage.csv").set_index("metric")["count"]
    total = int(cov["core_postings"])
    rows = [
        ("State any salary figure", int(cov["with_salary_figure"]), BASE),
        ("… but the figure is a single minimum", int(cov["minimum_only_figures"]), HILITE),
        ("… a genuine range", int(cov["with_range"]), THIRD),
        ("Name the collective agreement (KV)", int(cov["kv_minimum_mention"]), MUTED),
        ("Say they pay above it (Überzahlung)", int(cov["overpay_mention"]), MUTED),
        ("All-in contract wording", int(cov["all_in_mention"]), FOURTH),
        ("Bonus or variable component", int(cov["bonus_or_variable_mention"]), FOURTH),
    ]
    rows = rows[::-1]
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    colors = [r[2] for r in rows]

    fig, ax = new_figure(height=0.50 * len(rows) + 3.2, width=10.2)
    ax.barh(labels, values, color=colors)
    ax.set_xlim(0, total * 1.02)
    ax.set_xlabel(f"Core postings (of {total})")
    label_bars(ax, values, [f"{v}  ({v / total:.0%})" for v in values])
    finalise(
        fig,
        title=f"{int(cov['with_salary_figure'])} of {total} ads state a figure, but "
              f"{int(cov['minimum_only_figures']) / int(cov['with_salary_figure']):.0%} of those figures are a single "
              "collective-agreement minimum - the number is a legal floor, not an offer",
        source=DEMAND_SOURCE,
        units="postings",
        n=f"n = {total} core postings; {int(cov['with_salary_figure'])} with a parsed figure",
        note="Bars are not mutually exclusive and must not be summed. Actual compensation cannot be estimated from "
             "advertisements at all (docs/salary-context.md).",
    )
    return Spec(
        chart_id="BQ32_salary_evidence",
        question="When an advertisement shows me a salary, what am I actually looking at?",
        answer=f"A legal floor in most cases: {int(cov['with_salary_figure'])} of {total} ads state a figure, "
               f"{int(cov['minimum_only_figures'])} of those are a single minimum and only {int(cov['with_range'])} "
               f"are a range; {int(cov['kv_minimum_mention'])} name the collective agreement and "
               f"{int(cov['overpay_mention'])} say they pay above it - so every salary figure in this project is the "
               "bottom of a negotiation, never the market price.",
        relationship="comparison across categories",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["T09_salary_coverage.csv", "T09a_salary_basis_by_source.csv"],
        units="postings",
        caveat="Categories overlap by construction (an ad can state a minimum, name the KV and mention a bonus). "
               "LinkedIn omits a figure in 41 % of its core ads, so coverage is also a source-mix artefact.",
        anchors=[
            ("docs/market-guide.md", "after_heading", "## 9. Advertised salary (T09, docs/salary-context.md)"),
            ("docs/data-quality.md", "after_heading", "## 7. Salary parsing (Q07, Q07a, Q07b, T09)"),
            ("docs/salary-context.md", "after_heading", "## How to read our posting-level figures against these"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ33 - who is behind the postings
# --------------------------------------------------------------------------------------------
def bq33():
    conc = table("T04b_employer_concentration.csv").set_index("metric")["value"]
    total = int(conc["core_postings_total"])
    named = int(conc["postings_with_named_employer"])
    fig, ax = new_figure(height=5.4, width=10.2)
    segments = [
        ("Named employer", named, BASE),
        ("No employer named (all AMS/EURES rows)", int(conc["postings_without_named_employer"]), HILITE),
    ]
    left = 0.0
    for label, value, color in segments:
        ax.barh([""], [value], left=left, color=color, label=f"{label}: {value} ({value / total:.0%})")
        ax.text(left + value / 2, 0, f"{value}", ha="center", va="center", fontsize=11,
                color="white", fontweight="bold")
        left += value
    ax.set_xlim(0, total)
    ax.set_ylim(-0.9, 2.6)
    ax.set_xlabel(f"Core postings (n = {total})")
    ax.legend(fontsize=9, loc="upper left")
    ax.set_yticks([])
    notes = [
        f"{int(conc['unique_named_employers_austria'])} unique named employers in Austria, "
        f"{int(conc['unique_named_employers_styria'])} in Styria, {int(conc['unique_named_employers_graz_area'])} in the Graz area",
        f"Top 10 named employers hold {conc['top10_share_of_named']:.1%} of named postings; top 25 hold {conc['top25_share_of_named']:.1%}",
        f"Recruitment agencies are {conc['agency_share_of_named_postings']:.1%} of named postings",
        f"Styria: {int(conc['styria_postings_without_named_employer'])} of 58 postings name no employer",
    ]
    for i, text in enumerate(notes):
        ax.text(0, 1.9 - i * 0.42, "• " + text, fontsize=9.5, va="center")
    finalise(
        fig,
        title=f"{int(conc['unique_named_employers_austria'])} named employers hold {named} of {total} postings and no "
              f"employer holds more than a few - but {int(conc['postings_without_named_employer'])} ads name nobody at all",
        source=DEMAND_SOURCE,
        units="postings and unique employers",
        n=f"n = {total} core postings; {named} with a named employer",
        note="The 387 named employers are a lower bound on employers represented: the anonymous AMS rows may belong "
             "to the same firms or to different ones - that cannot be determined.",
    )
    return Spec(
        chart_id="BQ33_employer_structure",
        question="Who is actually behind these postings - is demand concentrated in a few employers I could target?",
        answer=f"No: {int(conc['unique_named_employers_austria'])} named employers share {named} postings, the top ten "
               f"hold only {conc['top10_share_of_named']:.1%} of them and agencies {conc['agency_share_of_named_postings']:.1%} - "
               f"the market is fragmented, so a target list is long rather than short; "
               f"{int(conc['postings_without_named_employer'])} postings ({int(conc['postings_without_named_employer']) / total:.0%}) "
               "name no employer at all and are invisible to any target list.",
        relationship="part to whole",
        mark="stacked_bar",
        data_signature="categorical-multi",
        tables=["T04b_employer_concentration.csv", "T04_employers.csv", "T04a_employers_styria.csv"],
        units="postings",
        caveat="Employer identity is taken from the advertisement; the same firm advertising under a group name and "
               "an agency is counted twice, and the anonymous AMS rows cannot be attributed at all.",
        anchors=[
            ("docs/market-guide.md", "after_match", "* **Named vs represented.**"),
        ],
    ), fig


BUILDERS = [bq27, bq28, bq29, bq30, bq31, bq32, bq33]
