"""Synthetic-data tests for src/analysis/labelling_audit.py and src/pipeline/snapshot_tracking.py.
No private data is read; nothing is written outside pytest's tmp_path.
Run: python -m pytest tests/test_labelling_and_snapshots.py -q
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "analysis"))
sys.path.insert(0, str(ROOT / "src" / "pipeline"))
import labelling_audit as LA  # noqa: E402
import snapshot_tracking as ST  # noqa: E402


# ------------------------------------------------------------------ synthetic corpus
def _corpus(n_core=40, n_sig=120, n_nosig=140, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_core):
        rows.append({"title": f"Data Analyst {i}", "description_text": "SQL und Python erforderlich. " * 20, "role_family": "data_analytics"})
    for i in range(n_sig):
        rows.append({"title": f"Controller {i}", "description_text": "Reporting und KPI Dashboards. " * 20,
                     "role_family": "other_data" if i % 10 == 0 else "out_of_scope"})
    for i in range(n_nosig):
        rows.append({"title": f"Koch {i}", "description_text": "Küche, Service, Gäste. " * 20, "role_family": "out_of_scope"})
    df = pd.DataFrame(rows)
    df["posting_uid"] = [f"karriere:{i}" for i in range(len(df))]
    df["company"] = "Firma " + df.index.astype(str)
    df["is_canonical"] = True
    df["normalized_title"] = np.where(df.role_family == "data_analytics", "Data Analyst", None)
    df["german_requirement"] = rng.choice(["required", "preferred", "not_mentioned", "german_or_english"], len(df))
    df["german_level_bucket"] = np.where(df.german_requirement == "required", "C1/fluent", None)
    df["salary_basis"] = rng.choice(["minimum_only", "range", "none"], len(df))
    df["salary_min_annual_eur"] = np.where(df.salary_basis == "none", np.nan, 49000.0)
    df["salary_max_annual_eur"] = np.nan
    df["salary_period"] = np.where(df.salary_basis == "none", None, "month")
    df["salary_source"] = "text"
    df["salary_text_raw"] = None
    for c in LA.SKILL_COLS:
        df[f"skills_{c}"] = "[]"
    df["skills_programming_languages"] = np.where(df.role_family == "data_analytics", json.dumps(["SQL", "Python"]), "[]")
    return df


# ------------------------------------------------------------------ helpers
def test_wilson_bounds():
    lo, hi = LA.wilson(8, 10)
    assert 0 < lo < 0.8 < hi < 1
    assert np.isnan(LA.wilson(0, 0)[0])


@pytest.mark.parametrize("raw,val", [("3.500,00", 3500.0), ("3,500.00", 3500.0), ("€ 48.000", 48000.0), ("3500", 3500.0),
                                     ("2800,50", 2800.5), ("", None)])
def test_parse_amount(raw, val):
    assert LA.parse_amount(raw) == val


def test_sheet_roundtrip_semicolon(tmp_path):
    df = pd.DataFrame({"row_id": ["001"], "title": ["A; B, C"], "label_data_role": [""]})
    LA.write_sheet(df, tmp_path / "s.csv")
    back = LA.read_sheet(tmp_path / "s.csv")
    assert back.loc[0, "title"] == "A; B, C" and back.loc[0, "row_id"] == "001"


def test_private_dir_gets_gitignore(tmp_path, monkeypatch):
    monkeypatch.setattr(LA, "LABELS", tmp_path / "labels")
    monkeypatch.setattr(LA, "PRIVATE", tmp_path / "private")
    LA.ensure_private_dir(tmp_path / "labels" / "2026-10-01")
    assert (tmp_path / "labels" / ".gitignore").read_text(encoding="utf-8").strip().endswith("*")


def test_public_guard_blocks_row_level_columns():
    with pytest.raises(ValueError):
        LA.assert_aggregate_only(pd.DataFrame({"posting_uid": ["x"], "recall": [1.0]}), "t")


# ------------------------------------------------------------------ recall
def test_recall_sample_is_blind_and_stratified():
    df = _corpus()
    sheet, key, texts = LA.draw_recall_sample(df, n=100, design="stratified", seed=3)
    assert len(sheet) == 100 and len(key) == 100 and len(texts) == 100
    assert not {"pred_family", "pred_core", "posting_uid", "stratum", "role_family"} & set(sheet.columns)
    assert set(key.stratum) == {"S1_pred_core", "S2_noncore_data_signal", "S3_noncore_no_signal"}
    n_by = key.groupby("stratum").row_id.count()
    assert n_by["S1_pred_core"] == 20 and n_by["S2_noncore_data_signal"] == 60
    # shuffled: first 20 rows are not all from one stratum
    assert key.head(20).stratum.nunique() > 1
    # SRS design
    _, k2, _ = LA.draw_recall_sample(df, n=50, design="srs", seed=3)
    assert (k2.stratum == "SRS_all_canonical").all() and (k2.stratum_N == len(df)).all()


def test_recall_score_known_truth(tmp_path):
    """Truth: every core posting and every other_data posting is a data role -> recall = 40 / (40 + 12)."""
    df = _corpus()
    sheet, key, _ = LA.draw_recall_sample(df, n=300, design="stratified", seed=5)  # takes whole strata here
    fam = key.set_index("row_id").pred_family
    sheet["label_data_role"] = sheet.row_id.map(lambda r: "Y" if fam[r] in ("data_analytics", "other_data") else "N")
    sheet["label_family"] = sheet.row_id.map(lambda r: "DA" if fam[r] == "data_analytics" else "")
    # round-trip through CSV like the owner's file
    LA.write_sheet(sheet, tmp_path / "s.csv")
    LA.write_sheet(key, tmp_path / "k.csv")
    q10, q10b, priv = LA.score_recall(LA.read_sheet(tmp_path / "s.csv"), LA.read_sheet(tmp_path / "k.csv"), n_boot=200)
    got = q10.set_index("metric")
    n_other = int((df.role_family == "other_data").sum())
    assert got.loc["recall_core", "estimate"] == pytest.approx(40 / (40 + n_other), abs=0.01)
    assert got.loc["recall_core_or_adjacent", "estimate"] == pytest.approx(1.0)
    assert got.loc["precision_core", "estimate"] == pytest.approx(1.0)
    assert got.loc["est_missed_data_roles", "estimate"] == pytest.approx(n_other, abs=0.5)
    assert got.loc["family_agreement_among_found", "estimate"] == pytest.approx(1.0)
    assert list(q10b.pred_family) == ["other_data"]
    LA.assert_aggregate_only(q10, "Q10")
    LA.assert_aggregate_only(q10b, "Q10b")
    assert len(priv) == n_other and "title" in priv.columns  # private diagnostics keep titles


def test_recall_weights_correct_oversampling():
    """Stratified sample with unequal inclusion probabilities must recover the population recall."""
    df = _corpus(n_core=50, n_sig=500, n_nosig=500, seed=2)
    # truth: core all data roles; 5 % of signal stratum are missed data roles (out_of_scope); none in no-signal
    sig_idx = df.index[(df.title.str.startswith("Controller")) & (df.role_family == "out_of_scope")]
    missed = set(df.loc[sig_idx[::20], "posting_uid"])
    truth_n = 50 + len(missed)
    sheet, key, _ = LA.draw_recall_sample(df, n=300, design="stratified", seed=11)
    uid = key.set_index("row_id").posting_uid
    fam = key.set_index("row_id").pred_family
    sheet["label_data_role"] = sheet.row_id.map(lambda r: "Y" if fam[r] == "data_analytics" or uid[r] in missed else "N")
    q10, _, _ = LA.score_recall(sheet, key, n_boot=200)
    est = q10.set_index("metric").loc["recall_core"]
    assert est.ci_low <= 50 / truth_n <= est.ci_high


def test_recall_requires_labels():
    df = _corpus()
    sheet, key, _ = LA.draw_recall_sample(df, n=30, seed=1)
    with pytest.raises(SystemExit):
        LA.score_recall(sheet, key)


# ------------------------------------------------------------------ extractors
def test_extractor_sample_and_score():
    df = _corpus()
    sheet, key, texts = LA.draw_extractor_sample(df, n=20, seed=1)
    assert len(sheet) == 20 and not {"pred_skills", "pred_german_requirement"} & set(sheet.columns)
    assert all(t["text"] for t in texts)
    # labeller agrees on SQL, finds Python missing in half, adds Excel the extractor missed
    sheet["skills_done"] = "1"
    sheet["sk_SQL"] = "1"
    sheet["sk_PY"] = ["1" if i % 2 else "" for i in range(20)]
    sheet["sk_EXCEL"] = "x"
    k = key.set_index("row_id")
    sheet["lang_done"] = "1"
    sheet["de_class"] = sheet.row_id.map(lambda r: LA.GERMAN_MAP[k.loc[r, "pred_german_requirement"]])
    sheet["de_level"] = sheet.row_id.map(lambda r: "C1" if k.loc[r, "pred_german_requirement"] == "required" else "")
    sheet["sal_done"] = "1"
    sheet["sal_basis"] = sheet.row_id.map(lambda r: {"none": "NONE", "range": "RANGE", "minimum_only": "MIN"}[k.loc[r, "pred_salary_basis"]])
    sheet["sal_amount"] = sheet.sal_basis.map(lambda b: "" if b == "NONE" else "3.500,00")
    sheet["sal_period"] = sheet.sal_basis.map(lambda b: "" if b == "NONE" else "M")
    q11 = LA.score_extractor(sheet, key)
    LA.assert_aggregate_only(q11, "Q11")
    g = q11.set_index(["field", "class", "metric"])["value"]
    assert g[("skill", "SQL", "recall")] == 1.0 and g[("skill", "SQL", "precision")] == 1.0
    assert g[("skill", "Python", "precision")] == pytest.approx(0.5)
    assert g[("skill", "Excel", "recall")] == 0.0
    assert g[("german_requirement", "5-class", "accuracy")] == 1.0
    assert g[("salary", "figure present", "recall")] == 1.0
    assert g[("salary", "annual minimum within 2 %", "accuracy")] == 1.0  # 3,500 x 14 = 49,000


def test_extractor_partial_blocks_are_ignored():
    df = _corpus()
    sheet, key, _ = LA.draw_extractor_sample(df, n=10, seed=1)
    assert LA.score_extractor(sheet, key).empty  # nothing ticked done -> nothing scored


# ------------------------------------------------------------------ projects
def _projects(n=60):
    rng = np.random.default_rng(0)
    p = pd.DataFrame({"project_id": [f"h{i}" for i in range(n)], "repo_full_name": [f"user{i}/repo{i}" for i in range(n)],
                      "is_substantive": [i % 3 != 0 for i in range(n)], "archetype": "analytics_project",
                      "readme_length_bucket": "medium (1.5k–5k)"})
    for f in set(LA.STRUCTURE_FLAGS) | {d for v in LA.RUBRIC_DETECTORS.values() for d in v}:
        p[f] = rng.random(n) > 0.5
    return p


def test_project_sample_and_score():
    sheet, key = LA.draw_project_sample(_projects(), n=40, seed=1)
    assert len(sheet) == 40 and sheet.repo_url.str.startswith("https://github.com/").all()
    assert "repo_full_name" not in key.columns and "repo_url" not in key.columns
    k = key.set_index("row_id")
    for c, _ in LA.RUBRIC:
        sheet[c] = sheet.row_id.map(lambda r: "2" if k.loc[r, "rd_h_methodology"] else "0")
    sheet["rated_done"] = "1"
    sheet.loc[0, "unavailable"] = "1"
    q12, q12b = LA.score_projects(sheet, key, n_boot=100)
    LA.assert_aggregate_only(q12, "Q12")
    LA.assert_aggregate_only(q12b, "Q12b")
    assert q12.iloc[-1]["n_unavailable"] == 1
    cal = q12b[(q12b.analysis == "detector_recall") & q12b.feature.str.startswith("q_method")]
    assert cal.value.iloc[0] == 1.0


# ------------------------------------------------------------------ application log
def test_application_log_template_and_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(LA, "PRIVATE", tmp_path / "private")
    p = LA.init_application_log(tmp_path / "private" / "application_log.csv")
    assert list(LA.read_sheet(p).columns) == LA.APPLICATION_LOG_COLUMNS
    assert (tmp_path / "private" / ".gitignore").exists()
    log = pd.DataFrame([{c: "" for c in LA.APPLICATION_LOG_COLUMNS} for _ in range(4)])
    log["application_date"] = "2026-10-01"
    log["stated_german_class"] = ["REQ", "REQ", "NONE", "NONE"]
    log["response"] = ["rejection", "none", "interview", "screening"]
    log["interview"] = ["", "", "1", ""]
    log["offer"] = ["", "", "1", ""]
    out = LA.summarise_applications(log)
    allrow = out[out.dimension == "ALL"].iloc[0]
    assert allrow.n_applications == 4 and allrow.responded_rate == 0.75 and allrow.offered_rate == 0.25
    assert not {"employer", "role_title", "posting_uid"} & set(out.columns)


# ------------------------------------------------------------------ snapshots
def _snap(uids, company="acme", title="data analyst"):
    return pd.DataFrame({"posting_uid": uids, "source": [u.split(":")[0] for u in uids], "company_norm": company,
                         "title_clean": [f"{title} {u}" for u in uids], "state": "Steiermark",
                         "role_family": "data_analytics", "is_canonical": True,
                         "dedupe_group_id": [f"g{i}" for i in range(len(uids))]})


def test_merge_snapshot_first_last_seen():
    h = ST.merge_snapshot(None, _snap(["k:1", "k:2", "l:3"]), "2026-09-16")
    h = ST.merge_snapshot(h, _snap(["k:2", "l:3", "l:4"]), "2027-01-10")
    h = ST.merge_snapshot(h, _snap(["l:3", "k:5"]), "2027-04-02").set_index("posting_uid")
    assert h.loc["k:1", "first_seen"] == "2026-09-16" and h.loc["k:1", "last_seen"] == "2026-09-16"
    assert not h.loc["k:1", "active_in_latest"]
    assert h.loc["l:3", "n_snapshots"] == 3 and h.loc["l:3", "last_seen"] == "2027-04-02"
    assert h.loc["k:2", "n_snapshots"] == 2 and h.loc["k:2", "last_seen"] == "2027-01-10"
    assert h.loc["k:5", "first_seen"] == "2027-04-02" and h.loc["k:5", "active_in_latest"]
    c = ST.add_censoring(h.reset_index()).set_index("posting_uid")
    assert c.loc["l:3", "left_censored"] and c.loc["l:3", "right_censored"] and c.loc["l:3", "days_observed"] == 198
    assert not c.loc["l:4", "left_censored"] and not c.loc["l:4", "right_censored"]


def test_merge_snapshot_is_idempotent_and_ordered():
    s = _snap(["k:1", "k:2"])
    h1 = ST.merge_snapshot(None, s, "2026-09-16")
    h2 = ST.merge_snapshot(h1, s, "2026-09-16")
    pd.testing.assert_frame_equal(h1, h2)
    with pytest.raises(ValueError):
        ST.merge_snapshot(h1, s, "2026-01-01")


def test_merge_snapshot_rejects_bad_keys():
    with pytest.raises(ValueError):
        ST.merge_snapshot(None, _snap(["k:1", "k:1"]), "2026-09-16")
    bad = _snap(["k:1"])
    bad.loc[0, "posting_uid"] = None
    with pytest.raises(ValueError):
        ST.merge_snapshot(None, bad, "2026-09-16")


def test_group_first_seen_survives_canonical_source_switch():
    h = ST.merge_snapshot(None, _snap(["karriere:1"]), "2026-09-16")
    cur = _snap(["karriere:1", "linkedin:9"])
    cur["dedupe_group_id"] = "g0"  # same job on two boards; canonical may now be the LinkedIn row
    h = ST.merge_snapshot(h, cur, "2027-01-10")
    g = ST.group_first_seen(h, cur).iloc[0]
    assert g.group_first_seen == "2026-09-16" and g.n_members == 2 and g.n_members_seen_before == 1


def test_uid_stability_detects_reposts():
    prev = _snap(["k:1", "k:2", "k:3"])
    cur = _snap(["k:1", "k:7"])
    cur.loc[cur.posting_uid == "k:7", "title_clean"] = "data analyst k:2"  # k:2 re-posted under a new id
    r = ST.uid_stability(prev, cur)
    assert r["n_persisting"] == 1 and r["n_disappeared"] == 2 and r["n_new"] == 1 and r["suspected_rekeyed"] == 1
