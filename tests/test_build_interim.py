"""Unit tests for src/pipeline/build_interim.py: helpers and the per-source mapping to the common interim schema.

Runs everywhere on the synthetic raw tree from conftest.py (five sources, 18 envelopes, 17 unique postings).
"""
import json

import pandas as pd

import build_interim as BI


# ---------------- helpers
def test_strip_html_keeps_structure_and_unescapes():
    s = BI.strip_html("<h2>Profil</h2><ul><li>Python &amp; SQL</li><li>Power&nbsp;BI</li></ul><p>Graz<br/>Wien</p>")
    assert "<" not in s and ">" not in s
    assert "- Python & SQL" in s and "- Power\xa0BI" in s
    assert "Graz\nWien" in s
    assert BI.strip_html(None) is None and BI.strip_html("") is None


def test_date_helpers():
    assert BI.de_date("8.9.2026") == "2026-09-08"
    assert BI.de_date("31.12.2025 (aktualisiert)") == "2025-12-31"
    assert BI.de_date("gestern") is None and BI.de_date(None) is None
    assert BI.ms_to_date(1_757_980_800_000) == "2025-09-16"
    assert BI.ms_to_date("not a number") is None and BI.ms_to_date(None) is None


def test_read_jsonl_skips_blank_and_broken_lines(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text('{"a": 1}\n\n{broken\n{"a": 2}\n', encoding="utf-8")
    assert [r["a"] for r in BI.read_jsonl(p)] == [1, 2]
    assert list(BI.read_jsonl(tmp_path / "missing.jsonl")) == []


def test_latest_run_picks_the_newest_dated_folder(tmp_path, monkeypatch):
    for name in ("2026-09-16", "2026-09-18", "_scratch", "notes"):
        (tmp_path / "karriere" / name).mkdir(parents=True)
    (tmp_path / "karriere" / "2026-09-20.txt").write_text("", encoding="utf-8")  # a file, not a run folder
    monkeypatch.setattr(BI, "RAW", tmp_path)
    assert BI.latest_run("karriere").name == "2026-09-18"
    assert BI.latest_run("willhaben") is None
    assert BI.build_willhaben() == []  # a source without a run contributes nothing instead of failing


# ---------------- per-source mapping on the synthetic raw tree
def test_every_source_is_mapped_and_nothing_is_dropped(synthetic_interim):
    counts = synthetic_interim.source.value_counts().to_dict()
    assert counts == {"karriere": 6, "linkedin": 4, "eures": 3, "willhaben": 2, "jobsat": 2}
    assert synthetic_interim.posting_uid.is_unique
    assert synthetic_interim.title.notna().all()
    assert synthetic_interim.description_text.str.len().gt(300).all()


def test_listing_seen_under_two_queries_is_collapsed_with_both_queries(synthetic_interim):
    r = synthetic_interim.set_index("posting_uid").loc["karriere:101"]
    assert r.queries == ["business intelligence", "data analyst"]


def test_karriere_fields(synthetic_interim):
    r = synthetic_interim.set_index("posting_uid").loc["karriere:101"]
    assert r.company == "Example Analytics GmbH"
    assert r.posted_date == "2026-01-10"
    assert r.salary_min_raw == 3500 and r.salary_period_raw == "MONTH"
    assert r.location_regions == ["Steiermark"] and r.country_codes == ["AT"]
    assert r.remote_flag_raw == "home_office" and r.has_detail
    assert "<p>" not in r.description_text


def test_eures_anonymised_employer_and_nuts(synthetic_interim):
    r = synthetic_interim.set_index("posting_uid").loc["eures:E1"]
    assert r.company is None and r.company_raw == "siehe Beschreibung"
    assert r.nuts_codes == ["AT221"] and r.country_codes == ["AT"]
    assert r.posted_date == "2026-01-05"
    assert r.source_reference == "ref-E1"


def test_linkedin_willhaben_jobsat_fields(synthetic_interim):
    m = synthetic_interim.set_index("posting_uid")
    assert m.at["linkedin:L2", "seniority_raw"] == "Mid-Senior level"
    assert m.at["linkedin:L2", "query_locations"] == ["Austria"]
    assert m.at["willhaben:901", "salary_min_raw"] == 44000 and m.at["willhaben:901", "salary_period_raw"] == "YEAR"
    assert m.at["willhaben:901", "location_text"] == "Salzburg" and m.at["willhaben:901", "posted_date"] == "2026-01-02"
    # jobs.at: company and location come from the meta description
    assert m.at["jobsat:J1", "company"] == "Beratung Graz GmbH" and m.at["jobsat:J1", "location_text"] == "Graz"


def _isolate(monkeypatch, raw, out):
    """Point the module at a temporary tree and reset its per-run globals (restored after the test)."""
    from collections import defaultdict
    monkeypatch.setattr(BI, "RAW", raw)
    monkeypatch.setattr(BI, "OUT", out)
    for name, value in (("RUN_DATE", None), ("SKIPPED_LINES", defaultdict(int)), ("RUNS_USED", {})):
        if hasattr(BI, name):
            monkeypatch.setattr(BI, name, value)


def test_main_writes_jsonl_and_parquet(synthetic_raw, tmp_path, monkeypatch):
    _isolate(monkeypatch, synthetic_raw, tmp_path)
    BI.main([])
    rows = [json.loads(line) for line in (tmp_path / "interim_postings.jsonl").read_text(encoding="utf-8").splitlines()]
    pq = pd.read_parquet(tmp_path / "interim_postings.parquet")
    assert len(rows) == len(pq) == 17
    assert set(pq.posting_uid) == {r["posting_uid"] for r in rows}
    # list columns survive in the jsonl and are JSON strings in the parquet
    k = next(r for r in rows if r["posting_uid"] == "karriere:101")
    assert k["queries"] == ["business intelligence", "data analyst"]
    assert json.loads(pq.set_index("posting_uid").at["karriere:101", "queries"]) == k["queries"]


def test_main_with_explicit_date_and_manifest(synthetic_raw, tmp_path, monkeypatch):
    from conftest import RUN_DATE
    _isolate(monkeypatch, synthetic_raw, tmp_path)
    BI.main(["--date", RUN_DATE])
    manifest = json.loads((tmp_path / "interim_build_manifest.json").read_text(encoding="utf-8"))
    assert manifest["requested_date"] == RUN_DATE
    assert manifest["rows_total"] == 17
    assert manifest["unique_postings_per_source"] == {"eures": 3, "karriere": 6, "linkedin": 4, "willhaben": 2, "jobsat": 2}


def test_main_refuses_a_missing_date_and_an_empty_tree(synthetic_raw, tmp_path, monkeypatch):
    import pytest
    _isolate(monkeypatch, synthetic_raw, tmp_path)
    with pytest.raises(SystemExit):
        BI.main(["--date", "1999-01-01"])
    _isolate(monkeypatch, tmp_path / "empty_raw", tmp_path)
    with pytest.raises(SystemExit):
        BI.main([])
    assert not (tmp_path / "interim_postings.jsonl").exists()


# ---------------- single-date snapshot rule for recurring runs (--allow-missing / --exclude, manifest record)
def _own_copy(synthetic_raw, tmp_path):
    """The synthetic raw tree is shared between tests; tests that remove or add folders work on their own copy."""
    import shutil
    dst = tmp_path / "raw_copy"
    shutil.copytree(synthetic_raw, dst)
    return dst


def _manifest(tmp_path):
    return json.loads((tmp_path / "interim_build_manifest.json").read_text(encoding="utf-8"))


def test_missing_source_with_allow_missing_is_left_out_and_recorded(synthetic_raw, tmp_path, monkeypatch):
    import shutil
    from conftest import RUN_DATE
    raw = _own_copy(synthetic_raw, tmp_path)
    shutil.rmtree(raw / "linkedin" / RUN_DATE)
    (raw / "linkedin" / "2025-12-01").mkdir(parents=True)                   # an older folder must NOT be substituted
    _isolate(monkeypatch, raw, tmp_path)
    BI.main(["--date", RUN_DATE, "--allow-missing"])
    man = _manifest(tmp_path)
    assert man["unique_postings_per_source"]["linkedin"] == 0 and man["rows_total"] == 13
    assert man["run_folders"]["linkedin"] is None and man["folder_dates"] == [RUN_DATE] and man["mixed_dates"] is False
    assert man["source_status"]["linkedin"] == {"status": "missing", "folder": None, "reason": f"no folder {RUN_DATE}", "n_postings": 0}
    assert man["source_status"]["eures"]["status"] == "current" and man["source_status"]["eures"]["folder"] == f"data/raw/eures/{RUN_DATE}"
    assert man["excluded_sources"] == {"linkedin": f"no folder {RUN_DATE}"}
    assert "never replaced by an older folder" in man["snapshot_rule"]
    assert "linkedin" not in set(pd.read_parquet(tmp_path / "interim_postings.parquet").source)


def test_exclude_names_a_source_whose_folder_exists_but_is_unusable(synthetic_raw, tmp_path, monkeypatch):
    from conftest import RUN_DATE
    _isolate(monkeypatch, synthetic_raw, tmp_path)
    BI.main(["--date", RUN_DATE, "--exclude", "karriere=blocked: 3 consecutive 403", "--exclude", "jobsat"])
    man = _manifest(tmp_path)
    assert man["unique_postings_per_source"]["karriere"] == 0 and man["unique_postings_per_source"]["jobsat"] == 0
    assert man["source_status"]["karriere"]["status"] == "excluded"
    assert man["excluded_sources"] == {"karriere": "blocked: 3 consecutive 403", "jobsat": "excluded by caller"}
    assert man["rows_total"] == 9


def test_a_missing_source_without_allow_missing_is_still_an_error(synthetic_raw, tmp_path, monkeypatch):
    import shutil
    import pytest
    from conftest import RUN_DATE
    raw = _own_copy(synthetic_raw, tmp_path)
    shutil.rmtree(raw / "linkedin" / RUN_DATE)
    _isolate(monkeypatch, raw, tmp_path)
    with pytest.raises(SystemExit):
        BI.main(["--date", RUN_DATE])
    for bad in (["--allow-missing"], ["--date", RUN_DATE, "--exclude", "stepstone"]):
        _isolate(monkeypatch, raw, tmp_path)
        with pytest.raises(SystemExit):
            BI.main(bad)


def test_legacy_newest_per_source_mode_refuses_mixed_dates(synthetic_raw, tmp_path, monkeypatch):
    import pytest
    raw = _own_copy(synthetic_raw, tmp_path)
    (raw / "linkedin" / "2026-02-01").mkdir()                                 # newer, empty folder for one source only
    _isolate(monkeypatch, raw, tmp_path)
    with pytest.raises(SystemExit) as e:
        BI.main([])
    assert "different dates" in str(e.value) and "nothing written" in str(e.value)
    assert not (tmp_path / "interim_postings.parquet").exists()
    assert not (tmp_path / "interim_postings.jsonl").exists()
    assert not (tmp_path / "interim_build_manifest.json").exists()


def test_allow_mixed_keeps_the_old_behaviour(synthetic_raw, tmp_path, monkeypatch, capsys):
    from conftest import RUN_DATE
    raw = _own_copy(synthetic_raw, tmp_path)
    (raw / "linkedin" / "2026-02-01").mkdir()
    _isolate(monkeypatch, raw, tmp_path)
    BI.main(["--allow-mixed"])
    man = _manifest(tmp_path)
    assert man["mixed_dates"] is True and man["folder_dates"] == [RUN_DATE, "2026-02-01"]
    assert "not one snapshot" in capsys.readouterr().out


def test_single_date_legacy_build_is_not_mixed(synthetic_raw, tmp_path, monkeypatch):
    _isolate(monkeypatch, synthetic_raw, tmp_path)
    BI.main([])                                                               # every source has the same newest date
    man = _manifest(tmp_path)
    assert man["mixed_dates"] is False and len(man["folder_dates"]) == 1
