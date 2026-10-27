"""Static HTML twin of the Power BI dashboard -> dashboards/html/index.html

    python src/reporting/dashboard_html.py            write dashboards/html/index.html
    python src/reporting/dashboard_html.py --check    change nothing; exit 1 if the committed file is not what the outputs give
    python src/reporting/dashboard_html.py --out PATH --root PATH   (tests / other trees)

run_all.py runs it as the `dashboard_html` step (target `dashboard`), after the visual layer and before the digest.

What it is. One self-contained HTML file with the five pages of dashboards/JobMarket.Report (page set, titles and German
subtitles from src/reporting/dashboard_spec.py). It reads the same public outputs the Power BI model loads
(outputs/tables/*.csv, outputs/market_summary.json, outputs/supply_summary.json) and, for the "Read with" caveat under a
chart, the caveat that outputs/visual_questions.json already attaches to the matching BQ figure. It adds no data, no
table and no conclusion: every number on the page is read from those files when the page is built, and every answer
sentence is composed from them, so a new snapshot re-renders the page instead of leaving old numbers behind (D-024).

How it is built. Python composes the markup; the charts are hand-built (an HTML row per category, the marks in an
inline SVG track, every label as real text so it stays readable at phone width); the page data is embedded as inline
JSON; a few lines of vanilla JavaScript drive the tabs (role=tablist, arrow keys, URL hash per page) and the tooltips.
No CDN, no web font, no network request, no backend. The output is deterministic: no timestamp except the data
vintages read from the outputs, stable key order, LF line endings, so the same outputs give a byte-identical file.

Design: the Braga design system v2.1 tokens (bk-viz, light and dark through prefers-color-scheme): flat opaque surfaces,
hairline axes and gridlines, one highlighted entity per chart in the accent, structure grey for the rest, a hatched
texture (not colour alone) for cells below the project's n >= 30 rule, colour in marks and never in text, square
corners, nothing below 12 px.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import dashboard_spec as spec  # noqa: E402
import vintages  # noqa: E402
from metrics_registry import fmt_value  # noqa: E402  (the repository's own number formats: "40 %", "€55.4k", "11,997")

OUT = Path("dashboards") / "html" / "index.html"
NBSP = " "
# DS10 capability groups that a public code repository can show (the business and domain groups are judged by other
# evidence; their rows stay in the data table of the chart)
TECHNICAL_GROUPS = ("tool", "technical", "engineering", "analytical", "ai")
SENIORITY = [("intern_student", "Intern / student"), ("trainee_junior", "Junior / trainee"), ("senior", "Senior"),
             ("lead_head", "Lead / head"), ("unspecified", "No seniority word")]
SOURCE_LABEL = {"eures": "EURES / AMS", "jobsat": "jobs.at", "karriere": "karriere.at", "linkedin": "LinkedIn", "willhaben": "willhaben"}
WEIGHTINGS = [("default", "Default"), ("geography_first", "Geography first"), ("language_first", "Language first"),
              ("equal", "Equal weights")]
FOCUS_STATE = "Steiermark"   # the repository's focus region (README: "with a Styria/Graz focus")
# Fixed reading notes (no numbers), worded as in README.md and docs/limitations.md
SKILL_CAVEAT = ("Rule-based text matching: title precision is measured, skill recall is not. A mention is not a requirement. "
                "AI (generic) counts any mention of AI, KI or artificial intelligence, so it names no specific skill.")
CAPABILITY_CAVEAT = ("Two universes with different denominators (ads, accounts): read the order of magnitude, not the exact ratio. "
                     "GitHub over-represents engineers, researchers and students and cannot see Power BI, Excel or SAP work or "
                     "private repositories; a missing public trace is not a missing skill.")
PREMIUM_CAVEAT = ("A floor is not a salary. After controls for role family, seniority and state, most raw skill premiums are not "
                  "distinguishable from zero (D05, BQ45): the family and the seniority label set the advertised floor, not the tool "
                  "named in the ad. Association, not causation.")
MATRIX_NOTE = ("The published D01/D02 tables were scored with the author's own profile; the public example profile "
               "(config/profile.json) gives different overlap and gap values (D-026).")


# ------------------------------------------------------------------------------------------------ inputs
def read_csv(root: Path, name: str) -> list[dict]:
    with open(root / "outputs" / "tables" / f"{name}.csv", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(root: Path, name: str) -> dict:
    return json.loads((root / "outputs" / name).read_text(encoding="utf-8"))


def num(value) -> float:
    return float(value) if value not in ("", None) else float("nan")


# ------------------------------------------------------------------------------------------------ formats
def pct(value: float, places: int = 0) -> str:
    return fmt_value(value, "share", f"pct{places}").replace(" %", NBSP + "%")


def count(value) -> str:
    return fmt_value(float(value), "count", "int")


def eur(value) -> str:
    return fmt_value(float(value), "eur", "eur_k")


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def join_words(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


# ------------------------------------------------------------------------------------------------ data
def bq_caveats(root: Path) -> dict[str, str]:
    """chart prefix (BQ01, ...) -> the caveat the visual layer attaches to that figure (outputs/visual_questions.json)."""
    figures = read_json(root, "visual_questions.json").get("figures", [])
    return {f["chart_id"].split("_", 1)[0]: f.get("caveat", "") for f in figures}


def family_labels(root: Path) -> dict[str, str]:
    return {r["category"]: r["label"] for r in read_csv(root, "DS01_demand_supply_role_families")}


def build_data(root: Path = ROOT) -> dict:
    """Every number and label the five pages show, read from outputs/ (no literals)."""
    labels = family_labels(root)
    caveat = bq_caveats(root)
    summary = read_json(root, "market_summary.json")
    counts = summary["counts"]
    core = int(counts["core_canonical"])
    supply = read_json(root, "supply_summary.json")
    meta = {"title": spec.REPORT_TITLE, "demand_vintage": vintages.demand_vintage(root),
            "supply_vintage": vintages.supply_vintage_label(root),
            "stale_after": vintages.stale_after(vintages.demand_vintage(root)),
            "supply_collection": str(supply.get("collection_date", ""))[:10]}

    # ---- page 1: market overview (T02, T03a, market_summary.json)
    families = []
    for r in sorted(read_csv(root, "T02_role_family_counts"), key=lambda r: (-int(r["count"]), r["role_family"])):
        families.append({"key": r["role_family"], "label": labels.get(r["role_family"], r["role_family"]),
                         "count": int(r["count"]), "n": int(r["n"]), "styria": int(r["styria_count"]),
                         "graz": int(r["graz_area_count"]), "vienna": int(r["vienna_count"]),
                         "small": int(r["count"]) < spec.MIN_N})
    states = [{"state": r["state"], "count": int(r["count"]), "n": int(r["n"])}
              for r in sorted(read_csv(root, "T03a_state_counts"), key=lambda r: (r["state"] == "unspecified", -int(r["count"]), r["state"]))]
    q03c_all = next((r for r in read_csv(root, "Q03c_precision_summary") if r["family"] == "ALL"), None)
    p1 = {"core": core, "precision_strict": num(q03c_all["precision_after_strict"]) if q03c_all else None,
          "precision_n": int(q03c_all["n_sampled"]) if q03c_all else None, "raw": int(counts["raw_rows_all_sources"]), "unique": int(counts["canonical_groups_all"]),
          "styria_primary": int(counts["styria_core_primary_state"]), "styria_flag": int(counts["styria_core"]),
          "graz_flag": int(counts["graz_area_core"]), "vienna_primary": int(counts["vienna_core_primary_state"]),
          "families": families, "states": states, "caveat_states": caveat.get("BQ01", "")}

    # ---- page 2: skills & stacks (T05, T05 by Styria, T06b)
    skills = sorted(read_csv(root, "T05_skills_all_tech"), key=lambda r: (-int(r["count"]), r["skill"]))
    skill_rows = [{"skill": r["skill"], "count": int(r["count"]), "n": int(r["n"]), "lo": num(r["ci_low"]), "hi": num(r["ci_high"]),
                   "rank": i + 1} for i, r in enumerate(skills)]
    regional = {(r["styria_flag"], r["skill"]): r for r in read_csv(root, "T05_skills_all_tech_by_styria")}
    reg_rows = []
    for s in skill_rows[:spec.TOP_REGIONAL_SKILLS]:
        sty, rest = regional.get(("Styria", s["skill"])), regional.get(("Rest of Austria", s["skill"]))
        reg_rows.append({"skill": s["skill"], "styria": int(sty["count"]) if sty else 0, "styria_n": int(sty["n"]) if sty else 0,
                         "styria_lo": num(sty["ci_low"]) if sty else float("nan"), "styria_hi": num(sty["ci_high"]) if sty else float("nan"),
                         "rest": int(rest["count"]) if rest else 0, "rest_n": int(rest["n"]) if rest else 0})
    stacks = sorted(read_csv(root, "T06b_top_stacks_size3"), key=lambda r: (-int(r["count"]), r["stack"]))
    p2 = {"skills": skill_rows, "regional": reg_rows,
          "stacks": [{"stack": r["stack"], "count": int(r["count"]), "n": int(r["n"])} for r in stacks],
          "caveat_regional": caveat.get("BQ06", ""), "caveat_stacks": caveat.get("BQ10", "")}

    # ---- page 3: advertised pay floors (T09, T09b by family / seniority / state)
    coverage = {r["metric"]: int(float(r["count"])) for r in read_csv(root, "T09_salary_coverage")}

    def floors(rows, key, label_of):
        return [{"key": r[key], "label": label_of(r[key]), "n": int(float(r["n"])), "p25": num(r["min_p25"]),
                 "median": num(r["min_median"]), "p75": num(r["min_p75"]), "small": int(float(r["n"])) < spec.MIN_N}
                for r in rows]
    fam_floor = sorted(floors(read_csv(root, "T09b_salary_by_role_family"), "role_family", lambda k: labels.get(k, k)),
                       key=lambda r: (r["small"], -r["median"], r["label"]))
    sen_map = dict(SENIORITY)
    sen_rows = {r["seniority"]: r for r in read_csv(root, "T09b_salary_by_seniority")}
    sen_floor = floors([sen_rows[k] for k, _ in SENIORITY if k in sen_rows], "seniority", lambda k: sen_map[k])
    state_floor = sorted(floors(read_csv(root, "T09b_salary_by_state"), "state", lambda k: k),
                         key=lambda r: (r["small"], -r["median"], r["label"]))
    p3 = {"coverage": coverage, "core": core, "families": fam_floor, "seniority": sen_floor, "states": state_floor,
          "caveat_family": caveat.get("BQ15", ""), "caveat_seniority": caveat.get("BQ16", "")}

    # ---- page 4: demand vs supply (DS10, D01, D02)
    caps = []
    for r in read_csv(root, "DS10_demand_supply_capability_evidence"):
        caps.append({"capability": r["category"], "group": r["group"], "observability": r["observability"],
                     "demand": num(r["demand_share"]), "demand_n": int(r["demand_n"]), "project": num(r["supply_project_share"]),
                     "supply_n": int(r["supply_n"])})
    technical = sorted([c for c in caps if c["observability"] == "observable" and c["group"] in TECHNICAL_GROUPS],
                       key=lambda c: (-c["demand"], c["capability"]))
    for i, c in enumerate(technical):
        c["rank"] = i + 1
    matrix = []
    for r in read_csv(root, "D01_decision_matrix"):
        matrix.append({"key": r["role_family"], "label": labels.get(r["role_family"], r["role_family"]),
                       "score": num(r["score_default"]), "rank": num(r["rank_default"]), "postings": int(r["V1_postings_at"]),
                       "styria": int(r["V2_postings_styria"]), "small": r["small_sample_flag"] == "True",
                       "robust": r["robust_top3"] == "True"})
    matrix.sort(key=lambda r: (r["rank"] != r["rank"], r["rank"] if r["rank"] == r["rank"] else 0, r["label"]))
    sens = []
    for r in read_csv(root, "D02_sensitivity"):
        sens.append({"key": r["role_family"], "label": labels.get(r["role_family"], r["role_family"]),
                     "ranks": {w: int(r[f"rank_{w}"]) for w, _ in WEIGHTINGS},
                     "scores": {w: num(r[f"score_{w}"]) for w, _ in WEIGHTINGS}})
    sens.sort(key=lambda r: (r["ranks"]["default"], r["label"]))
    p4 = {"capabilities": technical, "all_capabilities": sorted(caps, key=lambda c: (-c["demand"], c["capability"])),
          "matrix": matrix, "sensitivity": sens, "supply_n": technical[0]["supply_n"] if technical else 0, "core": core,
          "caveat_matrix": caveat.get("BQ05", ""), "caveat_sens": caveat.get("BQ07", "")}

    # ---- page 5: data quality & coverage (market_summary, T01, T13b, Q04, Q03c)
    age = {r["source"]: num(r["50%"]) for r in read_csv(root, "T13b_posting_age_by_source")}
    sources = [{"key": r["source"], "label": SOURCE_LABEL.get(r["source"], r["source"]), "rows": int(r["rows"]),
                "core": int(r["in_scope_canonical"]), "age": age.get(r["source"], float("nan"))}
               for r in read_csv(root, "T01_source_coverage")]
    sources.sort(key=lambda r: (-r["core"], r["label"]))
    q04 = {r["metric"]: num(r["value"]) for r in read_csv(root, "Q04_duplicates")}
    precision = []
    overall = None
    for r in read_csv(root, "Q03c_precision_summary"):
        row = {"key": r["family"], "label": labels.get(r["family"], r["family"]), "n": int(r["n_sampled"]),
               "before": num(r["precision_before_strict"]), "after": num(r["precision_after_strict"]),
               "lenient_after": num(r["precision_after_lenient"]), "kept": int(r["n_kept_after"])}
        if r["family"] == "ALL":
            overall = row
        else:
            precision.append(row)
    precision.sort(key=lambda r: (-r["after"], r["label"]))
    p5 = {"funnel": [("Raw rows, all sources", int(counts["raw_rows_all_sources"])),
                     ("Unique postings after de-duplication", int(counts["canonical_groups_all"])),
                     ("Core data-role postings", core)],
          "sources": sources, "multi_source": int(q04.get("cross_source_groups_core", 0)), "core_groups": int(q04.get("core_groups", 0)),
          "precision": precision, "overall": overall, "caveat_funnel": caveat.get("BQ27", ""),
          "caveat_precision": caveat.get("BQ28", ""), "caveat_sources": caveat.get("BQ30", "")}
    return {"meta": meta, "p1": p1, "p2": p2, "p3": p3, "p4": p4, "p5": p5}


# ------------------------------------------------------------------------------------------------ chart primitives
def nice_max(value: float, step: float) -> float:
    """Smallest multiple of `step` that is >= value (axis end)."""
    k = int(value / step)
    return step * (k if k * step >= value else k + 1)


def ticks(top: float, step: float) -> list[float]:
    out, v = [], 0.0
    while v <= top + 1e-9:
        out.append(round(v, 10))
        v += step
    return out


def x(value: float, top: float) -> float:
    """Position on the 0..1000 track."""
    return round(1000.0 * max(0.0, min(value, top)) / top, 1)


def grid(top: float, step: float) -> str:
    return "".join(f'<line class="gl" x1="{x(t, top)}" x2="{x(t, top)}" y1="0" y2="24"/>' for t in ticks(top, step))


def track(top: float, step: float, marks: str, height: int = 24) -> str:
    return (f'<svg class="trk" viewBox="0 0 1000 {height}" preserveAspectRatio="none" aria-hidden="true" focusable="false">'
            f'{grid(top, step)}{marks}</svg>')


def axis(top: float, step: float, fmt, unit: str, *, long: bool = False, max_labels: int = 6) -> str:
    """Tick labels under the tracks; every k-th gridline is labelled so that at most `max_labels` labels are set."""
    tk = ticks(top, step)
    every = max(1, -(-len(tk) // max_labels))
    spans = "".join(f'<span{" class=end" if x(t, top) >= 1000 else ""} style="left:{x(t, top) / 10:.2f}%">{esc(fmt(t))}</span>'
                    for i, t in enumerate(tk) if i % every == 0)
    return (f'<div class="axis{" long" if long else ""}" aria-hidden="true"><span></span><span class="ticks">{spans}</span><span></span></div>'
            f'<p class="unit">{esc(unit)}</p>')


def row(label: str, marks_svg: str, value: str, tip: str, *, flag: str = "", cls: str = "") -> str:
    flag_html = f' <span class="flag">{esc(flag)}</span>' if flag else ""
    return (f'<div class="row{" " + cls if cls else ""}" role="listitem" tabindex="0" data-tip="{esc(tip)}" aria-label="{esc(tip)}">'
            f'<span class="lab">{esc(label)}{flag_html}</span><span class="bar">{marks_svg}</span>'
            f'<span class="val">{value}</span></div>')


def bar(value: float, top: float, cls: str, y: int = 6, h: int = 12) -> str:
    return f'<rect class="{cls}" x="0" y="{y}" width="{x(value, top)}" height="{h}"/>'


def whisker(lo: float, hi: float, top: float, y: float = 12) -> str:
    a, b = x(lo, top), x(hi, top)
    return (f'<line class="wh" x1="{a}" x2="{b}" y1="{y}" y2="{y}"/><line class="wh" x1="{a}" x2="{a}" y1="{y - 5}" y2="{y + 5}"/>'
            f'<line class="wh" x1="{b}" x2="{b}" y1="{y - 5}" y2="{y + 5}"/>')


def tick_mark(value: float, top: float, cls: str) -> str:
    v = x(value, top)
    return f'<line class="{cls}" x1="{v}" x2="{v}" y1="3" y2="21"/>'


def data_table(caption: str, head: list[str], body: list[list[str]], numeric_from: int = 1) -> str:
    th = "".join(f'<th scope="col"{" class=num" if i >= numeric_from else ""}>{esc(h)}</th>' for i, h in enumerate(head))
    rows = []
    for r in body:
        cells = [f'<th scope="row">{esc(r[0])}</th>'] + [f'<td class="num">{esc(c)}</td>' if i + 1 >= numeric_from else f"<td>{esc(c)}</td>"
                                                       for i, c in enumerate(r[1:])]
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (f'<details class="tbl"><summary>Data table</summary><div class="scroll"><table><caption>{esc(caption)}</caption>'
            f'<thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div></details>')


def legend(items: list[tuple[str, str]]) -> str:
    return '<ul class="legend">' + "".join(f'<li><span class="key {cls}" aria-hidden="true"></span>{esc(text)}</li>'
                                           for cls, text in items) + "</ul>"


VAL_RE = __import__("re").compile(r'<span class="val">([^<]*)</span>')


def chart(cid: str, title: str, answer: str, body: str, read_with: str, table: str, *, legend_html: str = "", wide: bool = False) -> str:
    rw = f'<p class="readwith"><strong>Read with:</strong> {esc(read_with)}</p>' if read_with else ""
    # one value-column width per chart, so every track in the chart has the same length (ch of the longest value label)
    widest = max((len(html.unescape(v)) for v in VAL_RE.findall(body)), default=4)
    return (f'<figure class="card chart{" wide" if wide else ""}" id="{cid}" aria-labelledby="{cid}-t">'
            f'<h3 id="{cid}-t">{esc(title)}</h3><p class="answer">{answer}</p>{legend_html}'
            f'<div class="plot" role="list" aria-label="{esc(title)}" style="--valw:{widest + 1}ch">{body}</div>{rw}{table}</figure>')


def kpi(label: str, value: str, note: str, accent: bool = False) -> str:
    return (f'<div class="kpi{" accent" if accent else ""}"><p class="kl">{esc(label)}</p><p class="kv">{esc(value)}</p>'
            f'<p class="kn">{note}</p></div>')


def pct_tick(t: float) -> str:
    return fmt_value(t, "share", "pct0").replace(" %", NBSP + "%")


def eur_tick(t: float) -> str:
    return fmt_value(t, "eur", "eur_k0")


def count_tick(t: float) -> str:
    return fmt_value(t, "count", "int")


# ------------------------------------------------------------------------------------------------ pages
def page_market(d: dict, meta: dict) -> str:
    core = d["core"]
    fam = d["families"]
    small = [f["label"] for f in fam if f["small"]]
    top = fam[0]
    kpis = (kpi("Core data-role ads", count(core), f"open on {esc(meta['demand_vintage'])}; a one-day stock, not yearly demand or hires", True)
            + kpi("Unique ads, all titles", count(d["unique"]), f"de-duplicated from {count(d['raw'])} raw rows")
            + kpi("Vienna, primary state", count(d["vienna_primary"]), f"{pct(d['vienna_primary'] / core)} of core ads")
            + kpi("Styria, primary state", count(d["styria_primary"]),
                  f"{count(d['styria_flag'])} counting every listed site; every Styria-only figure is tentative"))
    fmax = nice_max(top["count"], 50)
    rows = []
    for f in fam:
        tip = f"{f['label']}: {count(f['count'])} of {count(core)} core ads ({pct(f['count'] / core)})" + (
            f"; below the n = {spec.MIN_N} rule, too small to rank" if f["small"] else "")
        rows.append(row(f["label"], track(fmax, 50, bar(f["count"], fmax, "m-small" if f["small"] else "m-base")),
                        f"{count(f['count'])} · {pct(f['count'] / core)}", tip, flag=f"n < {spec.MIN_N}" if f["small"] else ""))
    small_txt = (f" {join_words(small)} have fewer than {spec.MIN_N} ads each and are drawn but not ranked." if small else "")
    a1 = (f"{esc(top['label'])} is the largest family with {count(top['count'])} of {count(core)} core ads "
          f"({pct(top['count'] / core)}).{esc(small_txt)}")
    t1 = data_table("Core ads by role family (T02). Styria, Graz area and Vienna count every listed site.",
                    ["Role family", "Core ads", "Share", "Styria", "Graz area", "Vienna"],
                    [[f["label"], count(f["count"]), pct(f["count"] / core), count(f["styria"]), count(f["graz"]), count(f["vienna"])] for f in fam])
    read1 = ("Families are assigned from the job title by ordered rules"
             + (f"; strict precision {pct(d['precision_strict'])} on {count(d['precision_n'])} hand-labelled titles (Q03c)"
                if d["precision_strict"] is not None else "")
             + f"; recall is not measured. Families below {spec.MIN_N} ads are drawn but not ranked. One day of open ads, not yearly demand.")
    c1 = chart("c-families", "Which role families do the core ads fall into?", a1,
               "".join(rows) + axis(fmax, 50, count_tick, "core data-role ads (T02)"), read1, t1)

    st = d["states"]
    smax = nice_max(max(s["count"] for s in st), 50)
    srows = []
    for s in st:
        cls = "m-hl" if s["state"] == FOCUS_STATE else "m-base"
        tip = f"{s['state']}: {count(s['count'])} of {count(s['n'])} core ads ({pct(s['count'] / s['n'], 1)}) by primary state"
        srows.append(row(s["state"], track(smax, 50, bar(s["count"], smax, cls)), f"{count(s['count'])} · {pct(s['count'] / s['n'], 1)}", tip,
                         cls="focus" if s["state"] == FOCUS_STATE else ""))
    lead = st[0]
    a2 = (f"{esc(lead['state'])} holds {count(lead['count'])} of {count(core)} core ads ({pct(lead['count'] / core)}) by primary state; "
          f"<mark>{esc(FOCUS_STATE)}</mark> has {count(d['styria_primary'])} ({pct(d['styria_primary'] / core, 1)}), "
          f"or {count(d['styria_flag'])} if every listed site counts.")
    t2 = data_table("Core ads by primary state (T03a); one state per ad.", ["State", "Core ads", "Share"],
                    [[s["state"], count(s["count"]), pct(s["count"] / s["n"], 1)] for s in st])
    c2 = chart("c-states", "Where are the ads by primary state?", a2,
               "".join(srows) + axis(smax, 50, count_tick, "core data-role ads by primary state (T03a)"), d["caveat_states"], t2)
    return f'<div class="kpis">{kpis}</div><div class="grid">{c1}{c2}</div>'


def page_skills(d: dict, meta: dict) -> str:
    skills = d["skills"]
    n = skills[0]["n"] if skills else 0
    shown = skills[:spec.TOP_SKILLS]
    stack0 = d["stacks"][0] if d["stacks"] else None
    sty_n = d["regional"][0]["styria_n"] if d["regional"] else 0
    kpis = (kpi("Ads with a description", count(n), "the denominator of every share on this page", True)
            + kpi("Styria ads, any listed site", count(sty_n), "denominator of the Styria bars; tentative")
            + kpi("Most frequent three-skill stack", f"{count(stack0['count'])} ads" if stack0 else "–",
                  esc(stack0["stack"]) + f" ({pct(stack0['count'] / stack0['n'])} of ads)" if stack0 else ""))
    top = nice_max(max(s["hi"] for s in shown), 0.1)
    rows = []
    for s in shown:
        share = s["count"] / s["n"]
        tip = (f"{s['skill']}: mentioned in {count(s['count'])} of {count(s['n'])} ads ({pct(share)}); "
               f"95% Wilson interval {pct(s['lo'])} to {pct(s['hi'])}")
        rows.append(row(s["skill"], track(top, 0.1, bar(share, top, "m-base") + whisker(s["lo"], s["hi"], top)), pct(share), tip))
    specific = [s for s in skills if "(generic)" not in s["skill"]]
    generic = [s for s in skills if "(generic)" in s["skill"]]
    lead = specific[:2]
    a1 = ""
    if lead:
        ahead = [g for g in generic if g["count"] > lead[0]["count"]]
        pre = (f"Apart from generic wording ({', '.join(esc(g['skill']) + ' ' + pct(g['count'] / g['n']) for g in ahead)}), "
               if ahead else "")
        a1 = (pre + f"{esc(lead[0]['skill'])} ({pct(lead[0]['count'] / n)}) and {esc(lead[1]['skill'])} ({pct(lead[1]['count'] / n)}) "
              f"are the most-mentioned skills in {count(n)} ads.")
    t1 = data_table(f"Share of {count(n)} ads mentioning each skill, 95% Wilson interval (T05); all {len(skills)} tracked items.",
                    ["Skill", "Ads", "Share", "CI low", "CI high"],
                    [[s["skill"], count(s["count"]), pct(s["count"] / s["n"]), pct(s["lo"]), pct(s["hi"])] for s in skills])
    c1 = chart("c-skills", f"Which {len(shown)} skills do the ads mention most?", a1,
               "".join(rows) + axis(top, 0.1, pct_tick, f"share of {count(n)} ads mentioning the skill · whisker = 95% interval"),
               SKILL_CAVEAT, t1)

    reg = d["regional"]
    rtop = nice_max(max(max(r["styria"] / r["styria_n"] if r["styria_n"] else 0, r["rest"] / r["rest_n"] if r["rest_n"] else 0) for r in reg), 0.1)
    rrows, best = [], None
    for r in reg:
        ss = r["styria"] / r["styria_n"] if r["styria_n"] else 0.0
        rs = r["rest"] / r["rest_n"] if r["rest_n"] else 0.0
        if best is None or abs(ss - rs) > abs(best[1] - best[2]):
            best = (r, ss, rs)
        marks = bar(ss, rtop, "m-hl", 2, 9) + bar(rs, rtop, "m-base", 13, 9)
        tip = (f"{r['skill']}: Styria {count(r['styria'])} of {count(r['styria_n'])} ads ({pct(ss)}, 95% interval "
               f"{pct(r['styria_lo'])} to {pct(r['styria_hi'])}); "
               f"rest of Austria {count(r['rest'])} of {count(r['rest_n'])} ({pct(rs)})")
        rrows.append(row(r["skill"], track(rtop, 0.1, marks), f"{pct(ss)} / {pct(rs)}", tip))
    a2 = ""
    if best:
        r, ss, rs = best
        a2 = (f"The widest gap among the national top {len(reg)}: <mark>Styria</mark> mentions {esc(r['skill'])} in "
              f"{count(r['styria'])} of {count(r['styria_n'])} ads ({pct(ss)}) against {pct(rs)} in the rest of Austria. "
              f"Styrian shares rest on {count(r['styria_n'])} ads: read them as counts and directions.")
    t2 = data_table("Ads mentioning each skill: Styria (any listed site) and the rest of Austria (T05 by Styria).",
                    ["Skill", "Styria ads", "Styria share", "Styria 95% interval", "Rest ads", "Rest share"],
                    [[r["skill"], f"{count(r['styria'])} of {count(r['styria_n'])}", pct(r["styria"] / r["styria_n"]) if r["styria_n"] else "–",
                      f"{pct(r['styria_lo'])} to {pct(r['styria_hi'])}", f"{count(r['rest'])} of {count(r['rest_n'])}", pct(r["rest"] / r["rest_n"]) if r["rest_n"] else "–"] for r in reg])
    c2 = chart("c-regional", f"Does Styria mention the national top {len(reg)} skills differently?", a2,
               "".join(rrows) + axis(rtop, 0.1, pct_tick, "share of the region's ads mentioning the skill", max_labels=5),
               d["caveat_regional"], t2, legend_html=legend([("m-hl", f"Styria (n = {count(sty_n)}, tentative)"),
                                                            ("m-base", f"Rest of Austria (n = {count(reg[0]['rest_n']) if reg else '–'})")]))

    stacks = d["stacks"][:spec.TOP_STACKS]
    ktop = nice_max(max(s["count"] for s in stacks), 20)
    krows = [row(s["stack"], track(ktop, 20, bar(s["count"], ktop, "m-base")), f"{count(s['count'])} · {pct(s['count'] / s['n'])}",
                 f"{s['stack']}: {count(s['count'])} of {count(s['n'])} ads ({pct(s['count'] / s['n'])})", cls="long") for s in stacks]
    a3 = (f"The most frequent combination is {esc(stack0['stack'])}: {count(stack0['count'])} of {count(stack0['n'])} ads "
          f"({pct(stack0['count'] / stack0['n'])}).") if stack0 else ""
    t3 = data_table("Three-skill combinations named together in one ad (T06b).", ["Stack", "Ads", "Share"],
                    [[s["stack"], count(s["count"]), pct(s["count"] / s["n"])] for s in d["stacks"]])
    c3 = chart("c-stacks", f"Which {len(stacks)} three-skill stacks appear together most often?", a3,
               "".join(krows) + axis(ktop, 20, count_tick, "ads naming all three skills (T06b)", long=True), d["caveat_stacks"], t3, wide=True)
    return f'<div class="kpis">{kpis}</div><div class="grid">{c1}{c2}{c3}</div>'


def floor_rows(rows: list[dict], top: float, focus: str | None = None) -> str:
    out = []
    for r in rows:
        fill = "m-small" if r["small"] else ("m-hl" if r["label"] == focus else "m-range")
        marks = (f'<rect class="{fill}" x="{x(r["p25"], top)}" y="6" width="{round(x(r["p75"], top) - x(r["p25"], top), 1)}" height="12"/>'
                 + tick_mark(r["median"], top, "tk"))
        tip = (f"{r['label']}: median advertised floor {eur(r['median'])} (interquartile {eur(r['p25'])} to {eur(r['p75'])}) "
               f"on {count(r['n'])} ads with a figure" + (f"; below n = {spec.MIN_N}: indicative" if r["small"] else ""))
        out.append(row(r["label"], track(top, 10000, marks), f"{eur(r['median'])} · n = {count(r['n'])}", tip,
                       flag=f"n < {spec.MIN_N}" if r["small"] else "", cls="focus" if r["label"] == focus else ""))
    return "".join(out)


def floor_table(caption: str, first: str, rows: list[dict]) -> str:
    return data_table(caption, [first, "Ads with a figure", "P25", "Median", "P75"],
                      [[r["label"], count(r["n"]), eur(r["p25"]), eur(r["median"]), eur(r["p75"])] for r in rows])


def page_pay(d: dict, meta: dict) -> str:
    cov, core = d["coverage"], d["core"]
    fig, mono, rng = cov.get("with_salary_figure", 0), cov.get("minimum_only_figures", 0), cov.get("with_range", 0)
    kpis = (kpi("Ads stating a pay figure", count(fig), f"of {count(core)} core ads ({pct(fig / core)})", True)
            + kpi("Single collective-agreement minimum", count(mono), f"of {count(fig)} figures ({pct(mono / fig)}); a legal floor")
            + kpi("Ads stating a range", count(rng), f"of {count(fig)} figures; the rest name one number"))
    allrows = d["families"] + d["seniority"] + d["states"]
    top = nice_max(max(r["p75"] for r in allrows), 10000)
    unit = "advertised annual gross minimum (monthly figure × 14), bar = interquartile range, tick = median"
    fam = d["families"]
    big = [r for r in fam if not r["small"]]
    a1 = (f"Among families with at least {spec.MIN_N} figures, the median advertised floor runs from {eur(big[-1]['median'])} "
          f"({esc(big[-1]['label'])}) to {eur(big[0]['median'])} ({esc(big[0]['label'])}); the interquartile ranges overlap.") if big else ""
    c1 = chart("c-floor-family", "What floor does each role family advertise?", a1,
               floor_rows(fam, top) + axis(top, 10000, eur_tick, unit, max_labels=5), d["caveat_family"],
               floor_table("Advertised annual minimum by role family (T09b).", "Role family", fam),
               legend_html=legend([("m-range", "interquartile range (P25 to P75)"), ("tk", "median"), ("m-small", f"n < {spec.MIN_N}: indicative")]))
    sen = d["seniority"]
    lo, hi = min(sen, key=lambda r: r["median"]), max(sen, key=lambda r: r["median"])
    a2 = (f"{esc(hi['label'])} ads state a median floor of {eur(hi['median'])} against {eur(lo['median'])} for "
          f"{esc(lo['label'].lower())} ads (n = {count(lo['n'])}{', indicative' if lo['small'] else ''}).") if sen else ""
    c2 = chart("c-floor-seniority", "How does the floor move with the seniority word in the title?", a2,
               floor_rows(sen, top) + axis(top, 10000, eur_tick, unit, max_labels=5), d["caveat_seniority"],
               floor_table("Advertised annual minimum by seniority word (T09b).", "Seniority", sen))
    st = d["states"]
    foc = next((r for r in st if r["label"] == FOCUS_STATE), None)
    lead = max(st, key=lambda r: r["n"]) if st else None
    a3 = (f"<mark>{esc(FOCUS_STATE)}</mark> advertises a median floor of {eur(foc['median'])} on {count(foc['n'])} figures; "
          f"{esc(lead['label'])}, the largest market, {eur(lead['median'])} on {count(lead['n'])}.") if foc and lead else ""
    read3 = PREMIUM_CAVEAT
    c3 = chart("c-floor-state", "Does the advertised floor differ by state?", a3,
               floor_rows(st, top, FOCUS_STATE) + axis(top, 10000, eur_tick, unit), read3,
               floor_table("Advertised annual minimum by primary state (T09b).", "State", st), wide=True)
    return f'<div class="kpis">{kpis}</div><div class="grid">{c1}{c2}{c3}</div>'


def ordinal(k: int) -> str:
    return f"{k}{'th' if 10 <= k % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(k % 10, 'th')}"


def page_supply(d: dict, meta: dict) -> str:
    caps = d["capabilities"][:spec.TOP_CAPABILITIES]
    supply_n, core = d["supply_n"], d["core"]
    scored = [m for m in d["matrix"] if m["score"] == m["score"]]
    robust = sum(1 for m in d["matrix"] if m["robust"])
    kpis = (kpi("Families meeting the robustness rule", count(robust),
                f"of {count(len(scored))} scored families; top 3 under all four weightings and n ≥ {spec.MIN_N} in Austria and Styria", True)
            + kpi("Demand side: core ads", count(core), f"snapshot {esc(meta['demand_vintage'])}")
            + kpi("Supply side: GitHub accounts", count(supply_n), f"Austrian accounts with a data signal, <span class=nw>{esc(meta['supply_vintage'])}</span>"))
    top = nice_max(max(max(c["demand"], c["project"]) for c in caps), 0.1)
    rows = []
    for c in caps:
        marks = bar(c["demand"], top, "m-base", 2, 9) + bar(c["project"], top, "m-hl", 13, 9)
        tip = (f"{c['capability']}: mentioned in {pct(c['demand'])} of {count(c['demand_n'])} ads; shown in a project by "
               f"{pct(c['project'])} of {count(c['supply_n'])} accounts")
        rows.append(row(c["capability"], track(top, 0.1, marks), f"{pct(c['demand'])} / {pct(c['project'])}", tip))
    gaps = sorted(caps, key=lambda c: (-(c["demand"] - c["project"]), c["capability"]))[:3]
    a1 = ("Among the technical capabilities DS10 marks as observable on GitHub, the widest gaps between ads and projects are "
          + join_words([f"{esc(c['capability'])} ({pct(c['demand'])} of ads vs {pct(c['project'])} of accounts)" for c in gaps]) + ".") if gaps else ""
    t1 = data_table("Share of ads mentioning each capability and share of observed accounts showing it in a project (DS10), all rows.",
                    ["Capability", "Group", "GitHub can see it", "Ads", "Projects"],
                    [[c["capability"], c["group"], c["observability"], pct(c["demand"]), pct(c["project"])] for c in d["all_capabilities"]], 3)
    c1 = chart("c-caps", f"Which demanded capabilities do public projects rarely show? (top {len(caps)} technical, by demand)", a1,
               "".join(rows) + axis(top, 0.1, pct_tick, "share of ads (grey) and share of accounts with project evidence (accent)"),
               CAPABILITY_CAVEAT, t1, legend_html=legend([("m-base", f"ads mentioning it (n = {count(core)})"),
                                                         ("m-hl", f"accounts showing it in a project (n = {count(supply_n)})")]), wide=True)

    mtop = nice_max(max(m["score"] for m in scored), 0.1) if scored else 1.0
    mrows = []
    for m in d["matrix"]:
        if m["score"] != m["score"]:
            mrows.append(row(m["label"], track(mtop, 0.1, ""), "not scored",
                             f"{m['label']}: not scored, {count(m['postings'])} ads in Austria (below n = {spec.MIN_N})", flag=f"n < {spec.MIN_N}"))
            continue
        cls = "m-hl" if m["rank"] == 1 else "m-base"
        tip = (f"{m['label']}: score {fmt_value(m['score'], 'number', 'f2')}, rank {int(m['rank'])} under the default weights; "
               f"{count(m['postings'])} ads in Austria, {count(m['styria'])} in Styria"
               + ("; D01 small-sample flag (fewer than 30 ads in Austria or 10 in Styria)" if m["small"] else ""))
        mrows.append(row(m["label"], track(mtop, 0.1, bar(m["score"], mtop, cls)), f"{fmt_value(m['score'], 'number', 'f2')} · #{int(m['rank'])}",
                         tip, flag="small sample" if m["small"] else ""))
    first = scored[0] if scored else None
    a2 = (f"{esc(first['label'])} scores highest under the default weights ({fmt_value(first['score'], 'number', 'f2')}); "
          f"{count(robust)} families meet the robustness rule, because no Styrian family count reaches {spec.MIN_N}.") if first else ""
    t2 = data_table("Decision-matrix score under the default weights (D01).", ["Role family", "Score", "Rank", "Ads Austria", "Ads Styria"],
                    [[m["label"], fmt_value(m["score"], "number", "f2") if m["score"] == m["score"] else "not scored",
                      str(int(m["rank"])) if m["rank"] == m["rank"] else "–", count(m["postings"]), count(m["styria"])] for m in d["matrix"]])
    c2 = chart("c-matrix", "Which role family does the decision matrix put first?", a2,
               "".join(mrows) + axis(mtop, 0.1, lambda t: fmt_value(t, "number", "f1"), "weighted score, 0 to 1 (docs/decision-framework.md)"),
               (d["caveat_matrix"] + " " + MATRIX_NOTE).strip(), t2)

    sens = d["sensitivity"]
    top3 = {w: {s["label"] for s in sens if s["ranks"][w] <= 3} for w, _ in WEIGHTINGS}
    always = sorted(set.intersection(*top3.values()), key=lambda lab: next(s["ranks"]["default"] for s in sens if s["label"] == lab)) if sens else []
    moving = sorted(set.union(*top3.values()) - set(always)) if sens else []
    a3 = (f"{esc(join_words(always))} stay in the top three under all four weightings"
          + (f"; the remaining place moves between {esc(join_words(moving))}." if moving else ".")) if always else ""
    head = "".join(f'<th scope="col" class="num">{esc(lab)}</th>' for _, lab in WEIGHTINGS)
    body = []
    for s in sens:
        cells = "".join(f'<td class="num{" in3" if s["ranks"][w] <= 3 else ""}">{ordinal(s["ranks"][w])}</td>' for w, _ in WEIGHTINGS)
        body.append(f'<tr><th scope="row">{esc(s["label"])}</th>{cells}</tr>')
    rank_table = (f'<div class="scroll"><table class="ranks"><caption>Rank of each scored family under the four weightings (D02); '
                  f'a shaded cell is a top-three place.</caption><thead><tr><th scope="col">Role family</th>{head}</tr></thead>'
                  f'<tbody>{"".join(body)}</tbody></table></div>')
    c3 = (f'<figure class="card chart" id="c-sens" aria-labelledby="c-sens-t"><h3 id="c-sens-t">Does the ranking survive other weightings?</h3>'
          f'<p class="answer">{a3}</p>{rank_table}'
          f'<p class="readwith"><strong>Read with:</strong> {esc(d["caveat_sens"])}</p></figure>')
    return f'<div class="kpis">{kpis}</div><div class="grid">{c1}{c2}{c3}</div>'


def page_quality(d: dict, meta: dict) -> str:
    ov = d["overall"]
    srcs = d["sources"]
    core = d["funnel"][-1][1]
    kpis = (kpi("Strict title precision after the audit", pct(ov["after"]) if ov else "–",
                f"lenient {pct(ov['lenient_after'])}; {count(ov['n'])} hand-labelled titles; recall not measured" if ov else "", True)
            + kpi("Core ads seen on two or more sources", count(d["multi_source"]),
                  f"of {count(d['core_groups'])} ({pct(d['multi_source'] / d['core_groups'])}); the boards are largely disjoint")
            + kpi("Sources collected", count(len(srcs)), "StepStone.at, Indeed.at, hokify and Glassdoor were blocked and are missing"))
    fmax = nice_max(d["funnel"][0][1], 2000)
    frows = [row(lab, track(fmax, 2000, bar(v, fmax, "m-hl" if i == len(d["funnel"]) - 1 else "m-base")), count(v), f"{lab}: {count(v)}")
             for i, (lab, v) in enumerate(d["funnel"])]
    (l0, v0), (l1, v1), (l2, v2) = d["funnel"]
    a1 = (f"{count(v0)} raw rows de-duplicate to {count(v1)} unique postings, of which <mark>{count(v2)}</mark> carry a core "
          f"data-role title: the denominator behind almost every share in this dashboard.")
    t1 = data_table("Population funnel (market_summary.json); each step is a subset of the one above.", ["Step", "Rows"],
                    [[lab, count(v)] for lab, v in d["funnel"]])
    c1 = chart("c-funnel", "How do raw rows become the analysis set?", a1,
               "".join(frows) + axis(fmax, 2000, count_tick, "rows; bars are nested subsets, never add them", max_labels=4), d["caveat_funnel"], t1)

    smax = nice_max(max(s["core"] for s in srcs), 50)
    srows = [row(s["label"], track(smax, 50, bar(s["core"], smax, "m-base")),
                 f"{count(s['core'])} · {fmt_value(s['age'], 'days', 'int')}{NBSP}d",
                 f"{s['label']}: {count(s['core'])} of {count(core)} core ads; {count(s['rows'])} raw rows; median posting age "
                 f"{fmt_value(s['age'], 'days', 'int')} days") for s in srcs]
    young, old = min(srcs, key=lambda s: s["age"]), max(srcs, key=lambda s: s["age"])
    a2 = (f"{esc(srcs[0]['label'])} carries {count(srcs[0]['core'])} of {count(core)} core ads and {esc(srcs[1]['label'])} "
          f"{count(srcs[1]['core'])}; the median posting age runs from {fmt_value(young['age'], 'days', 'int')} days "
          f"({esc(young['label'])}) to {fmt_value(old['age'], 'days', 'int')} days ({esc(old['label'])}).")
    t2 = data_table("Core ads, raw rows and median posting age by source (T01, T13b).", ["Source", "Core ads", "Raw rows", "Median age (days)"],
                    [[s["label"], count(s["core"]), count(s["rows"]), fmt_value(s["age"], "days", "int")] for s in srcs])
    c2 = chart("c-sources", "Which sources carry the core ads, and how old are their ads?", a2,
               "".join(srows) + axis(smax, 50, count_tick, "core ads by source · value label: ads · median posting age in days"),
               d["caveat_sources"], t2)

    prec = d["precision"]
    prows = []
    for p in prec:
        a, b = x(p["before"], 1.0), x(p["after"], 1.0)
        marks = (f'<line class="cn" x1="{min(a, b)}" x2="{max(a, b)}" y1="12" y2="12"/>' + tick_mark(p["before"], 1.0, "tk-mid")
                 + tick_mark(p["after"], 1.0, "tk-hl"))
        tip = (f"{p['label']}: strict precision {pct(p['before'])} before (on {count(p['n'])} hand-labelled titles) and "
               f"{pct(p['after'])} after the audit (on the {count(p['kept'])} titles the revised rules keep)")
        prows.append(row(p["label"], track(1.0, 0.25, marks), f"{pct(p['before'])} → {pct(p['after'])} · n = {count(p['n'])}/{count(p['kept'])}", tip))
    worst = min(prec, key=lambda p: p["after"]) if prec else None
    best = max(prec, key=lambda p: (p["after"], -p["kept"])) if prec else None
    thin = (f" The top value rests on {count(best['kept'])} title{'s' if best['kept'] != 1 else ''} ({esc(best['label'])})."
            if best and best["kept"] == min(p["kept"] for p in prec) else "")
    a3 = (f"After the audit, strict precision runs from {pct(worst['after'])} ({esc(worst['label'])}) to {pct(best['after'])}; "
          f"overall {pct(ov['after'])} strict and {pct(ov['lenient_after'])} lenient on {count(ov['n'])} titles.{thin}") if worst and ov else ""
    t3 = data_table("Strict title precision before and after the D-012 audit (Q03c).", ["Role family", "Titles sampled", "Kept after", "Before", "After", "Lenient after"],
                    [[p["label"], count(p["n"]), count(p["kept"]), pct(p["before"]), pct(p["after"]), pct(p["lenient_after"])] for p in prec])
    c3 = chart("c-precision", "How often is a role label right? (hand-labelled title audit)", a3,
               "".join(prows) + axis(1.0, 0.25, pct_tick, "strict precision: share of titles that belong in the family · value label n = sampled/kept"),
               d["caveat_precision"], t3, wide=True,
               legend_html=legend([("tk-mid", "before the audit"), ("tk-hl", "after the audit")]))
    return f'<div class="kpis">{kpis}</div><div class="grid">{c1}{c2}{c3}</div>'


PAGE_BUILDERS = [page_market, page_skills, page_pay, page_supply, page_quality]


# ------------------------------------------------------------------------------------------------ document
CSS = """
:root{color-scheme:light dark;--surface:#E4E6EA;--surface-2:#DCDEE2;--surface-3:#D4D6DA;--ink:#26282C;--ink-2:#5A5C61;--mid:#9EA0A5;
--rule:#C2C4CA;--hl:#2F4BE0;--hl-8:#D0DEFF;--on-hl:#FFFFFF;--range:#9EA0A5}
@media (prefers-color-scheme:dark){:root{--surface:#191A1D;--surface-2:#2C2D30;--surface-3:#484A4D;--ink:#F3F5F9;--ink-2:#CED0D4;
--mid:#7E8084;--rule:#393A3D;--hl:#7C93FF;--hl-8:#2C2D30;--on-hl:#1A1A1A;--range:#7E8084}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--surface);color:var(--ink);font:400 15px/1.6 -apple-system,"Segoe UI",Inter,Roboto,sans-serif}
a{color:var(--ink);text-decoration-color:var(--hl);text-underline-offset:3px}
a:focus-visible,button:focus-visible,.row:focus-visible,summary:focus-visible{outline:2px solid var(--hl);outline-offset:2px}
.wrap{max-width:1320px;margin:0 auto;padding:0 64px}
header.top{padding:32px 0 8px;border-bottom:1px solid var(--ink)}
.eyebrow{margin:0;font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--ink-2)}
h1{margin:4px 0 4px;font-size:31px;line-height:1.2;font-weight:700}
.lede{margin:0 0 12px;max-width:72ch;color:var(--ink-2)}
.tabs{display:flex;flex-wrap:wrap;gap:0;margin:0;padding:0;border-bottom:1px solid var(--rule)}
.tabs button{appearance:none;border:0;border-bottom:3px solid transparent;background:none;color:var(--ink-2);font:600 14px/1.3 inherit;
font-family:inherit;padding:12px 14px 9px;cursor:pointer;min-height:44px}
.tabs button[aria-selected=true]{color:var(--ink);border-bottom-color:var(--hl)}
.tabs button:hover{color:var(--ink)}
section.page{padding:24px 0 8px}
section.page>h2{margin:0;font-size:24px;line-height:1.25;font-weight:700}
.subtitle{margin:4px 0 20px;color:var(--ink-2);font-size:16px;max-width:80ch}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;border-top:1px solid var(--ink);padding-top:16px;margin-bottom:24px}
.kpi{min-width:0}
.kl{margin:0;font-size:13px;color:var(--ink-2);font-weight:600}
.kv{margin:2px 0;font-size:36px;line-height:1.05;font-weight:700;overflow-wrap:anywhere}
.kpi.accent .kv{border-left:4px solid var(--hl);padding-left:10px}
.kn{margin:0;font-size:13px;color:var(--ink-2)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}
.card{margin:0;background:var(--surface-2);padding:20px 20px 16px;min-width:0}
.card.wide{grid-column:1/-1}
.card h3{margin:0 0 4px;font-size:17px;line-height:1.3;font-weight:700}
.answer{margin:0 0 12px;font-size:14px}
mark{background:none;color:var(--ink);font-weight:700;border-bottom:3px solid var(--hl)}
.legend{list-style:none;margin:0 0 10px;padding:0;display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13px;color:var(--ink-2)}
.legend li{display:flex;align-items:center;gap:6px}
.key{display:inline-block;width:14px;height:10px}
.key.m-base{background:var(--ink-2)}.key.m-hl{background:var(--hl)}.key.m-range{background:var(--range)}
.key.m-small{background:repeating-linear-gradient(135deg,var(--ink-2) 0 2px,var(--surface-2) 2px 5px)}
.key.tk,.key.tk-hl,.key.tk-mid{width:3px;height:14px}.key.tk{background:var(--ink)}.key.tk-hl{background:var(--hl)}.key.tk-mid{background:var(--ink-2)}
.plot{margin:0;font-size:13px}
.row{display:grid;grid-template-columns:minmax(120px,30%) minmax(0,1fr) var(--valw,8ch);align-items:center;column-gap:10px;min-height:28px;padding:2px 0}
.row.long,.axis.long{grid-template-columns:minmax(150px,46%) minmax(0,1fr) var(--valw,8ch)}
.row:hover .lab,.row:focus .lab{color:var(--ink)}
.row:hover,.row:focus{background:var(--surface-3)}
.lab{font-size:13px;line-height:1.25;color:var(--ink);overflow-wrap:anywhere}
.row.focus .lab{font-weight:700}
.flag{display:inline-block;margin-left:4px;font-size:12px;color:var(--ink-2);border:1px solid var(--ink-2);padding:0 4px;line-height:1.35;white-space:nowrap}
.bar{display:block;height:24px;min-width:0}
.trk{display:block;width:100%;height:24px;overflow:visible}
.val{font-size:13px;font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--ink);text-align:right}
.gl{stroke:var(--rule);stroke-width:1px;vector-effect:non-scaling-stroke}
.m-base{fill:var(--ink-2)}.m-hl{fill:var(--hl)}.m-range{fill:var(--range)}.m-small{fill:url(#hatch)}
.wh{stroke:var(--ink);stroke-width:1.5px;vector-effect:non-scaling-stroke}
.tk{stroke:var(--ink);stroke-width:3px;vector-effect:non-scaling-stroke}
.tk-hl{stroke:var(--hl);stroke-width:3px;vector-effect:non-scaling-stroke}
.tk-mid{stroke:var(--ink-2);stroke-width:3px;vector-effect:non-scaling-stroke}
.cn{stroke:var(--mid);stroke-width:2px;vector-effect:non-scaling-stroke}
.axis{display:grid;grid-template-columns:minmax(120px,30%) minmax(0,1fr) var(--valw,8ch);column-gap:10px;border-top:1px solid var(--mid);margin-top:2px}
.ticks{position:relative;height:20px;font-size:12px;color:var(--ink-2);font-variant-numeric:tabular-nums}
.ticks span{position:absolute;top:2px;transform:translateX(-50%);white-space:nowrap}
.ticks span:first-child{transform:none}.ticks span.end{transform:translateX(-100%)}
.unit{margin:2px 0 0;font-size:12px;color:var(--ink-2);text-align:right}
.readwith{margin:12px 0 0;font-size:13px;color:var(--ink-2)}
.readwith strong{color:var(--ink)}
details.tbl{margin-top:10px;font-size:13px}
details.tbl summary{cursor:pointer;color:var(--ink);font-weight:600;min-height:28px}
.scroll{overflow-x:auto;max-width:100%}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:6px}
caption{text-align:left;color:var(--ink-2);padding-bottom:4px}
th,td{padding:4px 8px;border-bottom:1px solid var(--rule);text-align:left;vertical-align:top}
thead th{border-bottom:1px solid var(--ink);font-weight:700}
.num{text-align:right;font-variant-numeric:tabular-nums}
table.ranks td.in3{background:var(--hl-8);font-weight:700}
@media (prefers-color-scheme:dark){table.ranks td.in3{background:var(--surface-3)}}
.pagefoot{margin:20px 0 8px;padding-top:10px;border-top:1px solid var(--ink);font-size:13px;color:var(--ink-2)}
.pagefoot p{margin:0 0 4px}
.pagefoot code{font-size:12px;overflow-wrap:anywhere}
code{overflow-wrap:anywhere}
.nw{white-space:nowrap}
footer.site{padding:12px 0 40px;font-size:13px;color:var(--ink-2)}
#tip{position:fixed;z-index:10;max-width:320px;padding:8px 10px;background:var(--ink);color:var(--surface);font-size:13px;line-height:1.4;pointer-events:none;display:none}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
@media (max-width:900px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:minmax(0,1fr)}}
@media (max-width:600px){.wrap{padding:0 16px}h1{font-size:24px}section.page>h2{font-size:20px}.kv{font-size:28px}
.card{padding:14px 12px 12px}
.row,.row.long{grid-template-columns:minmax(0,1fr) auto;grid-template-areas:"lab val" "bar bar";row-gap:2px;padding-top:4px}
.row .lab{grid-area:lab}.row .val{grid-area:val}.row .bar{grid-area:bar}
.axis,.axis.long{grid-template-columns:minmax(0,1fr)}.axis>span:first-child,.axis>span:last-child{display:none}
.tabs button{padding:10px 10px 7px;font-size:13px}}
@media (forced-colors:active){.m-base,.m-hl,.m-range,.m-small{fill:CanvasText}.key{forced-color-adjust:none}}
@media print{.tabs{display:none}section.page[hidden]{display:block}details.tbl{display:none}}
"""

JS = """
(function(){
var tabs=[].slice.call(document.querySelectorAll('[role=tab]'));
var pages=tabs.map(function(t){return document.getElementById(t.getAttribute('aria-controls'));});
function show(i,focus){tabs.forEach(function(t,k){var on=k===i;t.setAttribute('aria-selected',on?'true':'false');
t.tabIndex=on?0:-1;pages[k].hidden=!on;});if(focus){tabs[i].focus();}
var id=pages[i].id;if(location.hash!=='#'+id){history.replaceState(null,'','#'+id);}}
tabs.forEach(function(t,i){t.addEventListener('click',function(){show(i,false);});
t.addEventListener('keydown',function(e){var k=null;if(e.key==='ArrowRight'){k=(i+1)%tabs.length;}
else if(e.key==='ArrowLeft'){k=(i-1+tabs.length)%tabs.length;}else if(e.key==='Home'){k=0;}else if(e.key==='End'){k=tabs.length-1;}
if(k!==null){e.preventDefault();show(k,true);}});});
function fromHash(){var h=location.hash.slice(1);var i=pages.findIndex(function(p){return p.id===h;});show(i<0?0:i,false);}
window.addEventListener('hashchange',fromHash);fromHash();
var tip=document.getElementById('tip');
function place(el,cx,cy){tip.textContent=el.getAttribute('data-tip');tip.style.display='block';
var w=tip.offsetWidth,h=tip.offsetHeight,vw=window.innerWidth;var l=Math.min(Math.max(8,cx+12),vw-w-8);var t=cy-h-12;if(t<8){t=cy+16;}
tip.style.left=l+'px';tip.style.top=t+'px';}
function hide(){tip.style.display='none';}
[].slice.call(document.querySelectorAll('[data-tip]')).forEach(function(el){
el.addEventListener('mousemove',function(e){place(el,e.clientX,e.clientY);});el.addEventListener('mouseleave',hide);
el.addEventListener('focus',function(){var r=el.getBoundingClientRect();place(el,r.left+r.width/2,r.top);});el.addEventListener('blur',hide);});
document.addEventListener('keydown',function(e){if(e.key==='Escape'){hide();}});
})();
"""


def _clean(o):
    """JSON-safe copy: NaN (an empty cell, e.g. an unscored family) becomes null."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, float) and o != o:
        return None
    return o


def render(data: dict) -> str:
    meta = data["meta"]
    keys = ["p1", "p2", "p3", "p4", "p5"]
    tabs, sections = [], []
    for i, (page, builder, key) in enumerate(zip(spec.PAGES, PAGE_BUILDERS, keys)):
        pid = page["name"]
        tabs.append(f'<button role="tab" id="tab-{pid}" aria-controls="{pid}" aria-selected="{"true" if i == 0 else "false"}"'
                    f' tabindex="{0 if i == 0 else -1}">{i + 1} · {esc(page["nav"])}</button>')
        sources = ", ".join(f"<code>outputs/{'tables/' + t + '.csv' if not t.endswith('.json') else t}</code>" for t in page["tables"])
        foot = (f'<footer class="pagefoot"><p><strong>Sources:</strong> {sources}. Tag: <code>{esc(page["tag"])}</code>.</p>'
                f'<p>Demand snapshot {esc(meta["demand_vintage"])} (one day of open ads; stale after {esc(meta["stale_after"])}); '
                f'supply snapshot {esc(meta["supply_vintage"])}. A share is the share of ads that <em>mention</em> an item, never a '
                f'requirement; a posting is not a vacancy or a hire; no statement here is causal. '
                f'Limitations: <a href="../../docs/limitations.md">docs/limitations.md</a>.</p></footer>')
        sections.append(f'<section class="page" id="{pid}" role="tabpanel" aria-labelledby="tab-{pid}">'
                        f'<h2>{esc(page["title"])}</h2><p class="subtitle" lang="de">{esc(page["subtitle_de"])}</p>'
                        f'{builder(data[key], meta)}{foot}</section>')
    payload = json.dumps(_clean(data), ensure_ascii=False, sort_keys=True, allow_nan=False, default=str,
                         separators=(",", ":")).replace("</", "<\\/")
    hatch = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>'
             '<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             '<rect width="6" height="6" style="fill:var(--surface-2)"/><rect width="2.4" height="6" style="fill:var(--ink-2)"/>'
             '</pattern></defs></svg>')
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{esc(meta['title'])} · Dashboard</title>\n"
            f"<meta name=\"description\" content=\"Five-page dashboard of Austrian data-role job ads (snapshot {esc(meta['demand_vintage'])}): "
            "market, skills, advertised pay floors, demand vs supply, data quality.\">\n"
            f"<style>{CSS.strip()}</style>\n</head>\n<body>\n{hatch}\n"
            f'<div class="wrap"><header class="top"><p class="eyebrow">Dashboard · HTML twin of the Power BI report dashboards/JobMarket.pbip</p>'
            f'<h1>{esc(meta["title"])}</h1><p class="lede">Open data-role job ads in Austria on {esc(meta["demand_vintage"])}, '
            f"with a Styria focus, against public GitHub evidence of the same skills. Every number is read from the repository's "
            f"<code>outputs/</code> when this page is built.</p></header>\n"
            f'<nav aria-label="Dashboard pages"><div class="tabs" role="tablist" aria-label="Dashboard pages">{"".join(tabs)}</div></nav>\n'
            f'<main>{"".join(sections)}</main>\n'
            '<footer class="site"><p>Generated by <code>src/reporting/dashboard_html.py</code> from the committed outputs; '
            'the Power BI project in <code>dashboards/</code> loads the same files. Documents and aggregated outputs: CC BY 4.0. '
            'Method: <a href="../../docs/methodology.md">docs/methodology.md</a> · decision framework: '
            '<a href="../../docs/decision-framework.md">docs/decision-framework.md</a> · '
            '<a href="../README.md">dashboards/README.md</a>.</p></footer></div>\n'
            '<div id="tip" role="status" aria-live="polite"></div>\n'
            f'<script type="application/json" id="dashboard-data">{payload}</script>\n'
            f"<script>{JS.strip()}</script>\n</body>\n</html>\n")


def build(root: Path = ROOT) -> str:
    return render(build_data(root))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write the static HTML twin of the dashboard.")
    ap.add_argument("--root", type=Path, default=ROOT, help="repository root to read outputs/ from")
    ap.add_argument("--out", type=Path, default=None, help="output file (default <root>/dashboards/html/index.html)")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if the file differs from a fresh build")
    args = ap.parse_args(argv)
    out = args.out or (args.root / OUT)
    text = build(args.root)
    if args.check:
        current = out.read_text(encoding="utf-8") if out.exists() else None
        if current != text:
            print(f"dashboard_html: {out} is stale or missing; run python src/reporting/dashboard_html.py")
            return 1
        print(f"dashboard_html: {out} is up to date")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(out)
    print(f"dashboard_html: wrote {out} ({len(text.encode('utf-8')):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
