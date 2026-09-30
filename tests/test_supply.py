"""Layer 2 / Layer 3 tests: rule behaviour on known inputs + integrity of the aggregated supply outputs
(integrity tests skip when the private processed files / tables are absent). Run: python -m pytest tests -q
"""
import json
from pathlib import Path

import pandas as pd
import pytest

import build_supply as B  # src/pipeline via the pytest pythonpath (pyproject.toml)

ROOT = Path(__file__).resolve().parents[1]

PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"


# ---------------- rule tests (run anywhere)
@pytest.mark.parametrize("bio,family", [
    ("Data Scientist at ACME", "data_science"),
    ("Senior Data Engineer | Azure | Databricks", "data_engineering"),
    ("Marketing manager turned data analyst", "data_analytics"),
    ("BI Developer (Power BI, SQL)", "bi"),
    ("PhD student in machine learning, TU Graz", "ai_ml_generic"),  # generic ML wording without a role noun = adjacent, not a declared data role
    ("Machine learning engineer at ACME", "data_science"),
    ("Data Analyst | SQL · Python · Power BI", "data_analytics"),  # tool names must not pull analysts into BI
    ("Marketing Data Scientist", "marketing_analytics"),
    ("Growth analytics lead", "marketing_analytics"),
    ("Analytics Engineer (dbt, Snowflake)", "data_engineering"),
    ("Business Analyst", "business_analysis"),
    ("Full-stack web developer", None),
    ("", None),
    ("I love dogs and hiking", None),
])
def test_bio_role(bio, family):
    assert B.bio_role(bio)["bio_role_family"] == family


@pytest.mark.parametrize("bio,sen", [("Senior Data Scientist", "senior"), ("Head of Data", "lead_head"), ("MSc student in statistics", "student"),
                                     ("Junior data analyst, open to work", "junior"), ("Data analyst", "unlabelled"), ("", "unknown")])
def test_bio_seniority(bio, sen):
    assert B.bio_seniority(bio) == sen


@pytest.mark.parametrize("loc,state,styria,graz", [("Graz, Austria", "Steiermark", True, True), ("Vienna", "Wien", False, False), ("Seiersberg", "Steiermark", True, True),
                                                  ("Austria", "unspecified (Austria)", False, False), ("Leoben", "Steiermark", True, False), ("Berlin, Germany", None, False, False)])
def test_geo(loc, state, styria, graz):
    g = B.geo(loc)
    assert g["state"] == state and g["is_styria"] == styria and g["is_graz_area"] == graz


def test_transition_and_education():
    t = B.transitions("Former marketing manager, now data analyst. Background in economics.")
    assert t["transition_explicit"] and "marketing" in t["prior_domains"] and "economics" in t["prior_domains"]
    e = B.education("MSc Data Science, TU Graz; BSc economics at WU")
    assert "Master" in e["edu_levels"] and "Bachelor" in e["edu_levels"] and "TU Graz" in e["edu_institutions"] and "WU Wien" in e["edu_institutions"]


def test_certifications():
    c = B.certifications("Google Data Analytics Professional Certificate capstone (Cyclistic)")
    assert "Google Data Analytics Certificate" in c and "Certification (any mention)" in c


@pytest.mark.parametrize("repo,is_data", [({"name": "churn-prediction", "description": "", "topics": [], "language": "Python"}, True),
                                          ({"name": "dotfiles", "description": "my config", "topics": [], "language": "Shell"}, False),
                                          ({"name": "notes", "description": "", "topics": [], "language": "Jupyter Notebook"}, True),
                                          ({"name": "my-website", "description": "personal website", "topics": ["portfolio"], "language": "HTML"}, False),
                                          ({"name": "sales-dashboard", "description": "Power BI report", "topics": ["powerbi"], "language": None}, True),
                                          ({"name": "ai-code-review-bot", "description": "AI change control plane for agents", "topics": [], "language": "TypeScript"}, False),
                                          ({"name": "customer-churn-data-analysis", "description": "", "topics": [], "language": "Python"}, True),
                                          ({"name": "app", "description": "todo app", "topics": [], "language": "TypeScript"}, False)])
def test_data_repo(repo, is_data):
    assert B.is_data_repo(repo)[0] == is_data


def test_readme_features_and_formats():
    txt = "# Churn model\n\n## Data\nKaggle telco dataset\n\n## Methodology\nlogistic regression, AUC 0.84\n\n## Results\n![plot](img.png)\n\n## Limitations\nno causal claims\n\n## How to run\npip install -r requirements.txt\n"
    f = B.readme_features(txt)
    assert f["rd_h_data_source"] and f["rd_h_methodology"] and f["rd_h_results"] and f["rd_h_limitations"] and f["rd_h_reproducibility"] and f["rd_has_image"] and f["rd_mentions_metrics"]
    tree = [{"path": "Dockerfile", "type": "blob"}, {"path": "tests", "type": "tree"}, {"path": ".github", "type": "tree"}, {"path": "notebook.ipynb", "type": "blob"}, {"path": "requirements.txt", "type": "blob"}]
    fm = B.formats_for({"name": "churn-model", "description": "", "topics": [], "language": "Python", "homepage": "https://x.streamlit.app"}, tree, txt)
    for k in ("docker", "tests", "ci", "notebook", "reproducible_env", "streamlit_gradio_app"):
        assert k in fm, k


def test_themes():
    th = B.themes_for("customer churn prediction with xgboost and an a/b test readout; airflow pipeline into snowflake")
    weak = B.themes_for("my-repo", "the model uses energy to train; a solar panel image appears once")  # one generic README hit must not count
    assert "sustainability" not in weak["themes_analytics_domain"]
    assert "customer" in th["themes_analytics_domain"] and "classification" in th["themes_ds_method"] and "experimentation" in th["themes_ds_method"]
    assert "orchestration" in th["themes_engineering"] and "warehouse_modelling" in th["themes_engineering"]


def test_capability_map_names_exist():
    skills = json.load(open(ROOT / "config" / "skills_taxonomy.json", encoding="utf-8"))
    names = {n for c, d in skills.items() if not c.startswith("_") for n in d}
    cap = json.load(open(ROOT / "config" / "capability_map.json", encoding="utf-8"))["capabilities"]
    missing = {s for spec in cap.values() for s in spec["demand_skills"] if s not in names}
    assert not missing, missing


# ---------------- integrity tests on private processed data (skipped without it)
@pytest.fixture(scope="module")
def cands():
    p = PROC / "supply_candidates.jsonl"
    if not p.exists():
        pytest.skip("supply pipeline outputs not present")
    return pd.DataFrame([json.loads(l) for l in open(p, encoding="utf-8")])


def test_candidate_ids_unique(cands):
    assert cands.candidate_id.is_unique


def test_no_names_or_emails_stored(cands):
    assert "name" not in cands.columns and "email" not in cands.columns


def test_tiers_consistent(cands):
    t1 = cands[cands.data_tier == "T1_bio_declared"]
    assert t1.bio_role_family.notna().all()
    assert (cands[cands.data_tier == "T0_none"].n_data_repos == 0).all()


# ---------------- integrity of aggregated tables (public; skipped if absent)
@pytest.fixture(scope="module")
def tables():
    if not (TAB / "C04_role_family_distribution.csv").exists():
        pytest.skip("supply tables not built")
    return True


def test_shares_have_n_and_bounds(tables):
    for name in ["C04_role_family_distribution", "C06_seniority_distribution", "C10_technologies_evidence", "C17_project_formats", "DS01_demand_supply_role_families", "DS03_demand_supply_skills"]:
        df = pd.read_csv(TAB / f"{name}.csv")
        assert "n" in df.columns or "supply_n" in df.columns, name
        for col in [c for c in df.columns if c.endswith("share") and not c.startswith("difference")]:
            s = df[col].dropna()
            assert ((s >= 0) & (s <= 1.0001)).all(), (name, col)


def test_family_counts_sum(tables):
    c04 = pd.read_csv(TAB / "C04_role_family_distribution.csv")
    assert c04["count"].sum() == c04["n"].iloc[0]


def test_ds01_consistent_with_layer1(tables):
    ds01 = pd.read_csv(TAB / "DS01_demand_supply_role_families.csv"); t02 = pd.read_csv(TAB / "T02_role_family_counts.csv")
    m = ds01.merge(t02, left_on="category", right_on="role_family")
    assert (m.demand_count == m["count"]).all()


def test_public_tables_have_no_free_text(tables):
    import re
    email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    for p in list(TAB.glob("C*.csv")) + list(TAB.glob("DS*.csv")) + list(TAB.glob("SQ*.csv")) + list(TAB.glob("O*.csv")):
        t = p.read_text(encoding="utf-8")
        assert not email.search(t), p.name
        assert "github.com/" not in t and "linkedin.com/in/" not in t, p.name


def test_public_linkedin_summary_omits_people_and_small_cells():
    from supply_common import public_linkedin_summary
    counts = pd.DataFrame({"result_count": [1, 2, 3]})
    profs = pd.DataFrame({
        "location_text": ["Graz"] * 5 + ["Wien"] * 6 + ["Linz"],
        "languages_stated": ["de:C1"] * 5 + ["en:B2"] * 7,
        "headline": ["secret headline"] * 12,
        "pseudo_id": [f"AT-{i:04d}" for i in range(12)],
        "notes": ["k=5; pages=1-5; stratum=Data Analyst|Graz; rank=5"] * 12,
    })
    summary = public_linkedin_summary(counts, profs)
    blob = json.dumps(summary)
    assert "secret" not in blob
    assert "AT-000" not in blob
    assert "stratum" not in blob
    # Linz (1) is below 5, so the remainder is 1 and Graz (the smallest shown cell) is merged into it: the total (12) minus
    # the shown cells can no longer be differenced back to a cell of 1 (L80)
    assert summary["profiles_by_location_n_ge_5"] == {"Wien": 6}
    assert summary["profiles_by_location_other_or_suppressed"] == 6
    assert summary["languages_stated_n_ge_5"] == {"de:C1": 5, "en:B2": 7}
    assert summary["search_counts_recorded"] == 3
    assert summary["profiles_recorded"] == 12
    empty = public_linkedin_summary(pd.DataFrame(), pd.DataFrame())
    assert empty["profiles_recorded"] == 0
    assert "NOT COLLECTED" in empty["status"]
