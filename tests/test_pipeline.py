"""Validation tests: rule behaviour on known inputs + integrity of processed outputs.
Run: python -m pytest tests -q
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "pipeline"))
import normalize as N  # noqa: E402

PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"


# ---------------- unit tests on rules
@pytest.mark.parametrize("title,family", [
    ("Data Analyst (m/w/d)", "data_analytics"),
    ("Senior Data Scientist (all genders) - Wien", "data_science"),
    ("Data Engineer / Data Analyst (m/w/d)", "data_engineering"),
    ("BI Consultant Power BI (w/m/d)", "bi"),
    ("Business Intelligence Analyst", "bi"),
    ("Marketing Analyst:in", "marketing_analytics"),
    ("Machine Learning Engineer", "data_science"),
    ("Analytics Engineer (dbt)", "data_engineering"),
    ("Data Steward (m/w/x)", "data_governance"),
    ("Business Analyst*in", "business_analysis"),
    ("Datacenter Systems Engineer", "out_of_scope"),
    ("Data Entry Clerk", "out_of_scope"),
    ("Biomedizinische Analytikerin", "out_of_scope"),
    ("Softwareentwickler Backend Java", "out_of_scope"),
    ("AI Software Engineer", "ai_software_engineering"),
    ("Koch (m/w/d)", "out_of_scope"),
    # D-012 (2026-09-16 audit) precision fixes
    ('Master Thesis "Bi-Static Sensing of UAVs"', "out_of_scope"),
    ("Labormitarbeiter:in - Produktanalytiker:in in der Qualitätskontrolle (HPLC)", "out_of_scope"),
    ("Managing Consultant Banking (all genders)", "out_of_scope"),
    ("SAP Solution Consultant - Supply Chain (w/m/d)", "out_of_scope"),
    ("Senior Consultant GenAI (all genders)", "ai_software_engineering"),
    ("Senior IT-Analyst (w/m/d) Security Analysis", "out_of_scope"),
    ("Regulatory Reporting Specialist (all genders) - Group Finance", "out_of_scope"),
    ("Data Analyst:in im Meldewesen", "data_analytics"),
    ("Datenschutz-Experte (all genders)", "out_of_scope"),
    ("Aktuar (w/m/d) Krankenversicherung", "other_data"),
    ("Mitarbeiter Stammdatenmanagement (m/w/d)", "data_governance"),
    ("Data Governance Consultant (m/w/d)", "data_governance"),
    ("Senior Consultant SAP BW & Datasphere (m/w/d)", "bi"),
    ("Power BI Consultant (m/w/d)", "bi"),
    ("Staff Scientist - Embedded AI", "out_of_scope"),
    ("Product Analyst (all genders)", "product_analytics"),
    ("Senior Technical Product Owner / Analyst (m/w/d)", "other_data"),
])
def test_role_classification(title, family):
    tc, _ = N.clean_title(title)
    assert N.classify_role(tc)["role_family"] == family, (title, tc)


def test_governance_split_and_ai_engineer_label():
    assert N.classify_role(N.clean_title("Mitarbeiter Stammdatenmanagement")[0])["normalized_title"].startswith("Master / Product Data")
    assert N.classify_role(N.clean_title("Data Steward (m/w/d)")[0])["normalized_title"].startswith("Data Governance")
    assert N.classify_role(N.clean_title("AI Engineer (m/w/d)")[0])["normalized_title"] == "Machine Learning / AI Engineer"


@pytest.mark.parametrize("text,strength", [
    ("Abgeschlossenes Studium der Informatik oder Statistik erforderlich.", "required"),
    ("Ein abgeschlossenes Studium ist von Vorteil, aber nicht Bedingung.", "preferred"),
    ("Ideally you hold a degree in a quantitative field.", "preferred"),
    ("Wir bieten Weiterbildung an der FH.", "mentioned"),
    ("Du arbeitest gerne im Team.", "none"),
])
def test_degree_requirement_strength(text, strength):
    assert N.education(text)["degree_requirement"] == strength


def test_skill_aliases_sql_server_and_powerbi():
    sk = N.extract_skills("Erfahrung mit MS SQL Server und Microsoft Power BI, Power Query.", "")
    assert "SQL" in sk["skills_programming_languages"] and "SQL Server" in sk["skills_data_platforms"] and "Power BI" in sk["skills_bi_tools"]
    sk2 = N.extract_skills("Certifications such as DP-203 or Google Professional Data Engineer are a plus; IREB or CBAP welcome.", "")
    assert "Azure cert" in sk2["skills_certifications"] and "Requirements/BA cert (IREB/IIBA/CBAP)" in sk2["skills_certifications"]


def test_title_cleaning_removes_gender_and_keeps_ams_label():
    tc, ams = N.clean_title("Process Data Engineer, Wels, AT (Data-Warehouse-Analyst/in)")
    assert "m/w" not in tc and ams == "Data-Warehouse-Analyst/in"
    assert N.clean_title("Data Analyst (m/w/d)")[0] == "data analyst"
    assert N.clean_title("Data-Analyst*in")[0] == "data analyst"


@pytest.mark.parametrize("title,sen", [("Junior Data Analyst", "trainee_junior"), ("Senior BI Developer", "senior"), ("Head of Data", "lead_head"), ("Praktikum Data Science", "intern_student"), ("Data Scientist", None)])
def test_seniority(title, sen):
    assert N.seniority_from_title(N.clean_title(title)[0]) == sen


def test_salary_monthly_x14():
    r = {"description_text": "Das Mindestgehalt beträgt EUR 3.500,- brutto pro Monat auf Vollzeitbasis. Überzahlung möglich.", "source": "karriere"}
    s = N.normalize_salary(r)
    assert s["salary_min_annual_eur"] == 49000 and s["salary_period"] == "month" and s["salary_overpay_mention"]


def test_salary_annual_as_stated():
    r = {"description_text": "Für diese Position bieten wir ein Jahresbruttogehalt ab EUR 48.774,84.", "source": "jobsat"}
    s = N.normalize_salary(r)
    assert s["salary_min_annual_eur"] == 48775 and s["salary_period"] == "year"


def test_salary_structured_range():
    r = {"description_text": "", "salary_min_raw": 2303, "salary_max_raw": 4300, "salary_period_raw": "MONTH", "source": "karriere"}
    s = N.normalize_salary(r)
    assert s["salary_min_annual_eur"] == 2303 * 14 and s["salary_max_annual_eur"] == 4300 * 14 and s["salary_basis"] == "range"


def test_salary_ignores_phone_and_years():
    r = {"description_text": "Kontakt: Tel. 0316 2026 12345. Gehalt: laut KV.", "source": "eures"}
    s = N.normalize_salary(r)
    assert s["salary_min_annual_eur"] is None and s["salary_kv_mention"]


@pytest.mark.parametrize("text,req,bucket", [
    ("Sehr gute Deutsch- und Englischkenntnisse in Wort und Schrift", "required_implied", "C1/fluent"),
    ("Deutschkenntnisse von Vorteil", "preferred", None),
    ("German at least B2 level is required", "required", "B2/good"),
    ("Fluent English; German is a plus", "preferred", None),
    ("We are an English-speaking team. No German required.", "explicitly_not_required", None),
])
def test_language(text, req, bucket):
    out = N.language_requirements(text, "", "de")
    assert out["german_requirement"] == req, out
    if bucket:
        assert out["german_level_bucket"] == bucket, out


def test_posting_language():
    assert N.posting_language("Wir suchen eine Person, die mit uns und für unsere Kunden arbeitet und die Daten liebt. " * 3)[0] == "de"
    assert N.posting_language("We are looking for a person who will work with us and for our customers and who loves data. " * 3)[0] == "en"


def test_experience_years():
    assert N.experience("Mindestens 3 Jahre Berufserfahrung im Bereich Data Analytics")["experience_min_years"] == 3
    assert N.experience("2-4 years of experience with Python")["experience_min_years"] == 2
    assert N.experience("Wir freuen uns auch über Berufseinsteiger")["experience_entry_level_phrase"]


def test_location_nuts_and_city():
    out = N.normalize_location({"nuts_codes": ["AT221"], "location_text": None, "description_text": ""})
    assert out["state"] == "Steiermark" and out["is_graz_area"] and out["is_styria"]
    out = N.normalize_location({"nuts_codes": [], "location_text": "Hart bei Graz, Steiermark, Österreich", "description_text": ""})
    assert out["city"] == "Hart Bei Graz" and out["is_graz_area"]
    out = N.normalize_location({"nuts_codes": [], "location_text": "Wien", "description_text": ""})
    assert out["state"] == "Wien" and not out["is_styria"]


def test_remote():
    assert N.classify_remote({"description_text": "2 Tage Home Office pro Woche möglich", "title": ""})["remote_type"] == "hybrid"
    assert N.classify_remote({"description_text": "100% remote within Austria", "title": ""})["remote_type"] == "remote"
    assert N.classify_remote({"description_text": "Wir bieten Gleitzeit.", "title": ""})["remote_type"] == "unknown"


def test_skills_extraction():
    sk = N.extract_skills("Erfahrung mit Python, SQL und Power BI; Kenntnisse in scikit-learn und Azure. R oder Python.", "Data Analyst")
    assert sk["has_python"] and sk["has_sql"] and sk["has_power_bi"] and "scikit-learn" in sk["skills_python_ecosystem"] and "Azure" in sk["skills_cloud_platforms"] and sk["has_r"]
    sk2 = N.extract_skills("Wir suchen eine HR-Mitarbeiterin (R&D Abteilung).", "HR")
    assert not sk2["has_r"]


# ---------------- integrity tests on processed data (skipped if pipeline not run)
@pytest.fixture(scope="module")
def dedup():
    p = PROC / "postings_dedup.jsonl"
    if not p.exists():
        pytest.skip("pipeline outputs not present")
    return pd.read_json(p, lines=True)


def test_uids_unique(dedup):
    assert dedup.posting_uid.is_unique


def test_one_canonical_per_group(dedup):
    g = dedup.groupby("dedupe_group_id").is_canonical.sum()
    assert (g == 1).all()


def test_dates_plausible(dedup):
    d = pd.to_datetime(dedup.posted_date, errors="coerce")
    # long-running "evergreen" ads (nursing etc.) legitimately date back years; only reject impossible dates
    assert d.dropna().between("2019-01-01", pd.Timestamp.today() + pd.Timedelta(days=1)).all()


def test_salary_bounds(dedup):
    s = dedup.salary_min_annual_eur.dropna()
    assert s.between(12000, 300000).all()
    mx = dedup.dropna(subset=["salary_max_annual_eur"])
    assert (mx.salary_max_annual_eur >= mx.salary_min_annual_eur).all()


def test_states_valid(dedup):
    valid = set(json.load(open(ROOT / "config" / "geo.json", encoding="utf-8"))["states"])
    assert set(dedup.state.dropna().unique()) <= valid


def test_family_values(dedup):
    fams = set(json.load(open(ROOT / "config" / "role_taxonomy.json", encoding="utf-8"))["families"])
    assert set(dedup.role_family.unique()) <= fams


def test_table_shares_consistent():
    p = TAB / "T02_role_family_counts.csv"
    if not p.exists():
        pytest.skip("tables not present")
    t = pd.read_csv(p)
    assert abs(t.share.sum() - 1) < 0.02 and (t["count"].sum() == t.n.iloc[0])
    st = pd.read_csv(TAB / "T05_skills_all_tech.csv")
    assert (st["count"] <= st.n).all() and ((st.share - st["count"] / st.n).abs() < 0.001).all()


# ---------------- seasonality (D-015): the index must recover a known seasonal pattern
sys.path.insert(0, str(ROOT / "src" / "analysis"))


def _synthetic_quarterly(mult, years=12, base=1000.0, q_growth=1.0, y_growth=1.0):
    """Series with a known multiplicative seasonal pattern on a trend.

    q_growth compounds every quarter (a smooth trend); y_growth compounds once per year
    (a step trend that only moves in January). The two methods behave differently on them,
    which is what the tests below pin down.
    """
    rows = []
    t = 0
    for i, y in enumerate(range(2010, 2010 + years)):
        for q in (1, 2, 3, 4):
            rows.append({"year": y, "quarter": q,
                         "value": base * (y_growth ** i) * (q_growth ** t) * mult[q - 1]})
            t += 1
    return pd.DataFrame(rows)


MULT = [1.20, 0.95, 0.95, 0.90]  # mean exactly 1.0


def test_seasonal_index_recovers_known_pattern_smooth_trend():
    """On a smooth trend both methods recover the pattern; the moving average is the more accurate."""
    import seasonality as S
    df = _synthetic_quarterly(MULT, q_growth=1.015)  # +1.5% per quarter, ~6% per year
    a = S.ratio_own_year(df)
    got_a = [a[a.quarter == q].ratio_a.mean() for q in (1, 2, 3, 4)]
    b = S.ratio_moving_average(df)
    got_b = [b[b.quarter == q].ratio_b.mean() for q in (1, 2, 3, 4)]
    for g, m in zip(got_a, MULT):
        assert abs(g - m) < 0.03, ("method A", got_a, MULT)
    for g, m in zip(got_b, MULT):
        assert abs(g - m) < 0.01, ("method B", got_b, MULT)
    err_a = sum(abs(g - m) for g, m in zip(got_a, MULT))
    err_b = sum(abs(g - m) for g, m in zip(got_b, MULT))
    assert err_b < err_a, (err_a, err_b)


def test_seasonal_index_exact_when_trend_is_a_yearly_step():
    """Method A is exact when the level only changes between years (its design property)."""
    import seasonality as S
    df = _synthetic_quarterly(MULT, y_growth=1.08)
    a = S.ratio_own_year(df)
    got = [a[a.quarter == q].ratio_a.mean() for q in (1, 2, 3, 4)]
    for g, m in zip(got, MULT):
        assert abs(g - m) < 1e-9, (got, MULT)


def test_seasonal_index_is_flat_without_seasonality():
    import seasonality as S
    df = _synthetic_quarterly([1.0, 1.0, 1.0, 1.0])
    a = S.ratio_own_year(df)
    assert all(abs(a[a.quarter == q].ratio_a.mean() - 1) < 0.02 for q in (1, 2, 3, 4))


def test_centred_moving_average_weights():
    """CMA_t must equal (0.5x-2 + x-1 + x0 + x+1 + 0.5x+2)/4 and be NaN at the edges."""
    import seasonality as S
    df = pd.DataFrame([{"year": 2010 + i // 4, "quarter": i % 4 + 1, "value": float(v)}
                       for i, v in enumerate([10, 20, 30, 40, 50, 60, 70, 80])])
    out = S.ratio_moving_average(df).sort_values(["year", "quarter"]).reset_index(drop=True)
    x = df.value.tolist()
    expected = (0.5 * x[0] + x[1] + x[2] + x[3] + 0.5 * x[4]) / 4
    assert abs(out.cma.iloc[2] - expected) < 1e-9
    assert pd.isna(out.cma.iloc[0]) and pd.isna(out.cma.iloc[-1])


def test_seasonality_tables_consistent():
    p = TAB / "S01_seasonal_index.csv"
    if not p.exists():
        pytest.skip("seasonality tables not present")
    s = pd.read_csv(p)
    full = s[s["sample"] == "full"]
    # the four quarterly indices of a sector must average to ~1 by construction
    for sector, g in full.groupby("sector"):
        assert len(g) == 4
        assert abs(g.index_a_own_year_mean.mean() - 1) < 0.01, (sector, g.index_a_own_year_mean.tolist())
        assert (g.ci_low <= g.index_a_own_year_mean).all() and (g.index_a_own_year_mean <= g.ci_high).all()
    # Q4 must be the weakest quarter in every sector (the documented headline finding)
    for sector, g in full.groupby("sector"):
        assert g.sort_values("index_a_own_year_mean").iloc[0].quarter == "Q4", sector
