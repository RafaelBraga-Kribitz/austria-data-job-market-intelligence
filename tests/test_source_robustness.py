"""A snapshot that lacks one Layer 1 source (e.g. LinkedIn left out of a partial weekly collection) must not crash the build.

Regression for the 2026-10-16 weekly run, which stopped in run_analysis.py at `.sort_values("linkedin")` (KeyError) because the
snapshot had no LinkedIn rows. A missing source gives a zero column or a plain-wording fallback and a warning, never an exception.
Everything is written to tmp_path; nothing reads or writes outputs/ or data/.
"""
from __future__ import annotations

import pandas as pd
import pytest

import data_quality as DQ
import run_analysis as RA
import visual_questions_demand as VQD
import visual_questions_evidence as VQE


def test_industry_table_without_linkedin_rows_keeps_its_shape(capsys):
    core = pd.DataFrame({"source": ["eures", "eures", "karriere"], "industry_raw": ["IT", None, "IT"]})
    t = RA.industry_by_source(core)
    assert "linkedin" in t.columns and (t["linkedin"] == 0).all()
    assert t.loc["IT", "eures"] == 1 and t.loc["IT", "karriere"] == 1 and t.loc["unspecified", "eures"] == 1
    assert "WARNING" in capsys.readouterr().out


def test_industry_table_with_linkedin_rows_is_sorted_by_linkedin(capsys):
    core = pd.DataFrame({"source": ["linkedin", "linkedin", "linkedin", "eures"], "industry_raw": ["A", "B", "B", "A"]})
    t = RA.industry_by_source(core)
    assert list(t.index) == ["B", "A"] and "WARNING" not in capsys.readouterr().out


def test_share_table_of_an_empty_skill_group_keeps_its_columns():
    df = pd.DataFrame({"skills_x": [[], []], "role_family": ["a", "b"]})
    for t in (RA.share_table(df, "skills_x", "skill"), RA.share_table(df, "skills_x", "skill", "role_family")):
        assert t.empty and {"skill", "count", "share"} <= set(t.columns)
        t.sort_values("count", ascending=False)


def test_linkedin_salary_sentence_falls_back_without_linkedin(capsys):
    basis = pd.DataFrame({"source": ["eures", "karriere"], "none": [5, 3], "implausible": [0, 1], "range": [2, 2]}).set_index("source")
    assert VQE.linkedin_no_figure_text(basis) is None
    assert "WARNING" in capsys.readouterr().out
    basis.loc["linkedin"] = [6, 2, 2]
    assert VQE.linkedin_no_figure_text(basis) == VQD.pct_txt(0.8)


def test_largest_sources_text_follows_the_data():
    src = pd.DataFrame({"source": ["eures", "karriere", "willhaben"], "in_scope_canonical": [10, 30, 20]})
    assert VQE.largest_sources_text(src) == "karriere.at and willhaben"
    assert VQE.largest_sources_text(src.assign(in_scope_canonical=0)) == ""


def test_layer1_analysis_and_visual_evidence_run_on_a_snapshot_without_linkedin(synthetic_dedup, tmp_path, monkeypatch):
    df = synthetic_dedup[synthetic_dedup.source != "linkedin"].copy()
    df["description_length"] = df["description_length"].clip(lower=301)      # the tiny synthetic frame must keep some text rows
    assert len(df) < len(synthetic_dedup) and "linkedin" not in set(df.source) and len(df)
    proc, tab, out = tmp_path / "processed", tmp_path / "tables", tmp_path / "outputs"
    for p in (proc, tab, out):
        p.mkdir()
    df.to_json(proc / "postings_dedup.jsonl", orient="records", lines=True, force_ascii=False)
    for mod in (RA, DQ):
        monkeypatch.setattr(mod, "PROC", proc)
        monkeypatch.setattr(mod, "TAB", tab)
        monkeypatch.setattr(mod, "OUT", out)
    RA.main()
    DQ.main()
    assert (tab / "T04c_linkedin_industry_raw.csv").exists()
    t04c = pd.read_csv(tab / "T04c_linkedin_industry_raw.csv", index_col=0)
    assert "linkedin" in t04c.columns and (t04c["linkedin"] == 0).all()
    assert "linkedin" not in set(pd.read_csv(tab / "T01_source_coverage.csv").source)
    # the visual builders that name a source read these tables
    monkeypatch.setattr(VQD, "TABLES", tab)
    spec32, _fig32 = VQE.bq32()
    assert "LinkedIn is not part of this snapshot" in spec32.caveat
    spec30, _fig30 = VQE.bq30()
    assert "LinkedIn" not in spec30.answer.split("carry most")[0]
