"""Tests for src/reporting/digest.py: it writes its own UTF-8 file atomically, survives missing tables and reports them,
and takes the vintages in its headings from the data instead of hard-coded text (L7, L135, L136)."""
import json

import pandas as pd
import pytest

import digest as G
from conftest import ROOT


@pytest.fixture
def empty_tree(tmp_path, monkeypatch):
    out, tab, proc = tmp_path / "outputs", tmp_path / "outputs" / "tables", tmp_path / "processed"
    for p in (out, tab, proc):
        p.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(G, "OUT", out)
    monkeypatch.setattr(G, "TAB", tab)
    monkeypatch.setattr(G, "PROC", proc)
    return tmp_path


def test_missing_tables_do_not_abort_and_are_listed(empty_tree):
    text = G.render()
    assert "section incomplete - missing input" in text
    assert "=== Completeness of this digest" in text.split("\n=== Visual decision layer")[-1]
    assert any("market_summary.json" in m for m in G.MISSING)
    assert any("T02_role_family_counts.csv" in m for m in G.MISSING)
    assert not G.ERRORS, G.ERRORS
    # every Layer 1 section heading is still printed, so the reader sees what is absent
    for heading in ("=== Families", "=== Salary", "=== Decision matrix", "=== Data quality"):
        assert heading in text


def test_strict_exit_code_and_file_is_still_written(empty_tree):
    target = empty_tree / "reports" / "digest.txt"
    assert G.main(["--out", str(target)]) == 0
    assert G.main(["--out", str(target), "--strict"]) == 1
    assert target.exists() and "MISSING" in target.read_text(encoding="utf-8")


def test_output_is_utf8_with_lf_and_replaced_atomically(tmp_path):
    target = tmp_path / "digest.txt"
    target.write_bytes(b"old\r\n")
    G.write_atomic("Demand × supply — Österreich\nline 2\n", target)
    data = target.read_bytes()
    assert b"\r" not in data
    assert data.decode("utf-8").startswith("Demand × supply")
    assert [p.name for p in tmp_path.iterdir()] == ["digest.txt"]  # no temporary file left behind


def test_a_crash_leaves_the_previous_digest_untouched(tmp_path, monkeypatch):
    target = tmp_path / "digest.txt"
    target.write_text("previous complete digest\n", encoding="utf-8")

    def boom():
        raise RuntimeError("simulated failure while rendering")

    monkeypatch.setattr(G, "render", boom)
    with pytest.raises(RuntimeError):
        G.main(["--out", str(target)])
    assert target.read_text(encoding="utf-8") == "previous complete digest\n"


def test_vintages_come_from_the_data(empty_tree):
    (G.OUT / "market_summary.json").write_text(json.dumps({
        "counts": {"core_canonical": 1}, "posted_date_range": {}, "collected_at_range":
            {"min": "2027-03-01 08:00:00+00:00", "max": "2027-03-01 09:00:00+00:00"}}), encoding="utf-8")
    (G.OUT / "supply_summary.json").write_text(json.dumps({"collection_date": "2027-03-05"}), encoding="utf-8")
    pd.DataFrame({"sector": ["B-F"] * 2, "year": [2011, 2027], "mean_vacancies": [1.0, 2.0]}).to_csv(G.TAB / "S04a_levels_by_year.csv", index=False)
    pd.DataFrame({"sector": ["B-F"] * 4, "quarter": ["Q1", "Q2", "Q3", "Q4"], "sample": ["full"] * 4, "n_years": [2] * 4,
                  "index_a_own_year_mean": [1.1, 1.0, 1.0, 0.9], "ci_low": [1.0] * 4, "ci_high": [1.2] * 4,
                  "index_b_moving_average": [1.1] * 4, "years_above_average": [1] * 4}).to_csv(G.TAB / "S01_seasonal_index.csv", index=False)
    text = G.render()
    assert "Counts (demand snapshot collected 2027-03-01)" in text
    assert "Supply coverage" not in text  # no Layer 2 tables in this tree
    assert "Vintages: demand snapshot 2027-03-01 · supply collection 2027-03-05 · Eurostat JVS 2011-2027" in text
    assert "Seasonality (Eurostat JVS, quarterly 2011-2027)" in text
    assert "2009-2025" not in text


def test_private_supply_manifest_wins_over_public_summary(empty_tree):
    (G.PROC / "supply_build_manifest.json").write_text(json.dumps({"collection_date": "2027-04-01"}), encoding="utf-8")
    (G.OUT / "supply_summary.json").write_text(json.dumps({"collection_date": "2027-03-05"}), encoding="utf-8")
    assert G.vintages()["supply"] == "2027-04-01"


def test_digest_of_the_published_tables_is_complete(tmp_path, require_input):
    """On the tracked outputs every section renders; only the private-data sections may be missing."""
    require_input(ROOT / "outputs" / "market_summary.json", "published outputs")
    target = tmp_path / "digest.txt"
    code = G.main(["--out", str(target)])
    text = target.read_text(encoding="utf-8")
    assert code == 0 and not G.ERRORS, G.ERRORS
    assert "=== Counts (demand snapshot collected" in text and "=== Visual decision layer" in text
    years = pd.read_csv(ROOT / "outputs" / "tables" / "S04a_levels_by_year.csv").year
    assert f"Seasonality (Eurostat JVS, quarterly {years.min()}-{years.max()})" in text
