"""Weekly salary-floor history (src/reporting/metrics_history.py) and the derived registry keys (`__hist_*`, `__trend`, claim keys).

All tests build their inputs in tmp_path; none reads the real history file or the real outputs.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "reporting"))
import metrics_history as mh  # noqa: E402
import metrics_registry as mr  # noqa: E402


def row(run_date, key, value, unit="eur", n=""):
    return {"run_date": run_date, "week_id": "w", "demand_vintage": run_date, "key": key, "value": repr(float(value)), "unit": unit, "n": str(n)}


def entry(value, unit="eur", definition="a floor"):
    return {"value": value, "display": str(value), "unit": unit, "n": 10, "definition": definition}


def series_of(*pairs):
    return [(dt.date.fromisoformat(d), v) for d, v in pairs]


# ---------------------------------------------------------------------------------------------------- tracked keys
def test_tracked_keys_are_salary_floors_and_their_sample_sizes_not_derived_keys():
    reg = {"floor_junior_eur": entry(46000), "floor_junior_n": entry(18, "count"), "never_ask_below_eur": entry(46000),
           "family_salary_floor_median_eur__bi": entry(56000), "salary_state__wien__floor_p25_eur": entry(47000),
           "core_n": entry(700, "count"), "sql_share": entry(0.4, "share"), "salary_with_range_share": entry(0.15, "share"),
           "floor_junior_eur__hist_min": entry(42000), "floor_junior_eur__trend": entry("text", "text"),
           "_meta": {"week_id": "2026-W42", "demand_vintage": "2026-10-16"}}
    keys = {r["key"] for r in mh.tracked_rows(reg, "2026-10-16")}
    assert keys == {"floor_junior_eur", "floor_junior_n", "never_ask_below_eur", "family_salary_floor_median_eur__bi", "salary_state__wien__floor_p25_eur"}
    one = next(r for r in mh.tracked_rows(reg, "2026-10-16") if r["key"] == "floor_junior_eur")
    assert one["week_id"] == "2026-W42" and one["demand_vintage"] == "2026-10-16" and float(one["value"]) == 46000.0 and one["n"] == "10"


# ---------------------------------------------------------------------------------------------------- upsert
def test_upsert_replaces_the_rows_of_one_run_and_is_idempotent(tmp_path):
    path = tmp_path / "h" / "history.csv"
    old = [row("2026-09-16", "floor_junior_eur", 42000), row("2026-09-16", "floor_bi_eur", 52000)]
    mh.write_history(path, old)
    new = [row("2026-10-16", "floor_junior_eur", 45738), row("2026-10-16", "floor_bi_eur", 56000)]
    once = mh.upsert(mh.read_history(path), new, "2026-10-16")
    twice = mh.upsert(once, new, "2026-10-16")
    assert once == twice and len(once) == 4
    corrected = mh.upsert(once, [row("2026-10-16", "floor_junior_eur", 46000)], "2026-10-16")     # a re-run with other values replaces the whole run
    assert [(r["run_date"], r["key"]) for r in corrected] == [("2026-09-16", "floor_bi_eur"), ("2026-09-16", "floor_junior_eur"), ("2026-10-16", "floor_junior_eur")]
    assert next(r for r in corrected if r["run_date"] == "2026-10-16")["value"] == "46000.0"


def test_history_file_is_atomic_and_round_trips(tmp_path):
    path = tmp_path / "history.csv"
    rows = mh.upsert([], [row("2026-10-16", "floor_junior_eur", 45738.0, n=18)], "2026-10-16")
    mh.write_history(path, rows)
    assert mh.read_history(path) == rows
    assert not list(tmp_path.glob("*.tmp"))
    assert path.read_text(encoding="utf-8").splitlines()[0] == ",".join(mh.COLUMNS)
    assert mh.read_history(tmp_path / "missing.csv") == [] and mh.read_history(None) == []


# ---------------------------------------------------------------------------------------------------- statistics
def test_min_max_median_mode_and_change_of_a_series():
    st = mh.series_stats(series_of(("2026-09-16", 42000), ("2026-10-16", 45738), ("2026-10-23", 45738)))
    assert (st["min"], st["max"], st["median"], st["mode"], st["n"], st["first_date"]) == (42000, 45738, 45738, 45738, 3, "2026-09-16")
    assert st["change"] == pytest.approx(3738) and st["slope_per_week"] is None          # fewer than four runs: no slope


def test_mode_tie_goes_to_the_most_recent_value():
    st = mh.series_stats(series_of(("2026-09-16", 42000), ("2026-09-23", 45000), ("2026-09-30", 42000), ("2026-10-07", 45000)))
    assert st["mode"] == 45000                    # 42000 and 45000 both twice; 45000 occurred last
    st2 = mh.series_stats(series_of(("2026-09-16", 45000), ("2026-09-23", 42000)))
    assert st2["mode"] == 42000


def test_series_keeps_one_value_per_run_date_and_can_stop_at_a_date():
    rows = [row("2026-09-16", "k", 1), row("2026-10-16", "k", 2), row("2026-10-23", "k", 3), row("2026-10-23", "other", 9)]
    assert [v for _, v in mh.series(rows, "k")] == [1, 2, 3]
    assert [v for _, v in mh.series(rows, "k", up_to="2026-10-16")] == [1, 2]


def test_ols_slope_per_week_needs_four_runs_and_follows_the_dates():
    weekly = series_of(("2026-09-16", 42000), ("2026-09-23", 43000), ("2026-09-30", 44000), ("2026-10-07", 45000))
    assert mh.series_stats(weekly)["slope_per_week"] == pytest.approx(1000.0)
    fortnightly = series_of(("2026-09-16", 42000), ("2026-09-30", 44000), ("2026-10-14", 46000), ("2026-10-28", 48000))
    assert mh.series_stats(fortnightly)["slope_per_week"] == pytest.approx(1000.0)      # 2000 per two weeks = 1000 per week
    assert mh.series_stats(series_of(("2026-09-16", 42000), ("2026-09-23", 42000), ("2026-09-30", 42000), ("2026-10-07", 42000)))["slope_per_week"] == pytest.approx(0.0)


def test_trend_text_below_four_runs_says_too_few_and_gives_the_change():
    assert mr.trend_text(mh.series_stats(series_of(("2026-10-16", 45738)))) == "too few runs for a trend (n=1)"
    two = mr.trend_text(mh.series_stats(series_of(("2026-09-16", 42000), ("2026-10-16", 45738))))
    assert two == "too few runs for a trend (n=2); up +€3.7k since 2026-09-16 (2 runs)"
    down = mr.trend_text(mh.series_stats(series_of(("2026-09-16", 46000), ("2026-09-23", 45000), ("2026-09-30", 44000))))
    assert down == "too few runs for a trend (n=3); down −€2.0k since 2026-09-16 (3 runs)"
    same = mr.trend_text(mh.series_stats(series_of(("2026-09-16", 45000), ("2026-09-23", 45000))))
    assert same == "too few runs for a trend (n=2); unchanged since 2026-09-16 (2 runs)"


def test_trend_text_from_four_runs_uses_the_sign_of_the_weekly_slope():
    up = mr.trend_text(mh.series_stats(series_of(("2026-09-16", 42000), ("2026-09-23", 43000), ("2026-09-30", 44000), ("2026-10-07", 45000))))
    assert up == "rising +€1.0k/week (OLS over 4 runs since 2026-09-16); total change +€3.0k"
    down = mr.trend_text(mh.series_stats(series_of(("2026-09-16", 45000), ("2026-09-23", 44500), ("2026-09-30", 44000), ("2026-10-07", 43500))))
    assert down.startswith("falling −€0.5k/week") and "total change −€1.5k" in down
    flat = mr.trend_text(mh.series_stats(series_of(("2026-09-16", 45000), ("2026-09-23", 45000), ("2026-09-30", 45000), ("2026-10-07", 45000))))
    assert flat.startswith("flat +€0.0k/week")


# ---------------------------------------------------------------------------------------------------- registry keys
def reg_with(tmp_path, value, history_rows):
    path = tmp_path / "history.csv"
    mh.write_history(path, history_rows)
    reg = mr.Registry(tmp_path)
    reg.add("floor_junior_eur", value, "eur", source="t", definition="median advertised floor, junior ads", n=18)
    reg.add("sql_share", 0.4, "share", source="t", definition="x")
    mr.add_history_keys(reg, path, dt.date(2026, 10, 16), {"week_id": "2026-W42", "demand_vintage": "2026-10-16"})
    return reg.items


def test_registry_gets_min_max_median_mode_n_first_date_and_trend_for_every_floor_key(tmp_path):
    items = reg_with(tmp_path, 45738.0, [row("2026-09-16", "floor_junior_eur", 42000)])
    assert items["floor_junior_eur__hist_min"]["display"] == "€42.0k" and items["floor_junior_eur__hist_max"]["display"] == "€45.7k"
    assert mr.fmt_value(items["floor_junior_eur__hist_min"]["value"], "eur", "eur_k0") == "€42k"
    assert items["floor_junior_eur__hist_median"]["value"] == pytest.approx(43869.0)
    assert items["floor_junior_eur__hist_mode"]["value"] == 45738.0                 # tie of two values -> the most recent
    assert items["floor_junior_eur__hist_n"]["value"] == 2 and items["floor_junior_eur__hist_first_date"]["display"] == "2026-09-16"
    assert items["floor_junior_eur__trend"]["display"] == "too few runs for a trend (n=2); up +€3.7k since 2026-09-16 (2 runs)"
    assert not [k for k in items if k.startswith("sql_share__")]                    # only floor keys carry history keys


def test_history_keys_exist_with_one_run_and_without_a_history_file(tmp_path):
    reg = mr.Registry(tmp_path)
    reg.add("floor_junior_eur", 45738.0, "eur", source="t", definition="d")
    mr.add_history_keys(reg, None, dt.date(2026, 10, 16), {})
    assert reg.items["floor_junior_eur__hist_n"]["value"] == 1
    assert reg.items["floor_junior_eur__hist_min"]["value"] == reg.items["floor_junior_eur__hist_max"]["value"] == 45738.0
    assert reg.items["floor_junior_eur__trend"]["display"] == "too few runs for a trend (n=1)"


def test_a_rerun_of_an_old_run_date_ignores_later_runs_and_this_runs_own_stored_row(tmp_path):
    rows = [row("2026-09-16", "floor_junior_eur", 42000), row("2026-10-16", "floor_junior_eur", 99999), row("2026-10-23", "floor_junior_eur", 50000)]
    items = reg_with(tmp_path, 45738.0, rows)
    assert items["floor_junior_eur__hist_n"]["value"] == 2 and items["floor_junior_eur__hist_max"]["value"] == 45738.0


def test_from_four_runs_the_registry_trend_text_is_a_slope(tmp_path):
    rows = [row("2026-09-16", "floor_junior_eur", 42000), row("2026-09-23", "floor_junior_eur", 43000), row("2026-09-30", "floor_junior_eur", 44000)]
    path = tmp_path / "history.csv"
    mh.write_history(path, rows)
    reg = mr.Registry(tmp_path)
    reg.add("floor_junior_eur", 45000.0, "eur", source="t", definition="d")
    mr.add_history_keys(reg, path, dt.date(2026, 10, 7), {})
    assert reg.items["floor_junior_eur__trend"]["display"].startswith("rising +€1.0k/week (OLS over 4 runs")


def test_cli_stores_the_history_only_for_a_stamped_run_and_a_second_run_changes_nothing(tmp_path):
    csvdir = tmp_path / "outputs" / "tables"
    csvdir.mkdir(parents=True)
    with open(csvdir / "T09b_salary_by_seniority.csv", "w", newline="", encoding="utf-8") as handle:
        w = csv.writer(handle)
        w.writerow(["seniority", "n", "min_p25", "min_median", "min_p75", "max_median", "n_with_max", "mean_min"])
        w.writerow(["trainee_junior", 18, 35000, 45738, 45738, "", 0, 41000])
    out = tmp_path / "metrics.json"
    cmd = [sys.executable, str(ROOT / "src" / "reporting" / "metrics_registry.py"), "--root", str(tmp_path), "--out", str(out)]
    hist = tmp_path / "data" / "private" / "metrics_history" / "history.csv"
    done = subprocess.run(cmd, capture_output=True, text=True)                    # no --run-date: ad-hoc, nothing stored
    assert done.returncode == 0, done.stderr
    assert not hist.exists()
    for _ in range(2):
        done = subprocess.run(cmd + ["--run-date", "2026-10-16"], capture_output=True, text=True)
        assert done.returncode == 0, done.stderr
    rows = mh.read_history(hist)
    assert {r["key"] for r in rows} >= {"never_ask_below_eur", "floor_junior_eur"} and {r["run_date"] for r in rows} == {"2026-10-16"}
    assert len(rows) == len({(r["run_date"], r["key"]) for r in rows})
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["floor_junior_eur__hist_n"]["value"] == 1 and data["never_ask_below_eur__trend"]["value"].startswith("too few runs")
    done = subprocess.run(cmd + ["--run-date", "2026-10-16", "--no-history"], capture_output=True, text=True)
    assert done.returncode == 0 and mh.read_history(hist) == rows


def test_history_keys_are_part_of_the_final_registry_and_never_tracked_themselves(tmp_path):
    csvdir = tmp_path / "outputs" / "tables"
    csvdir.mkdir(parents=True)
    with open(csvdir / "T09b_salary_by_seniority.csv", "w", newline="", encoding="utf-8") as handle:
        w = csv.writer(handle)
        w.writerow(["seniority", "n", "min_p25", "min_median", "min_p75", "max_median", "n_with_max", "mean_min"])
        w.writerow(["trainee_junior", 18, 35000, 45738, 45738, "", 0, 41000])
    reg = mr.build_registry(tmp_path, dt.date(2026, 10, 16), generated_at="2026-10-16T00:00:00+00:00")
    assert "floor_junior_eur__hist_min" in reg and "never_ask_below_eur__trend" in reg
    assert not any(mh.is_tracked(k, v) for k, v in reg.items() if "__hist_" in k or k.endswith("__trend"))


# ---------------------------------------------------------------------------------------------------- claim keys
def claim_reg(tmp_path, **vals):
    reg = mr.Registry(tmp_path)
    for k, v in vals.items():
        unit = "count" if isinstance(v, int) else "share"
        reg.add(k, v, unit, source="t", definition="d", n=100, display=f"{v:+.0%}" if k.startswith("jb_") else None)
    mr.claim_keys(reg)
    return reg.items


def test_growing_regions_list_follows_the_sign_and_stays_present_when_none_grows(tmp_path):
    two = claim_reg(tmp_path, jb_data_scientist_change__styria=0.34, jb_data_scientist_change__vienna=0.15, jb_data_scientist_change__upper_austria=-0.11)
    assert two["jb_growing_regions"]["display"] == "Styria (+34%) and Vienna (+15%)" and two["jb_growing_regions_n"]["value"] == 2
    one = claim_reg(tmp_path, jb_data_scientist_change__styria=0.34, jb_data_scientist_change__vienna=-0.05, jb_data_scientist_change__upper_austria=-0.11)
    assert one["jb_growing_regions"]["display"] == "Styria (+34%)"
    none = claim_reg(tmp_path, jb_data_scientist_change__styria=-0.01, jb_data_scientist_change__vienna=-0.05, jb_data_scientist_change__upper_austria=-0.11)
    assert none["jb_growing_regions"]["display"] == "none of Styria, Vienna and Upper Austria" and none["jb_growing_regions_n"]["value"] == 0
    assert none["jb_regions_change_text"]["display"].startswith("Styria -1%")


def test_vienna_to_graz_ratio_is_present_even_when_the_graz_area_is_empty(tmp_path):
    ok = claim_reg(tmp_path, vienna_core_flag=329, graz_area_core_flag=63)
    assert ok["vienna_to_graz_core_ratio"]["display"] == "5.2×"
    empty = claim_reg(tmp_path, vienna_core_flag=329, graz_area_core_flag=0)
    assert empty["vienna_to_graz_core_ratio"]["display"].startswith("n/a")


def test_skill_ranks_share_the_better_rank_on_ties_and_always_cover_the_set(tmp_path):
    items = claim_reg(tmp_path, sql_share=0.41, python_share=0.41, generic_ai_share=0.43, visualisation_share=0.0)
    assert items["tech_skill_rank__generic_ai"]["display"] == "1st"
    assert items["tech_skill_rank__sql"]["display"] == items["tech_skill_rank__python"]["display"] == "2nd"
    assert items["tech_skill_rank__visualisation"]["display"] == "4th"              # an empty skill (0 %) still has a rank
    assert items["tech_skill_rank_set_n"]["value"] == 4 and items["tech_skill_top1_name"]["display"] == "generic AI"
    assert items["tech_skills_top3_text"]["display"] == "generic AI 43 %, SQL 41 % and Python 41 %"


def decision_inputs(**ranks):
    """ranks: {family: (default, geography_first, language_first, equal)}"""
    out = {}
    for fam, rs in ranks.items():
        for w, r in zip(("default", "geography_first", "language_first", "equal"), rs):
            out[f"decision_rank_{w}__{fam}"] = r
    return out


def test_decision_keys_report_a_changed_top_three_and_unchanged_one(tmp_path):
    moving = claim_reg(tmp_path, **decision_inputs(data_science=(1, 2, 1, 1), data_engineering=(2, 1, 2, 2), data_analytics=(3, 3, 3, 4), business_analysis=(4, 4, 4, 3)),
                       family_n__data_science=178, family_n__marketing_analytics=19)
    assert moving["analytics_decision_ranks_text"]["display"] == "3rd (default), 3rd (geography-first), 3rd (language-first) and 4th (equal)"
    assert moving["decision_top3_stability_text"]["display"] == "unchanged under 3 of 4 weightings (equal weights: business analysis replaces data analytics)"
    assert moving["decision_top3_default_text"]["display"] == "data science 1st, data engineering 2nd, data analytics 3rd"
    assert moving["decision_leaders_text"]["display"] == "data engineering under geography-first weights; data science under default, language-first and equal weights"
    assert moving["decision_unranked_text"]["display"] == "marketing analytics (n = 19)"
    steady = claim_reg(tmp_path, **decision_inputs(data_science=(1, 1, 1, 1), data_engineering=(2, 2, 2, 2), data_analytics=(3, 3, 3, 3), bi=(4, 4, 4, 4)), family_n__data_science=178)
    assert steady["decision_top3_stability_text"]["display"] == "unchanged under all four weightings"
    assert steady["analytics_decision_ranks_text"]["display"].count("3rd") == 4 and steady["decision_unranked_text"]["display"] == "none"


def test_entry_denominators_are_judged_against_the_rule_of_thirty(tmp_path):
    mixed = claim_reg(tmp_path, entry_track_desc_n__intern_student=30, entry_track_desc_n__trainee_junior=28)
    assert mixed["entry_track_denominators_vs_30"]["display"] == "intern 30 (at or above), junior 28 (below)" and mixed["entry_track_min_n"]["value"] == 28
    both = claim_reg(tmp_path, entry_track_desc_n__intern_student=42, entry_track_desc_n__trainee_junior=31)
    assert both["entry_track_denominators_vs_30"]["display"] == "intern 42 (at or above), junior 31 (at or above)"
