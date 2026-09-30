"""Unit tests for analysis helpers changed in the 2026-09-30 audit (H10/H11, L52, L68, L105, L116, L118, L135, SQ10/11).

Pure functions run on synthetic inputs everywhere; the two builder checks read tracked outputs/ tables only.
"""
import json
import math

import numpy as np
import pandas as pd
import pytest

import engine
import salary_premium as SP
import seasonality as SEAS


# ---------------- L52 multiplicity corrections
def test_holm_matches_hand_computation():
    p = [0.01, 0.04, 0.03, 0.005]
    # sorted: 0.005*4=0.02, 0.01*3=0.03, 0.03*2=0.06, 0.04*1=0.04 -> monotone 0.06
    assert SP.holm(p) == pytest.approx([0.03, 0.06, 0.06, 0.02])


def test_benjamini_hochberg_matches_hand_computation():
    p = [0.01, 0.04, 0.03, 0.005]
    # ranks: 0.005(1)->0.02, 0.01(2)->0.02, 0.03(3)->0.04, 0.04(4)->0.04
    assert SP.benjamini_hochberg(p) == pytest.approx([0.02, 0.04, 0.04, 0.02])


def test_adjusted_p_values_never_fall_below_raw():
    rng = np.random.default_rng(0)
    p = list(rng.uniform(0, 0.2, 16))
    for adj in (SP.holm(p), SP.benjamini_hochberg(p)):
        assert all(a >= r - 1e-12 and a <= 1 for a, r in zip(adj, p))


def test_wald_p_is_two_sided_normal():
    assert SP.wald_p(1.959964, 1.0) == pytest.approx(0.05, abs=1e-5)
    assert SP.wald_p(-1.959964, 1.0) == pytest.approx(0.05, abs=1e-5)
    assert math.isnan(SP.wald_p(1.0, 0.0))


def test_estimate_reports_adjusted_columns_on_synthetic_postings():
    rng = np.random.default_rng(1)
    n = 400
    frame = pd.DataFrame({"role_family": rng.choice(["bi", "data_science"], n),
                          "seniority": rng.choice(["senior", "unspecified"], n),
                          "state": rng.choice(["Wien", "other/unspecified"], n)})
    for s in SP.SKILLS:
        frame[s] = rng.integers(0, 2, n)
    frame["salary"] = np.exp(10.8 + 0.2 * frame["Databricks"] + rng.normal(0, 0.1, n))
    table, r2, dropped = SP.estimate(frame)
    assert not dropped and 0 < r2 < 1
    assert {"p_value", "p_holm", "p_bh", "survives_holm", "survives_bh"} <= set(table.columns)
    row = table.set_index("skill").loc["Databricks"]
    assert row.survives_holm and row.survives_bh and row.p_holm >= row.p_value


# ---------------- S06 writer (restored) and the dropped F13 figure
def test_season_vs_cycle_on_synthetic_sector():
    s01 = pd.DataFrame({"sector": "G-N", "sample": "full", "quarter": ["Q1", "Q2", "Q3", "Q4"],
                        "index_a_own_year_mean": [1.05, 1.0, 1.0, 0.95]})
    yr = pd.DataFrame({"sector": "G-N", "year": [2009, 2010, 2011], "mean_vacancies": [100.0, 300.0, 200.0]})
    row = SEAS.season_vs_cycle(s01, yr).iloc[0]
    assert row.seasonal_spread_pct == pytest.approx(10.5, abs=0.05)       # 1.05 / 0.95 - 1
    assert row.between_year_spread_pct == pytest.approx(200.0)
    assert (row.min_year, row.max_year, row.min_val, row.max_val) == (2009, 2010, 100, 300)
    assert row.ratio == pytest.approx(round(200.0 / (1.05 / 0.95 * 100 - 100), 1))


def test_seasonality_no_longer_writes_the_legacy_figure():
    assert not hasattr(SEAS, "make_figure")


# ---------------- SQ10/SQ11 precision tables
def test_precision_table_counts_labels(tmp_path, monkeypatch):
    import supply_quality as SQ
    pd.DataFrame({"strict_correct": [True, True, False, True], "lenient_correct": [True, True, True, True]}).to_csv(
        tmp_path / "labels.csv", index=False)
    monkeypatch.setattr(SQ, "PROC", tmp_path)
    t = SQ.precision_table({"labels": "labels.csv", "sample": "x", "error_types": "y"}).iloc[0]
    assert (t.n, t.strict_correct, t.strict_precision, t.lenient_correct, t.lenient_precision) == (4, 3, 0.75, 4, 1.0)
    assert SQ.precision_table({"labels": "missing.csv", "sample": "x", "error_types": "y"}) is None


def test_supply_analyses_refuse_redacted_candidates():
    import supply_analysis as SA
    import supply_quality as SQ
    clean = pd.DataFrame({"redacted": [None, False]})
    for mod in (SA, SQ):
        mod.refuse_if_redacted(clean)
        with pytest.raises(SystemExit, match="frozen on 2026-09-30"):
            mod.refuse_if_redacted(pd.DataFrame({"redacted": [None, True]}))


def test_c23_columns_are_declared_for_the_empty_path():
    import supply_analysis as SA
    empty = pd.DataFrame([], columns=SA.C23_COLUMNS)
    assert list(empty.columns)[:2] == ["cluster", "size"] and "silhouette_k" in empty.columns


# ---------------- L118 official supply: missing Stack Overflow extract is reported, Eurostat is unaffected
def test_stack_overflow_missing_is_reported_not_silent(tmp_path, monkeypatch, capsys):
    import official_supply as OS
    monkeypatch.setattr(OS, "SO_ROOT", tmp_path / "stackoverflow_survey")
    assert OS.so_year_default() == "2025"
    out = OS.so_tables("2031")
    assert out["available"] is False and out["survey_year"] == "2031"
    assert "O04_so2031_at_devtype" in out["tables_not_refreshed"]
    assert "NOT refreshed" in capsys.readouterr().err
    (tmp_path / "stackoverflow_survey" / "2026").mkdir(parents=True)
    (tmp_path / "stackoverflow_survey" / "2026" / "survey_results_austria.csv").write_text("x\n", encoding="utf-8")
    assert OS.so_year_default() == "2026"


# ---------------- L135 vintages derived from run metadata
def test_vintages_follow_metadata_and_fall_back(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "ROOT", tmp_path)
    monkeypatch.setattr(engine, "TABLES", tmp_path / "tables")
    assert engine._demand_vintage() == "2026-09-16" and engine._supply_vintage() == "2026-09-17/18"
    assert engine._year_span("JB01.csv", "2020-2025") == "2020-2025"
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "market_summary.json").write_text(
        json.dumps({"collected_at_range": {"min": "2027-03-02 08:00:00+00:00"}}), encoding="utf-8")
    (tmp_path / "data" / "processed").mkdir(parents=True)
    (tmp_path / "data" / "processed" / "supply_build_manifest.json").write_text(
        json.dumps({"collection_date": "2027-03-05", "built_at": "2027-03-05T10:00:00"}), encoding="utf-8")
    (tmp_path / "tables").mkdir()
    (tmp_path / "tables" / "JB01.csv").write_text("year,ads\n2021,1\n2026,2\n", encoding="utf-8")
    assert engine._demand_vintage() == "2027-03-02"
    assert engine._supply_vintage() == "2027-03-05"
    assert engine._year_span("JB01.csv", "2020-2025") == "2021-2026"


# ---------------- H10 / H11 builders on the tracked tables
@pytest.fixture
def tracked(require_input):
    require_input(engine.ROOT / "outputs" / "market_summary.json", "market_summary.json")
    require_input(engine.TABLES / "T04a_employers_styria.csv", "T04a")
    require_input(engine.TABLES / "T03a_state_counts.csv", "T03a")


def _numbers(text):
    import re
    return {int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", text)}


def test_bq04_headline_uses_the_styria_column(tracked):
    import matplotlib.pyplot as plt
    import visual_questions_demand as D
    spec, fig = D.bq04()
    plt.close(fig)
    t04a = pd.read_csv(engine.TABLES / "T04a_employers_styria.csv")
    lead = t04a.sort_values(["styria", "postings"], ascending=False).iloc[0]
    nums = _numbers(spec.answer)
    assert int(t04a.styria.sum()) in nums and len(t04a) in nums
    assert f"{lead.example_company} leads with {int(lead.styria)}" in spec.answer


def test_bq01_answer_stays_on_the_primary_state_basis(tracked):
    import matplotlib.pyplot as plt
    import visual_questions_demand as D
    spec, fig = D.bq01()
    plt.close(fig)
    c = engine.market_counts()
    nums = _numbers(spec.answer)
    assert {c["styria_primary"], c["vienna_primary"], c["core"]} <= nums
    assert c["styria_any_site"] not in nums and c["graz_area_any_site"] not in nums
    assert str(c["styria_any_site"]) in spec.caveat
