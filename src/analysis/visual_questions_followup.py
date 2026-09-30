"""Visual decision layer, second pass: BQ34-BQ44.

The two original briefs asked more questions than the first 26 figures answered.
`docs/question-coverage-audit.md` contrasts every question in those briefs with
the board; this module holds the figures added to close the answerable gaps:

  BQ34  German level actually demanded            (brief 1 §9)
  BQ35  tools and languages vs libraries          (brief 1 §12)
  BQ36  certifications on both sides              (brief 1 §11, brief 2 §12)
  BQ37  geography of supply against demand        (brief 2 §7, §26)
  BQ38  education on both sides                   (brief 2 §11, §28)
  BQ39  title fragmentation in the candidate pool (brief 2 §5)
  BQ40  how many projects a candidate shows       (brief 2 §13)
  BQ41  what candidates actually build            (brief 2 §15)
  BQ42  what kind of repositories these are       (brief 2 §18)
  BQ43  positioning clusters and their crowding   (brief 2 §30)
  BQ44  transitions into data                     (brief 2 §31)
  BQ45  skill premium after controls              (brief 1 §10/§14, brief 2 §46)

Questions that could not be answered from the data are not silently dropped:
they are registered in `docs/open-questions.md` with what is missing and what
would close them.
"""
from __future__ import annotations

import json
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
    PRIMARY_BASIS,
    SUPPLY_SOURCE,
    THIRD,
    Spec,
    finalise,
    label_bars,
    market_counts,
    new_figure,
    spread_labels,
    styria_basis_note,
)
from visual_questions_demand import FAMILY_LABEL, n_desc, table  # noqa: E402

JOINT_SOURCE = f"{DEMAND_SOURCE}; {SUPPLY_SOURCE}"
JOINT_NOTE = ("Two different universes joined on shared taxonomies - read rankings and orders of magnitude, "
              "never exact ratios.")


# --------------------------------------------------------------------------------------------
# BQ34 - what German level is actually demanded
# --------------------------------------------------------------------------------------------
def bq34():
    lvl = table("T07a_german_level_overall.csv")
    req = table("T07_german_requirement_by_overall.csv")
    order = {"A1-A2": 0, "B1": 1, "B2/good": 2, "C1/fluent": 3, "C2/native": 4}
    lvl = lvl.sort_values("german_level_bucket", key=lambda s: s.map(order))
    y = np.arange(len(lvl))
    my_level = {"A1-A2", "B1"}
    colors = [THIRD if b in my_level else HILITE for b in lvl.german_level_bucket]

    fig, ax = new_figure(height=0.52 * len(lvl) + 3.2, width=10.0)
    ax.barh(lvl.german_level_bucket, lvl.share, color=colors)
    ax.errorbar(lvl.share, y, xerr=[lvl.share - lvl.ci_low, lvl.ci_high - lvl.share],
                fmt="none", ecolor="#444444", capsize=2, linewidth=0.9)
    ax.set_xlim(0, lvl.ci_high.max() * 1.48)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of core postings stating this level (Wilson 95 % CI)")
    for i, row in enumerate(lvl.itertuples()):
        ax.text(row.ci_high + lvl.ci_high.max() * 0.03, i,
                f"{row.share:.1%}  ({int(row.count)} ads)", va="center", fontsize=9)
    c1 = lvl[lvl.german_level_bucket == "C1/fluent"].iloc[0]
    b2 = float(lvl[lvl.german_level_bucket == "B2/good"].share.iloc[0])
    reachable = int(lvl[lvl.german_level_bucket.isin(my_level)]["count"].sum())
    silent = req[req.german_requirement == "not_mentioned"]
    silent_share = float(silent.share.iloc[0]) if not silent.empty else float("nan")
    finalise(
        fig,
        title=f"When a level is named it is C1-equivalent in {c1.share:.0%} of all ads - B1 or below is stated as "
              f"sufficient in {reachable} advertisements in the entire corpus",
        source=DEMAND_SOURCE,
        units="share of core postings with a description",
        n=f"n = {int(c1.n)} core postings; {silent_share:.0%} state no German requirement at all",
        note="'C1-equivalent' bundles explicit C1 with 'verhandlungssicher/fliessend' and 'sehr gut'; the last is an "
             "Austrian HR convention, not a certified level, so read the bucket as 'a high level is demanded'.",
    )
    return Spec(
        chart_id="BQ34_german_level_demanded",
        question="When an advertisement names a German level, which level is it - and is my A2-B1 ever stated as enough?",
        answer=f"Essentially never: C1-equivalent wording appears in {c1.share:.0%} of core ads "
               f"({int(c1['count'])} postings) and B2/good in {b2:.0%}, while B1 or below is named as sufficient in "
               f"{reachable} advertisements in the whole corpus - so the realistic route is the {silent_share:.0%} of "
               "ads that state no level at all, not the ones that state a low one.",
        relationship="ranking",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["T07a_german_level_overall.csv", "T07_german_requirement_by_overall.csv"],
        units="share of postings",
        caveat="Wording-derived buckets: mapping 'sehr gut' to C1 is an assumption, and silence in a German-written "
               "ad usually still implies German (T07d). Whether a stated level is negotiable is not measured.",
        anchors=[
            ("docs/market-guide.md", "after_match", "* **Levels.**"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHICH GAPS ARE STRUCTURAL?"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ35 - tools and languages, or libraries?
# --------------------------------------------------------------------------------------------
def bq35():
    groups = [
        ("Programming languages", "T05_skills_programming_languages.csv", BASE),
        ("Python libraries", "T05_skills_python_ecosystem.csv", HILITE),
        ("BI / visualisation tools", "T05_skills_bi_tools.csv", THIRD),
        ("Cloud platforms", "T05_skills_cloud_platforms.csv", FOURTH),
    ]
    rows = []
    for label, filename, color in groups:
        d = table(filename).sort_values("share", ascending=False).head(5)
        for row in d.itertuples():
            rows.append({"group": label, "skill": row.skill, "share": row.share,
                         "count": row.count, "n": row.n, "color": color})
    frame = pd.DataFrame(rows).sort_values(["group", "share"]).reset_index(drop=True)
    y = np.arange(len(frame))

    fig, ax = new_figure(height=0.34 * len(frame) + 3.4, width=10.4)
    ax.barh(y, frame.share, color=list(frame.color))
    ax.set_yticks(y)
    ax.set_yticklabels(frame.skill)
    ax.set_xlim(0, frame.share.max() * 1.42)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of core postings naming the item")
    for i, row in enumerate(frame.itertuples()):
        ax.text(row.share + frame.share.max() * 0.012, i, f"{row.share:.1%}", va="center", fontsize=8.5)
    for label, _, color in groups:
        idx = frame.index[frame.group == label]
        ax.annotate(label, (frame.share.max() * 1.20, float(np.mean(idx))), color=color,
                    fontsize=9.5, va="center", ha="left", fontweight="bold")
    py = frame[frame.skill == "Python"].iloc[0]
    libs = frame[frame.group == "Python libraries"].sort_values("share", ascending=False)
    top_lib = libs.iloc[0]
    pandas_row = libs[libs.skill == "pandas"]
    if top_lib.skill == "pandas" or pandas_row.empty:
        lib_clause = f"the most-mentioned Python library ({top_lib.skill}) reaches {top_lib.share:.1%}"
    else:
        lib_clause = (f"the most-mentioned Python library ({top_lib.skill}) reaches {top_lib.share:.1%} and pandas "
                      f"{float(pandas_row.share.iloc[0]):.1%}")
    finalise(
        fig,
        title=f"Austrian ads name languages and tools, not libraries: Python appears in {py.share:.0%} of postings "
              f"and the most-named Python library ({top_lib.skill}) in {top_lib.share:.1%}",
        source=DEMAND_SOURCE,
        units="share of core postings with a description",
        n=f"n = {int(py.n)} core postings; top five items per vocabulary",
        note="The first brief asked for technologies, frameworks and libraries as separate dimensions. They are "
             "separate vocabularies in config/skills_taxonomy.json - and the library layer barely appears in ads.",
    )
    return Spec(
        chart_id="BQ35_tools_vs_libraries",
        question="Do employers ask for frameworks and libraries, or only for languages and tools?",
        answer=f"Only for languages and tools: Python is named in {py.share:.0%} of ads while {lib_clause} "
               "- a CV built on library lists speaks a vocabulary employers do not use, while "
               "the language, the BI tool and the cloud platform are the words they do use.",
        relationship="ranking",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["T05_skills_programming_languages.csv", "T05_skills_python_ecosystem.csv",
                "T05_skills_bi_tools.csv", "T05_skills_cloud_platforms.csv"],
        units="share of postings",
        caveat="Absence of a library in an advertisement is not absence in the job: ads compress a stack to its "
               "headline names. This measures advertising vocabulary, not the work.",
        anchors=[
            ("docs/market-guide.md", "after_match", "Interpretation. The Austrian data stack is **Microsoft-centred**"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHAT SHOULD I PUT ON MY CV?"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ36 - are certifications worth anything, on either side
# --------------------------------------------------------------------------------------------
def bq36():
    dem = table("T11d_certifications.csv")
    sup = table("C09_certifications.csv")
    sup = sup[sup.population == "P_data"]
    pairs = [
        ("Any certification wording", "Certification (any mention)", "Certification (any mention)"),
        ("Requirements / BA (IREB, IIBA)", "Requirements/BA cert (IREB/IIBA/CBAP)", None),
        ("Scrum / project management", "Scrum/PM cert", None),
        ("Azure", "Azure cert", "Microsoft/Azure (any)"),
        ("Google / GCP", "Google cert", "Google/GCP (any)"),
        ("AWS", None, "AWS (any)"),
        ("MOOC certificate (Coursera/edX/Udemy)", None, "Coursera/edX/Udemy (any)"),
    ]
    rows = []
    for label, demand_key, supply_key in pairs:
        d = dem[dem.certification == demand_key]
        s = sup[sup.certification == supply_key]
        rows.append({
            "label": label,
            "demand": float(d.share.iloc[0]) if len(d) else 0.0,
            "demand_known": bool(len(d)),
            "supply": float(s.share.iloc[0]) if len(s) else 0.0,
            "supply_known": bool(len(s)),
        })
    frame = pd.DataFrame(rows).sort_values("demand")
    y = np.arange(len(frame))

    fig, ax = new_figure(height=0.52 * len(frame) + 3.2, width=10.2)
    for i, row in enumerate(frame.itertuples()):
        ax.plot([row.demand, row.supply], [i, i], color=MUTED, linewidth=1.4, zorder=1)
    ax.scatter(frame.demand, y, color=BASE, s=85, zorder=3)
    ax.scatter(frame.supply, y, color=HILITE, s=85, marker="D", zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(frame.label)
    ax.set_xlim(0, max(frame.demand.max(), frame.supply.max()) * 1.45)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of the side's population mentioning the certification")
    top = len(frame) - 1
    ax.annotate("share of ads", (frame.demand.iloc[top], top), textcoords="offset points",
                xytext=(0, 15), ha="center", fontsize=9, color=BASE)
    ax.annotate("share of candidates", (frame.supply.iloc[top], top), textcoords="offset points",
                xytext=(0, -20), ha="center", fontsize=9, color=HILITE)
    any_dem = frame[frame.label == "Any certification wording"].iloc[0]
    finalise(
        fig,
        title=f"Certifications are rare on both sides: {any_dem.demand:.0%} of ads mention any certification and "
              f"{any_dem.supply:.1%} of observed candidates hold one - vendor data certificates are a rounding error",
        source=JOINT_SOURCE,
        units="share of the side's population",
        n=f"{n_desc()} / {int(sup.n.max()):,} data-signal candidates",
        note=JOINT_NOTE + " A missing marker means the vocabulary has no matching entry on that side, not a zero.",
    )
    return Spec(
        chart_id="BQ36_certifications_both_sides",
        question="Is a certification worth the money and the weeks - does either side of this market care?",
        answer=f"No evidence that it is: {any_dem.demand:.0%} of ads mention any certification at all and each "
               f"specific one stays at or under 3 %, while {any_dem.supply:.1%} of observed candidates show one and "
               "MOOC certificates outnumber vendor ones - certifications differentiate in neither direction here, "
               "which makes them the cheapest item to drop from a learning plan.",
        relationship="deviation from target",
        mark="dumbbell",
        data_signature="categorical-multi",
        tables=["T11d_certifications.csv", "C09_certifications.csv"],
        units="share of population",
        caveat="Both sides are wording-derived: an employer may still value a certificate it does not advertise, and "
               "a candidate may hold one they never mention in a bio or README.",
        anchors=[
            ("docs/market-guide.md", "after_match", "**Certifications are almost never requested.**"),
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_heading", "## 13. How common are certifications? (DS08, C09)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ37 - is supply distributed like demand across Austria
# --------------------------------------------------------------------------------------------
def bq37():
    geo = table("DS05_demand_supply_geography.csv")
    geo = geo[geo.dimension == "state"].copy()
    geo = geo[geo.demand_count >= 20].sort_values("demand_count")
    y = np.arange(len(geo))
    complete = geo.supply_frame.str.contains("complete", case=False, na=False)

    fig, ax = new_figure(height=0.56 * len(geo) + 3.4, width=10.4)
    width = 0.38
    ax.barh(y + width / 2, geo.demand_count, width, color=BASE, label="open core postings (demand)")
    ax.barh(y - width / 2, geo.supply_T1, width,
            color=[HILITE if c else MUTED for c in complete],
            label="bio-declared candidates observed (supply)")
    ax.set_yticks(y)
    ax.set_yticklabels(geo.category)
    ax.set_xlim(0, max(geo.demand_count.max(), geo.supply_T1.max()) * 1.30)
    ax.set_xlabel("Count")
    for i, row in enumerate(geo.itertuples()):
        frame_note = "complete frame" if "complete" in str(row.supply_frame).lower() else "lower bound"
        ax.text(max(row.demand_count, row.supply_T1) * 1.02, i,
                f"{int(row.demand_count)} ads · {int(row.supply_T1)} candidates ({frame_note})",
                va="center", fontsize=8.5)
    ax.legend(fontsize=8.5, loc="lower right")
    sty = geo[geo.category == "Steiermark"].iloc[0]
    vie = geo[geo.category == "Wien"].iloc[0]
    counts = market_counts()
    n_t1 = int(table("DS01_demand_supply_role_families.csv").supply_n.max())
    finalise(
        fig,
        title=f"Both sides concentrate on Vienna ({int(vie.demand_count)} ads against at least "
              f"{int(vie.supply_T1)} declared candidates); Styria is the only region where both sides are counted "
              "the same way",
        source=JOINT_SOURCE,
        units="postings and bio-declared candidate accounts",
        n=f"n = {int(geo.demand_n.max())} postings ({PRIMARY_BASIS}) / {n_t1} bio-declared accounts "
          "(location-resolved)",
        note=JOINT_NOTE + " Only the Styrian supply frame is complete; every other region's candidate count is a "
                          "lower bound from a keyword and base-rate sample, so regions are NOT comparable to each other. "
                          f"Demand {PRIMARY_BASIS}: {styria_basis_note(counts)}.",
    )
    return Spec(
        chart_id="BQ37_geography_demand_supply",
        question="Is the candidate pool distributed across Austria the way the jobs are?",
        answer=f"Roughly, and both sides pile into Vienna: {int(vie.demand_count)} Viennese ads ({PRIMARY_BASIS}) "
               f"against at least {int(vie.supply_T1)} declared candidates, and in Styria - the only region where the "
               f"candidate frame is complete - {int(sty.demand_count)} ads {PRIMARY_BASIS} against "
               f"{int(sty.supply_T1)} declared candidates (location-resolved). The "
               "structural shape is the same everywhere; Styria differs by being smaller and more industrial on both "
               "sides.",
        relationship="comparison across categories",
        mark="grouped_bar",
        data_signature="bivariate-dual",
        tables=["DS05_demand_supply_geography.csv"],
        units="counts",
        caveat="Supply frames differ by region by construction: Styria is a complete GitHub frame, every other state "
               "is a keyword plus base-rate sample and therefore a lower bound. Cross-region supply comparison is "
               f"not valid. Demand is {PRIMARY_BASIS} (T03a); counting every ad that lists a Styrian site gives "
               f"{counts['styria_any_site']}.",
        anchors=[
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_heading",
             "## 10. Where does geography materially change the market? (DS05, DS05b, DS13)"),
            ("docs/supply-findings.md", "after_heading", "## 3. Geography (C05, C05a–c, DS05, DS05b, DS13)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ38 - education on both sides
# --------------------------------------------------------------------------------------------
def bq38():
    edu = table("DS08_demand_supply_education.csv").copy()
    edu = edu[edu.dimension.isin(["education_level", "education_field"])]
    edu = edu[(edu.demand_share >= 0.02) | (edu.supply_share >= 0.02)]
    edu = edu.reindex(edu.difference_pp.abs().sort_values(ascending=False).index).head(14)
    edu = edu.sort_values("difference_pp")
    colors = [BASE if v < 0 else HILITE for v in edu.difference_pp]

    fig, ax = new_figure(height=0.44 * len(edu) + 3.2, width=10.4)
    ax.barh(edu.category, edu.difference_pp, color=colors)
    ax.axvline(0, color="#222222", linewidth=0.9)
    span = edu.difference_pp.abs().max()
    ax.set_xlim(-span * 1.75, span * 1.75)
    ax.set_xlabel("Percentage points: share of candidates naming it minus share of ads naming it")
    for i, row in enumerate(edu.itertuples()):
        ax.text(row.difference_pp + (0.6 if row.difference_pp >= 0 else -0.6), i,
                f"ads {row.demand_share:.0%} · candidates {row.supply_share:.0%}",
                va="center", ha="left" if row.difference_pp >= 0 else "right", fontsize=8)
    ax.text(0.99, 0.03, "→ more common in the candidate pool", transform=ax.transAxes,
            ha="right", fontsize=9, color=HILITE)
    ax.text(0.01, 0.03, "← more common in advertisements", transform=ax.transAxes,
            ha="left", fontsize=9, color=BASE)
    ds = edu[edu.category.str.contains("data science", case=False, na=False)]
    finalise(
        fig,
        title="The observable pool is credentialled in data science while the ads name informatics and engineering - "
              "the credential mismatch runs in both directions",
        source=JOINT_SOURCE,
        units="percentage points",
        n=f"n = {int(edu.demand_n.max())} core postings with a description / {int(edu.supply_n.max()):,} data-signal "
          "candidates",
        note=JOINT_NOTE + " Silence dominates both sides: 35 % of ads carry no education wording and 69 % of "
                          "candidates show none, so this compares wording, not qualifications.",
    )
    return Spec(
        chart_id="BQ38_education_both_sides",
        question="Is the pool I am competing with more credentialled than employers actually ask for?",
        answer="In its own direction, yes: candidates over-represent data-science degrees and Master's/PhD wording "
               "relative to the ads, while the ads name informatics, engineering and business fields more often than "
               "candidates do"
               + (f" (data-science wording: ads {float(ds.demand_share.iloc[0]):.0%} vs candidates "
                  f"{float(ds.supply_share.iloc[0]):.0%})" if len(ds) else "")
               + " - the credential gap is a mismatch of field, not a simple deficit of level.",
        relationship="deviation from target",
        mark="diverging_bar",
        data_signature="categorical-value",
        tables=["DS08_demand_supply_education.csv"],
        units="percentage points",
        caveat="Absence of education wording is not absence of a degree on either side; 69 % of candidates write "
               "nothing about education at all, so these shares are lower bounds of very different kinds.",
        anchors=[
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_heading", "## 12. How does education alter the picture? (DS08, O01)"),
            ("docs/supply-findings.md", "after_heading", "## 8. Education and certifications (C08, C08b–e, C09, C09b–d, DS08)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ39 - how fragmented is the candidate title market
# --------------------------------------------------------------------------------------------
def bq39():
    conc = table("C04b_title_concentration.csv").set_index("measure")
    titles = table("C03_normalized_title_distribution.csv")
    titles = titles.sort_values("count", ascending=False).head(12).sort_values("count")

    fig, ax = new_figure(height=0.42 * len(titles) + 3.6, width=10.2)
    total = float(titles["count"].sum())
    top_share = titles["count"].max() / float(conc.loc["total", "normalized_titles"])
    colors = [HILITE if i == len(titles) - 1 else BASE for i in range(len(titles))]
    ax.barh(titles.normalized_title, titles["count"], color=colors)
    ax.set_xlim(0, titles["count"].max() * 1.36)
    ax.set_xlabel("Bio-declared candidates using the normalised title")
    label_bars(ax, list(titles["count"]), [f"{int(v)}" for v in titles["count"]])
    distinct_raw = int(conc.loc["distinct", "raw_bio_titles"])
    distinct_norm = int(conc.loc["distinct", "normalized_titles"])
    ax.annotate(f"{distinct_raw} distinct raw bio titles collapse into {distinct_norm} normalised ones",
                xy=(0.99, 0.04), xycoords="axes fraction", ha="right", fontsize=9, color=MUTED)
    finalise(
        fig,
        title=f"The candidate pool writes {distinct_raw} different self-descriptions but stands in "
              f"{distinct_norm} queues - and {top_share:.0%} of it stands in the 'Data Scientist' one",
        source=SUPPLY_SOURCE,
        units="candidates per normalised title",
        n=f"n = {int(conc.loc['total', 'normalized_titles'])} bio-declared accounts",
        note="Normalisation uses the same taxonomy as the demand side, so titles are comparable across layers; the "
             "raw-title count measures self-description, not distinct roles.",
    )
    return Spec(
        chart_id="BQ39_title_fragmentation",
        question="How fragmented is the candidate market - does a title even mean anything here?",
        answer=f"Self-description is fragmented ({distinct_raw} distinct raw bio titles) but the underlying "
               f"positioning is not: it collapses into {distinct_norm} normalised titles, and 'Data Scientist' alone "
               f"holds {top_share:.0%} of bio-declared accounts - so a differentiated title is cheap to claim and "
               "crowded to hold, which is why the evidence behind it matters more than the label.",
        relationship="ranking",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["C04b_title_concentration.csv", "C03_normalized_title_distribution.csv"],
        units="candidates",
        caveat="Titles come from GitHub bios, which are written for a developer audience rather than a recruiter; "
               "this is self-presentation, not employment.",
        anchors=[
            ("docs/supply-findings.md", "after_heading", "## 2. Titles and families (C02, C03, C04, C04b, DS01, DS02)"),
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_heading",
             "## 1. Where is observable candidate supply concentrated? (C04, C05, C10, C23)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ40 - how many projects does a candidate show
# --------------------------------------------------------------------------------------------
def bq40():
    c16 = table("C16_project_count_distribution.csv")
    sub = c16[(c16.population == "P_data") & (c16.variable == "n_projects")].sort_values("bucket_order")
    doc = c16[(c16.population == "P_data") & (c16.variable == "n_documented_projects")].sort_values("bucket_order")
    x = np.arange(len(sub))
    width = 0.40

    fig, ax = new_figure(height=5.4, width=10.2)
    ax.bar(x - width / 2, sub.share, width, color=BASE, label="projects")
    ax.bar(x + width / 2, doc.share.values[:len(x)], width, color=HILITE, label="documented projects")
    ax.set_xticks(x)
    ax.set_xticklabels(sub.bucket)
    ax.set_ylim(0, max(sub.share.max(), doc.share.max()) * 1.25)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_ylabel("Share of observed candidates")
    ax.set_xlabel("Number of projects held by the candidate")
    for xi, (s, c) in zip(x - width / 2, zip(sub.share, sub["count"])):
        ax.text(xi, s + 0.006, f"{int(c)}", ha="center", fontsize=8)
    ax.legend(fontsize=8.5)
    cumulative = sub.set_index("bucket").share.cumsum()
    none_share = float(sub[sub.bucket == "0"].share.iloc[0])
    finalise(
        fig,
        title=f"{none_share:.0%} of observed candidates show no project at all and the median holds two - "
              "three documented projects already places an account in the upper part of the pool",
        source=SUPPLY_SOURCE,
        units="share of data-signal candidates",
        n=f"n = {int(sub.n.iloc[0]):,} data-signal candidates",
        note="A project is an owned, non-fork data repository with a README of at least 300 characters, a star or a "
             "description - repositories are not projects.",
    )
    return Spec(
        chart_id="BQ40_project_counts",
        question="How many projects does a candidate actually show - what would put me above the pool?",
        answer=f"Not many: {none_share:.0%} of observed candidates show no project at all, "
               f"{float(cumulative.get('2–3', float('nan'))):.0%} hold three or fewer, and the median is two - so "
               "two or three finished, documented projects is not a modest portfolio in this pool, it is an "
               "above-median one, and the differentiator is documentation rather than count.",
        relationship="comparison across categories",
        mark="grouped_bar",
        data_signature="bivariate-dual",
        tables=["C16_project_count_distribution.csv"],
        units="share of candidates",
        caveat="Counts only public, non-fork repositories: private, client and employer work is invisible, so this is "
               "a floor on what candidates have built, not a measure of their experience.",
        anchors=[
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_heading", "## 14. How common are public portfolios? (C14, C16, C15)"),
            ("docs/supply-findings.md", "after_heading", "## 9. Projects: counts, activity, archetypes (C14, C14b–e, C16)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ41 - what candidates actually build
# --------------------------------------------------------------------------------------------
def bq41():
    top = table("C18_project_topics.csv")
    top = top[top.population == "projects"].sort_values("share", ascending=False).head(18).sort_values("share")
    group_color = {"ds_method": BASE, "ai": FOURTH, "engineering": THIRD, "analytics_domain": HILITE}
    group_label = {"ds_method": "data-science method", "ai": "AI / LLM",
                   "engineering": "engineering", "analytics_domain": "business domain"}
    colors = [group_color.get(g, MUTED) for g in top.group]

    fig, ax = new_figure(height=0.36 * len(top) + 3.4, width=10.4)
    ax.barh(top.theme.str.replace("_", " "), top.share, color=colors)
    ax.set_xlim(0, top.share.max() * 1.34)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of public Austrian data projects on the theme")
    label_bars(ax, list(top.share), [f"{s:.1%} ({int(c):,})" for s, c in zip(top.share, top["count"])])
    handles = [ax.barh(0, 0, color=color, label=group_label[key]) for key, color in group_color.items()]
    ax.legend(fontsize=8.5, loc="lower right")
    method_share = top[top.group.isin(["ds_method", "ai"])].share.sum()
    domain_share = top[top.group == "analytics_domain"].share.sum()
    finalise(
        fig,
        title=f"Candidates build methods, not businesses: the method and AI themes in this list cover "
              f"{method_share:.0%} of projects against {domain_share:.0%} for business domains",
        source=SUPPLY_SOURCE,
        units="share of projects (themes overlap; a project can carry several)",
        n=f"n = {int(top.n.iloc[0]):,} public projects by data-signal accounts",
        note="Themes are not mutually exclusive, so shares do not sum to 100 %. Experimentation, causal inference and "
             "product analytics each stay under 1 % and do not appear in this top list at all.",
    )
    return Spec(
        chart_id="BQ41_project_topics",
        question="What is the pool actually building - and is it what Austrian employers pay for?",
        answer=f"Methods rather than businesses: NLP, classification, LLM apps and computer vision lead, with the "
               f"listed method and AI themes covering {method_share:.0%} of projects against {domain_share:.0%} for "
               "business domains - while the ads are dominated by finance/controlling, operations and marketing "
               "context, so a domain-framed project is scarce exactly where demand is thick.",
        relationship="ranking",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["C18_project_topics.csv", "C18c_project_theme_coverage.csv"],
        units="share of projects",
        caveat="Themes are rule-based over repository names, descriptions, topics and READMEs and can overlap; a "
               "project with no README text is under-classified rather than absent.",
        anchors=[
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_heading", "## 15. What do candidate projects look like? (C14c, C18, C18c, C19d)"),
            ("docs/supply-findings.md", "after_heading", "## 10. Project topics (C18, C18b, C18c, C24)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ42 - what kind of repositories are these
# --------------------------------------------------------------------------------------------
def bq42():
    arch = table("C14c_repository_archetypes.csv").sort_values("share_of_data_repos")
    demand_shaped = {"analytics_project", "data_engineering_project", "dashboard_project", "production_app"}
    colors = [HILITE if a in demand_shaped else BASE for a in arch.archetype]

    fig, ax = new_figure(height=0.44 * len(arch) + 3.2, width=10.2)
    ax.barh(arch.archetype.str.replace("_", " "), arch.share_of_data_repos, color=colors)
    ax.set_xlim(0, arch.share_of_data_repos.max() * 1.42)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of public Austrian data repositories")
    label_bars(ax, list(arch.share_of_data_repos),
               [f"{s:.1%} ({int(p):,} repos)" for s, p in zip(arch.share_of_data_repos, arch.projects)])
    inactive = arch[arch.archetype == "inactive_archive"]
    edu = arch[arch.archetype == "educational_tutorial"]
    analytics = arch[arch.archetype == "analytics_project"]
    finalise(
        fig,
        title=f"{float(inactive.share_of_data_repos.iloc[0]):.0%} of public Austrian data repositories are inactive "
              f"archives and {float(edu.share_of_data_repos.iloc[0]):.0%} are course work - analytics projects are "
              f"{float(analytics.share_of_data_repos.iloc[0]):.1%}",
        source=SUPPLY_SOURCE,
        units="share of data repositories",
        n=f"n = {int(arch.projects.sum()):,} classified data repositories",
        note="One archetype per repository, assigned in the priority order of config/supply_taxonomy.json; "
             "highlighted archetypes are the ones that map onto advertised work.",
    )
    return Spec(
        chart_id="BQ42_repository_archetypes",
        question="When I look at a competitor's GitHub, what am I usually looking at?",
        answer=f"Mostly abandoned or educational material: {float(inactive.share_of_data_repos.iloc[0]):.0%} of "
               f"public Austrian data repositories are inactive archives and "
               f"{float(edu.share_of_data_repos.iloc[0]):.0%} are course or tutorial work, while analytics projects "
               f"are {float(analytics.share_of_data_repos.iloc[0]):.1%} and data-engineering projects under 2 % - the "
               "bar for a maintained, business-shaped repository is far lower than the raw repository counts suggest.",
        relationship="ranking",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["C14c_repository_archetypes.csv", "C14d_data_repo_activity.csv"],
        units="share of repositories",
        caveat="Archetypes are rule-based and mutually exclusive by priority order; 'inactive' measures the last "
               "push date, which says nothing about whether the work was good when it was made.",
        anchors=[
            ("docs/supply-findings.md", "after_heading", "## 9. Projects: counts, activity, archetypes (C14, C14b–e, C16)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ43 - positioning clusters and their crowding
# --------------------------------------------------------------------------------------------
def bq43():
    cl = table("C23_positioning_clusters.csv").copy()

    def short(features: str, limit: int = 3) -> str:
        parts = [p.split(" (")[0] for p in str(features).split("; ") if p]
        return ", ".join(parts[:limit]) if parts else "no defining feature"

    cl["label"] = [f"C{int(row.cluster)}: {short(row.defining_features)}" for row in cl.itertuples()]
    cl = cl.sort_values("size")
    y = np.arange(len(cl))

    fig, ax = new_figure(height=0.54 * len(cl) + 3.4, width=10.6)
    ax.barh(y, cl["size"], color=BASE)
    ax.barh(y, cl.styria, color=HILITE)
    ax.set_yticks(y)
    ax.set_yticklabels(cl.label, fontsize=8.5)
    ax.set_xlim(0, cl["size"].max() * 1.82)
    ax.set_xlabel("Observed candidates in the cluster (Styrian candidates highlighted)")
    for i, row in enumerate(cl.itertuples()):
        ax.text(row.size + cl["size"].max() * 0.012, i,
                f"{int(row.size)} in total · {int(row.styria)} Styrian · "
                f"median {int(row.median_projects)} projects",
                va="center", fontsize=8.5)
    biggest = cl.iloc[-1]
    finalise(
        fig,
        title=f"The largest positioning cluster holds {int(biggest['size'])} of "
              f"{int(cl['size'].sum()):,} observed candidates and shows a median of "
              f"{int(biggest.median_projects)} projects - crowding and evidence are not the same axis",
        source=SUPPLY_SOURCE,
        units="candidates per cluster",
        n=f"n = {int(cl['size'].sum()):,} data-signal candidates in 8 k-means clusters",
        note="Descriptive archetypes from k-means over binary skill/theme/format indicators - not a classification of "
             "people and not a ranking. Cluster labels name the features that define them, not job titles.",
    )
    return Spec(
        chart_id="BQ43_positioning_clusters",
        question="Which positioning spaces actually exist in the pool, and which of them is least crowded?",
        answer=f"Eight descriptive clusters, of which the largest holds {int(biggest['size'])} of "
               f"{int(cl['size'].sum()):,} candidates with a median of {int(biggest.median_projects)} projects; the "
               "notebook-ML and deep-learning clusters are the dense ones, while clusters defined by pipelines, "
               "dashboards or business domains are both smaller and better evidenced - the space is chosen by what "
               "the projects show, not by the title claimed.",
        relationship="ranking",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["C23_positioning_clusters.csv", "DS11_demand_supply_positioning_clusters.csv"],
        units="candidates",
        caveat="k-means on binary indicators with weak separation: these are readable groupings, not natural kinds, "
               "and a candidate near a boundary could sit in either cluster.",
        anchors=[
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_match", "## 20. What does this imply for future career decisions?"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ44 - transitions into data
# --------------------------------------------------------------------------------------------
def bq44():
    dom = table("C22b_prior_domains.csv").sort_values("share")
    colors = [HILITE if d.lower().startswith("marketing") else BASE for d in dom.prior_domain]

    fig, ax = new_figure(height=0.40 * len(dom) + 3.4, width=10.2)
    ax.barh(dom.prior_domain.str.replace("_", " "), dom.share, color=colors)
    ax.errorbar(dom.share, np.arange(len(dom)),
                xerr=[dom.share - dom.ci_low, dom.ci_high - dom.share],
                fmt="none", ecolor="#444444", capsize=2, linewidth=0.9)
    ax.set_xlim(0, dom.ci_high.max() * 1.36)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of bio-declared accounts naming the prior domain (Wilson 95 % CI)")
    for i, row in enumerate(dom.itertuples()):
        ax.text(row.ci_high + dom.ci_high.max() * 0.025, i,
                f"{row.share:.1%} ({int(row.count)})", va="center", fontsize=8.5)
    marketing = dom[dom.prior_domain.str.lower().str.startswith("marketing")]
    marketing_count = int(marketing["count"].iloc[0]) if len(marketing) else 0
    business = dom[dom.prior_domain == "business"]
    finalise(
        fig,
        title=f"Prior domains are named by a minority of profiles, and marketing by "
              f"{marketing_count} of {int(dom.n.iloc[0])} - the transition I am making is almost unrepresented in "
              "public evidence",
        source=SUPPLY_SOURCE,
        units="share of bio-declared accounts",
        n=f"n = {int(dom.n.iloc[0])} bio-declared accounts",
        note="GitHub bios rarely narrate a career change (3.4 % state one explicitly), so this measures what people "
             "write about their past, not how they actually arrived.",
    )
    return Spec(
        chart_id="BQ44_transition_domains",
        question="How common is a career transition into data - and does anyone arrive from marketing?",
        answer=f"Rare in public evidence and almost absent from marketing: "
               + (f"{float(business.share.iloc[0]):.1%} of bio-declared accounts name a business background, "
                  if len(business) else "")
               + f"while marketing is named by {marketing_count} of {int(dom.n.iloc[0])} - but GitHub does not "
               "narrate careers (3.4 % state a transition at all), so this is evidence of silence, not evidence of "
               "absence, and the transition story is one the CV and LinkedIn must carry because the code cannot.",
        relationship="ranking",
        mark="horizontal_bar",
        data_signature="bivariate-simple",
        tables=["C22b_prior_domains.csv", "C22_transition_signals.csv", "C22d_marketing_named_bios.csv"],
        units="share of accounts",
        caveat="Prior domain is detected from bio wording only. Transitioners who do not write about their past are "
               "invisible here, which is the most likely explanation for the low counts.",
        anchors=[
            ("CAREER_SUPPLY_DEMAND_MAP.md", "after_match", "* **Transition patterns.**"),
            ("docs/supply-findings.md", "after_heading", "## 2. Titles and families (C02, C03, C04, C04b, DS01, DS02)"),
        ],
    ), fig


# --------------------------------------------------------------------------------------------
# BQ45 - does the skill premium survive the controls?
# --------------------------------------------------------------------------------------------
def bq45():
    prem = table("D05_skill_salary_premium.csv").sort_values("adjusted_premium_pct")
    y = np.arange(len(prem))
    colors = [HILITE if c else MUTED for c in prem.clears_zero]

    fig, ax = new_figure(height=0.46 * len(prem) + 3.4, width=10.6)
    ax.scatter(prem.raw_difference_pct, y, color=BASE, s=55, marker="s", zorder=2, alpha=0.75)
    ax.errorbar(prem.adjusted_premium_pct, y,
                xerr=[prem.adjusted_premium_pct - prem.ci_low_pct,
                      prem.ci_high_pct - prem.adjusted_premium_pct],
                fmt="o", markersize=7, capsize=3, linewidth=1.3,
                ecolor="#444444", color="#444444", zorder=3)
    for i, row in enumerate(prem.itertuples()):
        ax.plot([row.raw_difference_pct, row.adjusted_premium_pct], [i, i],
                color=MUTED, linewidth=0.8, alpha=0.5, zorder=1)
        ax.scatter([row.adjusted_premium_pct], [i], color=colors[i], s=70, zorder=4)
    ax.axvline(0, color="#222222", linewidth=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(prem.skill)
    ax.set_xlabel("Difference in the advertised annual minimum (%)")
    span = max(abs(prem.ci_low_pct.min()), prem.ci_high_pct.max())
    ax.set_xlim(-span * 1.55, span * 1.55)
    # One label column at the right edge: anchoring to ci_high would collide with the
    # raw-difference marker whenever the raw effect is the larger of the two.
    label_x = span * 1.30
    for i, row in enumerate(prem.itertuples()):
        ax.text(label_x, i, f"n = {int(row.ads_mentioning)}", va="center", fontsize=8)
    top = len(prem) - 1
    ax.annotate("raw difference", (prem.raw_difference_pct.iloc[top], top), textcoords="offset points",
                xytext=(0, 16), ha="center", fontsize=8.5, color=BASE)
    ax.annotate("after controls, with 95 % CI", (prem.adjusted_premium_pct.iloc[top], top),
                textcoords="offset points", xytext=(10, -22), ha="center", fontsize=8.5, color=HILITE)
    survivors = prem[prem.clears_zero].copy()
    survivors["magnitude"] = survivors.adjusted_premium_pct.abs()
    survivors = survivors.sort_values("magnitude", ascending=False)
    names = " and ".join(
        f"{row.skill} ({row.adjusted_premium_pct:+.0f} %)" for row in survivors.itertuples())
    # L52: D05 carries Holm (FWER) and Benjamini-Hochberg (FDR) adjusted p-values over the skill family
    has_adj = {"survives_holm", "survives_bh"} <= set(prem.columns)
    if has_adj:
        holm_ok = survivors[survivors.survives_holm.astype(bool)]
        bh_ok = survivors[survivors.survives_bh.astype(bool)]
        lost = survivors[~survivors.survives_holm.astype(bool)]
        mult_clause = (f" After a Holm correction over all {len(prem)} skills "
                       + (f"{' and '.join(holm_ok.skill)} still clear{'s' if len(holm_ok) == 1 else ''} zero"
                          if len(holm_ok) else "none clears zero")
                       + (f" ({' and '.join(lost.skill)} do{'es' if len(lost) == 1 else ''} not)" if len(lost) else "")
                       + (f"; Benjamini-Hochberg keeps {len(bh_ok)} of {len(survivors)}." if len(survivors) else "."))
        mult_note = (f"{len(prem)} coefficients are estimated together; the 95 % intervals are per coefficient, and the "
                     "table adds Holm and Benjamini-Hochberg adjusted p-values (D05 p_holm, p_bh).")
    else:
        mult_clause = ""
        mult_note = (f"{len(prem)} coefficients are estimated together and the intervals are not corrected for "
                     "multiplicity, so about one crossing by chance is expected - read the table as a whole.")
    finalise(
        fig,
        title=f"Almost every skill premium is composition, not skill: after controlling for family, seniority and "
              f"state, only {names} still differ from zero",
        source=DEMAND_SOURCE + "; OLS with HC1 robust standard errors (src/analysis/salary_premium.py)",
        units="percentage difference in the advertised annual minimum",
        n=f"n = {int(prem.n_model.iloc[0])} core postings with a parsed figure; model R² = {float(prem.model_r2.iloc[0]):.2f}",
        note=mult_note + " Association in advertised floors, never a causal claim about pay.",
    )
    return Spec(
        chart_id="BQ45_skill_premium_controlled",
        question="Do the better-paying skills actually pay better, or am I just looking at which family names them?",
        answer=f"Mostly the latter: after controlling for role family, seniority and state, "
               f"{len(prem) - len(survivors)} of {len(prem)} skills have intervals straddling zero - Python's raw "
               f"{float(prem[prem.skill == 'Python'].raw_difference_pct.iloc[0]):+.0f} % becomes "
               f"{float(prem[prem.skill == 'Python'].adjusted_premium_pct.iloc[0]):+.0f} % - and only "
               f"{names} still separate from zero.{mult_clause} The floor is set by the family and the seniority label, "
               "not by the tool named in the advertisement.",
        relationship="uncertainty",
        mark="error_bars",
        data_signature="interval-range",
        tables=["D05_skill_salary_premium.csv"],
        units="percent",
        caveat="Advertised minimums, not pay. Employer size, industry and hours basis are not controlled, "
               + ("the intervals shown are uncorrected (the adjusted p-values are in D05), " if has_adj
                  else "multiplicity is not corrected, ")
               + "and R² is low - this bounds how much of the raw gap is composition, it does not price a skill.",
        anchors=[
            ("docs/market-guide.md", "after_match", "By skill mentioned: Databricks"),
            ("CAREER_DECISION_MAP.md", "after_heading", "## WHAT SHOULD I LEARN?"),
            ("docs/salary-context.md", "after_heading", "## How to read our posting-level figures against these"),
        ],
    ), fig


BUILDERS = [bq34, bq35, bq36, bq37, bq38, bq39, bq40, bq41, bq42, bq43, bq44, bq45]
