"""Value-level checks of the visual decision layer (L77): does the number an answer quotes match the table it cites?

test_visual_layer.py checks that figures, seals, tables and anchors exist; that let three kinds of error through the
2026-09-30 audit: a Styria employer headline quoting the all-postings total instead of the named-employer total (BQ04),
and counts from two different geography definitions mixed in one sentence. Two definitions exist on purpose:

  * primary state  - `state` of a posting, one per posting: T03a_state_counts.csv, DS05 (Styria 54, Vienna 343 of 720)
  * location flags - is_styria / is_vienna / is_graz_area, true for any listed location: market_summary.json counts,
                     T03d, T04a/T04b, T07e (Styria 58, Graz area 52, Vienna 350)

A sentence may use either, but not both. These tests read only tracked outputs, so they run in every clone. A failure
here means an answer sentence (built in src/analysis/visual_questions_*.py and rendered by make_visual_layer.py) no
longer matches its table; it is a real defect to fix in the builder, never a reason to loosen the test.
"""
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from conftest import require

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
TAB = OUT / "tables"

pytestmark = pytest.mark.value_check


def _numbers(text: str) -> set[float]:
    """Every number written in an answer ('12,429' -> 12429, '10.9%' -> 10.9)."""
    return {float(m.replace(",", "")) for m in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


@pytest.fixture(scope="module")
def answers():
    contract = require(OUT / "visual_questions.json", "visual layer contract outputs/visual_questions.json")
    figs = json.loads(contract.read_text(encoding="utf-8"))["figures"]
    return {f["chart_id"].split("_")[0]: f["answer"] for f in figs}


@pytest.fixture(scope="module")
def counts():
    return json.loads(require(OUT / "market_summary.json", "outputs/market_summary.json").read_text(encoding="utf-8"))["counts"]


def _table(name: str) -> pd.DataFrame:
    return pd.read_csv(require(TAB / name, f"table {name}"))


def _mismatch(fig: str, answer: str, detail: str) -> str:
    return (f"VALUE MISMATCH {fig}: {detail}\n  answer: {answer}\n"
            "  fix the answer builder in src/analysis/visual_questions_*.py and re-run src/analysis/make_visual_layer.py")


# ---------------- table-level consistency behind the answers (both geography definitions agree with themselves)
def test_geography_tables_are_internally_consistent(counts):
    t03a = _table("T03a_state_counts.csv")
    assert t03a["count"].sum() == t03a.n.iloc[0] == counts["core_canonical"]
    t03d = _table("T03d_geo_summary.csv").set_index("metric")["count"]
    assert t03d["styria"] == counts["styria_core"] and t03d["graz_area"] == counts["graz_area_core"]
    assert t03d["vienna"] == counts["vienna_core"]
    ds05 = _table("DS05_demand_supply_geography.csv").set_index("category")
    for state in ("Wien", "Steiermark"):
        assert ds05.at[state, "demand_count"] == t03a.set_index("state").at[state, "count"], state


def test_styria_employer_tables_agree(counts):
    """T04a counts Styrian postings with a named employer: all Styrian core postings minus the anonymous ones (T04b)."""
    t04a = _table("T04a_employers_styria.csv")
    t04b = _table("T04b_employer_concentration.csv").set_index("metric")["value"]
    assert len(t04a) == t04b["unique_named_employers_styria"] == counts["unique_employers_styria"]
    assert t04a.styria.sum() == counts["styria_core"] - t04b["styria_postings_without_named_employer"]


# ---------------- answer sentences against their tables
def test_bq04_styria_employer_headline_matches_t04a(answers):
    """BQ04 cites T04a: the posting count in the headline must be T04a's `styria` column sum (named postings)."""
    t04a = _table("T04a_employers_styria.csv")
    a, nums = answers["BQ04"], _numbers(answers["BQ04"])
    named, employers = int(t04a.styria.sum()), len(t04a)
    assert employers in nums, _mismatch("BQ04", a, f"T04a lists {employers} Styrian employers")
    assert named in nums, _mismatch("BQ04", a, f"T04a `styria` column sums to {named} named Styrian postings")


def test_bq01_uses_one_geography_definition(answers, counts):
    """BQ01 cites T03a (primary state). Its Styria and Vienna counts must be T03a's, and it must not pair them with the
    flag-based Graz-area count (market_summary graz_area_core), which belongs to the 58-posting Styria definition."""
    t03a = _table("T03a_state_counts.csv").set_index("state")["count"]
    a, nums = answers["BQ01"], _numbers(answers["BQ01"])
    assert t03a["Steiermark"] in nums, _mismatch("BQ01", a, f"T03a Steiermark = {t03a['Steiermark']}")
    assert t03a["Wien"] in nums, _mismatch("BQ01", a, f"T03a Wien = {t03a['Wien']}")
    mixes = counts["graz_area_core"] in nums and counts["styria_core"] not in nums and counts["graz_area_core"] != t03a["Steiermark"]
    assert not mixes, _mismatch(
        "BQ01", a, f"Graz-area count {counts['graz_area_core']} is flag-based (Styria = {counts['styria_core']} on that "
                   f"definition) but is quoted as a part of the primary-state Styria count {t03a['Steiermark']}")


def test_bq27_funnel_matches_market_summary(answers, counts):
    a, nums = answers["BQ27"], _numbers(answers["BQ27"])
    for key in ("raw_rows_all_sources", "canonical_groups_all", "core_canonical", "styria_core", "graz_area_core"):
        assert counts[key] in nums, _mismatch("BQ27", a, f"market_summary {key} = {counts[key]}")


def test_bq12_addressable_scenarios_match_t07e(answers):
    t07e = _table("T07e_addressable_market_scenarios.csv").set_index("scope")
    a, nums = answers["BQ12"], _numbers(answers["BQ12"])
    styria = t07e.loc["Styria"]
    scen = styria.drop("n")
    for value, what in ((styria.n, "Styria n"), (scen.min(), "strictest Styria scenario"), (scen.max(), "widest Styria scenario"),
                        (t07e.at["Graz area", "english_posting_no_german_req"], "strictest Graz-area scenario")):
        assert value in nums, _mismatch("BQ12", a, f"T07e {what} = {value}")


def test_bq33_employer_structure_matches_t04b(answers):
    t04b = _table("T04b_employer_concentration.csv").set_index("metric")["value"]
    a, nums = answers["BQ33"], _numbers(answers["BQ33"])
    for key in ("unique_named_employers_austria", "postings_with_named_employer", "postings_without_named_employer"):
        assert t04b[key] in nums, _mismatch("BQ33", a, f"T04b {key} = {int(t04b[key])}")
    for key in ("top10_share_of_named", "agency_share_of_named_postings"):
        assert round(t04b[key] * 100, 1) in nums, _mismatch("BQ33", a, f"T04b {key} = {t04b[key]}")


def test_bq37_geography_matches_ds05(answers):
    ds05 = _table("DS05_demand_supply_geography.csv").set_index("category")
    a, nums = answers["BQ37"], _numbers(answers["BQ37"])
    for state in ("Wien", "Steiermark"):
        for col in ("demand_count", "supply_T1"):
            assert ds05.at[state, col] in nums, _mismatch("BQ37", a, f"DS05 {state} {col} = {ds05.at[state, col]}")
