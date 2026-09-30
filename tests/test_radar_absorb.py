"""D-023: additive taxonomy, Arbeitnow filter, radar parsers (skip if hunter absent), export guards.

The parser test needs the gitignored private hunter (src/private/radar) and the fixtures in tests/fixtures/radar, which
src/publish/export_public.py leaves out of the public tree; in any clone without the hunter it skips loudly.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import normalize as N
from collect_arbeitnow import is_austria
from conftest import MISSING_DATA_PREFIX

ROOT = Path(__file__).resolve().parents[1]

RADAR = ROOT / "src" / "private" / "radar"
FIX = ROOT / "tests" / "fixtures" / "radar"


def test_additive_genai_mlops_topics_extract():
    sk = N.extract_skills(
        "We run RAG with LangChain and Qdrant, tool-calling via MCP, LoRA fine-tuning, "
        "vLLM serving, a multimodal VLM, prompt engineering, MLflow experiment tracking, "
        "and we follow the EU AI Act. Industry 4.0 / OPC UA / MES and ROS 2 on the shop floor.",
        "AI Engineer",
    )
    ml = set(sk["skills_ml_ai"])
    de = set(sk["skills_data_engineering"])
    py = set(sk["skills_python_ecosystem"])
    biz = set(sk["skills_business_domain"])
    assert "RAG" in ml
    assert "Vector DBs" in ml
    assert "AI agents / tool-calling" in ml
    assert "Fine-tuning / LoRA / PEFT" in ml
    assert "Local LLM serving" in ml
    assert "Multimodal / VLM" in ml
    assert "Prompt engineering" in ml
    assert "EU AI Act / AI governance" in ml
    assert "ROS / ROS 2" in ml
    assert "LangChain/LLM frameworks" in py
    assert "Experiment tracking" in de
    assert "Industry 4.0 / MES / OPC UA" in biz
    assert "Generative AI / LLM" in ml  # umbrella kept


def test_topic_stacks_canonical_names_exist_in_taxonomy():
    tax = json.loads((ROOT / "config" / "skills_taxonomy.json").read_text(encoding="utf-8"))
    topics = json.loads((ROOT / "config" / "topic_stacks.json").read_text(encoding="utf-8"))["topics"]
    names = set()
    for cat, items in tax.items():
        if cat.startswith("_") or not isinstance(items, dict):
            continue
        names.update(items)
    missing = [s for s in topics if s not in names]
    assert missing == [], missing


def test_profile_new_topics_are_classified():
    prof = json.loads((ROOT / "config" / "profile.json").read_text(encoding="utf-8"))
    assert "LangChain/LLM frameworks" in prof["developing"]
    assert "RAG" in prof["developing"]
    assert "Vector DBs" in prof["structural"]
    assert "Experiment tracking" in prof["structural"]


@pytest.mark.parametrize("loc,ok", [
    ("Graz, Austria", True),
    ("Wien", True),
    ("Berlin, Germany", False),
    ("Remote, Österreich", True),
    ("Munich", False),
])
def test_arbeitnow_austria_filter(loc, ok):
    assert is_austria(loc) is ok


def test_radar_parsers_on_saved_fixtures(monkeypatch):
    if not (RADAR / "stepstone.py").exists() or not FIX.exists():
        pytest.skip(f"{MISSING_DATA_PREFIX}: private hunter src/private/radar (gitignored) or tests/fixtures/radar is absent "
                    "- the radar parser test did NOT run")
    monkeypatch.syspath_prepend(str(RADAR))
    import stepstone as ss
    import indeed_direct as ind
    cards = ss.parse_search((FIX / "stepstone_search.html").read_text(encoding="utf-8"))
    assert len(cards) == 1
    assert cards[0]["title"].startswith("Data Analyst")
    assert "stepstone.at" in cards[0]["url"]
    assert cards[0]["company"] == "Example GmbH"
    jd = ss._jobposting_description((FIX / "stepstone_detail.html").read_text(encoding="utf-8"))
    assert "Python" in jd
    icards = ind.parse_saved_html((FIX / "indeed_search.html").read_text(encoding="utf-8"))
    assert len(icards) == 1
    assert icards[0]["url"].startswith("https://at.indeed.com/viewjob?jk=abc123")
    assert icards[0]["title"]


def test_export_public_excludes_dark_paths():
    src = (ROOT / "src" / "publish" / "export_public.py").read_text(encoding="utf-8")
    assert "collect_arbeitnow.py" in src
    assert "src/private" not in src.split("INCLUDE_DIRS")[1].split("INCLUDE_ACQUISITION")[0]
    assert "data/raw/arbeitnow" not in src.split("INCLUDE_RAW_DIRS")[1].split("EXCLUDE_ACQUISITION")[0]
    assert "hunter/score artifact leaked" in src
    assert "jobs.db" in src


def test_t19_status_schema_if_present(require_input):
    p = require_input(ROOT / "outputs" / "tables" / "T19_supplement_status.csv",
                      "T19 supplement status table (written by src/analysis/supplement_radar.py)")
    import pandas as pd
    d = pd.read_csv(p)
    assert "status" in d.columns
    assert d.status.iloc[0] in ("not_collected", "below_threshold", "published_aggregates")
    for col in d.columns:
        assert "url" not in col.lower()
        assert col.lower() not in ("description", "description_text", "snippet")
    if d.status.iloc[0] == "published_aggregates":
        fam = ROOT / "outputs" / "tables" / "T19_supplement_families.csv"
        assert fam.exists()
        f = pd.read_csv(fam)
        for col in f.columns:
            assert col.lower() not in ("title", "url", "company", "description")
        assert int(d.core_data_role_rows.iloc[0]) >= 20
