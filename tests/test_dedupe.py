"""Unit tests for src/pipeline/dedupe.py: fingerprint, union-find, the four duplicate rules and the canonical choice.

Runs everywhere: hand-made frames plus the synthetic raw tree from conftest.py (no private data needed).
"""
import pandas as pd
import pytest

import dedupe as D

LONG = ("Wir suchen eine Person für Datenanalyse mit Python und SQL in einem wachsenden Team. " * 6).strip()


def _row(uid, source, title, company, state, desc=LONG):
    return {"posting_uid": uid, "source": source, "title_clean": title, "company_norm": company, "state": state,
            "description_text": desc, "role_family": "data_analytics"}


def _groups(df):
    """uid -> frozenset of uids in the same group (independent of the generated group ids)."""
    members = df.groupby("dedupe_group_id").posting_uid.apply(frozenset)
    return {u: members[g] for u, g in zip(df.posting_uid, df.dedupe_group_id)}


# ---------------- fingerprint
def test_fingerprint_needs_200_characters():
    assert D.fingerprint(None) is None
    assert D.fingerprint("") is None
    assert D.fingerprint("x" * 199) is None
    assert D.fingerprint("x" * 200) == "x" * 200


def test_fingerprint_ignores_case_punctuation_and_whitespace():
    a = "Data  Analyst, (m/w/d) -- Graz!\n" + LONG
    b = "data analyst m w d graz " + LONG.upper()
    assert D.fingerprint(a) == D.fingerprint(b)


def test_fingerprint_uses_only_the_first_400_normalised_characters():
    base = "a" * 400
    assert D.fingerprint(base + " ending one") == D.fingerprint(base + " a different ending")
    assert len(D.fingerprint(LONG * 3)) == 400


# ---------------- union-find
def test_union_find_is_transitive():
    uf = D.UF(5)
    uf.union(0, 1)
    uf.union(3, 4)
    uf.union(1, 4)
    assert len({uf.find(i) for i in (0, 1, 3, 4)}) == 1
    assert uf.find(2) == 2


# ---------------- grouping rules
def test_rule_b_company_title_state():
    df = D.assign_groups(pd.DataFrame([
        _row("karriere:1", "karriere", "data analyst", "acme", "Steiermark", desc="short"),
        _row("linkedin:1", "linkedin", "data analyst", "acme", "Steiermark", desc="also short"),
        _row("linkedin:2", "linkedin", "data analyst", "acme", "Wien", desc="short again"),  # other state, no fingerprint
    ]))
    g = _groups(df)
    assert g["karriere:1"] == {"karriere:1", "linkedin:1"}
    assert g["linkedin:2"] == {"linkedin:2"}
    assert df.set_index("posting_uid").dedupe_method.to_dict() == {
        "karriere:1": "group_root", "linkedin:1": "company_title_state", "linkedin:2": "unique"}


def test_rule_c_title_fingerprint_is_state_agnostic():
    """EURES rows with an anonymised employer can only match through the fingerprint, whatever the state."""
    df = D.assign_groups(pd.DataFrame([
        _row("karriere:1", "karriere", "junior data scientist", "acme", "Steiermark"),
        _row("eures:1", "eures", "junior data scientist", None, "Wien"),
        _row("eures:2", "eures", "senior data scientist", None, "Wien"),  # same text, other title -> not a duplicate
    ]))
    g = _groups(df)
    assert g["eures:1"] == {"karriere:1", "eures:1"}
    assert g["eures:2"] == {"eures:2"}
    assert df.set_index("posting_uid").at["eures:1", "dedupe_method"] == "title_fingerprint"


def test_rule_d_company_title_only_when_one_side_has_no_state():
    df = D.assign_groups(pd.DataFrame([
        _row("a:1", "karriere", "bi developer", "acme", "Wien", desc="x"),
        _row("a:2", "jobsat", "bi developer", "acme", None, desc="y"),
        _row("b:1", "karriere", "bi consultant", "beta", "Wien", desc="x"),
        _row("b:2", "jobsat", "bi consultant", "beta", "Tirol", desc="y"),  # both states known and different
    ]))
    g = _groups(df)
    assert g["a:1"] == {"a:1", "a:2"}
    assert df.set_index("posting_uid").at["a:2", "dedupe_method"] == "company_title_nostate"
    assert g["b:1"] == {"b:1"} and g["b:2"] == {"b:2"}


def test_groups_chain_across_rules():
    """a~b by (b) and b~c by (c) put a, b and c in one group (union-find, not pairwise)."""
    df = D.assign_groups(pd.DataFrame([
        _row("a", "karriere", "data engineer", "acme", "Wien", desc="short a"),
        _row("b", "linkedin", "data engineer", "acme", "Wien"),
        _row("c", "eures", "data engineer", None, "Steiermark"),
    ]))
    assert df.dedupe_group_id.nunique() == 1
    assert (df.dedupe_group_size == 3).all()
    assert df.sources_in_group.iloc[0] == "eures,karriere,linkedin"


def test_canonical_is_longest_description_then_source_priority():
    df = D.assign_groups(pd.DataFrame([
        _row("jobsat:1", "jobsat", "data analyst", "acme", "Wien", desc="z" * 50),
        _row("linkedin:1", "linkedin", "data analyst", "acme", "Wien", desc="z" * 80),   # longest wins
        _row("karriere:1", "karriere", "data analyst", "acme", "Wien", desc="z" * 60),
        _row("willhaben:2", "willhaben", "bi analyst", "beta", "Tirol", desc="q" * 40),
        _row("karriere:2", "karriere", "bi analyst", "beta", "Tirol", desc="q" * 40),    # tie -> karriere before willhaben
        _row("eures:3", "eures", "bi lead", "gamma", "Wien", desc=None),                 # missing description counts as length 0
        _row("jobsat:3", "jobsat", "bi lead", "gamma", "Wien", desc="w"),
    ]))
    canon = set(df[df.is_canonical].posting_uid)
    assert canon == {"linkedin:1", "karriere:2", "jobsat:3"}


def test_exactly_one_canonical_per_group_and_sizes_add_up(synthetic_dedup):
    g = synthetic_dedup.groupby("dedupe_group_id")
    assert (g.is_canonical.sum() == 1).all()
    assert (g.size() == g.dedupe_group_size.first()).all()
    assert synthetic_dedup.posting_uid.is_unique


def test_synthetic_duplicates_are_found(synthetic_dedup):
    g = _groups(synthetic_dedup)
    m = synthetic_dedup.set_index("posting_uid")
    # same company + title + state on karriere and LinkedIn
    assert g["karriere:101"] == {"karriere:101", "linkedin:L1"}
    assert m.at["linkedin:L1", "dedupe_method"] == "company_title_state"
    # anonymised EURES copy of a karriere ad: same title + same description
    assert g["eures:E1"] == {"eures:E1", "karriere:104"}
    assert m.at["karriere:104", "dedupe_method"] == "title_fingerprint"
    # equal description length -> source priority: karriere is canonical, not EURES
    assert m.at["karriere:104", "is_canonical"] and not m.at["eures:E1", "is_canonical"]
    # the LinkedIn copy carries a longer description, so it is the canonical row of its group
    assert m.at["linkedin:L1", "is_canonical"] and not m.at["karriere:101", "is_canonical"]
    assert synthetic_dedup.dedupe_group_id.nunique() == len(synthetic_dedup) - 2


def test_main_writes_outputs_and_summary(synthetic_interim, synthetic_dedup, tmp_path, monkeypatch):
    """dedupe.main() on the synthetic normalised rows: jsonl + parquet + dedupe_summary.csv, all rows kept."""
    proc, tab = tmp_path / "processed", tmp_path / "tables"
    proc.mkdir(); tab.mkdir()
    cols = [c for c in synthetic_dedup.columns
            if c not in ("dedupe_group_id", "dedupe_group_size", "is_canonical", "dedupe_method", "sources_in_group")]
    synthetic_dedup[cols].to_json(proc / "postings_normalized.jsonl", orient="records", lines=True, force_ascii=False)
    monkeypatch.setattr(D, "PROC", proc)
    monkeypatch.setattr(D, "TAB", tab)
    D.main()
    out = pd.read_json(proc / "postings_dedup.jsonl", lines=True)
    assert len(out) == len(synthetic_interim)
    assert len(pd.read_parquet(proc / "postings_dedup.parquet")) == len(out)
    s = pd.read_csv(tab / "dedupe_summary.csv").iloc[0]
    assert s.rows_total == len(out)
    assert s.unique_groups_total == out.dedupe_group_id.nunique()
    assert 0 <= s.duplicate_rate_in_scope < 1


@pytest.mark.parametrize("state", [None, float("nan")])
def test_missing_state_forms_its_own_key(state):
    """NaN and None states both count as 'no state' for rule (d)."""
    df = D.assign_groups(pd.DataFrame([
        _row("x:1", "karriere", "data analyst", "acme", "Wien", desc="a"),
        _row("x:2", "jobsat", "data analyst", "acme", state, desc="b"),
    ]))
    assert df.dedupe_group_id.nunique() == 1
