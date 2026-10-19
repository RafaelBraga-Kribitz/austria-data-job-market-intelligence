"""Marker renderer (src/reporting/render_docs.py): inner text follows the registry, everything else is left byte for byte."""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "reporting"))
import metrics_registry as mr  # noqa: E402
import render_docs as rd  # noqa: E402

METRICS = {
    "_meta": {"demand_vintage": "2026-09-16", "stale_after_demand": "2026-12-16", "week_id": "2026-W42", "run_date": "2026-10-18"},
    "core_n": {"value": 720, "display": "720", "unit": "count"},
    "vienna_share_core": {"value": 0.4764, "display": "48 %", "unit": "share"},
    "sql_share": {"value": 0.4047, "display": "40 %", "unit": "share"},
    "german_stated_share": {"value": 0.3964, "display": "40 %", "unit": "share"},
    "floor_analytics_eur": {"value": 47810.0, "display": "€47.8k", "unit": "eur"},
}


def m(key, inner, fmt=None):
    return f"<!--m:{key}{':' + fmt if fmt else ''}-->{inner}<!--/m-->"


# ---------------------------------------------------------------------------------------------------- rendering
def test_inner_text_is_replaced_by_the_registry_display():
    text = f"There are {m('core_n', '650')} core postings; Vienna holds {m('vienna_share_core', '10 %')}."
    new, stats = rd.render_text(text, METRICS)
    assert new == f"There are {m('core_n', '720')} core postings; Vienna holds {m('vienna_share_core', '48 %')}."
    assert stats["markers"] == 2 and len(stats["stale"]) == 2 and stats["errors"] == []


def test_same_literal_different_metrics_stay_separate():
    text = f"SQL {m('sql_share', '40 %')}; German stated in {m('german_stated_share', '40 %')}"
    METRICS2 = {**METRICS, "sql_share": {"value": 0.41, "display": "41 %", "unit": "share"}}
    new, _ = rd.render_text(text, METRICS2)
    assert new == f"SQL {m('sql_share', '41 %')}; German stated in {m('german_stated_share', '40 %')}"


def test_explicit_format_and_meta_keys_and_date_arithmetic():
    text = (f"{m('vienna_share_core', '48 %', 'pct1')} | {m('_meta.demand_vintage', 'x')} | {m('_meta.stale_after_demand', 'x')} | "
            f"{m('_meta.demand_vintage', 'x', '+91d')} | {m('_meta.stale_after_demand', 'x', 'ym')} | {m('_meta.stale_after_demand', 'x', 'dmon')} | "
            f"{m('floor_analytics_eur', 'x', 'eur_k0')}")
    new, stats = rd.render_text(text, METRICS)
    assert new == (f"{m('vienna_share_core', '47.6 %', 'pct1')} | {m('_meta.demand_vintage', '2026-09-16')} | {m('_meta.stale_after_demand', '2026-12-16')} | "
                   f"{m('_meta.demand_vintage', '2026-12-16', '+91d')} | {m('_meta.stale_after_demand', '2026-12', 'ym')} | {m('_meta.stale_after_demand', '16 Dec', 'dmon')} | "
                   f"{m('floor_analytics_eur', '€48k', 'eur_k0')}")
    assert stats["errors"] == []


def test_markers_work_inside_markdown_tables_and_emphasis():
    text = f"| Core | **{m('core_n', '1')}** | {m('vienna_share_core', '2 %')} |\n"
    new, stats = rd.render_text(text, METRICS)
    assert new == f"| Core | **{m('core_n', '720')}** | {m('vienna_share_core', '48 %')} |\n" and stats["errors"] == []


def test_rendering_is_idempotent():
    text = f"a {m('core_n', '1')} b {m('sql_share', '2 %', 'pct1')}\nc"
    once, _ = rd.render_text(text, METRICS)
    twice, stats = rd.render_text(once, METRICS)
    assert once == twice and stats["stale"] == []


def test_text_outside_markers_is_never_touched():
    text = "Intro 720 and 48 % stay as they are.\n" + m("core_n", "1") + "\n  trailing   spaces \t\n"
    new, _ = rd.render_text(text, METRICS)
    assert new.replace(m("core_n", "720"), m("core_n", "1")) == text


# ---------------------------------------------------------------------------------------------------- errors
def test_unknown_key_is_an_error():
    new, stats = rd.render_text(f"x {m('no_such_key', '1')}", METRICS)
    assert any("unknown metric key" in e for e in stats["errors"]) and "no_such_key" in new


def test_unknown_meta_key_and_unknown_format_are_errors():
    _, stats = rd.render_text(m("_meta.nope", "1") + m("core_n", "1", "pct9"), METRICS)
    assert len(stats["errors"]) == 2


def test_unterminated_or_multiline_marker_is_malformed():
    _, stats = rd.render_text("<!--m:core_n-->720 and no end", METRICS)
    assert any("malformed" in e for e in stats["errors"])
    _, stats = rd.render_text("<!--m:core_n-->7\n20<!--/m-->", METRICS)
    assert any("malformed" in e for e in stats["errors"])


def test_markers_in_code_are_documentation_not_markers():
    text = "Syntax: `<!--m:core_n-->720<!--/m-->` and\n```\n<!--m:no_such_key-->1<!--/m-->\n```\n"
    new, stats = rd.render_text(text, METRICS)
    assert new == text and stats["markers"] == 0 and stats["errors"] == []


# ---------------------------------------------------------------------------------------------------- files, exclude list, check mode
def write_tree(tmp_path: Path, files: dict[str, bytes | str], metrics=METRICS) -> Path:
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    (tmp_path / "outputs").mkdir(exist_ok=True)
    (tmp_path / "outputs" / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    return tmp_path


def run_main(root: Path, *args: str) -> int:
    return rd.main(["--root", str(root), *args])


def test_update_rewrites_stale_markers_and_check_detects_them(tmp_path, capsys):
    root = write_tree(tmp_path, {"doc.md": f"n = {m('core_n', '650')}\n"})
    assert run_main(root, "--check") == 1                                        # stale -> exit 1, nothing written
    assert (root / "doc.md").read_text(encoding="utf-8") == f"n = {m('core_n', '650')}\n"
    assert run_main(root) == 0                                                   # rewrite
    assert (root / "doc.md").read_text(encoding="utf-8") == f"n = {m('core_n', '720')}\n"
    assert run_main(root, "--check") == 0                                        # now current
    out = capsys.readouterr().out
    assert "stale" in out


def test_check_exits_1_on_unknown_key_even_when_nothing_is_stale(tmp_path):
    root = write_tree(tmp_path, {"doc.md": f"{m('typo_key', '1')}\n"})
    assert run_main(root, "--check") == 1 and run_main(root) == 1


def test_exclude_list_blocks_historical_records(tmp_path):
    assert rd.is_excluded("DECISION_LOG.md") and rd.is_excluded("PROGRESS.md") and rd.is_excluded("docs/open-questions.md")
    assert not rd.is_excluded("docs/market-guide.md") and not rd.is_excluded("AGENT_CONTEXT.md")
    root = write_tree(tmp_path, {"DECISION_LOG.md": f"D-001: {m('core_n', '1')}\n", "docs/market-guide.md": f"{m('core_n', '1')}\n"})
    assert run_main(root) == 1                                                   # a marker in a frozen file is an error ...
    assert (root / "DECISION_LOG.md").read_text(encoding="utf-8") == f"D-001: {m('core_n', '1')}\n"          # ... and the file is not rewritten
    root2 = write_tree(tmp_path / "t2", {"DECISION_LOG.md": "D-001: 720 core postings, 48 %\n", "docs/market-guide.md": f"{m('core_n', '1')}\n"})
    assert run_main(root2) == 0                                                  # frozen files without markers are simply ignored
    assert (root2 / "DECISION_LOG.md").read_text(encoding="utf-8") == "D-001: 720 core postings, 48 %\n"


def test_private_and_generated_trees_are_not_scanned(tmp_path):
    root = write_tree(tmp_path, {"data/raw/x.md": f"{m('typo', '1')}\n", "outputs/reports/y.md": f"{m('typo', '1')}\n", "archive/z.md": f"{m('typo', '1')}\n"})
    assert run_main(root, "--check") == 0


def test_line_endings_are_preserved_byte_for_byte(tmp_path):
    crlf = f"line one {m('core_n', '1')}\r\nline two\r\n".encode()
    lf = f"line one {m('core_n', '1')}\nline two\n".encode()
    root = write_tree(tmp_path, {"crlf.md": crlf, "lf.md": lf})
    assert run_main(root) == 0
    assert (root / "crlf.md").read_bytes() == crlf.replace(b"<!--m:core_n-->1", b"<!--m:core_n-->720")
    assert (root / "lf.md").read_bytes() == lf.replace(b"<!--m:core_n-->1", b"<!--m:core_n-->720")


def test_run_date_must_match_the_registry(tmp_path):
    root = write_tree(tmp_path, {"doc.md": f"{m('core_n', '720')}\n"})
    assert run_main(root, "--check", "--run-date", "2026-10-18") == 0
    assert run_main(root, "--check", "--run-date", "2026-11-01") == 1


def test_missing_registry_is_an_error(tmp_path):
    (tmp_path / "doc.md").write_text(f"{m('core_n', '1')}\n", encoding="utf-8")
    assert run_main(tmp_path) == 1


def test_cli_help_and_list():
    script = str(ROOT / "src" / "reporting" / "render_docs.py")
    out = subprocess.run([sys.executable, script, "--help"], capture_output=True, text=True)
    assert out.returncode == 0 and "--check" in out.stdout and "--run-date" in out.stdout
    listing = subprocess.run([sys.executable, script, "--list"], capture_output=True, text=True)
    assert listing.returncode == 0 and "DECISION_LOG.md" in listing.stdout


# ---------------------------------------------------------------------------------------------------- the living documents
LIVING = ["AGENT_CONTEXT.md", "README.md", "CAREER_DECISION_MAP.md", "CAREER_SUPPLY_DEMAND_MAP.md", "docs/market-guide.md", "docs/data-quality.md",
          "docs/limitations.md", "docs/methodology.md", "docs/seasonality.md", "docs/operational-career-intelligence.md", "docs/career-map.md"]


def test_living_documents_carry_markers_and_none_is_excluded():
    for rel in LIVING:
        path = ROOT / rel
        if not path.exists():
            pytest.skip(f"{rel} not present in this tree")
        assert not rd.is_excluded(rel), rel
        assert path.read_text(encoding="utf-8").count("<!--m:") > 10, f"{rel} has no metric markers"


def test_living_documents_are_current_against_the_registry_built_from_the_outputs():
    if not (ROOT / "outputs" / "market_summary.json").exists():
        pytest.skip("outputs not present")
    reg = mr.build_registry(ROOT, dt.date.today())
    result = rd.process(ROOT, reg, check=True)
    stale = [(f, s["stale"][:3]) for f, s in result["files"].items() if s["stale"]]
    assert result["errors"] == [], result["errors"][:5]
    assert stale == [], f"documents out of date: run python src/reporting/metrics_registry.py && python src/reporting/render_docs.py -- {stale[:2]}"
