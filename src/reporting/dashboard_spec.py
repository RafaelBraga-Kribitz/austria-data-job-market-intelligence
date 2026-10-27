"""Dashboard specification: the page set shared by the Power BI project (dashboards/JobMarket.*) and its HTML twin.

This module is the single place that names the pages, their order, their English titles, their one-sentence German
subtitles, the tables each page reads and the epistemic tag it carries. Three consumers read it and nothing else:

    src/reporting/dashboard_html.py   writes the static HTML twin (dashboards/html/index.html)
    src/reporting/dashboard_pbip.py   writes the PBIR report pages of dashboards/JobMarket.Report
    tests/test_dashboards.py          checks that both artefacts still match this list (order, names, subtitles)

It holds no numbers. Every number on a page is read from outputs/ when a page is built (outputs/tables/*.csv and
outputs/market_summary.json), so the dashboards inherit the anti-drift rule of the visual layer (D-024): nothing on a
page is typed by hand. The one constant is the project's own small-sample rule (MIN_N, docs/limitations.md item 9 and
D-024: "families below 30 postings are drawn but labelled too small to rank").
"""
from __future__ import annotations

# The robustness threshold the repository already applies to cells (docs/limitations.md, docs/decision-framework.md).
MIN_N = 30
# Display cuts (how many rows a chart shows; the full table stays in the data table under each chart and in outputs/).
TOP_SKILLS = 15
TOP_REGIONAL_SKILLS = 12
TOP_STACKS = 10
TOP_CAPABILITIES = 14

DASHBOARD_NAME = "JobMarket"
REPORT_TITLE = "Austria Data-Job Market Intelligence"

# The page set. `name` is the PBIR page folder / page name (stable, never shown), `title` the page title on both
# surfaces, `subtitle_de` the one German sentence under it, `tables` the outputs the page reads (its provenance footer),
# `tag` the epistemic tag of the README tag table.
PAGES: list[dict] = [
    {
        "name": "p1-market-overview",
        "nav": "Market overview",
        "title": "Market overview: where the open data-role ads are",
        "subtitle_de": "Wo in Österreich offene Data-Stellen ausgeschrieben sind: Kerninserate nach Rollenfamilie und "
                       "Bundesland an einem einzigen Stichtag.",
        "tables": ["T02_role_family_counts", "T03a_state_counts", "market_summary.json"],
        "tag": "VERIFIED counts of a rule-based selection",
    },
    {
        "name": "p2-skills-stacks",
        "nav": "Skills & stacks",
        "title": "Skills & stacks: what the ads mention, and what they mention together",
        "subtitle_de": "Welche Skills die Inserate nennen, wie sich die Steiermark vom Rest Österreichs unterscheidet "
                       "und welche Dreier-Kombinationen gemeinsam vorkommen.",
        "tables": ["T05_skills_all_tech", "T05_skills_all_tech_by_styria", "T06b_top_stacks_size3"],
        "tag": "CALIBRATED (rule-based text matching)",
    },
    {
        "name": "p3-pay-floors",
        "nav": "Advertised pay floors",
        "title": "Advertised pay floors: the legal minimum an ad states, not what a job pays",
        "subtitle_de": "Beworbene Mindestgehälter nach Rollenfamilie, Seniorität und Bundesland: kollektivvertragliche "
                       "Untergrenzen in Inseraten, keine tatsächlich bezahlten Gehälter.",
        "tables": ["T09_salary_coverage", "T09b_salary_by_role_family", "T09b_salary_by_seniority", "T09b_salary_by_state"],
        "tag": "CALIBRATED (salary figures parsed from ad text)",
    },
    {
        "name": "p4-demand-supply",
        "nav": "Demand vs supply",
        "title": "Demand vs supply: what ads ask for, what public portfolios show, and how stable the family ranking is",
        "subtitle_de": "Was die Inserate verlangen, was öffentliche GitHub-Portfolios zeigen und wie stabil die Reihung "
                       "der Rollenfamilien unter vier Gewichtungen bleibt.",
        "tables": ["DS10_demand_supply_capability_evidence", "D01_decision_matrix", "D02_sensitivity"],
        "tag": "CALIBRATED (two universes joined on shared taxonomies)",
    },
    {
        "name": "p5-data-quality",
        "nav": "Data quality & coverage",
        "title": "Data quality & coverage: how the denominator is built and how far to trust the labels",
        "subtitle_de": "Wie aus Rohzeilen die Analysebasis entsteht, welche Quellen sie tragen und wie genau die "
                       "Titelklassifikation laut Handprüfung ist.",
        "tables": ["market_summary.json", "T01_source_coverage", "T13b_posting_age_by_source", "Q04_duplicates",
                   "Q03c_precision_summary"],
        "tag": "VERIFIED counts; precision measured on a hand-labelled sample",
    },
]


def page_names() -> list[str]:
    return [p["name"] for p in PAGES]
