"""Dashboards (dashboards/JobMarket.* Power BI project and dashboards/html/index.html): integrity, provenance, determinism.

What these protect:
  * model <-> report integrity of the PBIP: every field a visual references (projections, sort, selectors) exists in the
    TMDL; every DAX reference in a measure resolves; every relationship endpoint exists; no measure shares a name with
    a column; every measure has a description, a display folder and (unless it returns text) a format string;
  * the model still fits the outputs it loads: every file a partition reads exists in outputs/, and every source column
    a partition types exists in that CSV's header, so a renamed table column fails here instead of at refresh time;
  * the report follows the page spec (src/reporting/dashboard_spec.py): page order, names, titles, one German subtitle
    per page, a provenance footer, alt text and a title on every data visual, a unique reading-order tab order;
  * the custom theme is registered and present; the report points at the semantic model by path;
  * the committed files are exactly what the generators write (no hand drift, deterministic output);
  * the HTML twin shows the source values (headline numbers read independently from outputs/), loads nothing from
    the network and carries the same pages and subtitles.

Schema validation against Microsoft's JSON schemas needs an offline schema copy and runs outside CI:
python src/reporting/validate_pbip.py --schemas <json-schemas root> (see dashboards/README.md).
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest

import dashboard_html as DH
import dashboard_pbip as DP
import dashboard_spec as spec
from metrics_registry import fmt_value

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboards"
MODEL = DASH / f"{spec.DASHBOARD_NAME}.SemanticModel" / "definition"
REPORT = DASH / f"{spec.DASHBOARD_NAME}.Report"
HTML = DASH / "html" / "index.html"
OUTPUTS = ROOT / "outputs"
# measures that return text (a label, a date as text or a reading note): no number format applies
TEXT_MEASURES = {"Demand Snapshot", "Supply Snapshot", "Market Caveat", "Family Sample Flag", "Top Stack", "Skills Caveat",
                 "Pay Sample Flag by Family", "Pay Sample Flag by Seniority", "Pay Sample Flag by State", "Pay Caveat",
                 "Supply Caveat", "Quality Caveat"}


# ------------------------------------------------------------------------------------------------ TMDL parsing
def unquote(name: str) -> str:
    name = name.strip()
    return name[1:-1].replace("''", "'") if name.startswith("'") and name.endswith("'") else name


def parse_tmdl() -> dict:
    """{table: {"columns": {name: props}, "measures": {name: {"expr", "props", "desc"}}, "partition": text}}"""
    model = {}
    for path in sorted((MODEL / "tables").glob("*.tmdl")):
        text = path.read_text(encoding="utf-8")
        table = unquote(re.search(r"^table (.+)$", text, re.M).group(1))
        cols, meas = {}, {}
        lines = text.splitlines()
        desc: list[str] = []
        current = None
        for i, line in enumerate(lines):
            if line.startswith("\t///"):
                desc.append(line[4:].strip())
                continue
            m_col = re.match(r"^\tcolumn (.+)$", line)
            m_mea = re.match(r"^\tmeasure ('[^']*(?:''[^']*)*'|\S+) =\s*(.*)$", line)
            if m_col:
                current = cols.setdefault(unquote(m_col.group(1)), {"props": [], "desc": " ".join(desc)})
            elif m_mea:
                expr = [m_mea.group(2)] if m_mea.group(2) else []
                j = i + 1
                while j < len(lines) and lines[j].startswith("\t\t\t"):
                    expr.append(lines[j].strip())
                    j += 1
                current = meas.setdefault(unquote(m_mea.group(1)), {"expr": "\n".join(expr), "props": [], "desc": " ".join(desc)})
            elif re.match(r"^\t\S", line):
                current = None
            elif current is not None and re.match(r"^\t\t[a-zA-Z]", line):
                current["props"].append(line.strip())
            if not line.startswith("\t///"):
                desc = []
        partition = text[text.index("\tpartition "):]
        model[table] = {"columns": cols, "measures": meas, "partition": partition}
    return model


@pytest.fixture(scope="module")
def model():
    return parse_tmdl()


def report_jsons() -> list[tuple[Path, dict]]:
    return [(p, json.loads(p.read_text(encoding="utf-8"))) for p in sorted(REPORT.rglob("*.json"))]


def field_refs(obj, out=None):
    """Every (kind, entity, property) a PBIR JSON tree references through SourceRef."""
    out = [] if out is None else out
    if isinstance(obj, dict):
        for kind in ("Measure", "Column"):
            node = obj.get(kind)
            if isinstance(node, dict) and "Property" in node and "SourceRef" in node.get("Expression", {}):
                out.append((kind, node["Expression"]["SourceRef"]["Entity"], node["Property"]))
        for v in obj.values():
            field_refs(v, out)
    elif isinstance(obj, list):
        for v in obj:
            field_refs(v, out)
    return out


def visuals_by_page() -> dict[str, list[dict]]:
    pages = {}
    for page in spec.page_names():
        pages[page] = [json.loads(p.read_text(encoding="utf-8"))
                       for p in sorted((REPORT / "definition" / "pages" / page / "visuals").glob("*/visual.json"))]
    return pages


def literal(value_node) -> str:
    return value_node["expr"]["Literal"]["Value"]


def textbox_text(v: dict) -> str:
    paras = v["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
    return " ".join(run["value"] for p in paras for run in p["textRuns"])


# ------------------------------------------------------------------------------------------------ PBIP: files and structure
def test_every_project_json_parses_without_bom():
    files = [p for p in DASH.rglob("*") if p.is_file() and (p.suffix in {".json", ".pbir", ".pbism", ".pbip"} or p.name == ".platform")]
    assert len(files) > 20
    for p in files:
        raw = p.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{p} starts with a BOM"
        json.loads(raw.decode("utf-8"))


def test_report_points_at_the_semantic_model_by_path():
    pbir = json.loads((REPORT / "definition.pbir").read_text(encoding="utf-8"))
    target = (REPORT / pbir["datasetReference"]["byPath"]["path"]).resolve()
    assert target.is_dir() and (target / "definition.pbism").exists()
    pbip = json.loads((DASH / f"{spec.DASHBOARD_NAME}.pbip").read_text(encoding="utf-8"))
    assert (DASH / pbip["artifacts"][0]["report"]["path"]).is_dir()


def test_theme_is_registered_and_present():
    rep = json.loads((REPORT / "definition" / "report.json").read_text(encoding="utf-8"))
    custom = rep["themeCollection"]["customTheme"]
    items = [i for pkg in rep["resourcePackages"] if pkg["type"] == "RegisteredResources" for i in pkg["items"]]
    theme_items = [i for i in items if i["type"] == "CustomTheme"]
    assert [i["name"] for i in theme_items] == [custom["name"]]
    theme_path = REPORT / "StaticResources" / "RegisteredResources" / theme_items[0]["path"]
    theme = json.loads(theme_path.read_text(encoding="utf-8"))
    assert theme["background"] and theme["foreground"] and len(theme["dataColors"]) >= 5


def test_every_visual_field_exists_in_the_model(model):
    missing = []
    for path, doc in report_jsons():
        for kind, entity, prop in field_refs(doc):
            table = model.get(entity)
            names = table and (table["measures"] if kind == "Measure" else table["columns"])
            if not names or prop not in names:
                missing.append(f"{path.relative_to(DASH).as_posix()}: {kind} {entity}[{prop}]")
    assert not missing, "visual references a field the TMDL does not define:\n" + "\n".join(missing)


def test_relationship_endpoints_exist_and_point_to_unique_keys(model):
    text = (MODEL / "relationships.tmdl").read_text(encoding="utf-8")
    pairs = re.findall(r"fromColumn: (.+)\n\ttoColumn: (.+)\n", text)
    assert pairs
    for frm, to in pairs:
        for ref in (frm, to):
            m = re.match(r"^('(?:[^']|'')+'|[^.]+)\.('(?:[^']|'')+'|.+)$", ref.strip())
            table, column = unquote(m.group(1)), unquote(m.group(2))
            assert table in model and column in model[table]["columns"], f"relationship endpoint {ref} does not exist"


DAX_COLUMN_RE = re.compile(r"('(?:[^']|'')+'|\b[A-Za-z_][A-Za-z0-9_]*)\[([^\]]+)\]")
DAX_MEASURE_RE = re.compile(r"(?<![\]'\w])\[([^\]]+)\]")


def test_every_dax_reference_resolves(model):
    measures = {m for t in model.values() for m in t["measures"]}
    problems = []
    for t in model.values():
        for name, m in t["measures"].items():
            expr = re.sub(r'"[^"]*"', '""', m["expr"])   # ignore text inside string literals
            for table, column in DAX_COLUMN_RE.findall(expr):
                table = unquote(table)
                if table not in model or column not in model[table]["columns"]:
                    problems.append(f"{name}: {table}[{column}]")
            for ref in DAX_MEASURE_RE.findall(DAX_COLUMN_RE.sub("", expr)):
                if ref not in measures:
                    problems.append(f"{name}: [{ref}] is not a measure")
    assert not problems, "\n".join(problems)


def test_measures_are_documented_formatted_and_unambiguous(model):
    columns = {c for t in model.values() for c in t["columns"]}
    seen = set()
    for t in model.values():
        for name, m in t["measures"].items():
            assert name not in seen, f"duplicate measure {name}"
            seen.add(name)
            assert name not in columns, f"measure {name} shares its name with a column"
            assert m["desc"], f"measure {name} has no /// description"
            assert any(p.startswith("displayFolder:") for p in m["props"]), f"measure {name} has no display folder"
            has_fmt = any(p.startswith("formatString:") for p in m["props"])
            assert has_fmt or name in TEXT_MEASURES, f"measure {name} has no format string"
    assert TEXT_MEASURES <= seen


def test_columns_follow_the_modelling_rules(model):
    for table, t in model.items():
        for name, c in t["columns"].items():
            props = dict(p.split(": ", 1) if ": " in p else (p, True) for p in c["props"])
            assert "dataType" in props and "summarizeBy" in props, f"{table}[{name}]"
            if name.endswith(("Key", "Order", "Rank")):
                assert props["summarizeBy"] == "none", f"{table}[{name}] is a key/order column and must not summarise"
            if "sortByColumn" in props:
                assert unquote(props["sortByColumn"]) in t["columns"]


def test_partitions_read_existing_outputs_and_existing_csv_columns(model):
    for table, t in model.items():
        part = t["partition"]
        assert "mode: import" in part
        if table == "Measures":
            continue
        assert "ExportsPath" in part, f"{table} does not read through the ExportsPath parameter"
        for f in re.findall(r'"tables\\\\?([A-Za-z0-9_]+)\.csv"', part):
            path = OUTPUTS / "tables" / f"{f}.csv"
            assert path.exists(), f"{table} reads {path}, which is not in outputs/tables"
            with open(path, encoding="utf-8", newline="") as h:
                header = set(next(csv.reader(h)))
            typed = re.search(r'Table\.TransformColumnTypes\(Promoted, \{(.*?)\}, "en-US"\)', part)
            if typed and f in part.split("Promoted")[0]:
                for col in re.findall(r'\{"([^"]+)", ', typed.group(1)):
                    assert col in header, f"{table}: column {col!r} is not in {f}.csv"
        for f in re.findall(r'ExportsPath & "([a-z_]+\.json)"', part):
            assert (OUTPUTS / f).exists(), f"{table} reads outputs/{f}, which does not exist"
    expr = (MODEL / "expressions.tmdl").read_text(encoding="utf-8")
    assert re.search(r"expression ExportsPath = .* meta \[IsParameterQuery=true, Type=\"Text\"", expr)


# ------------------------------------------------------------------------------------------------ PBIP: pages and accessibility
def test_pages_match_the_spec():
    meta = json.loads((REPORT / "definition" / "pages" / "pages.json").read_text(encoding="utf-8"))
    assert meta["pageOrder"] == spec.page_names()
    for i, page in enumerate(spec.PAGES):
        doc = json.loads((REPORT / "definition" / "pages" / page["name"] / "page.json").read_text(encoding="utf-8"))
        assert doc["name"] == page["name"] and doc["displayName"] == f"{i + 1} {page['nav']}"
        assert (doc["width"], doc["height"]) == (1280, 720)


def test_every_page_has_title_german_subtitle_and_provenance_footer():
    for page in spec.PAGES:
        texts = [textbox_text(v) for v in visuals_by_page()[page["name"]] if v["visual"]["visualType"] == "textbox"]
        assert page["title"] in texts
        assert page["subtitle_de"] in texts and re.search(r"[äöüßÄÖÜ]|\b(und|die|der|nach)\b", page["subtitle_de"])
        footers = [t for t in texts if t.startswith("Sources: ")]
        assert len(footers) == 1
        for table in page["tables"]:
            assert table in footers[0]


def test_alt_text_titles_and_tab_order():
    for page, visuals in visuals_by_page().items():
        orders = []
        for v in visuals:
            vco = v["visual"].get("visualContainerObjects", {})
            alt = literal(vco["general"][0]["properties"]["altText"]).strip("'")
            assert len(alt) > 10, f"{page}/{v['name']} has no meaningful alt text"
            if v["visual"]["visualType"] not in ("textbox", "card"):
                assert literal(vco["title"][0]["properties"]["text"]).strip("'"), f"{page}/{v['name']} has no title"
            orders.append(v["position"]["tabOrder"])
            x, y, w, h = (v["position"][k] for k in ("x", "y", "width", "height"))
            assert 0 <= x and x + w <= 1280 and 0 <= y and y + h <= 720, f"{page}/{v['name']} leaves the page"
        assert len(set(orders)) == len(orders) and min(orders) > 0
        first = max(visuals, key=lambda v: v["position"]["tabOrder"])
        assert first["name"].endswith("-title"), "the page title must receive focus first"


def test_committed_pbip_is_what_the_generator_writes():
    files = DP.project_files()
    stale = [rel for rel, text in files.items() if (DASH / rel).read_text(encoding="utf-8") != text]
    assert not stale, f"run python src/reporting/dashboard_pbip.py (or review Desktop edits): {stale}"
    committed = {p.relative_to(DASH).as_posix() for p in DASH.rglob("*") if p.is_file()
                 and p.relative_to(DASH).parts[0].startswith(spec.DASHBOARD_NAME) and ".pbi" not in p.parts}
    assert committed == set(files), f"files not written by the generator: {sorted(committed - set(files))}"


# ------------------------------------------------------------------------------------------------ HTML twin
@pytest.fixture(scope="module")
def html_text():
    return DH.build(ROOT)


def test_html_is_deterministic_and_committed(html_text):
    assert DH.build(ROOT) == html_text
    assert HTML.read_text(encoding="utf-8") == html_text, "run python src/reporting/dashboard_html.py"


def test_html_loads_nothing_from_the_network(html_text):
    assert "http://" not in html_text and "https://" not in html_text
    assert not re.search(r"<(script|link|img|iframe)[^>]+(src|href)=", html_text)
    assert "@import" not in html_text and "url(http" not in html_text


def test_html_has_the_spec_pages_with_german_subtitles(html_text):
    for page in spec.PAGES:
        assert f'<section class="page" id="{page["name"]}"' in html_text
        assert f'<p class="subtitle" lang="de">{DH.esc(page["subtitle_de"])}</p>' in html_text
    assert html_text.count('role="tab"') == len(spec.PAGES)
    # every chart has a data table and every mark row a tooltip
    assert html_text.count('<details class="tbl">') >= 12
    assert html_text.count('role="listitem"') == html_text.count("data-tip=") and 'data-tip=""' not in html_text


def kpis(html_text: str, page: str) -> list[str]:
    section = html_text.split(f'id="{page}"', 1)[1].split("</section>", 1)[0]
    return re.findall(r'<p class="kv">([^<]*)</p>', section)


def rows(name: str) -> list[dict]:
    with open(OUTPUTS / "tables" / f"{name}.csv", encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))


def n(value) -> str:
    return fmt_value(float(value), "count", "int")


def test_html_headline_numbers_equal_the_source_files(html_text):
    counts = json.loads((OUTPUTS / "market_summary.json").read_text(encoding="utf-8"))["counts"]
    assert kpis(html_text, "p1-market-overview") == [n(counts["core_canonical"]), n(counts["canonical_groups_all"]),
                                                     n(counts["vienna_core_primary_state"]), n(counts["styria_core_primary_state"])]
    skills = rows("T05_skills_all_tech")
    styria_n = next(r["n"] for r in rows("T05_skills_all_tech_by_styria") if r["styria_flag"] == "Styria")
    assert kpis(html_text, "p2-skills-stacks")[:2] == [n(skills[0]["n"]), n(styria_n)]
    cov = {r["metric"]: r["count"] for r in rows("T09_salary_coverage")}
    assert kpis(html_text, "p3-pay-floors") == [n(cov["with_salary_figure"]), n(cov["minimum_only_figures"]), n(cov["with_range"])]
    robust = sum(r["robust_top3"] == "True" for r in rows("D01_decision_matrix"))
    supply_n = rows("DS10_demand_supply_capability_evidence")[0]["supply_n"]
    assert kpis(html_text, "p4-demand-supply") == [n(robust), n(counts["core_canonical"]), n(supply_n)]
    overall = next(r for r in rows("Q03c_precision_summary") if r["family"] == "ALL")
    q04 = {r["metric"]: r["value"] for r in rows("Q04_duplicates")}
    assert kpis(html_text, "p5-data-quality") == [fmt_value(float(overall["precision_after_strict"]), "share", "pct0").replace(" %", " %"),
                                                  n(q04["cross_source_groups_core"]), n(len(rows("T01_source_coverage")))]
    # a chart value: the share of the most-mentioned skill, recomputed from its counts
    top = max(skills, key=lambda r: int(r["count"]))
    share = fmt_value(int(top["count"]) / int(top["n"]), "share", "pct0").replace(" %", " %")
    assert f'<span class="lab">{DH.esc(top["skill"])}</span>' in html_text and f'<span class="val">{share}</span>' in html_text


def test_html_embeds_the_data_it_shows(html_text):
    payload = re.search(r'<script type="application/json" id="dashboard-data">(.*?)</script>', html_text, re.S).group(1)
    data = json.loads(payload.replace("<\\/", "</"))
    counts = json.loads((OUTPUTS / "market_summary.json").read_text(encoding="utf-8"))["counts"]
    assert data["p1"]["core"] == counts["core_canonical"]
    assert sum(f["count"] for f in data["p1"]["families"]) == counts["core_canonical"]
    assert sum(s["count"] for s in data["p1"]["states"]) == counts["core_canonical"]
