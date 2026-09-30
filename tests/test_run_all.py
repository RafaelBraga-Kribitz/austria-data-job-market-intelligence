"""Tests for run_all.py (H1/M84/M94/M9/L9): step coverage, order, preflight, stop-on-failure, log and run manifest.

Nothing here runs the real pipeline: order and coverage are checked on the step table, execution on throwaway scripts
in a temporary folder.
"""
import json
import re
import sys

import pytest

import run_all as R
from conftest import ROOT

MAIN_RE = re.compile(r"^if __name__ == [\"']__main__[\"']", re.M)


def _entry_points(folder: str) -> list[str]:
    return sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).rglob("*.py")
                  if "__pycache__" not in p.parts and MAIN_RE.search(p.read_text(encoding="utf-8")))


def test_every_pipeline_script_has_a_documented_place():
    """M9: each runnable script is a step of `all`, a documented one-off tool, or (acquisition) a collect command."""
    steps = {s.script for s in R.STEPS}
    for script in _entry_points("src/pipeline") + _entry_points("src/analysis") + _entry_points("src/reporting") + _entry_points("src/publish"):
        assert script in steps or script in R.TOOLS, f"{script} is neither a run_all step nor listed under `tools`"
    for script in _entry_points("src/acquisition"):
        assert script in R.COLLECT, f"{script} is missing from the `collect` listing"


def test_order_respects_data_dependencies():
    order = [s.name for s in R.STEPS]
    pos = {n: i for i, n in enumerate(order)}
    must_precede = [
        ("build_interim", "normalize"), ("normalize", "dedupe"), ("dedupe", "redact_layer1_contacts"),
        ("redact_layer1_contacts", "run_analysis"),
        ("run_analysis", "cluster_requirements"), ("run_analysis", "data_quality"), ("run_analysis", "build_decision_matrix"),
        ("run_analysis", "export_agent_json"), ("jobbarometer_analysis", "make_figures"), ("run_analysis", "make_figures"),
        ("dedupe", "seasonality"), ("dedupe", "salary_premium"),
        ("build_supply", "supply_analysis"), ("build_supply", "project_analysis"), ("build_supply", "supply_quality"),
        ("official_supply", "demand_supply"), ("supply_analysis", "demand_supply"), ("run_analysis", "demand_supply"),
        ("demand_supply", "supply_figures"), ("official_supply", "supply_figures"),
        ("demand_supply", "export_supply_json"), ("project_analysis", "export_supply_json"),
        ("supply_quality", "export_supply_json"),
    ]
    # the visual layer reads tables of every layer; the digest reads everything; tests come last
    must_precede += [(n, "make_visual_layer") for n in order[:pos["make_visual_layer"]]]
    must_precede += [("make_visual_layer", "embed_figures"), ("embed_figures", "digest"), ("digest", "pytest")]
    for a, b in must_precede:
        assert pos[a] < pos[b], f"{a} must run before {b}"


def test_collection_and_one_off_tools_are_not_in_all():
    scripts = " ".join(s.script for s in R.STEPS)
    for never in ("collect_", "ingest_", "redact_supply_raw", "precision_audit", "export_public", "job_radar", "migrations/"):
        assert never not in scripts, never
    # L6: the GitHub token prerequisite is stated where the command is listed
    for prerequisite in ("GH_TOKEN", "GITHUB_TOKEN", "gh auth login"):
        assert prerequisite in R.COLLECT


def test_github_token_status_names_the_source_without_the_token(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret-value-not-to-print")
    assert R.github_token_status() == "GH_TOKEN is set"
    monkeypatch.delenv("GH_TOKEN"); monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(R.shutil, "which", lambda name: None)
    assert R.github_token_status().startswith("MISSING")


def test_targets_select_in_global_order():
    assert [s.name for s in R.select("all")] == [s.name for s in R.STEPS]
    l3 = [s.name for s in R.select("layer3")]
    assert l3 == ["demand_supply", "supply_figures", "export_supply_json"]
    assert [s.name for s in R.select("all", "embed_figures")] == ["embed_figures", "digest", "pytest"]
    with pytest.raises(SystemExit):
        R.select("layer1", "demand_supply")


def test_list_and_print_only_targets(capsys):
    assert R.main(["--list"]) == 0
    listing = capsys.readouterr().out
    for t in R.TARGETS:
        assert f"{t}:" in listing
    assert R.main(["collect"]) == 0 and "collect_github_supply.py all" in capsys.readouterr().out
    assert R.main(["tools"]) == 0 and "redact_supply_raw.py" in capsys.readouterr().out


def test_requirements_parser_reads_every_pin():
    reqs = dict(R.requirement_names())
    assert reqs, "requirements.txt parsed to nothing"
    assert all(v for v in reqs.values()), f"unpinned requirement(s): {[k for k, v in reqs.items() if not v]}"
    assert reqs.get("pyarrow") == "24.0.0"


# ---------------- execution on throwaway scripts
@pytest.fixture
def sandbox(tmp_path):
    (tmp_path / "ok.py").write_text("print('step ok: Österreich')\n", encoding="utf-8")
    (tmp_path / "fail.py").write_text("import sys\nprint('about to fail')\nsys.exit(3)\n", encoding="utf-8")
    (tmp_path / "never.py").write_text("open('never_ran', 'w').close()\n", encoding="utf-8")
    return tmp_path


def _run(sandbox, steps, dry_run=False):
    return R.run(steps, target="test", from_step=None, dry_run=dry_run, root=sandbox,
                 log_dir=sandbox / "logs", manifest=sandbox / "outputs" / "run_manifest.json")


def test_stops_at_first_failure_and_records_the_run(sandbox, capsys):
    steps = [R.Step("first", "layer1", "ok.py"),
             R.Step("optional_private", "layer1", "ok.py", optional=True, requires=["data/private_input"]),
             R.Step("planned", "layer1", "not_written_yet.py", if_script_exists=True),
             R.Step("breaks", "layer1", "fail.py"),
             R.Step("after", "layer1", "never.py")]
    assert _run(sandbox, steps) == 1
    out = capsys.readouterr().out
    assert "OPTIONAL STEP SKIPPED: optional_private" in out
    assert "FAILED (exit 3)" in out
    assert not (sandbox / "never_ran").exists()

    manifest = json.loads((sandbox / "outputs" / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed at breaks"
    assert [(s["step"], s["status"]) for s in manifest["steps"]] == [
        ("first", "ok"), ("optional_private", "skipped"), ("planned", "skipped"), ("breaks", "failed")]
    env = manifest["environment"]
    assert env["python"] == ".".join(map(str, sys.version_info[:3]))
    assert "pandas" in env["requirements_installed"] and "git_commit" in env
    log = (sandbox / manifest["log"]).read_text(encoding="utf-8")
    assert "step ok: Österreich" in log and "about to fail" in log


def test_preflight_fails_before_anything_runs(sandbox, capsys):
    steps = [R.Step("first", "layer1", "never.py"), R.Step("needs_private", "layer1", "ok.py", requires=["data/raw/karriere"])]
    assert _run(sandbox, steps) == 2
    assert "PREFLIGHT FAILED" in capsys.readouterr().out
    assert not (sandbox / "never_ran").exists()
    assert not (sandbox / "outputs" / "run_manifest.json").exists()


def test_dry_run_executes_nothing(sandbox, capsys):
    assert _run(sandbox, [R.Step("first", "layer1", "never.py")], dry_run=True) == 0
    assert "dry run: nothing executed" in capsys.readouterr().out
    assert not (sandbox / "never_ran").exists() and not (sandbox / "logs").exists()


def test_tests_only_run_does_not_overwrite_the_manifest(sandbox):
    assert _run(sandbox, [R.Step("pytest", "tests", "ok.py", writes_outputs=False)]) == 0
    assert not (sandbox / "outputs" / "run_manifest.json").exists()


def test_real_step_table_preflight_on_this_clone(capsys):
    """Dry run of `all` on this checkout: either everything is present (author's machine) or the preflight names
    exactly which private inputs are missing - it never crashes."""
    code = R.run(R.select("all"), target="all", from_step=None, dry_run=True)
    out = capsys.readouterr().out
    assert code in (0, 2)
    if code == 2:
        assert "PREFLIGHT FAILED" in out
