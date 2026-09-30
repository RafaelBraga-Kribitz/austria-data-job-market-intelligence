"""Integrity tests for the visual decision layer (outputs/figures/BQ*).

What these protect:
  * a figure on disk still matches the bytes its manifest sealed (a figure edited
    or re-rendered without re-sealing is detectable without opening it);
  * every figure names tables that exist, so a caption can always be traced;
  * no figure uses a mark the chart catalogue refuses (3D, dual axis, gauge,
    radar, word cloud);
  * every documentation anchor still resolves, so a figure cannot drift away from
    the passage it claims to illustrate;
  * every embedded block in the documents corresponds to a rendered figure.

Value-level checks (does an answer's number match its table?) live in tests/test_manifest_values.py.

Run: python -m pytest tests/test_visual_layer.py -q
"""
import json
import re
from pathlib import Path

import pytest

from conftest import require

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "outputs" / "visual_questions.json"
MANIFEST = ROOT / "outputs" / "figures" / "FIGURE-MANIFEST.yaml"
TABLES = ROOT / "outputs" / "tables"

# Marks the GSD-DSX chart catalogue flags `refusal`; see references/chart-catalog.md.
REFUSED_MARKS = {"3d_bar", "3d_line", "3d_pie", "dual_axis_line", "gauge", "radar", "word_cloud"}


@pytest.fixture(scope="module")
def figures():
    require(CONTRACT, "visual layer contract (run src/analysis/make_visual_layer.py)")
    return json.loads(CONTRACT.read_text(encoding="utf-8"))["figures"]


def test_every_figure_file_exists(figures):
    for fig in figures:
        for name in (fig["png"], fig["svg"]):
            assert (ROOT / "outputs" / "figures" / name).exists(), f"{fig['chart_id']}: missing {name}"


def test_seal_matches_the_rendered_bytes(figures):
    from engine import seal

    for fig in figures:
        path = ROOT / "outputs" / "figures" / fig["svg"]
        assert seal(path) == fig["svg_sha256"], (
            f"{fig['chart_id']}: the SVG on disk is not the one that was sealed - "
            "re-run src/analysis/make_visual_layer.py"
        )


def test_source_tables_exist(figures):
    for fig in figures:
        for name in fig["tables"]:
            if name.endswith(".csv"):
                assert (TABLES / name).exists(), f"{fig['chart_id']} cites a missing table {name}"
            else:  # config files are cited by path from the repository root
                assert (ROOT / name).exists(), f"{fig['chart_id']} cites a missing file {name}"


def test_no_refused_mark_is_used(figures):
    used = {fig["mark"] for fig in figures}
    assert not (used & REFUSED_MARKS), f"refused marks in use: {used & REFUSED_MARKS}"


def test_every_figure_declares_question_answer_units_and_caveat(figures):
    for fig in figures:
        assert fig["question"].endswith("?"), f"{fig['chart_id']}: question is not a question"
        assert len(fig["answer"]) > 40, f"{fig['chart_id']}: answer is too thin to be an answer"
        assert re.search(r"\d", fig["answer"]), f"{fig['chart_id']}: answer carries no magnitude"
        assert fig["units"], f"{fig['chart_id']}: no units declared"
        assert fig["caveat"], f"{fig['chart_id']}: no caveat declared"


def test_manifest_covers_every_figure(figures):
    text = MANIFEST.read_text(encoding="utf-8")
    for fig in figures:
        assert f"chart_id: {fig['chart_id']}" in text, f"{fig['chart_id']} missing from FIGURE-MANIFEST.yaml"


def test_every_anchor_still_resolves(figures):
    from embed_figures import embed

    problems = embed(figures, check_only=True)
    assert not problems, "unresolved anchors:\n" + "\n".join(problems)


def test_documents_contain_no_orphan_blocks(figures):
    known = {fig["chart_id"] for fig in figures}
    docs = {ROOT / doc for fig in figures for doc, _, _ in fig["anchors"]}
    for doc in docs:
        for cid in re.findall(r"<!-- (BQ\w+):start", doc.read_text(encoding="utf-8")):
            assert cid in known, f"{doc.name} embeds {cid}, which no longer exists"


def test_contract_and_manifest_list_the_same_figures(figures):
    """L77 baseline: visual_questions.json and FIGURE-MANIFEST.yaml describe the same set of BQ figures, and every
    manifest seal equals the contract's seal (so neither file can be regenerated without the other)."""
    text = MANIFEST.read_text(encoding="utf-8")
    manifest_ids = set(re.findall(r"chart_id:\s*(BQ\w+)", text))
    assert manifest_ids == {fig["chart_id"] for fig in figures}
    for fig in figures:
        assert fig["svg_sha256"] in text, f"{fig['chart_id']}: manifest seal differs from visual_questions.json"


def test_contract_ids_are_unique_and_files_named_after_them(figures):
    ids = [fig["chart_id"] for fig in figures]
    assert len(ids) == len(set(ids))
    for fig in figures:
        assert fig["svg"].startswith(fig["chart_id"]) and fig["png"].startswith(fig["chart_id"]), fig["chart_id"]
