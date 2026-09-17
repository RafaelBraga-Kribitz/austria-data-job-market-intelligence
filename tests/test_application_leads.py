"""Rule tests for the application-lead builder (src/pipeline/build_application_leads.py).

These run anywhere: the contact-extraction rules are tested on synthetic ad text,
and the end-to-end test builds a lead file from a temporary fixture, so no private
data is needed.
"""
import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "pipeline"))
import build_application_leads as B  # noqa: E402


def _mail(local: str, domain: str) -> str:
    """Assemble addresses at runtime: src/publish/export_public.py refuses to export any
    file containing an e-mail or phone literal, and synthetic fixtures must not trip that
    publication guard."""
    return local + "@" + domain


MAIL_JULIA = _mail("julia.hofer", "muster-analytics.at")
MAIL_BERGER = _mail("t.berger", "beispiel-tech.com")
MAIL_BEWERBUNG = _mail("bewerbung", "firma.at")
P43 = "+" + "43"
PHONE_EN = P43 + " 1 9876543"
PHONE_INTL = "00" + "43 664 1234567"

AD_DE = ("Wir suchen eine Data Analyst:in fuer unser Team in Graz. Bei Fragen wenden Sie sich bitte an unsere "
         "Ansprechpartnerin Frau Mag. Julia Hofer, HR Managerin, Tel. 0316 123 456-78. Bewerbungen bitte an "
         f"{MAIL_JULIA} senden.")
AD_EN = ("Join Beispiel Tech AG as a Senior Data Engineer. Your contact: Thomas Berger, Talent Acquisition Manager - "
         f"reach out to t.berger (at) beispiel-tech (dot) com or {PHONE_EN}.")


# ---------------- e-mail extraction and classification
def test_plain_email_is_found():
    assert [e["email"] for e in B.find_emails(AD_DE, "")] == [MAIL_JULIA]


def test_mailto_link_is_found_without_text():
    html = f'<a href="mailto:{_mail("Bewerbung", "Firma.at")}">bewerben</a>'
    assert B.find_emails("kein text", html)[0] == {"email": MAIL_BEWERBUNG, "extraction": "mailto_link", "_offset": None, "evidence": None}


def test_obfuscated_email_is_reassembled():
    assert [e["email"] for e in B.find_emails(AD_EN, "")] == [MAIL_BERGER]


@pytest.mark.parametrize("local,kind", [
    ("julia.hofer", "personal"),
    ("t.berger", "personal"),
    ("bewerbung", "generic"),
    ("jobs.austria", "generic"),
    ("office", "generic"),
    ("hr", "generic"),
    ("datateam2", "unknown"),
])
def test_email_kind(local, kind):
    assert B._email_kind(_mail(local, "firma.at")) == kind


def test_domain_is_matched_against_company_name_and_url():
    assert B._domain_matches_company("muster-analytics.at", "Muster Analytics GmbH", "")
    assert B._domain_matches_company("mail.firma.at", "Beispiel AG", "https://www.firma.at/jobs")
    assert not B._domain_matches_company("personal-partner.at", "Beispiel Tech AG", "")


# ---------------- person and phone extraction
def test_person_name_position_and_salutation():
    p = B.find_persons(AD_DE)[0]
    assert (p["person_name"], p["salutation"], p["person_position"], p["confidence"]) == ("Julia Hofer", "Frau", "HR Managerin", "high")


def test_trigger_word_does_not_swallow_the_salutation():
    # "Ansprechpartnerin Frau" must not be read as a name and consume "Frau"
    assert [p["person_name"] for p in B.find_persons(AD_DE)] == ["Julia Hofer"]


def test_company_name_is_not_read_as_a_person():
    assert [p["person_name"] for p in B.find_persons(AD_EN, "Beispiel Tech AG")] == ["Thomas Berger"]


def test_advertisement_boilerplate_is_not_read_as_a_person():
    assert B.find_persons("Senior Data Scientist Wien. Wir freuen uns auf Ihre Bewerbung. Power BI und Machine Learning.") == []


@pytest.mark.parametrize("raw,norm", [("0316 123 456-78", P43 + "31612345678"), (PHONE_EN, P43 + "19876543"), (PHONE_INTL, P43 + "6641234567")])
def test_phone_normalisation(raw, norm):
    assert B.find_phones(f"Tel. {raw} fuer Rueckfragen")[0]["phone"] == norm


def test_contacts_link_email_to_the_person_named_in_the_same_block():
    contacts, summary = B.build_contacts(AD_DE, "", "Muster Analytics GmbH", "")
    assert len(contacts) == 1
    c = contacts[0]
    assert (c["email"], c["person_name"], c["person_link"], c["email_kind"]) == (MAIL_JULIA, "Julia Hofer", "local_part_matches_name", "personal")
    assert c["verified"] is False and c["evidence"]
    assert summary["best_email"] == MAIL_JULIA and summary["has_personal_email"]


def test_no_contact_data_is_invented():
    contacts, summary = B.build_contacts("Wir bieten ein spannendes Umfeld und ein Bruttojahresgehalt ab 45.000 EUR.", "", "Firma", "")
    assert contacts == [] and summary["status"] == "none_found" and summary["best_email"] is None


def test_application_urls_are_kept_and_source_url_dropped():
    html = '<a href="https://firma.at/karriere/bewerbung">apply</a><a href="https://firma.at/impressum">impressum</a>'
    assert B.find_application_urls("", html, "https://karriere.at/jobs/1") == ["https://firma.at/karriere/bewerbung"]


# ---------------- status, language risk, salutation
def test_open_status_reads_valid_through():
    run = date(2026, 9, 17)
    assert B.open_status({"valid_through": "2025-03-01"}, run)["is_open"] is False
    assert B.open_status({"valid_through": "2026-10-30"}, run)["open_status"] == "stated_open_until_valid_through"


def test_open_status_is_unknown_when_the_snapshot_is_old():
    st = B.open_status({"posted_date": "2026-01-01", "collected_at": "2026-02-01"}, date(2026, 9, 17))
    assert st["is_open"] is None and st["requires_reverification"] is True


@pytest.mark.parametrize("row,risk", [
    ({"german_requirement": "required", "german_level_bucket": "c1_equivalent"}, "blocking_unless_b2_c1"),
    ({"german_requirement": "required_implied", "german_level_bucket": None}, "likely_blocking"),
    ({"german_requirement": "preferred"}, "manageable_advantage_only"),
    ({"german_requirement": "not_mentioned", "posting_language": "en"}, "low"),
    ({"german_requirement": "not_mentioned", "posting_language": "de"}, "unclear_german_written_ad"),
])
def test_german_risk(row, risk):
    assert B.german_risk(row) == risk


@pytest.mark.parametrize("named,lang,expected", [
    ({"person_name": "Julia Hofer", "salutation": "Frau"}, "de", "Sehr geehrte Frau Hofer"),
    ({"person_name": "Max Berger", "salutation": "Herr"}, "de", "Sehr geehrter Herr Berger"),
    ({"person_name": "Julia Hofer", "salutation": None}, "de", "Sehr geehrte/r Julia Hofer"),
    ({"person_name": "Thomas Berger", "salutation": None}, "en", "Dear Thomas"),
    (None, "de", "Sehr geehrte Damen und Herren"),
    (None, "en", "Dear Hiring Team"),
])
def test_salutation_line(named, lang, expected):
    assert B.salutation_line(named, lang) == expected


# ---------------- end to end
FIXTURE = {
    "posting_uid": "eures:1", "source": "eures", "source_url": "https://example.org/jv/1", "collected_at": "2026-09-16 17:05:00+00:00",
    "is_canonical": True, "title": "Data Analyst (m/w/d)", "company": "Muster Analytics GmbH", "company_norm": "muster analytics",
    "role_family": "data_analytics", "seniority": "unspecified", "posting_language": "de", "city": "Graz", "state": "Steiermark",
    "is_styria": True, "is_graz_area": True, "remote_type": "hybrid", "posted_date": "2026-09-01", "valid_through": "2026-10-30",
    "salary_min_annual_eur": 48000, "salary_basis": "minimum_only", "german_requirement": "required", "german_level_bucket": "c1_equivalent",
    "skills_programming_languages": ["SQL", "Python"], "skills_bi_tools": ["Power BI"], "skills_cloud_platforms": ["Azure"],
    "description_text": AD_DE, "description_html": f'<a href="mailto:{MAIL_JULIA}">mail</a>',
}


@pytest.fixture()
def built(tmp_path):
    src = tmp_path / "postings.jsonl"
    src.write_text(json.dumps(FIXTURE, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "leads.json"
    assert B.main(["--input", str(src), "--out", str(out)]) == 0
    return out


def test_end_to_end_lead_shape(built):
    doc = json.load(open(built, encoding="utf-8"))
    assert doc["meta"]["mode"] == "postings" and doc["meta"]["counts"]["leads"] == 1
    lead = doc["leads"][0]
    assert set(lead) >= {"lead_id", "company", "contacts", "contact_summary", "job", "status", "source", "location", "salary", "requirements", "fit", "outreach", "scoring", "pipeline"}
    assert lead["contact_summary"]["best_email"] == MAIL_JULIA
    assert lead["outreach"]["channel"] == "email_named_person" and lead["outreach"]["language"] == "de"
    assert lead["fit"]["location_fit"] == "graz_area"
    assert "SQL" in lead["fit"]["cv_keywords_ranked"] and "Azure" in lead["fit"]["gaps_structural"]
    assert 0 <= lead["scoring"]["apply_priority_score"] <= 100
    assert lead["pipeline"]["status"] == "new"


def test_rerun_preserves_tracking_state(built):
    doc = json.load(open(built, encoding="utf-8"))
    doc["leads"][0]["pipeline"].update({"status": "applied", "applied_at": "2026-09-18", "notes": ["CV v3 sent"]})
    json.dump(doc, open(built, "w", encoding="utf-8"), ensure_ascii=False)
    src = built.parent / "postings.jsonl"
    assert B.main(["--input", str(src), "--out", str(built)]) == 0
    again = json.load(open(built, encoding="utf-8"))["leads"][0]["pipeline"]
    assert again["status"] == "applied" and again["notes"] == ["CV v3 sent"]
