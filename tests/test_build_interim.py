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
