"""LinkedIn slot: ingest validation and write guards, the build_supply fold, the public summary contract and the JSON export
wording. Everything runs on tmp_path fixtures; nothing under data/ is read or written. Run: python -m pytest tests -q
"""
import json
from pathlib import Path

import pandas as pd
import pytest

import build_supply as B
import export_supply_json as X
import ingest_linkedin_manual as ing
from supply_common import public_linkedin_summary

DATE = "2026-09-21"


def slot(root: Path, date: str = DATE) -> Path:
    return root / "data" / "raw" / "linkedin_supply" / date


def write_slot(root: Path, counts: list[dict], profiles: list[dict], date: str = DATE, extra: dict | None = None) -> Path:
    folder = slot(root, date); folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(counts, columns=ing.COUNT_COLS + list((extra or {}).get("counts", []))).to_csv(folder / "search_counts.csv", index=False)
    pd.DataFrame(profiles, columns=ing.PROFILE_COLS).to_csv(folder / "profiles_manual.csv", index=False)
    return folder


def count_row(**kw) -> dict:
    row = {"observed_at": "2026-09-21T21:05:00+02:00", "observer": "RB", "acquisition_method": "manual_ui", "evidence_ref": "session:2026-09-21",
           "query_title": "Data Analyst", "location_filter": "Graz", "extra_filters": "keyword=Data Analyst", "language_filter": "",
           "result_count": "120", "count_is_capped": "false", "source_quality": "", "notes": "block=A"}
    row.update(kw)
    return row


def profile_row(**kw) -> dict:
    row = {c: "" for c in ing.PROFILE_COLS}
    row.update({"pseudo_id": "AT-0001", "observed_at": "2026-09-21", "observer": "RB", "acquisition_method": "manual_ui",
                "evidence_ref": "session:2026-09-21", "headline": "Turning data into decisions", "current_title": "Data Analyst",
                "location_text": "Graz", "seniority_label": "junior", "languages_stated": "de:C2;en:C1", "has_github_link": "1",
                "notes": "k=5; pages=1-5; stratum=Data Analyst|Graz; rank=5"})
    row.update(kw)
    return row


def processed(root: Path) -> Path:
    return root / "data" / "processed"


# ---------------- boolean parser
@pytest.mark.parametrize("raw,expected", [("true", "true"), ("Yes", "true"), ("1", "true"), ("1.0", "true"), (" y ", "true"),
                                          ("false", "false"), ("NO", "false"), ("0", "false"), ("0.0", "false"),
                                          ("", ""), (None, ""), (float("nan"), ""), ("maybe", None), ("2", None)])
def test_parse_bool(raw, expected):
    assert ing.parse_bool(raw) == expected


# ---------------- templates, default date, empty-table guard (H3/H13, L78)
def test_templates_mode_writes_and_upgrades_header_only_files(tmp_path):
    folder = slot(tmp_path, "2026-09-17"); folder.mkdir(parents=True)
    (folder / "search_counts.csv").write_text("observed_at,observer,query_title\n", encoding="utf-8")  # 2026-09-17 header
    assert ing.main(["--templates", "--date", "2026-09-17"], root=tmp_path) == 0
    assert list(pd.read_csv(folder / "search_counts.csv").columns) == ing.COUNT_COLS
    assert list(pd.read_csv(folder / "profiles_manual.csv").columns) == ing.PROFILE_COLS
    assert not processed(tmp_path).exists()


def test_templates_mode_never_touches_a_filled_file(tmp_path):
    folder = write_slot(tmp_path, [count_row()], [])
    before = (folder / "search_counts.csv").read_bytes()
    assert ing.main(["--templates", "--date", DATE], root=tmp_path) == 0
    assert (folder / "search_counts.csv").read_bytes() == before


def test_ingest_without_folder_creates_nothing(tmp_path):
    assert ing.main([], root=tmp_path) == 1
    assert not (tmp_path / "data").exists()


def test_ingest_defaults_to_latest_folder_and_refuses_empty_tables(tmp_path):
    write_slot(tmp_path, [count_row()], [], date="2026-09-17")
    write_slot(tmp_path, [], [], date=DATE)
    (slot(tmp_path, "2026-09-22_test")).mkdir(parents=True)  # suffixed folders are never "latest"
    assert ing.latest_folder(tmp_path / "data" / "raw" / "linkedin_supply") == DATE
    assert ing.main([], root=tmp_path) == 1  # latest (2026-09-21) is empty
    assert not processed(tmp_path).exists()
    assert ing.main(["--date", DATE, "--check"], root=tmp_path) == 0


def test_old_header_only_template_is_read_as_empty(tmp_path, capsys):
    folder = slot(tmp_path, "2026-09-17"); folder.mkdir(parents=True)
    (folder / "search_counts.csv").write_text("observed_at,observer,query_title\n", encoding="utf-8")
    (folder / "profiles_manual.csv").write_text("pseudo_id,observed_at\n", encoding="utf-8")
    assert ing.main(["--date", "2026-09-17", "--check"], root=tmp_path) == 0
    assert "older header" in capsys.readouterr().out


# ---------------- a clean ingest normalises before writing (L13, M52)
def test_ingest_writes_normalised_processed_tables(tmp_path):
    folder = write_slot(tmp_path, [count_row(acquisition_method="Manual_UI ", count_is_capped="YES", result_count="1000")],
                        [profile_row(has_kaggle_link="0", open_to_work_signal="")])
    df = pd.read_csv(folder / "search_counts.csv", dtype=str, keep_default_na=False); df["private_extra"] = "x"; df.to_csv(folder / "search_counts.csv", index=False)
    assert ing.main([], root=tmp_path) == 0
    c = pd.read_csv(processed(tmp_path) / "supply_linkedin_counts.csv", dtype=str, keep_default_na=False)
    p = pd.read_csv(processed(tmp_path) / "supply_linkedin_profiles.csv", dtype=str, keep_default_na=False)
    assert c.loc[0, "acquisition_method"] == "manual_ui" and c.loc[0, "count_is_capped"] == "true" and c.loc[0, "source_quality"] == "C"
    assert "private_extra" not in c.columns and c.loc[0, "collection_date"] == DATE
    assert p.loc[0, "has_github_link"] == "true" and p.loc[0, "has_kaggle_link"] == "false" and p.loc[0, "open_to_work_signal"] == ""
    assert p.loc[0, "source"] == "linkedin_manual" and p.loc[0, "source_quality"] == "C"


def test_check_mode_writes_nothing(tmp_path):
    write_slot(tmp_path, [count_row()], [profile_row()])
    assert ing.main(["--check"], root=tmp_path) == 0
    assert not processed(tmp_path).exists()


def test_other_collection_date_needs_replace(tmp_path):
    write_slot(tmp_path, [count_row()], [profile_row()], date="2026-09-17")
    assert ing.main(["--date", "2026-09-17"], root=tmp_path) == 0
    write_slot(tmp_path, [count_row()], [profile_row()])
    assert ing.main(["--date", DATE], root=tmp_path) == 1
    assert set(pd.read_csv(processed(tmp_path) / "supply_linkedin_profiles.csv", dtype=str).collection_date) == {"2026-09-17"}
    assert ing.main(["--date", DATE, "--replace"], root=tmp_path) == 0
    assert set(pd.read_csv(processed(tmp_path) / "supply_linkedin_profiles.csv", dtype=str).collection_date) == {DATE}


# ---------------- validation (M10, M11, M49, M50)
@pytest.mark.parametrize("counts,profiles,needle", [
    ([count_row(observer="")], [], "required column observer"),
    ([count_row(result_count="1,000+")], [], "result_count"),
    ([count_row(count_is_capped="maybe")], [], "count_is_capped"),
    ([count_row(source_quality="F")], [], "source_quality"),
    ([count_row(notes="seen at linkedin.com/in/someone")], [], "column notes"),
    ([count_row(evidence_ref="a@b.at")], [], "column evidence_ref"),
    ([count_row(acquisition_method="selenium_scrape")], [], "out of scope"),
    ([count_row(acquisition_method="phone_book")], [], "unknown acquisition_method"),
    ([count_row(observed_at="yesterday")], [], "observed_at"),
    ([], [profile_row(pseudo_id="")], "required column pseudo_id"),
    ([], [profile_row(current_title="")], "required column current_title"),
    ([], [profile_row(evidence_ref="")], "required column evidence_ref"),
    ([], [profile_row(), profile_row()], "duplicate pseudo_id"),
    ([], [profile_row(seniority_label="Senior Analyst")], "seniority_label"),
    ([], [profile_row(education_level="Master")], "education_level"),
    ([], [profile_row(prior_domain="art")], "prior_domain"),
    ([], [profile_row(years_experience_explicit="3.5")], "years_experience_explicit"),
    ([], [profile_row(current_title="Data Analyst @ ACME")], "column current_title"),
    ([], [profile_row(transition_wording="ex marketing, see linkedin.com/in/x")], "column transition_wording"),
    ([], [profile_row(acquisition_method="talent_insights")], "aggregates only"),
])
def test_validation_rejects(tmp_path, capsys, counts, profiles, needle):
    write_slot(tmp_path, counts, profiles)
    assert ing.main(["--check"], root=tmp_path) == 1
    out = capsys.readouterr().out
    assert needle in out
    assert "someone" not in out and "ACME" not in out  # problems name lines, never the cell content


# ---------------- build_supply fold (M53, M86, L133, M47)
def test_linkedin_fold_is_nan_safe_and_maps_coded_fields(tmp_path):
    rows = [profile_row(pseudo_id="AT-0001", certifications="", skills_listed="SQL;Python;Power BI", has_github_link="1.0",
                        transition_wording="from marketing", prior_domain="marketing", years_experience_explicit="3",
                        open_to_work_signal="true", education_level="none_stated"),
            profile_row(pseudo_id="AT-0002", current_title="Chef", location_text="", headline="", has_github_link="",
                        seniority_label="", source_quality="")]
    p = tmp_path / "supply_linkedin_profiles.csv"
    pd.DataFrame(rows).assign(collection_date=DATE, source="linkedin_manual").to_csv(p, index=False)
    a, b = B.linkedin_candidates(p)
    for c in (a, b):
        assert "nan" not in json.dumps(c, default=str).lower()
        assert c["n_repos_owned"] == 0 and c["hireable"] is False and c["frames"] == ["L"] and c["login"] is None
    assert a["bio"] == "Data Analyst" and "decisions" not in json.dumps(a)  # headline never copied
    assert a["bio_role_family"] == "data_analytics" and a["data_tier"] == "T1_bio_declared" and a["is_data_signal"]
    assert a["certifications_any"] == [] and {"SQL", "Python", "Power BI"} <= set(a["skills_any"])
    assert a["links_any"] == ["github"] and a["transition_explicit"] and a["prior_domains"] == ["marketing"]
    assert a["years_experience_explicit"] == 3 and a["open_to_work_signal"] is True and a["edu_levels_any"] == []
    assert a["state"] == "Steiermark" and a["collection_date"] == DATE
    assert b["bio_role_family"] is None and b["data_tier"] == "T0_none" and b["seniority_bio"] == "unknown"
    assert b["links_any"] == [] and b["open_to_work_signal"] is None and b["source_quality"] == "C"


def test_latest_github_folder_ignores_partial_and_suffixed_folders(tmp_path):
    for name, full in (("2026-09-17", True), ("2026-09-20", False), ("2026-09-18_test", True)):
        (tmp_path / name).mkdir()
        if full:
            (tmp_path / name / "profiles.jsonl").write_text("", encoding="utf-8")
    assert B.latest_github_folder(tmp_path) == "2026-09-17"


# ---------------- public summary contract (L79, L80, L101) and export wording (L110)
SUMMARY_KEYS = {"status", "linkedin_collection_dates", "search_counts_recorded", "profiles_recorded", "search_counts_by_method",
                "search_counts_by_source_quality", "profiles_by_method_n_ge_5", "profiles_by_method_other_or_suppressed",
                "profiles_by_source_quality_n_ge_5", "profiles_by_source_quality_other_or_suppressed", "profiles_by_location_n_ge_5",
                "profiles_by_location_other_or_suppressed", "languages_stated_n_ge_5", "public_profile_aggregates", "protocol"}


def test_public_summary_key_contract_and_dates():
    empty = public_linkedin_summary(pd.DataFrame(), None)
    assert set(empty) == SUMMARY_KEYS and "NOT COLLECTED" in empty["status"]
    counts = pd.DataFrame({"acquisition_method": ["manual_ui"] * 3 + ["talent_insights"], "source_quality": ["C"] * 3 + ["A"],
                           "collection_date": [DATE] * 4})
    profs = pd.DataFrame({"acquisition_method": ["manual_ui"] * 6, "source_quality": ["C"] * 6, "location_text": ["Graz"] * 6,
                          "collection_date": [DATE] * 6, "languages_stated": [float("nan")] * 6})
    s = public_linkedin_summary(counts, profs)
    assert set(s) == SUMMARY_KEYS and "status" in s
    assert s["linkedin_collection_dates"] == [DATE]
    assert s["search_counts_by_method"] == {"manual_ui": 3, "talent_insights": 1}
    assert s["profiles_by_method_n_ge_5"] == {"manual_ui": 6} and s["profiles_by_source_quality_n_ge_5"] == {"C": 6}
    assert "source_quality" not in s  # never inherits the GitHub grade
    assert "4 search counts, 6 coded profiles" in s["status"]


def test_small_cells_cannot_be_differenced():
    profs = pd.DataFrame({"location_text": ["Graz"] * 5 + [""] * 2})  # 7 in total, 2 not stated
    s = public_linkedin_summary(None, profs)
    shown = sum(s["profiles_by_location_n_ge_5"].values())
    rest = s["profiles_by_location_other_or_suppressed"]
    assert shown + rest == s["profiles_recorded"] and (rest == 0 or rest >= 5)


def test_export_wording_follows_the_slot_counts():
    assert "slot empty" in X.linkedin_open_question({"profiles_recorded": 0, "search_counts_recorded": 0})
    q = X.linkedin_open_question({"profiles_recorded": 12, "search_counts_recorded": 700, "linkedin_collection_dates": [DATE]})
    assert "slot empty" not in q and "12 coded profiles" in q and DATE in q
    assert X.linkedin_status({"status": "x"}) == "x"
    assert "status not recorded" in X.linkedin_status({})


def test_ingest_forwarder_matches_supply_common():
    profs = pd.DataFrame({"location_text": ["Graz"] * 5})
    assert ing.public_linkedin_summary(pd.DataFrame(), profs) == public_linkedin_summary(pd.DataFrame(), profs)
