"""Author the Power BI project (PBIP: TMDL semantic model + PBIR report) in dashboards/ from dashboard_spec.py.

    python src/reporting/dashboard_pbip.py            (re)write dashboards/JobMarket.pbip, .SemanticModel/, .Report/
    python src/reporting/dashboard_pbip.py --check    change nothing; exit 1 if a committed project file differs

Why a generator. A .pbix is a binary that only Power BI Desktop writes; the PBIP text format (TMDL for the model, PBIR
JSON for the report) can be authored, diffed, reviewed and tested like code (DECISION_LOG, dashboard entry). This script
is the authoring tool: it writes every file deterministically (stable key order, LF, no BOM, lineage tags derived from
names with uuid5), so a change to the spec or the model shows up as a readable diff. It holds NO data and NO numbers:
the model loads the repository's public outputs (outputs/tables/*.csv, outputs/market_summary.json,
outputs/supply_summary.json) at refresh time through one Power Query text parameter, ExportsPath.

After the project has been opened and edited in Power BI Desktop, Desktop owns the files: do not re-run this script over
Desktop edits without reviewing the diff (it would overwrite them). tests/test_dashboards.py checks the integrity of the
committed project (every field a visual uses exists in the TMDL, relationships, pages, alt text, German subtitles, theme).

Schema versions (validated offline with src/reporting/validate_pbip.py): report 3.1.0, page 2.0.0, visualContainer 2.5.0,
pagesMetadata 1.0.0, versionMetadata 1.0.0, report definitionProperties 2.0.0, semanticModel definitionProperties 1.0.0,
pbipProperties 1.0.0, platformProperties 2.0.0.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import dashboard_spec as spec  # noqa: E402

NAME = spec.DASHBOARD_NAME
DASH = Path("dashboards")
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/"
V_REPORT, V_PAGE, V_VISUAL, V_PAGES, V_VERSION = "3.1.0", "2.0.0", "2.5.0", "1.0.0", "1.0.0"
NS = uuid.UUID("6f1c2b1e-4a57-4c3a-9a51-6a6f62d6a001")   # fixed namespace: lineage tags are uuid5(name) -> deterministic
THEME_FILE = "BragaLight.json"
W, H = 1280, 720

# Braga design system v2.1, light (bk-viz bk_tokens.json): chrome roles and the categorical slots
C = {"surface": "#E4E6EA", "surface-2": "#DCDEE2", "ink": "#26282C", "ink-2": "#5A5C61", "mid": "#9EA0A5", "rule": "#C2C4CA",
     "hl": "#2F4BE0", "cat": ["#2F4BE0", "#966400", "#0A7399", "#C4278F", "#7A4A1E"], "cat-other": "#9EA0A5",
     "var-pos": "#007A66", "var-neg": "#CC3710", "seq-low": "#EAF0FF", "neutral": "#D4D6DA"}


def tag(*parts: str) -> str:
    return str(uuid.uuid5(NS, "/".join(parts)))


# ================================================================================================ semantic model
def q(name: str) -> str:
    """TMDL / DAX object name, quoted when needed."""
    return f"'{name}'" if any(not (ch.isalnum() or ch == "_") for ch in name) else name


def csv_source(file: str) -> str:
    return (f'Csv.Document(File.Contents(ExportsPath & "tables\\{file}.csv"), '
            f'[Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv])')


def m_csv(file: str, types: dict[str, str], renames: dict[str, str], extra: list[tuple[str, str]] | None = None,
          keep: list[str] | None = None) -> list[tuple[str, str]]:
    """Power Query steps: read one exported CSV, promote headers, type with en-US culture, rename, extra steps, select."""
    steps = [("Source", csv_source(file)),
             ("Promoted", "Table.PromoteHeaders(Source, [PromoteAllScalars = true])"),
             ("Typed", "Table.TransformColumnTypes(Promoted, {" + ", ".join(f'{{"{k}", {v}}}' for k, v in types.items()) + '}, "en-US")'),
             ("Renamed", "Table.RenameColumns(Typed, {" + ", ".join(f'{{"{k}", "{v}"}}' for k, v in renames.items()) + "})")]
    steps += extra or []
    if keep:
        steps.append(("Result", f"Table.SelectColumns({steps[-1][0]}, {{" + ", ".join(f'"{k}"' for k in keep) + "})"))
    return steps


def labels_join(step: str, key: str, label: str, fallback: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """Merge the display label of a role family from DS01 (category -> label), keeping the key when no label exists."""
    fb = " else ".join(f'if [{key}] = "{k}" then "{v}"' for k, v in (fallback or {}).items())
    fallback_expr = (fb + " else " if fb else "") + f"[{key}]"
    return [("Labels", f'Table.SelectColumns(Table.PromoteHeaders({csv_source("DS01_demand_supply_role_families")}, '
                       f'[PromoteAllScalars = true]), {{"category", "label"}})'),
            ("Joined", f'Table.NestedJoin({step}, {{"{key}"}}, Labels, {{"category"}}, "L", JoinKind.LeftOuter)'),
            ("Expanded", 'Table.ExpandTableColumn(Joined, "L", {"label"}, {"Label"})'),
            ("Labelled", f'Table.AddColumn(Expanded, "{label}", each if [Label] <> null and [Label] <> "" then [Label] else {fallback_expr}, type text)')]


def small_flag(step: str, col: str, out: str = "Sample Size") -> tuple[str, str]:
    return ("Flagged", f'Table.AddColumn({step}, "{out}", each if [{col}] < {spec.MIN_N} then "n < {spec.MIN_N}: indicative" '
                       f'else "n >= {spec.MIN_N}", type text)')


# A column: (name, dataType, props) ; props: hidden, summarize, sortBy, fmt, desc
def col(name, dtype, *, hidden=False, summarize="none", sort_by=None, fmt=None, desc=None):
    return {"name": name, "type": dtype, "hidden": hidden, "summarize": summarize, "sortBy": sort_by, "fmt": fmt, "desc": desc}


def measure(name, expr, fmt, folder, desc):
    return {"name": name, "expr": expr, "fmt": fmt, "folder": folder, "desc": desc}


INT, DBL, STR, BOOL, DATE = "int64", "double", "string", "boolean", "dateTime"
SEN_LABELS = {"intern_student": "Intern / student", "trainee_junior": "Junior / trainee", "senior": "Senior",
              "lead_head": "Lead / head", "unspecified": "No seniority word"}
SEN_ORDER = {k: i + 1 for i, k in enumerate(SEN_LABELS)}
SOURCE_LABELS = {"eures": "EURES / AMS", "jobsat": "jobs.at", "karriere": "karriere.at", "linkedin": "LinkedIn", "willhaben": "willhaben"}
WEIGHTINGS = [("default", "Default"), ("geography_first", "Geography first"), ("language_first", "Language first"), ("equal", "Equal weights")]
TECHNICAL_GROUPS = ["tool", "technical", "engineering", "analytical", "ai"]


def map_expr(field: str, mapping: dict, default: str = "null") -> str:
    return " else ".join(f'if [{field}] = "{k}" then {json.dumps(v)}' for k, v in mapping.items()) + f" else {default}"


def tables() -> list[dict]:
    T = []
    T.append({
        "name": "Role Family", "file": "T02_role_family_counts",
        "desc": "One row per core role family (outputs/tables/T02_role_family_counts.csv), labelled from DS01. Dimension for the family tables.",
        "steps": m_csv("T02_role_family_counts", {"role_family": "type text", "count": "Int64.Type", "n": "Int64.Type",
                                                   "styria_count": "Int64.Type", "graz_area_count": "Int64.Type", "vienna_count": "Int64.Type"},
                       {"count": "Ads", "n": "Ads Base", "styria_count": "Ads Styria Any Site", "graz_area_count": "Ads Graz Area Any Site",
                        "vienna_count": "Ads Vienna Any Site"},
                       labels_join("Renamed", "role_family", "Family")
                       + [("Sorted", 'Table.Sort(Labelled, {{"Ads", Order.Descending}, {"role_family", Order.Ascending}})'),
                          ("Indexed", 'Table.AddIndexColumn(Sorted, "Family Order", 1, 1, Int64.Type)'),
                          small_flag("Indexed", "Ads"),
                          ("Keyed", 'Table.RenameColumns(Flagged, {{"role_family", "Family Key"}})')],
                       ["Family Key", "Family", "Family Order", "Ads", "Ads Base", "Ads Styria Any Site", "Ads Graz Area Any Site",
                        "Ads Vienna Any Site", "Sample Size"]),
        "columns": [col("Family Key", STR, hidden=True, desc="Taxonomy key of the role family (config/role_taxonomy.json)."),
                    col("Family", STR, sort_by="Family Order", desc="Display name of the role family."),
                    col("Family Order", INT, hidden=True, desc="1 = family with the most core ads."),
                    col("Ads", INT, hidden=True, summarize="sum", desc="Core ads in the family (T02 count)."),
                    col("Ads Base", INT, hidden=True, desc="All core ads (T02 n), the denominator of the family share."),
                    col("Ads Styria Any Site", INT, hidden=True, summarize="sum", desc="Core ads listing at least one Styrian site (location flag; multi-site ads count in every state)."),
                    col("Ads Graz Area Any Site", INT, hidden=True, summarize="sum", desc="Core ads listing a site in the Graz commuting area (config/geo.json)."),
                    col("Ads Vienna Any Site", INT, hidden=True, summarize="sum", desc="Core ads listing at least one Vienna site."),
                    col("Sample Size", STR, desc=f"'n < {spec.MIN_N}: indicative' when the family has fewer than {spec.MIN_N} core ads (docs/limitations.md item 9).")],
    })
    T.append({
        "name": "State", "file": "T03a_state_counts",
        "desc": "Core ads by primary state, one state per ad (outputs/tables/T03a_state_counts.csv).",
        "steps": m_csv("T03a_state_counts", {"state": "type text", "count": "Int64.Type", "n": "Int64.Type"},
                       {"state": "State", "count": "Ads Primary State", "n": "Ads Base"},
                       [("Unspecified", 'Table.AddColumn(Renamed, "Is Unspecified", each if [State] = "unspecified" then 1 else 0, Int64.Type)'),
                        ("Sorted", 'Table.Sort(Unspecified, {{"Is Unspecified", Order.Ascending}, {"Ads Primary State", Order.Descending}, {"State", Order.Ascending}})'),
                        ("Indexed", 'Table.AddIndexColumn(Sorted, "State Order", 1, 1, Int64.Type)')],
                       ["State", "State Order", "Ads Primary State", "Ads Base"]),
        "columns": [col("State", STR, sort_by="State Order", desc="Bundesland (German name as in the tables); 'unspecified' = Austria-wide or unknown."),
                    col("State Order", INT, hidden=True, desc="Largest state first; 'unspecified' last."),
                    col("Ads Primary State", INT, hidden=True, summarize="sum", desc="Core ads whose primary state is this state (T03a count)."),
                    col("Ads Base", INT, hidden=True, desc="All core ads (T03a n).")],
    })
    T.append({
        "name": "Skill", "file": "T05_skills_all_tech",
        "desc": "Share of core ads mentioning each skill, with Wilson 95% interval (outputs/tables/T05_skills_all_tech.csv).",
        "steps": m_csv("T05_skills_all_tech", {"skill": "type text", "count": "Int64.Type", "n": "Int64.Type", "ci_low": "type number", "ci_high": "type number"},
                       {"skill": "Skill", "count": "Ads Mentioning", "n": "Ads Base", "ci_low": "CI Low", "ci_high": "CI High"},
                       [("Sorted", 'Table.Sort(Renamed, {{"Ads Mentioning", Order.Descending}, {"Skill", Order.Ascending}})'),
                        ("Indexed", 'Table.AddIndexColumn(Sorted, "Skill Rank", 1, 1, Int64.Type)')],
                       ["Skill", "Skill Rank", "Ads Mentioning", "Ads Base", "CI Low", "CI High"]),
        "columns": [col("Skill", STR, sort_by="Skill Rank", desc="Canonical skill name (config/skills_taxonomy.json)."),
                    col("Skill Rank", INT, desc="1 = most-mentioned skill nationally (ties by name)."),
                    col("Ads Mentioning", INT, hidden=True, summarize="sum", desc="Core ads whose text mentions the skill."),
                    col("Ads Base", INT, hidden=True, desc="Core ads with a description (the text-derived denominator)."),
                    col("CI Low", DBL, hidden=True, fmt="0 %", desc="Lower bound of the Wilson 95% interval of the share."),
                    col("CI High", DBL, hidden=True, fmt="0 %", desc="Upper bound of the Wilson 95% interval of the share.")],
    })
    T.append({
        "name": "Skill by Region", "file": "T05_skills_all_tech_by_styria",
        "desc": "Skill mentions split into Styria (any listed site) and the rest of Austria (outputs/tables/T05_skills_all_tech_by_styria.csv).",
        "steps": m_csv("T05_skills_all_tech_by_styria", {"styria_flag": "type text", "skill": "type text", "count": "Int64.Type", "n": "Int64.Type",
                                                         "ci_low": "type number", "ci_high": "type number"},
                       {"styria_flag": "Region", "skill": "Skill", "count": "Ads Mentioning", "n": "Ads Base", "ci_low": "CI Low", "ci_high": "CI High"},
                       None, ["Region", "Skill", "Ads Mentioning", "Ads Base", "CI Low", "CI High"]),
        "columns": [col("Region", STR, desc="'Styria' (ads listing a Styrian site) or 'Rest of Austria'."),
                    col("Skill", STR, hidden=True, desc="Skill name; relates to Skill[Skill]."),
                    col("Ads Mentioning", INT, hidden=True, summarize="sum", desc="Ads of the region mentioning the skill."),
                    col("Ads Base", INT, hidden=True, desc="All ads of the region (the denominator of its shares)."),
                    col("CI Low", DBL, hidden=True, fmt="0 %", desc="Wilson 95% lower bound."),
                    col("CI High", DBL, hidden=True, fmt="0 %", desc="Wilson 95% upper bound.")],
    })
    T.append({
        "name": "Skill Stack", "file": "T06b_top_stacks_size3",
        "desc": "Three-skill combinations named together in one ad (outputs/tables/T06b_top_stacks_size3.csv).",
        "steps": m_csv("T06b_top_stacks_size3", {"stack": "type text", "count": "Int64.Type", "n": "Int64.Type"},
                       {"stack": "Stack", "count": "Ads", "n": "Ads Base"},
                       [("Sorted", 'Table.Sort(Renamed, {{"Ads", Order.Descending}, {"Stack", Order.Ascending}})'),
                        ("Indexed", 'Table.AddIndexColumn(Sorted, "Stack Rank", 1, 1, Int64.Type)')],
                       ["Stack", "Stack Rank", "Ads", "Ads Base"]),
        "columns": [col("Stack", STR, sort_by="Stack Rank", desc="Three skills joined with ' + '."),
                    col("Stack Rank", INT, desc="1 = most frequent combination."),
                    col("Ads", INT, hidden=True, summarize="sum", desc="Ads naming all three skills."),
                    col("Ads Base", INT, hidden=True, desc="Core ads with a description.")],
    })
    floor_types = {"n": "type number", "min_p25": "type number", "min_median": "type number", "min_p75": "type number"}
    floor_names = {"n": "Ads With Figure", "min_p25": "Floor P25", "min_median": "Floor Median", "min_p75": "Floor P75"}
    floor_cols = [col("Ads With Figure", DBL, hidden=True, summarize="sum", fmt="#,0", desc="Ads in the cell that state a pay figure."),
                  col("Floor P25", DBL, hidden=True, fmt="€#,0", desc="25th percentile of the advertised annual minimum (monthly × 14), euro."),
                  col("Floor Median", DBL, hidden=True, fmt="€#,0", desc="Median advertised annual minimum (monthly × 14), euro."),
                  col("Floor P75", DBL, hidden=True, fmt="€#,0", desc="75th percentile of the advertised annual minimum, euro."),
                  col("Sample Size", STR, desc=f"'n < {spec.MIN_N}: indicative' when fewer than {spec.MIN_N} ads state a figure.")]
    T.append({
        "name": "Pay Floor by Family", "file": "T09b_salary_by_role_family",
        "desc": "Advertised annual minimum by role family (outputs/tables/T09b_salary_by_role_family.csv). A legal floor in the ad, not pay.",
        "steps": m_csv("T09b_salary_by_role_family", {"role_family": "type text", **floor_types}, {"role_family": "Family Key", **floor_names},
                       [small_flag("Renamed", "Ads With Figure")], ["Family Key", *floor_names.values(), "Sample Size"]),
        "columns": [col("Family Key", STR, hidden=True, desc="Relates to Role Family[Family Key].")] + floor_cols,
    })
    T.append({
        "name": "Seniority", "file": "T09b_salary_by_seniority",
        "desc": "Advertised annual minimum by the seniority word in the title (outputs/tables/T09b_salary_by_seniority.csv).",
        "steps": m_csv("T09b_salary_by_seniority", {"seniority": "type text", **floor_types}, {"seniority": "Seniority Key", **floor_names},
                       [("Labelled", f'Table.AddColumn(Renamed, "Seniority", each {map_expr("Seniority Key", SEN_LABELS, "[Seniority Key]")}, type text)'),
                        ("Ordered", f'Table.AddColumn(Labelled, "Seniority Order", each {map_expr("Seniority Key", SEN_ORDER, "99")}, Int64.Type)'),
                        small_flag("Ordered", "Ads With Figure")],
                       ["Seniority Key", "Seniority", "Seniority Order", *floor_names.values(), "Sample Size"]),
        "columns": [col("Seniority Key", STR, hidden=True, desc="Seniority class key (T08/T09b)."),
                    col("Seniority", STR, sort_by="Seniority Order", desc="Seniority word read from the ad title."),
                    col("Seniority Order", INT, hidden=True, desc="Intern first, no seniority word last.")] + floor_cols,
    })
    T.append({
        "name": "Pay Floor by State", "file": "T09b_salary_by_state",
        "desc": "Advertised annual minimum by primary state (outputs/tables/T09b_salary_by_state.csv).",
        "steps": m_csv("T09b_salary_by_state", {"state": "type text", **floor_types}, {"state": "State", **floor_names},
                       [small_flag("Renamed", "Ads With Figure")], ["State", *floor_names.values(), "Sample Size"]),
        "columns": [col("State", STR, hidden=True, desc="Relates to State[State].")] + floor_cols,
    })
    T.append({
        "name": "Salary Evidence", "file": "T09_salary_coverage",
        "desc": "What the pay figures in the ads are (outputs/tables/T09_salary_coverage.csv): counts per evidence type.",
        "steps": m_csv("T09_salary_coverage", {"metric": "type text", "count": "type number"}, {"metric": "Metric", "count": "Ads"}, None, ["Metric", "Ads"]),
        "columns": [col("Metric", STR, desc="Evidence type key, e.g. with_salary_figure, minimum_only_figures, with_range."),
                    col("Ads", DBL, hidden=True, summarize="sum", fmt="#,0", desc="Core ads (or figures) of that evidence type.")],
    })
    T.append({
        "name": "Decision Matrix", "file": "D01_decision_matrix",
        "desc": "Transparent weighted-sum score per role family under the default weights (outputs/tables/D01_decision_matrix.csv; docs/decision-framework.md).",
        "steps": m_csv("D01_decision_matrix", {"role_family": "type text", "V1_postings_at": "Int64.Type", "V2_postings_styria": "Int64.Type",
                                               "score_default": "type number", "rank_default": "type number", "small_sample_flag": "type logical",
                                               "robust_top3": "type logical"},
                       {"role_family": "Family Key", "V1_postings_at": "Ads Austria", "V2_postings_styria": "Ads Styria",
                        "score_default": "Default Score", "rank_default": "Default Rank", "small_sample_flag": "Small Sample",
                        "robust_top3": "Robust Top 3"},
                       None, ["Family Key", "Ads Austria", "Ads Styria", "Default Score", "Default Rank", "Small Sample", "Robust Top 3"]),
        "columns": [col("Family Key", STR, hidden=True, desc="Relates to Role Family[Family Key]."),
                    col("Ads Austria", INT, hidden=True, summarize="sum", desc="V1: core ads in Austria."),
                    col("Ads Styria", INT, hidden=True, summarize="sum", desc="V2: core ads listing a Styrian site."),
                    col("Default Score", DBL, hidden=True, fmt="0.00", desc="Weighted score 0-1 under the default weights; blank = family not scored (fewer than 30 ads)."),
                    col("Default Rank", DBL, hidden=True, fmt="0", desc="Rank under the default weights."),
                    col("Small Sample", BOOL, desc="D01 small_sample_flag: fewer than 30 ads in Austria or fewer than 10 in Styria."),
                    col("Robust Top 3", BOOL, desc="Top 3 under all four weightings AND at least 30 ads in Austria and in Styria.")],
    })
    combine = ", ".join(f'Table.AddColumn(Table.RenameColumns(Table.SelectColumns(Typed, {{"role_family", "score_{w}", "rank_{w}"}}), '
                        f'{{{{"score_{w}", "Score"}}, {{"rank_{w}", "Rank"}}}}), "Weighting", each "{lab}", type text)'
                        for w, lab in WEIGHTINGS)
    sens_types = {"role_family": "type text", **{f"score_{w}": "type number" for w, _ in WEIGHTINGS}, **{f"rank_{w}": "Int64.Type" for w, _ in WEIGHTINGS}}
    T.append({
        "name": "Weighting Rank", "file": "D02_sensitivity",
        "desc": "Score and rank of each scored family under the four weightings (outputs/tables/D02_sensitivity.csv), unpivoted to one row per family and weighting.",
        "steps": [("Source", csv_source("D02_sensitivity")), ("Promoted", "Table.PromoteHeaders(Source, [PromoteAllScalars = true])"),
                  ("Typed", "Table.TransformColumnTypes(Promoted, {" + ", ".join(f'{{"{k}", {v}}}' for k, v in sens_types.items()) + '}, "en-US")'),
                  ("Combined", f"Table.Combine({{{combine}}})"),
                  ("Ordered", f'Table.AddColumn(Combined, "Weighting Order", each {map_expr("Weighting", {lab: i + 1 for i, (_, lab) in enumerate(WEIGHTINGS)}, "99")}, Int64.Type)'),
                  ("Keyed", 'Table.RenameColumns(Ordered, {{"role_family", "Family Key"}})'),
                  ("Result", 'Table.TransformColumnTypes(Keyed, {{"Score", type number}, {"Rank", Int64.Type}})')],
        "columns": [col("Family Key", STR, hidden=True, desc="Relates to Role Family[Family Key]."),
                    col("Score", DBL, hidden=True, fmt="0.00", desc="Weighted score 0-1 under this weighting."),
                    col("Rank", INT, hidden=True, desc="Rank of the family under this weighting (1 = first)."),
                    col("Weighting", STR, sort_by="Weighting Order", desc="Default, Geography first, Language first or Equal weights (docs/decision-framework.md)."),
                    col("Weighting Order", INT, hidden=True, desc="Default first.")],
    })
    groups = "{" + ", ".join(f'"{g}"' for g in TECHNICAL_GROUPS) + "}"
    T.append({
        "name": "Capability Evidence", "file": "DS10_demand_supply_capability_evidence",
        "desc": "Share of ads mentioning a capability vs share of observed Austrian GitHub accounts showing it in a project (outputs/tables/DS10_demand_supply_capability_evidence.csv). Two universes, one taxonomy.",
        "steps": m_csv("DS10_demand_supply_capability_evidence",
                       {"category": "type text", "group": "type text", "observability": "type text", "demand_share": "type number",
                        "demand_n": "Int64.Type", "supply_project_share": "type number", "supply_n": "Int64.Type"},
                       {"category": "Capability", "group": "Capability Group", "observability": "Observability", "demand_share": "Demand Share",
                        "demand_n": "Ads Base", "supply_project_share": "Project Share", "supply_n": "Accounts Base"},
                       [("Base", 'Table.SelectColumns(Renamed, {"Capability", "Capability Group", "Observability", "Demand Share", "Ads Base", "Project Share", "Accounts Base"})'),
                        ("SortedAll", 'Table.Sort(Base, {{"Demand Share", Order.Descending}, {"Capability", Order.Ascending}})'),
                        ("IndexedAll", 'Table.AddIndexColumn(SortedAll, "Demand Order", 1, 1, Int64.Type)'),
                        ("Technical", f'Table.SelectRows(IndexedAll, each [Observability] = "observable" and List.Contains({groups}, [Capability Group]))'),
                        ("TechRanked", 'Table.AddIndexColumn(Table.Sort(Technical, {{"Demand Share", Order.Descending}, {"Capability", Order.Ascending}}), "Technical Demand Rank", 1, 1, Int64.Type)'),
                        ("Joined", 'Table.NestedJoin(IndexedAll, {"Capability"}, Table.SelectColumns(TechRanked, {"Capability", "Technical Demand Rank"}), {"Capability"}, "R", JoinKind.LeftOuter)'),
                        ("Expanded", 'Table.ExpandTableColumn(Joined, "R", {"Technical Demand Rank"})'),
                        ("Result", 'Table.TransformColumnTypes(Expanded, {{"Technical Demand Rank", Int64.Type}})')]),
        "columns": [col("Capability", STR, sort_by="Demand Order", desc="Capability of the shared capability map (config)."),
                    col("Capability Group", STR, desc="tool, technical, engineering, analytical, ai, business, domain or credential."),
                    col("Observability", STR, desc="Whether a public GitHub profile can show the capability at all."),
                    col("Demand Share", DBL, hidden=True, fmt="0 %", desc="Share of core ads mentioning any skill of the capability."),
                    col("Ads Base", INT, hidden=True, desc="Core ads (demand denominator)."),
                    col("Project Share", DBL, hidden=True, fmt="0 %", desc="Share of observed accounts with a data signal that show the capability in a project."),
                    col("Accounts Base", INT, hidden=True, desc="Austrian GitHub accounts with a data signal (supply denominator)."),
                    col("Demand Order", INT, hidden=True, desc="1 = most-demanded capability."),
                    col("Technical Demand Rank", INT, desc="Rank by demand among observable technical capabilities (groups tool, technical, engineering, analytical, ai); blank otherwise.")],
    })
    T.append({
        "name": "Source", "file": "T01_source_coverage",
        "desc": "Rows and core ads by posting source (outputs/tables/T01_source_coverage.csv) with the median posting age (T13b_posting_age_by_source.csv).",
        "steps": m_csv("T01_source_coverage", {"source": "type text", "rows": "Int64.Type", "in_scope_canonical": "Int64.Type"},
                       {"source": "Source Key", "rows": "Raw Rows", "in_scope_canonical": "Core Postings"},
                       [("Ages", f'Table.TransformColumnTypes(Table.PromoteHeaders({csv_source("T13b_posting_age_by_source")}, [PromoteAllScalars = true]), {{{{"50%", type number}}}}, "en-US")'),
                        ("Joined", 'Table.NestedJoin(Renamed, {"Source Key"}, Ages, {"source"}, "A", JoinKind.LeftOuter)'),
                        ("Expanded", 'Table.ExpandTableColumn(Joined, "A", {"50%"}, {"Median Posting Age Days"})'),
                        ("Labelled", f'Table.AddColumn(Expanded, "Source", each {map_expr("Source Key", SOURCE_LABELS, "[Source Key]")}, type text)'),
                        ("Sorted", 'Table.Sort(Labelled, {{"Core Postings", Order.Descending}, {"Source", Order.Ascending}})'),
                        ("Indexed", 'Table.AddIndexColumn(Sorted, "Source Order", 1, 1, Int64.Type)')],
                       ["Source Key", "Source", "Source Order", "Raw Rows", "Core Postings", "Median Posting Age Days"]),
        "columns": [col("Source Key", STR, hidden=True, desc="Source key (eures, karriere, linkedin, jobsat, willhaben)."),
                    col("Source", STR, sort_by="Source Order", desc="Posting source."),
                    col("Source Order", INT, hidden=True, desc="Source with the most core ads first."),
                    col("Raw Rows", INT, hidden=True, summarize="sum", desc="Rows collected from the source (all titles)."),
                    col("Core Postings", INT, hidden=True, summarize="sum", desc="Canonical core ads attributed to the source after de-duplication."),
                    col("Median Posting Age Days", DBL, hidden=True, fmt="#,0", desc="Median days since first publication of the source's core ads (T13b).")],
    })
    T.append({
        "name": "Title Precision", "file": "Q03c_precision_summary",
        "desc": "Hand-labelled title audit (outputs/tables/Q03c_precision_summary.csv): strict and lenient precision before and after the D-012 rule revision. Row ALL = overall.",
        "steps": m_csv("Q03c_precision_summary", {"family": "type text", "n_sampled": "Int64.Type", "n_kept_after": "Int64.Type", "precision_before_strict": "type number",
                                                  "precision_after_strict": "type number", "precision_after_lenient": "type number"},
                       {"family": "Family Key", "n_sampled": "Titles Sampled", "n_kept_after": "Titles Kept", "precision_before_strict": "Strict Before",
                        "precision_after_strict": "Strict After", "precision_after_lenient": "Lenient After"},
                       labels_join("Renamed", "Family Key", "Family", {"ALL": "All families"}),
                       ["Family Key", "Family", "Titles Sampled", "Titles Kept", "Strict Before", "Strict After", "Lenient After"]),
        "columns": [col("Family Key", STR, hidden=True, desc="Role family key; ALL = the whole sample."),
                    col("Family", STR, desc="Role family display name ('All families' for the whole sample)."),
                    col("Titles Sampled", INT, hidden=True, summarize="sum", desc="Hand-labelled titles in the audit sample."),
                    col("Titles Kept", INT, hidden=True, summarize="sum", desc="Sampled titles the revised (D-012) rules still assign to the family: the n of the 'after' precision."),
                    col("Strict Before", DBL, hidden=True, fmt="0 %", desc="Strict precision before the D-012 revision."),
                    col("Strict After", DBL, hidden=True, fmt="0 %", desc="Strict precision after the D-012 revision."),
                    col("Lenient After", DBL, hidden=True, fmt="0 %", desc="Lenient precision (borderline counted as correct) after the revision.")],
    })
    T.append({
        "name": "Population Funnel", "file": "market_summary.json",
        "desc": "Raw rows -> unique postings -> core postings (outputs/market_summary.json, counts). Each step is a subset of the one before.",
        "steps": [("Source", 'Json.Document(File.Contents(ExportsPath & "market_summary.json"), 65001)'),
                  ("Counts", "Source[counts]"),
                  ("Result", "#table(type table [Step Key = text, Step = text, Step Order = Int64.Type, Rows = Int64.Type], {"
                             '{"raw", "Raw rows, all sources", 1, Counts[raw_rows_all_sources]}, '
                             '{"unique", "Unique postings after de-duplication", 2, Counts[canonical_groups_all]}, '
                             '{"core", "Core data-role postings", 3, Counts[core_canonical]}})')],
        "columns": [col("Step Key", STR, hidden=True, desc="raw, unique or core."),
                    col("Step", STR, sort_by="Step Order", desc="Funnel step."),
                    col("Step Order", INT, hidden=True, desc="Raw first."),
                    col("Rows", INT, hidden=True, summarize="sum", desc="Rows at this step (market_summary.json counts).")],
    })
    T.append({
        "name": "Duplicates", "file": "Q04_duplicates",
        "desc": "De-duplication metrics (outputs/tables/Q04_duplicates.csv).",
        "steps": m_csv("Q04_duplicates", {"metric": "type text", "value": "type number"}, {"metric": "Metric", "value": "Value"}, None, ["Metric", "Value"]),
        "columns": [col("Metric", STR, desc="Metric key, e.g. core_groups, cross_source_groups_core."),
                    col("Value", DBL, hidden=True, summarize="sum", fmt="#,0.###", desc="Metric value.")],
    })
    T.append({
        "name": "Snapshot", "file": "market_summary.json",
        "desc": "Data vintages read from the outputs: demand = first collection timestamp of the posting snapshot (market_summary.json), supply = GitHub collection date (supply_summary.json).",
        "steps": [("Demand", 'Json.Document(File.Contents(ExportsPath & "market_summary.json"), 65001)'),
                  ("Supply", 'Json.Document(File.Contents(ExportsPath & "supply_summary.json"), 65001)'),
                  ("Result", "#table(type table [Demand Collected = date, Supply Collected = date], "
                             '{{Date.From(DateTimeZone.From(Demand[collected_at_range][min])), Date.From(Supply[collection_date])}})')],
        "columns": [col("Demand Collected", DATE, hidden=True, fmt="yyyy-mm-dd", desc="Date of the one-day posting snapshot."),
                    col("Supply Collected", DATE, hidden=True, fmt="yyyy-mm-dd", desc="Date the GitHub supply collection started.")],
    })
    T.append({"name": "Measures", "file": None, "desc": "Home table of every measure of the report (no data).",
              "steps": [("Result", "#table(type table [Marker = Int64.Type], {})")],
              "columns": [col("Marker", INT, hidden=True, desc="Placeholder column of the measure table.")],
              "measures": measures()})
    return T


def measures() -> list[dict]:
    pct, cnt, eur = "0 %", "#,0", "€#,0"
    top = spec.TOP_SKILLS
    M = [
        # ---- market
        measure("Core Ads", "SUM('Role Family'[Ads])", cnt, "1 Market",
                "Core data-role ads in the current filter (sum of T02 count). Unfiltered it equals market_summary.json counts.core_canonical (README marker core_n)."),
        measure("Core Ads Share", "DIVIDE([Core Ads], CALCULATE([Core Ads], REMOVEFILTERS('Role Family')))", pct, "1 Market",
                "Share of all core ads that fall into the families in the filter (T02 share, recomputed from counts)."),
        measure("Styria Ads Any Site", "SUM('Role Family'[Ads Styria Any Site])", cnt, "1 Market",
                "Core ads listing at least one Styrian site (location flag; multi-site ads count in every state). Unfiltered = market_summary.json counts.styria_core. Tentative: every Styria-only figure."),
        measure("Ads by Primary State", "SUM('State'[Ads Primary State])", cnt, "1 Market", "Core ads by primary state, one state per ad (T03a count)."),
        measure("Ads Primary State Share", "DIVIDE([Ads by Primary State], CALCULATE([Ads by Primary State], REMOVEFILTERS('State')))", "0.0 %", "1 Market",
                "Share of all core ads whose primary state is in the filter (T03a share)."),
        measure("Ads Vienna Primary State", "CALCULATE([Ads by Primary State], 'State'[State] = \"Wien\")", cnt, "1 Market",
                "Core ads whose primary state is Wien. Equals market_summary.json counts.vienna_core_primary_state."),
        measure("Vienna Share Primary State", "DIVIDE([Ads Vienna Primary State], CALCULATE([Ads by Primary State], REMOVEFILTERS('State')))", pct, "1 Market",
                "Wien's share of core ads by primary state (README marker vienna_share_core)."),
        measure("Ads Styria Primary State", "CALCULATE([Ads by Primary State], 'State'[State] = \"Steiermark\")", cnt, "1 Market",
                "Core ads whose primary state is Steiermark. Equals market_summary.json counts.styria_core_primary_state (README marker styria_core_primary_state)."),
        measure("Unique Postings", "CALCULATE(SUM('Population Funnel'[Rows]), 'Population Funnel'[Step Key] = \"unique\")", cnt, "1 Market",
                "Unique postings of all titles after de-duplication (market_summary.json counts.canonical_groups_all)."),
        measure("Raw Rows All Sources", "CALCULATE(SUM('Population Funnel'[Rows]), 'Population Funnel'[Step Key] = \"raw\")", cnt, "1 Market",
                "Raw rows collected from all sources before de-duplication (market_summary.json counts.raw_rows_all_sources)."),
        measure("Demand Snapshot", "FORMAT(MIN('Snapshot'[Demand Collected]), \"yyyy-mm-dd\")", None, "1 Market",
                "Date of the one-day posting snapshot, as text (market_summary.json collected_at_range.min)."),
        measure("Supply Snapshot", "FORMAT(MIN('Snapshot'[Supply Collected]), \"yyyy-mm-dd\")", None, "1 Market",
                "Date the GitHub supply collection started, as text (supply_summary.json collection_date)."),
        measure("Market Caveat",
                "\"One day of open ads (\" & [Demand Snapshot] & \"), not yearly demand, vacancies or hires. Styria: \" & FORMAT([Ads Styria Primary State], \"#,0\") & "
                "\" ads by primary state, \" & FORMAT([Styria Ads Any Site], \"#,0\") & \" counting every listed site; every Styria-only figure is tentative. "
                f"Families below {spec.MIN_N} ads are shown but not ranked.\"", None, "1 Market",
                "Reading note of the market page, with its numbers bound to the model."),
        measure("Family Sample Flag", "IF(HASONEVALUE('Role Family'[Family]), SELECTEDVALUE('Role Family'[Sample Size]))", None, "1 Market",
                f"Small-sample flag of the family in context ('n < {spec.MIN_N}: indicative' or 'n >= {spec.MIN_N}')."),
        # ---- skills
        measure("Skill Share", "IF(HASONEVALUE('Skill'[Skill]), DIVIDE(SUM('Skill'[Ads Mentioning]), MAX('Skill'[Ads Base])))", pct, "2 Skills",
                "Share of core ads with a description that mention the skill (T05). Blank unless exactly one skill is in context. A mention is not a requirement."),
        measure(f"Skill Share Top {top}", f"VAR r = SELECTEDVALUE('Skill'[Skill Rank])\nRETURN IF(NOT ISBLANK(r) && r <= {top}, [Skill Share])", pct, "2 Skills",
                f"Skill Share, shown only for the {top} most-mentioned skills nationally (display cut; the Skill table holds all)."),
        measure("Skill CI Low", "IF(HASONEVALUE('Skill'[Skill]), MAX('Skill'[CI Low]))", pct, "2 Skills", "Lower bound of the Wilson 95% interval of Skill Share (T05 ci_low)."),
        measure("Skill CI High", "IF(HASONEVALUE('Skill'[Skill]), MAX('Skill'[CI High]))", pct, "2 Skills", "Upper bound of the Wilson 95% interval of Skill Share (T05 ci_high)."),
        measure("Text Basis Ads", "MAX('Skill'[Ads Base])", cnt, "2 Skills", "Core ads with a description: the denominator of every text-derived share (README marker core_n_text_basis)."),
        measure("Styria Basis Ads", "CALCULATE(MAX('Skill by Region'[Ads Base]), 'Skill by Region'[Region] = \"Styria\")", cnt, "2 Skills",
                "Ads listing a Styrian site: the denominator of the Styrian skill shares (T05 by Styria n). Tentative."),
        measure("Skill Share Styria",
                f"VAR r = SELECTEDVALUE('Skill'[Skill Rank])\nRETURN IF(NOT ISBLANK(r) && r <= {spec.TOP_REGIONAL_SKILLS}, "
                "CALCULATE(DIVIDE(SUM('Skill by Region'[Ads Mentioning]), MAX('Skill by Region'[Ads Base])), 'Skill by Region'[Region] = \"Styria\"))",
                pct, "2 Skills", f"Share of Styrian ads (any listed site) mentioning the skill, for the national top {spec.TOP_REGIONAL_SKILLS}. Tentative: n is the Styria Basis Ads."),
        measure("Skill Share Rest of Austria",
                f"VAR r = SELECTEDVALUE('Skill'[Skill Rank])\nRETURN IF(NOT ISBLANK(r) && r <= {spec.TOP_REGIONAL_SKILLS}, "
                "CALCULATE(DIVIDE(SUM('Skill by Region'[Ads Mentioning]), MAX('Skill by Region'[Ads Base])), 'Skill by Region'[Region] = \"Rest of Austria\"))",
                pct, "2 Skills", f"Share of the other core ads mentioning the skill, for the national top {spec.TOP_REGIONAL_SKILLS}."),
        measure("Stack Ads", "SUM('Skill Stack'[Ads])", cnt, "2 Skills", "Ads naming all three skills of the stack (T06b count)."),
        measure(f"Stack Ads Top {spec.TOP_STACKS}", f"VAR r = SELECTEDVALUE('Skill Stack'[Stack Rank])\nRETURN IF(NOT ISBLANK(r) && r <= {spec.TOP_STACKS}, [Stack Ads])",
                cnt, "2 Skills", f"Stack Ads for the {spec.TOP_STACKS} most frequent stacks (display cut)."),
        measure("Stack Share", "IF(HASONEVALUE('Skill Stack'[Stack]), DIVIDE([Stack Ads], MAX('Skill Stack'[Ads Base])))", pct, "2 Skills",
                "Share of core ads naming all three skills (T06b share)."),
        measure("Top Stack Ads", "CALCULATE([Stack Ads], 'Skill Stack'[Stack Rank] = 1)", cnt, "2 Skills", "Ads naming the most frequent three-skill stack."),
        measure("Top Stack", "CALCULATE(SELECTEDVALUE('Skill Stack'[Stack]), 'Skill Stack'[Stack Rank] = 1)", None, "2 Skills", "Name of the most frequent three-skill stack."),
        measure("Skills Caveat",
                "\"Share of \" & FORMAT([Text Basis Ads], \"#,0\") & \" ads that mention a skill (rule-based text matching; skill recall not measured). "
                "A mention is not a requirement. Styria bars rest on \" & FORMAT([Styria Basis Ads], \"#,0\") & \" ads: read as counts and directions.\"",
                None, "2 Skills", "Reading note of the skills page, with its numbers bound to the model."),
        # ---- pay
        measure("Ads Stating a Figure", "CALCULATE(SUM('Salary Evidence'[Ads]), 'Salary Evidence'[Metric] = \"with_salary_figure\")", cnt, "3 Pay",
                "Core ads that state a pay figure (T09 with_salary_figure; README marker salary_with_salary_figure_n)."),
        measure("Minimum-only Figures", "CALCULATE(SUM('Salary Evidence'[Ads]), 'Salary Evidence'[Metric] = \"minimum_only_figures\")", cnt, "3 Pay",
                "Figures that are a single collective-agreement minimum (T09 minimum_only_figures; README marker salary_minimum_only_n)."),
        measure("Ads Stating a Range", "CALCULATE(SUM('Salary Evidence'[Ads]), 'Salary Evidence'[Metric] = \"with_range\")", cnt, "3 Pay",
                "Ads stating a pay range (T09 with_range)."),
        measure("Share of Ads Stating a Figure", "DIVIDE([Ads Stating a Figure], CALCULATE([Core Ads], REMOVEFILTERS('Role Family')))", pct, "3 Pay",
                "Ads stating a figure as a share of all core ads."),
        measure("Median Floor by Family", "IF(HASONEVALUE('Pay Floor by Family'[Family Key]), MAX('Pay Floor by Family'[Floor Median]))", eur, "3 Pay",
                "Median advertised annual minimum (monthly × 14) of the family; a legal floor in ads, not pay. Blank for several families (medians do not add)."),
        measure("Floor P25 by Family", "IF(HASONEVALUE('Pay Floor by Family'[Family Key]), MAX('Pay Floor by Family'[Floor P25]))", eur, "3 Pay", "25th percentile of the family's advertised minimum."),
        measure("Floor P75 by Family", "IF(HASONEVALUE('Pay Floor by Family'[Family Key]), MAX('Pay Floor by Family'[Floor P75]))", eur, "3 Pay", "75th percentile of the family's advertised minimum."),
        measure("Ads With Figure by Family", "SUM('Pay Floor by Family'[Ads With Figure])", cnt, "3 Pay", "Ads of the family that state a pay figure (the n of the median)."),
        measure("Pay Sample Flag by Family", "IF(HASONEVALUE('Pay Floor by Family'[Family Key]), SELECTEDVALUE('Pay Floor by Family'[Sample Size]))", None, "3 Pay",
                f"'n < {spec.MIN_N}: indicative' when fewer than {spec.MIN_N} ads of the family state a figure."),
        measure("Median Floor by Seniority", "IF(HASONEVALUE('Seniority'[Seniority Key]), MAX('Seniority'[Floor Median]))", eur, "3 Pay",
                "Median advertised annual minimum by the seniority word in the title; a legal floor, not pay."),
        measure("Ads With Figure by Seniority", "SUM('Seniority'[Ads With Figure])", cnt, "3 Pay", "Ads of the seniority class stating a figure."),
        measure("Pay Sample Flag by Seniority", "IF(HASONEVALUE('Seniority'[Seniority Key]), SELECTEDVALUE('Seniority'[Sample Size]))", None, "3 Pay",
                f"'n < {spec.MIN_N}: indicative' when fewer than {spec.MIN_N} ads of the class state a figure."),
        measure("Median Floor by State", "IF(HASONEVALUE('Pay Floor by State'[State]), MAX('Pay Floor by State'[Floor Median]))", eur, "3 Pay",
                "Median advertised annual minimum by primary state; a legal floor, not pay."),
        measure("Floor P25 by State", "IF(HASONEVALUE('Pay Floor by State'[State]), MAX('Pay Floor by State'[Floor P25]))", eur, "3 Pay", "25th percentile by state."),
        measure("Floor P75 by State", "IF(HASONEVALUE('Pay Floor by State'[State]), MAX('Pay Floor by State'[Floor P75]))", eur, "3 Pay", "75th percentile by state."),
        measure("Ads With Figure by State", "SUM('Pay Floor by State'[Ads With Figure])", cnt, "3 Pay", "Ads of the state stating a figure."),
        measure("Pay Sample Flag by State", "IF(HASONEVALUE('Pay Floor by State'[State]), SELECTEDVALUE('Pay Floor by State'[Sample Size]))", None, "3 Pay",
                f"'n < {spec.MIN_N}: indicative' when fewer than {spec.MIN_N} ads of the state state a figure."),
        measure("Pay Caveat",
                "\"Annual gross = monthly figure × 14. \" & FORMAT([Minimum-only Figures], \"#,0\") & \" of \" & FORMAT([Ads Stating a Figure], \"#,0\") & "
                "\" figures are a single collective-agreement minimum: a legal floor in the ad, not a salary. After controls for family, seniority and state "
                f"most raw skill premiums are not distinguishable from zero (D05). Cells with n < {spec.MIN_N} are indicative.\"",
                None, "3 Pay", "Reading note of the pay page, with its numbers bound to the model."),
        # ---- demand vs supply
        measure("Capability Demand Share", "IF(HASONEVALUE('Capability Evidence'[Capability]), MAX('Capability Evidence'[Demand Share]))", pct, "4 Demand vs supply",
                "Share of core ads mentioning the capability (DS10 demand_share)."),
        measure("Capability Project Share", "IF(HASONEVALUE('Capability Evidence'[Capability]), MAX('Capability Evidence'[Project Share]))", pct, "4 Demand vs supply",
                "Share of observed Austrian GitHub accounts with a data signal that show the capability in a project (DS10 supply_project_share)."),
        measure("Capability Demand Share Chart",
                f"VAR r = SELECTEDVALUE('Capability Evidence'[Technical Demand Rank])\nRETURN IF(NOT ISBLANK(r) && r <= {spec.TOP_CAPABILITIES}, [Capability Demand Share])",
                pct, "4 Demand vs supply", f"Capability Demand Share for the {spec.TOP_CAPABILITIES} most-demanded observable technical capabilities (display cut)."),
        measure("Capability Project Share Chart",
                f"VAR r = SELECTEDVALUE('Capability Evidence'[Technical Demand Rank])\nRETURN IF(NOT ISBLANK(r) && r <= {spec.TOP_CAPABILITIES}, [Capability Project Share])",
                pct, "4 Demand vs supply", f"Capability Project Share for the same {spec.TOP_CAPABILITIES} capabilities."),
        measure("Supply Basis Accounts", "MAX('Capability Evidence'[Accounts Base])", cnt, "4 Demand vs supply",
                "Austrian GitHub accounts with a data signal: the supply denominator (README marker supply_p_data_n)."),
        measure("Decision Score", "IF(HASONEVALUE('Decision Matrix'[Family Key]), MAX('Decision Matrix'[Default Score]))", "0.00", "4 Demand vs supply",
                "Weighted score 0-1 under the default weights (D01). Ranks market attractiveness for one profile, not the probability of being hired."),
        measure("Decision Rank", "IF(HASONEVALUE('Decision Matrix'[Family Key]), MAX('Decision Matrix'[Default Rank]))", "0", "4 Demand vs supply", "Rank under the default weights (D01)."),
        measure("Families Robust in Top 3", "COALESCE(CALCULATE(COUNTROWS('Decision Matrix'), 'Decision Matrix'[Robust Top 3] = TRUE()), 0)", cnt, "4 Demand vs supply",
                "Families in the top 3 under all four weightings with at least 30 ads in Austria and in Styria (docs/decision-framework.md). Zero on the current snapshot."),
        measure("Scored Families", "COALESCE(CALCULATE(COUNTROWS('Decision Matrix'), NOT ISBLANK('Decision Matrix'[Default Score])), 0)", cnt, "4 Demand vs supply",
                "Families that receive a score (at least 30 ads in Austria)."),
        measure("Rank under Weighting", "IF(HASONEVALUE('Weighting Rank'[Weighting]) && HASONEVALUE('Weighting Rank'[Family Key]), MAX('Weighting Rank'[Rank]))", "0", "4 Demand vs supply",
                "Rank of the family under the weighting in context (D02)."),
        measure("Supply Caveat",
                "\"Two universes: \" & FORMAT(CALCULATE([Core Ads], REMOVEFILTERS('Role Family')), \"#,0\") & \" ads (\" & [Demand Snapshot] & \") against \" & "
                "FORMAT([Supply Basis Accounts], \"#,0\") & \" GitHub accounts (\" & [Supply Snapshot] & \"); read orders of magnitude. GitHub cannot see Power BI, Excel or SAP work "
                "or private repositories. D01/D02 were scored with the author's own profile (D-026). \" & FORMAT([Families Robust in Top 3], \"#,0\") & "
                "\" families meet the robustness rule.\"", None, "4 Demand vs supply", "Reading note of the demand vs supply page, with its numbers bound to the model."),
        # ---- quality
        measure("Strict Precision After Audit", "CALCULATE(MAX('Title Precision'[Strict After]), 'Title Precision'[Family Key] = \"ALL\")", pct, "5 Quality",
                "Overall strict title-classification precision after the D-012 audit (Q03c row ALL; README marker title_precision_strict_after)."),
        measure("Lenient Precision After Audit", "CALCULATE(MAX('Title Precision'[Lenient After]), 'Title Precision'[Family Key] = \"ALL\")", pct, "5 Quality",
                "Overall lenient precision after the audit (Q03c row ALL)."),
        measure("Titles Audited", "CALCULATE(SUM('Title Precision'[Titles Sampled]), 'Title Precision'[Family Key] = \"ALL\")", cnt, "5 Quality",
                "Hand-labelled titles in the precision audit (Q03c row ALL)."),
        measure("Strict Precision Before by Family",
                "IF(HASONEVALUE('Title Precision'[Family Key]) && SELECTEDVALUE('Title Precision'[Family Key]) <> \"ALL\", MAX('Title Precision'[Strict Before]))",
                pct, "5 Quality", "Strict precision of the family before the D-012 revision; blank for the overall row."),
        measure("Strict Precision After by Family",
                "IF(HASONEVALUE('Title Precision'[Family Key]) && SELECTEDVALUE('Title Precision'[Family Key]) <> \"ALL\", MAX('Title Precision'[Strict After]))",
                pct, "5 Quality", "Strict precision of the family after the D-012 revision; blank for the overall row."),
        measure("Titles Sampled by Family", "SUM('Title Precision'[Titles Sampled])", cnt, "5 Quality", "Hand-labelled titles of the family."),
        measure("Titles Kept by Family", "SUM('Title Precision'[Titles Kept])", cnt, "5 Quality",
                "Sampled titles the revised rules keep in the family: the n behind Strict Precision After by Family."),
        measure("Funnel Rows", "SUM('Population Funnel'[Rows])", cnt, "5 Quality", "Rows at the funnel step in context (bars are nested subsets; never add them)."),
        measure("Core Ads by Source", "SUM('Source'[Core Postings])", cnt, "5 Quality", "Canonical core ads attributed to the source (T01 in_scope_canonical)."),
        measure("Raw Rows by Source", "SUM('Source'[Raw Rows])", cnt, "5 Quality", "Rows collected from the source (T01 rows)."),
        measure("Median Posting Age", "IF(HASONEVALUE('Source'[Source Key]), MAX('Source'[Median Posting Age Days]))", "#,0", "5 Quality",
                "Median days since first publication of the source's core ads (T13b)."),
        measure("Sources Collected", "COUNTROWS('Source')", cnt, "5 Quality", "Posting sources in the snapshot (T01 rows)."),
        measure("Core Ads on Several Sources", "CALCULATE(SUM('Duplicates'[Value]), 'Duplicates'[Metric] = \"cross_source_groups_core\")", cnt, "5 Quality",
                "Core postings seen on two or more sources (Q04 cross_source_groups_core)."),
        measure("Core Ads on Several Sources Share",
                "DIVIDE([Core Ads on Several Sources], CALCULATE(SUM('Duplicates'[Value]), 'Duplicates'[Metric] = \"core_groups\"))", pct, "5 Quality",
                "Share of core postings seen on two or more sources (README marker core_multi_source_groups_share)."),
        measure("Quality Caveat",
                "\"Precision measured on \" & FORMAT([Titles Audited], \"#,0\") & \" hand-labelled titles; recall is not measured. StepStone.at, Indeed.at, hokify and Glassdoor "
                "were blocked; company career pages were not collected. Only \" & FORMAT([Core Ads on Several Sources Share], \"0 %\") & \" of core postings appear on more than one source.\"",
                None, "5 Quality", "Reading note of the quality page, with its numbers bound to the model."),
    ]
    return M


def tmdl_desc(text: str | None, indent: str) -> str:
    return "".join(f"{indent}/// {line}\n" for line in text.splitlines()) if text else ""


def tmdl_m(steps: list[tuple[str, str]], indent: str) -> str:
    body = ",\n".join(f"{indent}\t{name} = {expr}" for name, expr in steps)
    return f"{indent}let\n{body}\n{indent}in\n{indent}\t{steps[-1][0]}\n"


def tmdl_table(t: dict) -> str:
    out = [tmdl_desc(t["desc"], ""), f"table {q(t['name'])}\n", f"\tlineageTag: {tag('table', t['name'])}\n"]
    for m in t.get("measures", []):
        out.append("\n" + tmdl_desc(m["desc"], "\t"))
        if "\n" in m["expr"]:
            out.append(f"\tmeasure {q(m['name'])} =\n" + "".join(f"\t\t\t{line}\n" for line in m["expr"].splitlines()))
        else:
            out.append(f"\tmeasure {q(m['name'])} = {m['expr']}\n")
        if m["fmt"]:
            out.append(f"\t\tformatString: {m['fmt']}\n")
        out.append(f"\t\tdisplayFolder: {m['folder']}\n\t\tlineageTag: {tag('measure', m['name'])}\n")
    for c in t["columns"]:
        out.append("\n" + tmdl_desc(c["desc"], "\t"))
        out.append(f"\tcolumn {q(c['name'])}\n\t\tdataType: {c['type']}\n")
        if c["hidden"]:
            out.append("\t\tisHidden\n")
        if c["fmt"]:
            out.append(f"\t\tformatString: {c['fmt']}\n")
        out.append(f"\t\tlineageTag: {tag('column', t['name'], c['name'])}\n\t\tsummarizeBy: {c['summarize']}\n\t\tsourceColumn: {c['name']}\n")
        if c["sortBy"]:
            out.append(f"\t\tsortByColumn: {q(c['sortBy'])}\n")
        out.append("\n\t\tannotation SummarizationSetBy = User\n")
    out.append(f"\n\tpartition {q(t['name'])} = m\n\t\tmode: import\n\t\tsource =\n")
    out.append(tmdl_m(t["steps"], "\t\t\t\t"))
    out.append("\n\tannotation PBI_ResultType = Table\n")
    return "".join(out)


RELATIONSHIPS = [("Pay Floor by Family", "Family Key", "Role Family", "Family Key"),
                 ("Decision Matrix", "Family Key", "Role Family", "Family Key"),
                 ("Weighting Rank", "Family Key", "Role Family", "Family Key"),
                 ("Skill by Region", "Skill", "Skill", "Skill"),
                 ("Pay Floor by State", "State", "State", "State")]


def model_files() -> dict[str, str]:
    T = tables()
    files = {}
    base = f"{NAME}.SemanticModel"
    files[f"{base}/definition.pbism"] = jdump({"$schema": SCHEMA + "item/semanticModel/definitionProperties/1.0.0/schema.json",
                                               "version": "4.2", "settings": {}})
    files[f"{base}/.platform"] = jdump({"$schema": SCHEMA + "gitIntegration/platformProperties/2.0.0/schema.json",
                                        "metadata": {"type": "SemanticModel", "displayName": NAME},
                                        "config": {"version": "2.0", "logicalId": tag("logical", "semanticModel")}})
    files[f"{base}/definition/database.tmdl"] = "database\n\tcompatibilityLevel: 1601\n"
    files[f"{base}/definition/model.tmdl"] = (
        "model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n\tsourceQueryCulture: en-US\n\n"
        "\tannotation PBI_ProTooling = [\"DevMode\"]\n\n" + "".join(f"ref table {q(t['name'])}\n" for t in T))
    files[f"{base}/definition/expressions.tmdl"] = (
        "/// Folder that holds the repository's public outputs: the folder with market_summary.json, supply_summary.json and the\n"
        "/// tables subfolder (outputs\\tables\\*.csv). Ends with a backslash. Change this one value to re-point every table, then refresh.\n"
        "expression ExportsPath = \"C:\\\\path\\\\to\\\\austria-data-job-market-intelligence\\\\outputs\\\\\" "
        "meta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]\n"
        f"\tlineageTag: {tag('expression', 'ExportsPath')}\n\n\tannotation PBI_ResultType = Text\n").replace("\\\\", "\\")
    files[f"{base}/definition/relationships.tmdl"] = "".join(
        f"relationship {tag('relationship', ft, fc, tt, tc)}\n\tfromColumn: {q(ft)}.{q(fc)}\n\ttoColumn: {q(tt)}.{q(tc)}\n\n"
        for ft, fc, tt, tc in RELATIONSHIPS).rstrip("\n") + "\n"
    for t in T:
        files[f"{base}/definition/tables/{t['name']}.tmdl"] = tmdl_table(t)
    return files


# ================================================================================================ report
def jdump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def lit(value) -> dict:
    """PBIR literal expression: strings are single-quoted, numbers carry the D (double) suffix, booleans plain."""
    if isinstance(value, bool):
        v = "true" if value else "false"
    elif isinstance(value, (int, float)):
        v = f"{value}D"
    else:
        v = "'" + str(value).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": v}}}


def color(hex_: str) -> dict:
    return {"solid": {"color": lit(hex_)}}


def measure_ref(name: str) -> dict:
    return {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Measures"}}, "Property": name}},
            "queryRef": f"Measures.{name}", "nativeQueryRef": name}


def column_ref(table: str, name: str) -> dict:
    return {"field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}},
            "queryRef": f"{table}.{name}", "nativeQueryRef": name}


def sort_by(ref: dict, direction: str = "Descending") -> dict:
    return {"sort": [{"field": ref["field"], "direction": direction}], "isDefaultSort": True}


def container_objects(title: str | None, alt: str) -> dict:
    objs = {"general": [{"properties": {"altText": lit(alt[:250])}}]}
    if title:
        objs["title"] = [{"properties": {"show": lit(True), "text": lit(title), "fontSize": lit(11), "fontColor": color(C["ink"])}}]
    return objs


def textbox(name: str, text: str, pos: tuple, *, size: str, bold: bool = False, colour: str | None = None, alt: str | None = None) -> dict:
    style = {"fontSize": size, "color": colour or C["ink"], "fontFamily": "Segoe UI"}
    if bold:
        style["fontWeight"] = "bold"
    return {"name": name, "pos": pos, "visual": {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {"paragraphs": [{"textRuns": [{"value": text, "textStyle": style}]}]}}]},
        "visualContainerObjects": container_objects(None, alt or text),
        "drillFilterOtherVisuals": True}}


def card(name: str, measure_name: str, pos: tuple, alt: str, *, label: str | None = None, text: bool = False) -> dict:
    ref = measure_ref(measure_name)
    if label:
        ref["displayName"] = label
    objects = {"labels": [{"properties": {"fontSize": lit(11 if text else 26), "color": color(C["ink"])}}],
               "categoryLabels": [{"properties": {"show": lit(True), "fontSize": lit(9), "color": color(C["ink-2"])}}]}
    if text:
        objects["wordWrap"] = [{"properties": {"show": lit(True)}}]
        objects["categoryLabels"] = [{"properties": {"show": lit(False)}}]
    return {"name": name, "pos": pos, "visual": {"visualType": "card", "query": {"queryState": {"Values": {"projections": [ref]}}},
                                                 "objects": objects, "visualContainerObjects": container_objects(None, alt),
                                                 "drillFilterOtherVisuals": True}}


def bar_chart(name: str, category: dict, values: list[dict], pos: tuple, title: str, alt: str, *, sort: dict | None = None,
              tooltips: list[dict] | None = None, series_colors: dict[str, str] | None = None, highlight: tuple | None = None) -> dict:
    query = {"queryState": {"Category": {"projections": [category]}, "Y": {"projections": values}}}
    if tooltips:
        query["queryState"]["Tooltips"] = {"projections": tooltips}
    if sort:
        query["sortDefinition"] = sort
    data_point = []
    if series_colors:
        for qref, hex_ in series_colors.items():
            data_point.append({"properties": {"fill": color(hex_)}, "selector": {"metadata": qref}})
    else:
        data_point.append({"properties": {"fill": color(C["ink-2"])}})
    if highlight:
        table, column, value = highlight
        data_point.append({"properties": {"fill": color(C["hl"])}, "selector": {"data": [{"scopeId": {"Comparison": {
            "ComparisonKind": 0, "Left": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": column}},
            "Right": {"Literal": {"Value": "'" + value + "'"}}}}}]}})
    objects = {"dataPoint": data_point,
               "labels": [{"properties": {"show": lit(True), "fontSize": lit(9), "color": color(C["ink"])}}],
               "categoryAxis": [{"properties": {"fontSize": lit(9), "labelColor": color(C["ink"])}}],
               "valueAxis": [{"properties": {"show": lit(True), "fontSize": lit(9), "labelColor": color(C["ink-2"]),
                                             "gridlineColor": color(C["rule"])}}],
               "legend": [{"properties": {"show": lit(len(values) > 1), "position": lit("Top"), "fontSize": lit(9)}}]}
    return {"name": name, "pos": pos, "visual": {"visualType": "clusteredBarChart", "query": query, "objects": objects,
                                                 "visualContainerObjects": container_objects(title, alt), "drillFilterOtherVisuals": True}}


def table_visual(name: str, kind: str, roles: dict[str, list[dict]], pos: tuple, title: str, alt: str, sort: dict | None = None) -> dict:
    query = {"queryState": {role: {"projections": refs} for role, refs in roles.items()}}
    if sort:
        query["sortDefinition"] = sort
    objects = {"values": [{"properties": {"fontSize": lit(9)}}], "columnHeaders": [{"properties": {"fontSize": lit(9)}}]}
    if kind == "tableEx":
        objects["total"] = [{"properties": {"totals": lit(False)}}]
    else:
        objects["subTotals"] = [{"properties": {"rowSubtotals": lit(False), "columnSubtotals": lit(False)}}]
    return {"name": name, "pos": pos, "visual": {"visualType": kind, "query": query, "objects": objects,
                                                 "visualContainerObjects": container_objects(title, alt), "drillFilterOtherVisuals": True}}


def footer_text(page: dict) -> str:
    srcs = ", ".join(("outputs/" + t) if t.endswith(".json") else f"outputs/tables/{t}.csv" for t in page["tables"])
    return (f"Sources: {srcs}. Tag: {page['tag']}. A share is the share of ads that mention an item, never a requirement; "
            "a posting is not a vacancy or a hire; no statement is causal. Limitations: docs/limitations.md. "
            "HTML twin: dashboards/html/index.html.")


def kpi_row(prefix: str, items: list[tuple[str, str, str]]) -> list[dict]:
    """items: (measure, card label, alt text); evenly spread over the page width."""
    n, gap, x0, width = len(items), 16, 24, W - 48
    w = (width - gap * (n - 1)) / n
    return [card(f"{prefix}-kpi{i + 1}", m, (round(x0 + i * (w + gap)), 92, round(w), 76), alt, label=label)
            for i, (m, label, alt) in enumerate(items)]


def page_visuals(idx: int, page: dict) -> list[dict]:
    p = f"p{idx + 1}"
    head = [textbox(f"{p}-title", page["title"], (24, 12, 1232, 44), size="20pt", bold=True),
            textbox(f"{p}-subtitle", page["subtitle_de"], (24, 54, 1232, 32), size="12pt", colour=C["ink-2"],
                    alt="German subtitle: " + page["subtitle_de"])]
    foot = [textbox(f"{p}-footer", footer_text(page), (24, 652, 1232, 60), size="9pt", colour=C["ink-2"])]
    fam, state = column_ref("Role Family", "Family"), column_ref("State", "State")
    if idx == 0:
        body = kpi_row(p, [("Core Ads", "Core data-role ads (one-day stock)", "Card: number of core data-role ads in the snapshot."),
                           ("Unique Postings", "Unique ads, all titles", "Card: unique postings of all titles after de-duplication."),
                           ("Ads Vienna Primary State", "Vienna, primary state", "Card: core ads whose primary state is Vienna."),
                           ("Ads Styria Primary State", "Styria, primary state (tentative)", "Card: core ads whose primary state is Styria; tentative.")])
        body += [bar_chart(f"{p}-families", fam, [measure_ref("Core Ads")], (24, 180, 600, 360),
                           "Which role families do the core ads fall into?",
                           "Bar chart comparing the number of core ads per role family; families below 30 ads are flagged in the tooltip.",
                           sort=sort_by(measure_ref("Core Ads")), tooltips=[measure_ref("Core Ads Share"), measure_ref("Styria Ads Any Site"),
                                                                             measure_ref("Family Sample Flag")]),
                 bar_chart(f"{p}-states", state, [measure_ref("Ads by Primary State")], (640, 180, 616, 360),
                           "Where are the ads by primary state?",
                           "Bar chart comparing core ads by primary state, with Steiermark highlighted.",
                           sort=sort_by(state, "Ascending"), tooltips=[measure_ref("Ads Primary State Share")],
                           highlight=("State", "State", "Steiermark")),
                 card(f"{p}-caveat", "Market Caveat", (24, 548, 1232, 92), "Reading note: snapshot date, Styrian counts and the small-sample rule.", text=True)]
    elif idx == 1:
        skill = column_ref("Skill", "Skill")
        body = kpi_row(p, [("Text Basis Ads", "Ads with a description (denominator)", "Card: core ads with a description, the denominator of every share."),
                           ("Styria Basis Ads", "Styria ads, any listed site (tentative)", "Card: Styrian ads, the denominator of the Styria shares."),
                           ("Top Stack Ads", "Ads naming the most frequent three-skill stack", "Card: ads naming the most frequent three-skill stack."),
                           ("Top Stack", "Most frequent three-skill stack", "Card: name of the most frequent three-skill stack.")])
        body += [bar_chart(f"{p}-skills", skill, [measure_ref(f"Skill Share Top {spec.TOP_SKILLS}")], (24, 180, 400, 360),
                           f"Which {spec.TOP_SKILLS} skills do the ads mention most?",
                           f"Bar chart comparing the share of ads that mention each of the {spec.TOP_SKILLS} most-mentioned skills; the tooltip shows the 95% interval.",
                           sort=sort_by(measure_ref(f"Skill Share Top {spec.TOP_SKILLS}")),
                           tooltips=[measure_ref("Skill CI Low"), measure_ref("Skill CI High")]),
                 bar_chart(f"{p}-regional", skill, [measure_ref("Skill Share Styria"), measure_ref("Skill Share Rest of Austria")], (436, 180, 400, 360),
                           f"Does Styria mention the national top {spec.TOP_REGIONAL_SKILLS} skills differently?",
                           "Clustered bar chart comparing the skill shares of Styrian ads and of the rest of Austria for the national top skills.",
                           sort=sort_by(skill, "Ascending"),
                           series_colors={"Measures.Skill Share Styria": C["hl"], "Measures.Skill Share Rest of Austria": C["ink-2"]}),
                 table_visual(f"{p}-stacks", "tableEx", {"Values": [column_ref("Skill Stack", "Stack"), measure_ref(f"Stack Ads Top {spec.TOP_STACKS}"),
                                                                    measure_ref("Stack Share")]}, (848, 180, 408, 360),
                              f"Which {spec.TOP_STACKS} three-skill stacks appear together most often?",
                              "Table summarising the most frequent three-skill combinations with ads and share.",
                              sort=sort_by(measure_ref(f"Stack Ads Top {spec.TOP_STACKS}"))),
                 card(f"{p}-caveat", "Skills Caveat", (24, 548, 1232, 92), "Reading note: denominators and what a mention means.", text=True)]
    elif idx == 2:
        sen = column_ref("Seniority", "Seniority")
        body = kpi_row(p, [("Ads Stating a Figure", "Ads stating a pay figure", "Card: core ads that state a pay figure."),
                           ("Minimum-only Figures", "Single collective-agreement minimum", "Card: figures that are a single legal minimum."),
                           ("Ads Stating a Range", "Ads stating a range", "Card: ads that state a pay range."),
                           ("Share of Ads Stating a Figure", "Share of core ads with a figure", "Card: share of core ads that state a figure.")])
        body += [bar_chart(f"{p}-family", fam, [measure_ref("Median Floor by Family")], (24, 180, 400, 360),
                           "What floor does each role family advertise?",
                           "Bar chart comparing the median advertised annual minimum per role family; tooltip shows quartiles, n and the small-sample flag.",
                           sort=sort_by(measure_ref("Median Floor by Family")),
                           tooltips=[measure_ref("Floor P25 by Family"), measure_ref("Floor P75 by Family"), measure_ref("Ads With Figure by Family"),
                                     measure_ref("Pay Sample Flag by Family")]),
                 bar_chart(f"{p}-seniority", sen, [measure_ref("Median Floor by Seniority")], (436, 180, 400, 360),
                           "How does the floor move with the seniority word in the title?",
                           "Bar chart comparing the median advertised annual minimum by seniority word, intern first.",
                           sort=sort_by(sen, "Ascending"),
                           tooltips=[measure_ref("Ads With Figure by Seniority"), measure_ref("Pay Sample Flag by Seniority")]),
                 table_visual(f"{p}-state", "tableEx", {"Values": [state, measure_ref("Ads With Figure by State"), measure_ref("Floor P25 by State"),
                                                                   measure_ref("Median Floor by State"), measure_ref("Floor P75 by State"),
                                                                   measure_ref("Pay Sample Flag by State")]}, (848, 180, 408, 360),
                              "Does the advertised floor differ by state?",
                              "Table summarising the advertised annual minimum by primary state with n, quartiles and the small-sample flag.",
                              sort=sort_by(measure_ref("Median Floor by State"))),
                 card(f"{p}-caveat", "Pay Caveat", (24, 548, 1232, 92), "Reading note: what an advertised floor is and is not.", text=True)]
    elif idx == 3:
        cap = column_ref("Capability Evidence", "Capability")
        body = kpi_row(p, [("Families Robust in Top 3", "Families meeting the robustness rule", "Card: families meeting the robustness rule."),
                           ("Scored Families", "Scored families", "Card: number of role families with a decision score."),
                           ("Core Ads", "Demand side: core ads", "Card: core ads, the demand denominator."),
                           ("Supply Basis Accounts", "Supply side: GitHub accounts with a data signal", "Card: observed GitHub accounts, the supply denominator.")])
        body += [bar_chart(f"{p}-caps", cap, [measure_ref("Capability Demand Share Chart"), measure_ref("Capability Project Share Chart")], (24, 180, 600, 360),
                           f"Which demanded capabilities do public projects rarely show? (top {spec.TOP_CAPABILITIES} technical)",
                           "Clustered bar chart comparing the share of ads that mention each technical capability with the share of GitHub accounts showing it in a project.",
                           sort=sort_by(measure_ref("Capability Demand Share Chart")),
                           series_colors={"Measures.Capability Demand Share Chart": C["ink-2"], "Measures.Capability Project Share Chart": C["hl"]}),
                 bar_chart(f"{p}-matrix", fam, [measure_ref("Decision Score")], (640, 180, 300, 360),
                           "Which family does the decision matrix put first?",
                           "Bar chart comparing the decision-matrix score of each scored role family under the default weights.",
                           sort=sort_by(measure_ref("Decision Score")), tooltips=[measure_ref("Decision Rank")]),
                 table_visual(f"{p}-sensitivity", "pivotTable", {"Rows": [fam], "Columns": [column_ref("Weighting Rank", "Weighting")],
                                                                 "Values": [measure_ref("Rank under Weighting")]}, (956, 180, 300, 360),
                              "Does the ranking survive other weightings?",
                              "Matrix summarising the rank of each scored role family under the four weightings."),
                 card(f"{p}-caveat", "Supply Caveat", (24, 548, 1232, 92), "Reading note: two universes, profile dependence and the robustness rule.", text=True)]
    else:
        body = kpi_row(p, [("Strict Precision After Audit", "Strict title precision after the audit", "Card: strict title-classification precision."),
                           ("Lenient Precision After Audit", "Lenient title precision after the audit", "Card: lenient title-classification precision."),
                           ("Core Ads on Several Sources", "Core ads seen on two or more sources", "Card: core postings seen on more than one source."),
                           ("Sources Collected", "Sources collected", "Card: number of posting sources in the snapshot.")])
        body += [bar_chart(f"{p}-funnel", column_ref("Population Funnel", "Step"), [measure_ref("Funnel Rows")], (24, 180, 400, 360),
                           "How do raw rows become the analysis set?",
                           "Bar chart comparing raw rows, unique postings and core postings; each bar is a subset of the one above.",
                           sort=sort_by(column_ref("Population Funnel", "Step"), "Ascending"),
                           highlight=("Population Funnel", "Step", "Core data-role postings")),
                 bar_chart(f"{p}-sources", column_ref("Source", "Source"), [measure_ref("Core Ads by Source")], (436, 180, 400, 360),
                           "Which sources carry the core ads, and how old are their ads?",
                           "Bar chart comparing core ads by posting source; the tooltip shows raw rows and the median posting age.",
                           sort=sort_by(measure_ref("Core Ads by Source")),
                           tooltips=[measure_ref("Raw Rows by Source"), measure_ref("Median Posting Age")]),
                 bar_chart(f"{p}-precision", column_ref("Title Precision", "Family"),
                           [measure_ref("Strict Precision Before by Family"), measure_ref("Strict Precision After by Family")], (848, 180, 408, 360),
                           "How often is a role label right? (hand-labelled audit)",
                           "Clustered bar chart comparing strict title precision per role family before and after the audit.",
                           sort=sort_by(measure_ref("Strict Precision After by Family")), tooltips=[measure_ref("Titles Sampled by Family"), measure_ref("Titles Kept by Family")],
                           series_colors={"Measures.Strict Precision Before by Family": C["mid"], "Measures.Strict Precision After by Family": C["hl"]}),
                 card(f"{p}-caveat", "Quality Caveat", (24, 548, 1232, 92), "Reading note: audit size, blocked sources and source overlap.", text=True)]
    return head + body + foot


def reading_order(visuals: list[dict]) -> list[dict]:
    """Assign tabOrder in reading order (rows by vertical overlap, then left to right); higher value = focused first."""
    items = sorted(visuals, key=lambda v: (v["pos"][1], v["pos"][0]))
    rows: list[list[dict]] = []
    for v in items:
        y, h = v["pos"][1], v["pos"][3]
        for r in rows:
            ry, rh = r[0]["pos"][1], r[0]["pos"][3]
            if min(y + h, ry + rh) - max(y, ry) >= min(h, rh) / 2:
                r.append(v)
                break
        else:
            rows.append([v])
    ordered = [v for r in rows for v in sorted(r, key=lambda v: v["pos"][0])]
    for i, v in enumerate(ordered):
        v["tab"] = (len(ordered) - i) * 1000
    return ordered


def theme() -> dict:
    text = {"color": C["ink"], "fontFace": "Segoe UI"}
    return {
        "name": "Braga Light (design system v2.1)",
        "dataColors": C["cat"] + [C["cat-other"], C["ink-2"], C["mid"]],
        "foreground": C["ink"], "foregroundNeutralSecondary": C["ink-2"], "foregroundNeutralTertiary": C["ink-2"],
        "background": C["surface"], "backgroundLight": C["surface-2"], "backgroundNeutral": C["rule"],
        "tableAccent": C["hl"], "hyperlink": C["hl"], "visitedHyperlink": C["hl"],
        "good": C["var-pos"], "bad": C["var-neg"], "neutral": C["mid"],
        "maximum": C["hl"], "center": C["neutral"], "minimum": C["seq-low"],
        "textClasses": {"callout": {**text, "fontSize": 26, "fontFace": "Segoe UI Semibold"},
                        "title": {**text, "fontSize": 11, "fontFace": "Segoe UI Semibold"},
                        "header": {**text, "fontSize": 11, "fontFace": "Segoe UI Semibold"},
                        "label": {"color": C["ink-2"], "fontFace": "Segoe UI", "fontSize": 9}},
        "visualStyles": {
            "*": {"*": {"background": [{"show": True, "color": {"solid": {"color": C["surface-2"]}}, "transparency": 0}],
                        "border": [{"show": False}], "dropShadow": [{"show": False}],
                        "visualHeader": [{"show": True}]}},
            "page": {"*": {"background": [{"color": {"solid": {"color": C["surface"]}}, "transparency": 0}],
                           "outspace": [{"color": {"solid": {"color": C["surface"]}}, "transparency": 0}]}},
            "textbox": {"*": {"background": [{"show": False}]}},
        },
    }


def report_files() -> dict[str, str]:
    base = f"{NAME}.Report"
    files = {}
    files[f"{base}/definition.pbir"] = jdump({"$schema": SCHEMA + "item/report/definitionProperties/2.0.0/schema.json", "version": "4.0",
                                             "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    files[f"{base}/.platform"] = jdump({"$schema": SCHEMA + "gitIntegration/platformProperties/2.0.0/schema.json",
                                        "metadata": {"type": "Report", "displayName": NAME},
                                        "config": {"version": "2.0", "logicalId": tag("logical", "report")}})
    d = f"{base}/definition"
    files[f"{d}/version.json"] = jdump({"$schema": SCHEMA + f"item/report/definition/versionMetadata/{V_VERSION}/schema.json", "version": "2.0.0"})
    files[f"{d}/report.json"] = jdump({
        "$schema": SCHEMA + f"item/report/definition/report/{V_REPORT}/schema.json",
        "themeCollection": {"customTheme": {"name": THEME_FILE, "reportVersionAtImport": {"visual": V_VISUAL, "report": V_REPORT, "page": V_PAGE},
                                            "type": "RegisteredResources"}},
        "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                              "items": [{"name": THEME_FILE, "path": THEME_FILE, "type": "CustomTheme"}]}],
    })
    files[f"{base}/StaticResources/RegisteredResources/{THEME_FILE}"] = jdump(theme())
    files[f"{d}/pages/pages.json"] = jdump({"$schema": SCHEMA + f"item/report/definition/pagesMetadata/{V_PAGES}/schema.json",
                                           "pageOrder": spec.page_names(), "activePageName": spec.page_names()[0]})
    for i, page in enumerate(spec.PAGES):
        pd = f"{d}/pages/{page['name']}"
        files[f"{pd}/page.json"] = jdump({"$schema": SCHEMA + f"item/report/definition/page/{V_PAGE}/schema.json", "name": page["name"],
                                          "displayName": f"{i + 1} {page['nav']}", "displayOption": "FitToPage", "height": H, "width": W})
        for z, v in enumerate(reading_order(page_visuals(i, page))):
            x, y, w, h = v["pos"]
            files[f"{pd}/visuals/{v['name']}/visual.json"] = jdump({
                "$schema": SCHEMA + f"item/report/definition/visualContainer/{V_VISUAL}/schema.json", "name": v["name"],
                "position": {"x": x, "y": y, "z": z * 1000, "height": h, "width": w, "tabOrder": v["tab"]}, "visual": v["visual"]})
    return files


def project_files() -> dict[str, str]:
    files = {f"{NAME}.pbip": jdump({"$schema": SCHEMA + "pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
                                    "artifacts": [{"report": {"path": f"{NAME}.Report"}}], "settings": {"enableAutoRecovery": True}})}
    files.update(model_files())
    files.update(report_files())
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write the PBIP project (TMDL model + PBIR report) into dashboards/.")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if a committed file differs from the generator")
    args = ap.parse_args(argv)
    out = args.root / DASH
    files = project_files()
    if args.check:
        stale = [rel for rel, text in files.items() if not (out / rel).exists() or (out / rel).read_text(encoding="utf-8") != text]
        for rel in stale:
            print(f"dashboard_pbip: differs from the generator: dashboards/{rel}")
        return 1 if stale else 0
    for rel, text in files.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    print(f"dashboard_pbip: wrote {len(files)} files under {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
