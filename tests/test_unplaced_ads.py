"""Ads that AMS cannot assign to a state (P-02): the registry keys that carry the caveat.

The AMS method paper (Methodenpaper v1.2, section 3.1.6) says the Austria total can exceed the sum of the states.
These tests build a small JB01 table by hand, so the expected numbers are easy to check.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "reporting"))

from metrics_registry import Registry, official_and_seasonality  # noqa: E402

CLASS = "Data Scientist (m/w)"
OTHER = "Other class (m/w)"


def _registry(tmp_path: Path, table: dict[tuple[str, str, int], float]) -> dict:
    out = tmp_path / "outputs" / "tables"
    out.mkdir(parents=True)
    with open(out / "JB01_yearly_counts_long.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["group_id", "beruf_id", "beruf", "bl", "bundesland", "year", "ads", "censored_lt20"])
        for (beruf, bl, year), ads in table.items():
            writer.writerow([1, 1, beruf, bl, bl, year, ads, False])
    reg = Registry(tmp_path)
    official_and_seasonality(reg)
    return reg.items


def _table() -> dict[tuple[str, str, int], float]:
    # first year: Austria 1000, states hold 600 (400 unplaced). Peak and latest year: Austria 800 / 500, states hold 720 / 450.
    rows = {}
    for beruf in (CLASS, OTHER):
        for year, at, ar, st in ((2020, 1000, 100, 300), (2021, 800, 200, 520), (2022, 500, 150, 300)):
            rows[(beruf, "AT", year)] = at
            rows[(beruf, "AT22", year)] = ar
            rows[(beruf, "AT13", year)] = st - ar
            if beruf == CLASS and year == 2020:
                rows[(beruf, "AT22", year)] = 100
    return rows


def test_unplaced_share_is_austria_total_minus_published_states(tmp_path):
    items = _registry(tmp_path, _table())
    # 2020: states 100 + 200 = 300 of 1000, so 70 % have no named state
    assert abs(items["jb_data_scientist_unplaced_share__2020"]["value"] - 0.70) < 1e-9
    # 2022: states 150 + 150 = 300 of 500, so 40 %
    assert abs(items["jb_data_scientist_unplaced_share__2022"]["value"] - 0.40) < 1e-9
    assert items["jb_data_scientist_unplaced_share__2020"]["display"] == "70.0 %"


def test_allocation_is_a_sensitivity_reading_not_the_raw_change(tmp_path):
    items = _registry(tmp_path, _table())
    raw = items["jb_data_scientist_change__styria"]["value"]
    alloc = items["jb_data_scientist_change_allocated__styria"]["value"]
    assert abs(raw - (150 / 100 - 1)) < 1e-9
    # Styria share of the named states: 100/300 in 2020 and 150/300 in 2022; scaled by the Austria totals 1000 and 500
    assert abs(alloc - ((150 / 300 * 500) / (100 / 300 * 1000) - 1)) < 1e-9
    assert raw > 0 > alloc
    assert "sensitivity reading" in items["jb_data_scientist_change_allocated__styria"]["definition"]
    assert "uncertain" in items["jb_data_scientist_change__styria"]["caveat"]
    assert items["jb_data_scientist_change__austria"]["caveat"] == ""


def test_stable_window_runs_from_the_austria_peak(tmp_path):
    items = _registry(tmp_path, _table())
    # Austria peaks in 2020 here, so the window is 2020 to 2022 for Styria, the named states and Austria
    assert abs(items["jb_data_scientist_change_from_austria_peak__styria"]["value"] - 0.5) < 1e-9
    assert abs(items["jb_data_scientist_change_from_austria_peak__named_states"]["value"] - 0.0) < 1e-9
    assert items["jb_data_scientist_ads_at_austria_peak__styria"]["value"] == 100


def test_class_wide_counts_cover_every_class_with_both_years(tmp_path):
    items = _registry(tmp_path, _table())
    assert items["jb_unplaced_classes_n"]["value"] == 2
    assert items["jb_unplaced_lower_n"]["value"] == 2
    assert abs(items["jb_unplaced_share_median__first"]["value"] - 0.70) < 1e-9
    assert abs(items["jb_unplaced_share_median__latest"]["value"] - 0.40) < 1e-9
