"""Shared pytest configuration: synthetic Layer 1 fixtures and loud reporting of skipped integrity checks.

Imports: `pyproject.toml` puts src/pipeline, src/analysis, src/acquisition, src/viz, src/reporting, src/publish and the
repository root on sys.path, so tests import pipeline modules by name (`import normalize as N`) without path hacks.

Synthetic fixtures (M4/H2): a tiny raw tree for all five Layer 1 sources is written to a temporary folder and run through
the real build_interim -> normalize -> dedupe code, so the integrity checks and the analysis smoke tests run in every clone,
not only on the author's machine with the private data. Nothing here reads or writes data/ or outputs/.

Skipped checks: many integrity tests need the private processed data (data/processed, gitignored) and skip without it. A
green run without that data therefore does NOT cover them. The terminal summary below lists every skipped test under a
banner, and `--require-private-data` turns each of those skips into a failure (use it on the author's machine).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
MISSING_DATA_PREFIX = "MISSING PRIVATE DATA"


# ---------------------------------------------------------------- options and skip reporting
def pytest_addoption(parser):
    parser.addoption("--require-private-data", action="store_true", default=False,
                     help="fail (instead of skip) every test that needs private data or not-yet-built outputs")


def require(path: Path, what: str) -> Path:
    """Skip loudly when a private or generated input is absent (tests call this through the `require_input` fixture)."""
    if not path.exists():
        pytest.skip(f"{MISSING_DATA_PREFIX}: {what} ({path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path}) "
                    "is absent - this integrity check did NOT run")
    return path


@pytest.fixture
def require_input():
    return require


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.skipped and not hasattr(rep, "wasxfail") and item.config.getoption("--require-private-data"):
        rep.outcome = "failed"
        rep.longrepr = f"--require-private-data: test skipped: {_skip_reason(rep)}"


def _skip_reason(rep) -> str:
    lr = rep.longrepr
    if isinstance(lr, tuple) and len(lr) == 3:
        return str(lr[2]).removeprefix("Skipped: ")
    return str(lr)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    skipped = terminalreporter.stats.get("skipped", [])
    if not skipped:
        return
    tr = terminalreporter
    tr.section(f"SKIPPED INTEGRITY CHECKS: {len(skipped)} test(s) did not run", sep="!", yellow=True, bold=True)
    tr.write_line("A passing run does not cover these. Typical cause: private data (data/processed, data/raw) or")
    tr.write_line("private code (src/private) is absent in this clone. Re-run with --require-private-data to fail on them.")
    by_reason: dict[str, list[str]] = {}
    for rep in skipped:
        by_reason.setdefault(_skip_reason(rep), []).append(rep.nodeid)
    for reason, ids in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
        tr.write_line(f"  [{len(ids)}] {reason}", yellow=True)
        for nid in ids[:5]:
            tr.write_line(f"        {nid}")
        if len(ids) > 5:
            tr.write_line(f"        ... and {len(ids) - 5} more")


# ---------------------------------------------------------------- synthetic Layer 1 raw tree
RUN_DATE = "2026-01-15"
COLLECTED = "2026-01-15T10:00:00+00:00"

_DE_ANALYST = (
    "Wir suchen ab sofort eine:n Data Analyst:in für unser Team in Graz. Deine Aufgaben: Aufbau von Dashboards mit Power BI, "
    "Analysen mit Python und SQL, Zusammenarbeit mit dem Controlling und dem Vertrieb. Dein Profil: abgeschlossenes Studium "
    "der Informatik, Statistik oder Wirtschaftsinformatik; mindestens 2 Jahre Berufserfahrung im Bereich Data Analytics; sehr "
    "gute Deutsch- und Englischkenntnisse in Wort und Schrift; Erfahrung mit Excel und Power Query. Wir bieten: 2 Tage Home "
    "Office pro Woche, Gleitzeit, Weiterbildung. Das Mindestgehalt beträgt EUR 3.500,- brutto pro Monat auf Vollzeitbasis, "
    "Überzahlung je nach Qualifikation möglich. Wir freuen uns auf deine Bewerbung über unser Karriereportal."
)
_EN_ENGINEER = (
    "We are looking for a Senior Data Engineer to build our lakehouse on Azure and Databricks. You will design ETL pipelines "
    "with Spark and Airflow, model data in the warehouse with dbt, and work with our data scientists on MLOps. Requirements: "
    "at least 5 years of professional experience, strong Python and SQL, experience with Kafka streaming and Docker; a degree "
    "in computer science or equivalent experience. Fluent English is required; German is a plus. We are an English-speaking "
    "team. Hybrid work with up to 3 days remote per week. The annual gross salary starts at EUR 65.000 depending on "
    "experience. Apply now and join a growing team in Vienna."
)
_DE_SCIENTIST = (
    "Für unser Forschungsteam in Graz suchen wir eine:n Junior Data Scientist. Du entwickelst Machine-Learning-Modelle mit "
    "Python, scikit-learn und PyTorch, führst statistische Analysen und Regressionen durch und präsentierst Ergebnisse. "
    "Voraussetzungen: abgeschlossenes Masterstudium in Mathematik, Physik oder Data Science; erste Berufserfahrung von "
    "Vorteil, auch Berufseinsteiger sind willkommen; gute Deutschkenntnisse (mindestens B2) und gute Englischkenntnisse. "
    "Wir bieten ein Jahresbruttogehalt ab EUR 48.000 sowie die Möglichkeit, teilweise remote zu arbeiten. Arbeitsort: Graz."
)
_DE_BI = (
    "Als BI Developer (w/m/d) in Linz verantwortest du unsere Berichte in Power BI und SAP BW. Du modellierst Daten im Data "
    "Warehouse, schreibst SQL-Abfragen und betreust die Fachbereiche. Anforderungen: HTL oder Studium mit Schwerpunkt "
    "Informatik; mindestens 3 Jahre Erfahrung mit Business Intelligence; sehr gute Deutschkenntnisse sind erforderlich. "
    "Gehalt laut Kollektivvertrag mindestens EUR 3.800 brutto pro Monat, Bereitschaft zur Überzahlung. Vollzeit, 38,5 "
    "Stunden, Arbeitsort Linz, Oberösterreich. Wir bieten Home Office nach Vereinbarung und ein kollegiales Umfeld."
)
_DE_INTERN = (
    "Praktikum Data Science (m/w/d) in Graz für Studierende der Informatik oder Statistik. Du unterstützt unser Team bei der "
    "Datenaufbereitung mit Python und pandas, bei Visualisierungen und bei ersten Machine-Learning-Experimenten. "
    "Voraussetzungen: laufendes Studium, Grundkenntnisse in Python und SQL, Deutsch oder Englisch. Dauer 3 bis 6 Monate, "
    "Teilzeit oder Vollzeit möglich. Die Vergütung beträgt EUR 2.300 brutto pro Monat auf Vollzeitbasis. Arbeitsort Graz, "
    "Steiermark; Home Office an einzelnen Tagen möglich. Wir freuen uns auf deine Bewerbung mit Lebenslauf und Zeugnissen."
)
_EN_SCIENTIST = (
    "Our product team in Vienna is hiring a Data Scientist to work on forecasting and experimentation. You will run A/B "
    "tests, build forecasting models in Python and R, and communicate results to stakeholders. Requirements: a university "
    "degree in statistics, economics or a quantitative field; 3+ years of experience; strong SQL; experience with AWS and "
    "Snowflake is an advantage. English is our working language; German skills are helpful but not required. The minimum "
    "annual salary for this position is EUR 58.000 gross, with willingness to overpay depending on qualification."
)
_DE_MARKETING = (
    "Wir suchen eine:n Marketing Analyst:in in Wien. Du analysierst Kampagnen mit Google Analytics und SQL, baust Reports in "
    "Tableau und unterstützt das Performance-Marketing-Team bei Customer Analytics und Segmentierung. Dein Profil: Studium im "
    "Bereich Wirtschaft oder Marketing, 2 bis 4 Jahre Erfahrung im Online-Marketing, sehr gute Deutschkenntnisse. Wir bieten "
    "ein Monatsgehalt ab EUR 3.200 brutto (14x), flexible Arbeitszeiten und 2 Tage Home Office pro Woche in Wien."
)
_EN_PRODUCT = (
    "As a Product Analyst in Vienna you will define product metrics, build dashboards in Looker and analyse user behaviour "
    "with SQL and Python. You work closely with product managers on experimentation and funnel analysis. Requirements: 2+ "
    "years of experience in product analytics, excellent communication skills, fluent English; German is a plus. We offer "
    "a hybrid setup with 2 days home office, an annual gross salary from EUR 52.000 and a learning budget for conferences."
)
_DE_ENGINEER = (
    "Data Engineer (m/w/d) in Wien gesucht. Du entwickelst Datenpipelines mit Python, SQL und Azure Data Factory, betreust "
    "unser Data Warehouse auf Snowflake und automatisierst Deployments mit CI/CD und Docker. Anforderungen: abgeschlossene "
    "technische Ausbildung (HTL, FH oder Universität), mindestens 3 Jahre Erfahrung, sehr gute Deutschkenntnisse. Wir bieten "
    "ein Jahresgehalt ab EUR 55.000 brutto, Überzahlung je nach Erfahrung, sowie hybrides Arbeiten mit 2 Tagen Home Office."
)
_DE_BA = (
    "Business Analyst*in in Linz: Du erhebst Anforderungen der Fachbereiche, modellierst Prozesse in BPMN und übersetzt sie "
    "in User Stories für die Entwicklung. Erfahrung mit SQL und Jira ist von Vorteil, eine IREB-Zertifizierung ist ein Plus. "
    "Anforderungen: abgeschlossenes Studium der Wirtschaftsinformatik, mindestens 2 Jahre Erfahrung, sehr gute Deutsch- und "
    "gute Englischkenntnisse. Gehalt: mindestens EUR 3.600 brutto pro Monat; Vollzeit 38,5 Stunden; Arbeitsort Linz."
)
_DE_SALZBURG = (
    "Data Analyst (m/w/d) in Salzburg: Du erstellst Auswertungen mit Excel, SQL und Power BI für unseren Handel, betreust das "
    "Reporting und arbeitest eng mit dem Einkauf zusammen. Voraussetzungen: kaufmännische Ausbildung oder Studium, erste "
    "Erfahrung in der Datenanalyse, sehr gute Deutschkenntnisse. Wir bieten ein Jahresbruttogehalt ab EUR 44.000, "
    "Vollzeit, und die Möglichkeit von Home Office an einem Tag pro Woche. Arbeitsort Salzburg Stadt, Österreich."
)
_DE_GOVERNANCE = (
    "Data Governance Specialist (m/w/d) in Innsbruck: Du verantwortest Stammdatenqualität, definierst Datenstandards und "
    "betreust unseren Datenkatalog. Du arbeitest mit SAP, SQL und Collibra. Anforderungen: Studium der Informatik oder "
    "Wirtschaft, mindestens 3 Jahre Erfahrung im Datenmanagement, sehr gute Deutschkenntnisse. Gehalt ab EUR 3.900 brutto "
    "pro Monat. Vollzeit; Arbeitsort Innsbruck, Tirol. Home Office an zwei Tagen pro Woche ist möglich."
)
_DE_CONSULT = (
    "BI Consultant Power BI (w/m/d) in Graz: Du berätst Kunden bei Reporting-Lösungen mit Power BI, modellierst Daten mit "
    "DAX und SQL und führst Workshops durch. Anforderungen: mindestens 2 Jahre Erfahrung mit Power BI, Reisebereitschaft, "
    "sehr gute Deutschkenntnisse. Wir bieten ein Jahresbruttogehalt ab EUR 50.000, Firmenhandy und hybrides Arbeiten mit "
    "bis zu 40 % Home Office. Arbeitsort Graz, Steiermark. Bewerbungen bitte über unser Karriereportal."
)
_DE_STEWARD = (
    "Data Steward (m/w/x) in Wien: Du pflegst Stammdaten im SAP-System, prüfst Datenqualität mit SQL und Excel und "
    "dokumentierst Datenflüsse. Anforderungen: abgeschlossene kaufmännische Ausbildung, erste Erfahrung im Datenmanagement, "
    "sehr gute Deutschkenntnisse. Gehalt ab EUR 3.100 brutto pro Monat, Vollzeit, Arbeitsort Wien, Home Office möglich."
)
_DE_COOK = (
    "Koch (m/w/d) für unser Restaurant in Graz gesucht. Du bereitest regionale Gerichte zu, achtest auf Hygiene und "
    "arbeitest im Team mit dem Service. Voraussetzung: abgeschlossene Lehre als Koch, Teamfähigkeit, Deutschkenntnisse. "
    "Entlohnung laut Kollektivvertrag mindestens EUR 2.200 brutto pro Monat; Überzahlung möglich; Vollzeit 40 Stunden."
)


def _html(text: str) -> str:
    return "<p>" + text.replace(". ", ".</p><p>") + "</p>"


def _ms(date: str) -> int:
    return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp() * 1000)


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def write_synthetic_raw(raw: Path) -> Path:
    """Write a tiny raw tree (5 sources, 17 postings in 18 listing envelopes) in the envelope formats build_interim.py reads.

    Built-in duplicates, so dedupe has something to find:
      * karriere k1 and linkedin l1: same company + title + state   -> company_title_state
      * karriere k4 and eures e1: same title + same description, EURES employer anonymised -> title_fingerprint
      * karriere k1 is listed under two queries (collapsed in build_interim, both queries kept)
    """
    d = RUN_DATE
    # karriere: listing envelope {query, collected_at, record: {jobsItem}}, detail envelope {listing_id, record: {ld_json}}
    kar = [
        ("101", "Data Analyst (m/w/d)", "Example Analytics GmbH", "Graz", "Steiermark", _DE_ANALYST, {"minValue": 3500, "unitText": "MONTH"}, True),
        ("102", "Senior Data Engineer", "Beispiel Tech AG", "Wien", "Wien", _EN_ENGINEER, {"minValue": 65000, "unitText": "YEAR"}, False),
        ("103", "BI Developer Power BI (w/m/d)", "Muster Industrie GmbH", "Linz", "Oberösterreich", _DE_BI, {}, True),
        ("104", "Junior Data Scientist", "Graz Research GmbH", "Graz", "Steiermark", _DE_SCIENTIST, {"minValue": 48000, "unitText": "YEAR"}, False),
        ("105", "Praktikum Data Science", "Grazer Start GmbH", "Graz", "Steiermark", _DE_INTERN, {}, True),
        ("106", "Koch (m/w/d)", "Gasthaus Zur Linde", "Graz", "Steiermark", _DE_COOK, {}, False),
    ]
    listings, details = [], []
    for jid, title, comp, city, region, text, sal, ho in kar:
        item = {"id": jid, "title": title, "link": f"synthetic:karriere:{jid}", "company": {"name": comp, "employees": "50-249"},
                "locations": [{"name": city}], "date": "10.1.2026", "summary": text[:120], "salary": None, "isHomeOffice": ho}
        listings.append({"query": "data analyst", "collected_at": COLLECTED, "record": {"jobsItem": item}})
        ld = {"title": title, "description": _html(text), "datePosted": "2026-01-10T08:00:00",
              "jobLocation": {"address": {"addressLocality": city, "addressRegion": region, "addressCountry": "AT"}},
              "employmentType": ["FULL_TIME"]}
        if sal:
            ld["baseSalary"] = {"currency": "EUR", "value": sal}
        details.append({"listing_id": jid, "record": {"ld_json": ld, "status": 200}})
    listings.append({"query": "business intelligence", "collected_at": COLLECTED, "record": {"jobsItem": listings[0]["record"]["jobsItem"]}})
    _jsonl(raw / "karriere" / d / "listings.jsonl", listings)
    _jsonl(raw / "karriere" / d / "details.jsonl", details)

    # linkedin: {query, location, collected_at, record: {id, title, company, location, posted_date}}, detail {listing_id, record}
    lin = [
        ("L1", "Data Analyst (m/w/d)", "Example Analytics GmbH", "Graz, Steiermark, Österreich", _DE_ANALYST + " Bewerbung über LinkedIn.", "Entry level"),
        ("L2", "Data Scientist", "Beispiel Tech AG", "Wien, Wien, Österreich", _EN_SCIENTIST, "Mid-Senior level"),
        ("L3", "Marketing Analyst:in", "Werbe Agentur GmbH", "Wien, Österreich", _DE_MARKETING, "Associate"),
        ("L4", "Product Analyst (all genders)", "App Studio GmbH", "Vienna, Austria", _EN_PRODUCT, "Associate"),
    ]
    _jsonl(raw / "linkedin" / d / "listings.jsonl", [
        {"query": "data", "location": "Austria", "collected_at": COLLECTED,
         "record": {"id": jid, "url": f"synthetic:linkedin:{jid}", "title": t, "company": c, "location": loc, "posted_date": "2026-01-08"}}
        for jid, t, c, loc, _, _ in lin])
    _jsonl(raw / "linkedin" / d / "details.jsonl", [
        {"listing_id": jid, "record": {"title": t, "company": c, "location": loc, "description_text": text, "criteria": {"Seniority level": sen}, "status": 200}}
        for jid, t, c, loc, text, sen in lin])

    # eures: {query, collected_at, record: {id, translations, employer, locationMap, creationDate}}, detail {record: {id, ...}}
    eur = [
        ("E1", "Junior Data Scientist", "siehe Beschreibung", "AT221", _DE_SCIENTIST),  # fingerprint duplicate of k104
        ("E2", "Data Engineer (m/w/d)", "Daten Werk GmbH", "AT130", _DE_ENGINEER),
        ("E3", "Business Analyst*in", "Prozess Partner GmbH", "AT312", _DE_BA),
    ]
    _jsonl(raw / "eures" / d / "listings.jsonl", [
        {"query": "data", "collected_at": COLLECTED,
         "record": {"id": jid, "availableLanguages": ["de"], "translations": {"de": {"title": t, "description": _html(text)}},
                    "employer": {"name": emp}, "locationMap": {"AT": [nuts]}, "creationDate": _ms("2026-01-05"),
                    "lastModificationDate": _ms("2026-01-06"), "positionScheduleCodes": ["fulltime"], "numberOfPosts": 1}}
        for jid, t, emp, nuts, text in eur])
    _jsonl(raw / "eures" / d / "details.jsonl", [
        {"record": {"id": jid, "connectionPointId": "AT", "source": "AMS", "reference": f"ref-{jid}"}} for jid, *_ in eur])

    # willhaben: {query, collected_at, record: {id, title, company, jobLocations, ...}}, detail {listing_id, record: {data}}
    wil = [
        (901, "Data Analyst (m/w/d)", "Handel Salzburg GmbH", "Salzburg", _DE_SALZBURG, 44000),
        (902, "Data Governance Specialist (m/w/d)", "Tirol Daten GmbH", "Innsbruck", _DE_GOVERNANCE, None),
    ]
    _jsonl(raw / "willhaben" / d / "listings.jsonl", [
        {"query": "data", "collected_at": COLLECTED,
         "record": {"id": jid, "slugTitle": "job", "title": t, "company": {"title": c}, "jobLocations": [{"name": city}],
                    "firstPublishDate": "2026-01-02T09:00:00", "employmentModes": [{"name": "Vollzeit"}],
                    **({"salary": sal, "salaryTimeFrame": "YEAR"} if sal else {})}}
        for jid, t, c, city, _, sal in wil])
    _jsonl(raw / "willhaben" / d / "details.jsonl", [
        {"listing_id": jid, "record": {"data": {"description": text}}} for jid, _, _, _, text, _ in wil])

    # jobs.at: {query, collected_at, record: {id, url, title, date_epoch}}, detail {listing_id, record: {meta_description, ...}}
    job = [
        ("J1", "BI Consultant Power BI (w/m/d)", "Beratung Graz GmbH", "Graz", _DE_CONSULT),
        ("J2", "Data Steward (m/w/x)", "Wiener Versorgung AG", "Wien", _DE_STEWARD),
    ]
    _jsonl(raw / "jobsat" / d / "listings.jsonl", [
        {"query": "data", "collected_at": COLLECTED,
         "record": {"id": jid, "url": f"synthetic:jobsat:{jid}", "title": t, "date_epoch": 1767600000}}
        for jid, t, *_ in job])
    _jsonl(raw / "jobsat" / d / "details.jsonl", [
        {"listing_id": jid, "record": {"title": t, "meta_description": f"{t} in {city} bei der Firma {c} (Job-NR {jid})",
                                       "description_text": text, "meta": "Vollzeit", "status": 200}}
        for jid, t, c, city, text in job])
    return raw


def _build_interim(raw: Path) -> pd.DataFrame:
    import build_interim as BI
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(BI, "RAW", raw)
        rows = []
        for fn in (BI.build_eures, BI.build_karriere, BI.build_linkedin, BI.build_willhaben, BI.build_jobsat):
            rows.extend(fn())
    df = pd.DataFrame(rows)
    df["posting_uid"] = df["source"] + ":" + df["source_id"].astype(str)
    return df


@pytest.fixture(scope="session")
def synthetic_raw(tmp_path_factory) -> Path:
    return write_synthetic_raw(tmp_path_factory.mktemp("synthetic") / "raw")


@pytest.fixture(scope="session")
def synthetic_interim(synthetic_raw) -> pd.DataFrame:
    """The synthetic raw tree after build_interim's per-source mapping (same code path as main())."""
    return _build_interim(synthetic_raw)


@pytest.fixture(scope="session")
def synthetic_dedup(synthetic_interim) -> pd.DataFrame:
    """Synthetic interim rows after normalize.normalize_row and dedupe.assign_groups (the postings_dedup schema)."""
    import dedupe as D
    import normalize as N
    # round-trip through JSON lines exactly like the real pipeline (build_interim writes .jsonl, normalize reads it)
    text = synthetic_interim.to_json(orient="records", lines=True, force_ascii=False)
    rows = [N.normalize_row(json.loads(line)) for line in text.splitlines() if line.strip()]
    return D.assign_groups(pd.DataFrame(rows))
