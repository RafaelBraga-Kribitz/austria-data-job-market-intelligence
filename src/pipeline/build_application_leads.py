"""Step 8 (private output): application / cold-outreach lead file.

Input  : data/processed/postings_dedup.jsonl  (private, schemas/postings_schema.md)
Fallback: outputs/tables/T04_employers.csv + outputs/ aggregates, used automatically
          when the per-posting file is absent (public checkout) -- employer-level
          leads with no contact data instead of per-posting leads.
Output : data/private/application_leads.json  (git-ignored: ad text, URLs, contacts)

One record per canonical posting (or per employer in fallback mode) carrying
everything an application funnel needs: contacts (e-mail / person / position /
phone, each with the snippet it was read from), company, ad title and text, open
status, source, location, salary, requirements, a profile-fit block for CV
tailoring, outreach slots for cold e-mail, and a `pipeline` block for tracking.

Contact fields are heuristic extractions from advertisement text; every one keeps
its evidence snippet and a confidence label so it can be verified before use, and
nothing is invented -- absent data stays null.

Re-running is safe: the `pipeline` block of existing leads (status, dates, notes)
is preserved by lead_id and only new leads are initialised.

Usage:
  python src/pipeline/build_application_leads.py
  python src/pipeline/build_application_leads.py --include-adjacent --out /path/x.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config"
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
OUT_JSON = ROOT / "outputs"
DEFAULT_IN = PROC / "postings_dedup.jsonl"
DEFAULT_OUT = ROOT / "data" / "private" / "application_leads.json"

CORE_FAMILIES = ["data_analytics", "bi", "data_science", "data_engineering", "data_governance", "marketing_analytics", "product_analytics", "business_analysis"]
ADJACENT_FAMILIES = ["ai_software_engineering", "other_data"]
SKILL_FIELDS = ["skills_programming_languages", "skills_bi_tools", "skills_cloud_platforms", "skills_data_platforms", "skills_python_ecosystem", "skills_data_engineering", "skills_ml_ai", "skills_statistics_methods", "skills_business_domain", "skills_soft_skills", "skills_certifications", "skills_work_model"]


def _rx(p: str) -> re.Pattern:
    return re.compile(p, re.I)


# ------------------------------------------------------------------ contacts
EMAIL_RE = _rx(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
MAILTO_RE = _rx(r"mailto:\s*([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})")
OBFUSCATED_RE = _rx(r"([A-Za-z0-9._%+\-]{2,})\s*(?:\(|\[|\{)?\s*(?:at|ät)\s*(?:\)|\]|\})?\s*([A-Za-z0-9.\-]{2,})\s*(?:\(|\[|\{)?\s*(?:dot|punkt)\s*(?:\)|\]|\})?\s*([A-Za-z]{2,})")
PHONE_RE = _rx(r"(?:\+\s?43|0043|\b0)[\s\-/]?\d[\d\s/().\-]{5,20}\d")
URL_RE = _rx(r"https?://[^\s\"'<>)\]]{5,}")
HREF_RE = _rx(r"href=[\"']([^\"']+)[\"']")
TAG_RE = _rx(r"<[^>]+>")

GENERIC_LOCALS = {"info", "office", "kontakt", "contact", "bewerbung", "bewerbungen", "jobs", "job", "karriere", "career", "careers", "recruiting", "recruitment", "recruiter", "hr", "personal", "personalabteilung", "apply", "application", "bewerber", "team", "talent", "talents", "people", "welcome", "hello", "hallo", "mail", "email", "post", "service", "sekretariat", "empfang", "admin", "verwaltung", "noreply", "no-reply"}

CONTACT_TRIGGER_RE = _rx(r"ansprechpartner\w*|ansprechperson\w*|kontaktperson\w*|ihre? kontakt\w*|kontakt\b|bei fragen|für fragen|fuer fragen|rückfragen|rueckfragen|wenden sie sich|steht (?:ihnen|dir) [^.]{0,60}zur verfügung|bewerbung(?:en)?\s+(?:bitte\s+)?(?:an|per|unter|über)|bewirb dich|senden sie|schicken sie|richten sie|z\.\s?h(?:d)?\.|freuen uns auf (?:ihre|deine) bewerbung|recruit\w*|personalabteilung|personalmanagement|human resources|talent acquisition|employer branding|contact person|your contact|please contact|reach out to|send your application|feel free to (?:contact|reach)|questions\?")

TITLE_PREFIX = r"Mag\.(?:\s?\(FH\))?|Dr\.|Dipl\.-?Ing\.(?:in)?|DI(?:\s?\(FH\))?|Ing\.|BSc|MSc|MBA|BA|MA|LL\.M\.|Prof\."
NAME_CORE = r"[A-ZÄÖÜ][a-zäöüß'\-]{1,20}(?:\s+(?:van|von|de|da|di|del|dos|der))?\s+[A-ZÄÖÜ][a-zäöüß'\-]{1,22}"
NAME_RE = re.compile(rf"(?:(?P<sal>Frau|Herr|Ms\.|Mrs\.|Mr\.)\s+)?(?:(?:{TITLE_PREFIX})\s+)*(?P<name>{NAME_CORE})")

POSITION_RE = _rx(r"head of [a-zäöüß &/\-]{2,40}|leiter(?:in)?\s+[a-zäöüß\- ]{2,40}|team ?lead(?:er(?:in)?)?|geschäftsführer(?:in)?|managing director|c[etfoi]o\b|hr[ \-]?(?:manager(?:in)?|business ?partner|generalist(?:in)?|specialist|assistent(?:in)?|referent(?:in)?)|human resources(?: manager(?:in)?| business partner)?|personal(?:referent(?:in)?|leiter(?:in)?|verantwortliche[rn]?|entwicklung|management|abteilung|marketing)|recruit(?:er(?:in)?|ing[ \-](?:manager(?:in)?|specialist|partner|lead))|talent acquisition(?: (?:manager(?:in)?|specialist|partner))?|employer branding[ a-zäöüß]{0,20}|(?:senior |lead |principal )?consultant|berater(?:in)?|office manager(?:in)?|assistenz der geschäftsführung|business ?partner|director|specialist|generalist|manager(?:in)?")

# tokens that look like names to the regex but never are, in advertisement text
NON_NAME_TOKENS = {"data", "scientist", "engineer", "engineering", "analyst", "analytics", "analysis", "business", "intelligence", "machine", "learning", "power", "bi", "master", "science", "senior", "junior", "lead", "head", "team", "manager", "managerin", "developer", "consultant", "gmbh", "ag", "kg", "og", "mbh", "co", "wien", "vienna", "graz", "linz", "salzburg", "innsbruck", "klagenfurt", "villach", "steiermark", "österreich", "austria", "europe", "group", "solutions", "services", "technologies", "technology", "software", "systems", "digital", "international", "sehr", "geehrte", "geehrter", "liebe", "lieber", "ihre", "ihr", "deine", "dein", "unser", "unsere", "wir", "sie", "bitte", "bewerbung", "bewerbungen", "kontakt", "stelle", "stellenangebot", "job", "jobs", "karriere", "position", "standort", "dienstort", "arbeitsort", "vollzeit", "teilzeit", "home", "office", "remote", "hybrid", "benefits", "gehalt", "bruttojahresgehalt", "kollektivvertrag", "über", "uns", "was", "du", "dich", "als", "der", "die", "das", "und", "für", "mit", "von", "bei", "the", "and", "for", "with", "you", "your", "our", "we", "join", "apply", "please", "about", "role", "about us", "cloud", "azure", "python", "sql", "excel", "sap", "linkedin", "xing", "gmbh.", "mensch", "menschen", "chancengleichheit", "diversity", "ansprechpartner", "ansprechpartnerin", "ansprechperson", "kontaktperson", "frau", "herr", "damen", "herren", "talent", "acquisition", "recruiting", "recruiter", "recruiterin", "hr", "human", "resources", "personal", "personalabteilung", "fragen", "tel", "telefon", "mail", "e-mail", "jetzt", "bewerben", "rückfragen", "verfügung", "kunden", "kunde"}


def _txt(v) -> str:
    return v if isinstance(v, str) else ""


def strip_html(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html or "")).strip()


def _snippet(text: str, start: int, end: int, pad: int = 110) -> str:
    return re.sub(r"\s+", " ", text[max(0, start - pad): min(len(text), end + pad)]).strip()


def _plausible_name(name: str) -> bool:
    toks = [t for t in re.split(r"\s+", name) if t]
    if len(toks) < 2:
        return False
    low = [t.lower().strip(".,;:") for t in toks]
    if any(t in NON_NAME_TOKENS for t in low):
        return False
    if any(len(t) < 2 for t in low):
        return False
    return True


def find_persons(text: str, company: str = "") -> list[dict]:
    """Named contact persons: salutation/academic title or a contact trigger nearby.
    The employer name is excluded, since "Beispiel Tech AG" also looks like a name."""
    company_tokens = {t for t in re.split(r"[^a-zäöüß]+", (company or "").lower()) if len(t) > 1}
    out = []
    triggers = [(m.start(), m.end()) for m in CONTACT_TRIGGER_RE.finditer(text)]
    scan = 0
    while (m := NAME_RE.search(text, scan)) is not None:
        name = re.sub(r"\s+", " ", m.group("name")).strip()
        if not _plausible_name(name) or all(t.lower() in company_tokens for t in name.split()):
            # the rejected candidate may have swallowed the salutation of a real
            # name ("Ansprechpartnerin Frau" before "Frau Julia Hofer"): rescan
            scan = m.start() + 1
            continue
        scan = m.end()
        sal = m.group("sal")
        near = min((abs(m.start() - s) for s, _ in triggers), default=10 ** 9)
        if sal:
            conf = "high" if near <= 400 else "medium"
        elif near <= 200:
            conf = "medium"
        else:
            continue
        tail = text[m.end(): m.end() + 140]
        lead = text[max(0, m.start() - 90): m.start()]
        pos = POSITION_RE.search(tail) or POSITION_RE.search(lead)
        out.append({"person_name": name, "salutation": sal, "person_position": re.sub(r"\s+", " ", pos.group(0)).strip() if pos else None,
                    "_offset": m.start(), "confidence": conf, "evidence": _snippet(text, m.start(), m.end())})
    # de-duplicate on name, keep the best-evidenced occurrence
    best: dict[str, dict] = {}
    order = {"high": 0, "medium": 1, "low": 2}
    for p in out:
        k = p["person_name"].lower()
        cur = best.get(k)
        if cur is None or (order[p["confidence"]], p["person_position"] is None) < (order[cur["confidence"]], cur["person_position"] is None):
            best[k] = p
    return sorted(best.values(), key=lambda p: p["_offset"])


def _email_kind(addr: str) -> str:
    local = addr.split("@", 1)[0].lower()
    base = re.split(r"[+._\-]", local)[0]
    if local in GENERIC_LOCALS or base in GENERIC_LOCALS:
        return "generic"
    if re.fullmatch(r"[a-z]{1,}[._\-][a-z]{2,}\d{0,3}", local) or re.fullmatch(r"[a-z]\.[a-z]{2,}", local):
        return "personal"
    return "unknown"


def _name_matches_local(name: str, addr: str) -> bool:
    local = addr.split("@", 1)[0].lower()
    parts = [re.sub(r"[^a-zß]", "", t.lower()) for t in name.split() if t]
    parts = [p for p in parts if len(p) > 1]
    if not parts:
        return False
    fold = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "s"})
    parts = [p.translate(fold) for p in parts]
    return all(p in local for p in parts[-2:]) or (parts[-1] in local and parts[0][0] == local[0])


def _domain_matches_company(domain: str, company: str, company_url: str) -> bool:
    host = re.sub(r"^www\.", "", (company_url or "").split("//")[-1].split("/")[0].lower())
    if host and domain.lower().endswith(host.split(":")[0]):
        return True
    tokens = [t for t in re.split(r"[^a-z0-9]+", (company or "").lower()) if len(t) > 3 and t not in {"gmbh", "austria", "group", "solutions", "services", "technologies", "international", "holding", "consulting"}]
    stem = domain.lower().split(".")[0]
    return any(t in stem or stem in t for t in tokens)


def find_emails(text: str, html: str) -> list[dict]:
    found: dict[str, dict] = {}

    def add(addr: str, how: str, offset: int | None, ev: str | None):
        addr = addr.strip(" .,;:<>()[]\"'").lower()
        if not addr or addr.count("@") != 1 or addr.endswith((".png", ".jpg", ".gif", ".webp")):
            return
        if addr not in found:
            found[addr] = {"email": addr, "extraction": how, "_offset": offset, "evidence": ev}

    for m in MAILTO_RE.finditer(html or ""):
        add(m.group(1), "mailto_link", None, None)
    for m in EMAIL_RE.finditer(text):
        add(m.group(0), "text", m.start(), _snippet(text, m.start(), m.end()))
    for m in OBFUSCATED_RE.finditer(text):
        add(f"{m.group(1)}@{m.group(2)}.{m.group(3)}", "obfuscated_text", m.start(), _snippet(text, m.start(), m.end()))
    return list(found.values())


def find_phones(text: str) -> list[dict]:
    out, seen = [], set()
    for m in PHONE_RE.finditer(text):
        raw = m.group(0).strip()
        digits = re.sub(r"\D", "", raw)
        if not (7 <= len(digits) <= 15):
            continue
        norm = "+43" + digits[4:] if digits.startswith("0043") else ("+43" + digits[1:] if digits.startswith("0") else "+" + digits)
        if norm in seen:
            continue
        seen.add(norm)
        out.append({"phone": norm, "phone_raw": re.sub(r"\s+", " ", raw), "evidence": _snippet(text, m.start(), m.end(), 70)})
    return out[:4]


def build_contacts(text: str, html: str, company: str, company_url: str) -> tuple[list[dict], dict]:
    """Contacts = e-mails joined to the nearest named person; named persons without
    an e-mail are kept as their own record. Every record carries its evidence."""
    emails = find_emails(text, html)
    persons = find_persons(text, company)
    phones = find_phones(text)
    used_persons: set[int] = set()
    contacts: list[dict] = []

    for e in emails:
        kind = _email_kind(e["email"])
        domain = e["email"].split("@", 1)[1]
        linked, how = None, None
        by_name = [p for p in persons if _name_matches_local(p["person_name"], e["email"])]
        if by_name:
            linked, how = by_name[0], "local_part_matches_name"
        elif e["_offset"] is not None and persons:
            near = min(persons, key=lambda p: abs(p["_offset"] - e["_offset"]))
            if abs(near["_offset"] - e["_offset"]) <= 400:
                linked, how = near, "same_text_block"
        if linked is not None:
            used_persons.add(linked["_offset"])
        conf = "high" if how == "local_part_matches_name" else ("high" if kind == "generic" and e["extraction"] == "mailto_link" else "medium")
        contacts.append({
            "email": e["email"], "email_kind": kind, "email_domain": domain,
            "domain_matches_company": _domain_matches_company(domain, company, company_url),
            "person_name": linked["person_name"] if linked else None,
            "salutation": linked["salutation"] if linked else None,
            "person_position": linked["person_position"] if linked else None,
            "phone": phones[0]["phone"] if phones else None,
            "extraction": e["extraction"], "person_link": how, "confidence": conf,
            "evidence": e.get("evidence") or (linked or {}).get("evidence"),
            "verified": False,
        })
    for p in persons:
        if p["_offset"] in used_persons:
            continue
        contacts.append({"email": None, "email_kind": None, "email_domain": None, "domain_matches_company": None,
                         "person_name": p["person_name"], "salutation": p["salutation"], "person_position": p["person_position"],
                         "phone": phones[0]["phone"] if phones else None, "extraction": "text", "person_link": None,
                         "confidence": p["confidence"], "evidence": p["evidence"], "verified": False})

    rank = {"personal": 0, "unknown": 1, "generic": 2, None: 3}
    best = sorted([c for c in contacts if c["email"]], key=lambda c: (rank[c["email_kind"]], not c["domain_matches_company"]))
    summary = {
        "status": "extracted" if contacts else "none_found",
        "n_contacts": len(contacts),
        "best_email": best[0]["email"] if best else None,
        "best_email_kind": best[0]["email_kind"] if best else None,
        "has_personal_email": any(c["email_kind"] == "personal" for c in contacts),
        "has_named_person": any(c["person_name"] for c in contacts),
        "phones": [p["phone"] for p in phones],
        "note": "Heuristic extraction from advertisement text; verify against the ad before sending anything.",
    }
    return contacts, summary


def find_application_urls(text: str, html: str, source_url: str) -> list[str]:
    cand = [m.group(1) for m in HREF_RE.finditer(html or "")] + [m.group(0) for m in URL_RE.finditer(text)]
    keep, seen = [], set()
    for u in cand:
        if not u.lower().startswith("http"):
            continue
        if not re.search(r"bewerb|apply|application|jobs?|karriere|career|stelle|vacanc|recruit", u, re.I):
            continue
        u = u.strip(" .,;)\"'")
        if u in seen or u == source_url:
            continue
        seen.add(u)
        keep.append(u)
    return keep[:5]


# ------------------------------------------------------------------ helpers
def _as_date(v) -> date | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        ts = pd.to_datetime(v, errors="coerce", utc=True)
    except Exception:
        return None
    return None if pd.isna(ts) else ts.date()


def _as_list(v) -> list:
    if isinstance(v, list):
        return [x for x in v if x is not None]
    if isinstance(v, str) and v.startswith("["):
        try:
            return json.loads(v)
        except Exception:
            return []
    if isinstance(v, str) and v:
        return [v]
    return []


def _clean(v):
    """JSON-safe scalar (NaN/NaT -> None, numpy -> python)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (pd._libs.tslibs.timestamps.Timestamp, datetime)):
        return str(v)
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            return v
    return v


def open_status(row: dict, run_day: date) -> dict:
    vt, posted, coll = _as_date(row.get("valid_through")), _as_date(row.get("posted_date")), _as_date(row.get("collected_at"))
    age_posted = (run_day - posted).days if posted else None
    age_coll = (run_day - coll).days if coll else None
    if vt and vt < run_day:
        is_open, status = False, "expired_per_source"
    elif vt:
        is_open, status = True, "stated_open_until_valid_through"
    elif age_coll is not None and age_coll <= 7:
        is_open, status = True, "open_at_collection_recent_snapshot"
    elif age_posted is not None and age_posted > 120:
        is_open, status = None, "unknown_stale_posting"
    else:
        is_open, status = None, "unknown_snapshot_aged"
    return {"is_open": is_open, "open_status": status, "valid_through": str(vt) if vt else None,
            "posted_date": str(posted) if posted else None, "days_since_posted": age_posted,
            "snapshot_age_days": age_coll,
            "requires_reverification": bool(age_coll is None or age_coll > 7),
            "reverify_url": row.get("source_url")}


GERMAN_RISK = {"required": "blocking_unless_b2_c1", "required_implied": "blocking_unless_b2_c1", "preferred": "manageable_advantage_only", "mentioned": "manageable_advantage_only", "german_or_english": "low", "not_required": "low", "not_mentioned": None}
GERMAN_RISK_SCORE = {"blocking_unless_b2_c1": 0.15, "likely_blocking": 0.3, "manageable_advantage_only": 0.7, "unclear_german_written_ad": 0.5, "low": 1.0}


def german_risk(row: dict) -> str:
    req = (row.get("german_requirement") or "not_mentioned")
    risk = GERMAN_RISK.get(req)
    if risk is None:
        risk = "low" if (row.get("posting_language") == "en") else "unclear_german_written_ad"
    if risk == "blocking_unless_b2_c1" and (row.get("german_level_bucket") in (None, "", "unspecified")):
        risk = "likely_blocking"
    return risk


def location_fit(row: dict) -> tuple[str, float]:
    if row.get("remote_type") == "remote":
        return "fully_remote", 0.95
    if row.get("is_graz_area"):
        return "graz_area", 1.0
    if row.get("is_styria"):
        return "styria", 0.9
    if row.get("is_austria_wide"):
        return "austria_wide", 0.7
    if row.get("is_vienna"):
        return ("vienna_hybrid", 0.55) if row.get("remote_type") in ("hybrid", "hybrid_or_flexible") else ("vienna_on_site", 0.4)
    return ("other_region_hybrid", 0.45) if row.get("remote_type") in ("hybrid", "hybrid_or_flexible") else ("other_region_on_site", 0.3)


def fit_block(row: dict, ctx: dict) -> dict:
    skills = []
    for f in SKILL_FIELDS:
        skills += _as_list(row.get(f))
    skills = list(dict.fromkeys(skills))
    have, developing, structural = ctx["have"], ctx["developing"], ctx["structural"]
    matched_have = [s for s in skills if s in have]
    matched_dev = [s for s in skills if s in developing]
    gaps_struct = [s for s in skills if s in structural]
    gaps_other = [s for s in skills if s not in have and s not in developing and s not in structural]
    denom = len(skills) or 1
    overlap = round((len(matched_have) + 0.6 * len(matched_dev)) / denom, 3)
    rank = ctx["skill_rank"]
    cv_keywords = sorted([s for s in skills if s in have or s in developing], key=lambda s: rank.get(s, 999))
    fam = row.get("role_family")
    med = ctx["family_salary"].get(fam)
    smin = _clean(row.get("salary_min_annual_eur"))
    lf, lf_score = location_fit(row)
    return {
        "posting_skills": skills,
        "matched_have": matched_have, "matched_developing": matched_dev,
        "gaps_structural": gaps_struct, "gaps_other": gaps_other,
        "profile_overlap_share": overlap,
        "cv_keywords_ranked": cv_keywords[:25],
        "cv_keywords_missing_high_value": [s for s in sorted(gaps_other + gaps_struct, key=lambda s: rank.get(s, 999)) if rank.get(s, 999) < 40][:10],
        "german_risk": german_risk(row),
        "german_requirement": row.get("german_requirement"), "german_level_bucket": row.get("german_level_bucket"),
        "english_requirement": row.get("english_requirement"),
        "location_fit": lf,
        "seniority": row.get("seniority"),
        "seniority_fit": {"intern_student": "below_profile", "trainee_junior": "entry_ok_pay_low", "senior": "title_asks_domain_seniority", "lead_head": "title_asks_domain_seniority"}.get(row.get("seniority"), "unlabelled_open"),
        "experience_min_years": _clean(row.get("experience_min_years")),
        "degree_requirement": row.get("degree_requirement"),
        "salary_vs_family_median": (round(smin - med) if (smin and med) else None),
        "family_median_min_salary": med,
    }


def scoring_block(row: dict, fit: dict, contact_summary: dict, ctx: dict) -> dict:
    fam_rank = ctx["family_rank"].get(row.get("role_family"), 8)
    comp = {
        "skill_overlap": round(30 * min(fit["profile_overlap_share"], 1.0), 1),
        "language": round(25 * GERMAN_RISK_SCORE.get(fit["german_risk"], 0.5), 1),
        "location": round(20 * location_fit(row)[1], 1),
        "family_priority": round(15 * (1 - (fam_rank - 1) / 7), 1),
        "contactability": round(10 * ({"personal": 1.0, "unknown": 0.8, "generic": 0.6}.get(contact_summary.get("best_email_kind"), 0.35)), 1),
    }
    total = round(sum(comp.values()), 1)
    return {"apply_priority_score": total, "score_components": comp, "score_max": 100,
            "priority_tier": "A" if total >= 65 else ("B" if total >= 48 else "C"),
            "weights_note": "Transparent weighted sum (skills 30 / language 25 / location 20 / family 15 / contactability 10). Ordinal triage aid, not a hiring probability."}


def outreach_block(row: dict, fit: dict, contacts: list[dict], contact_summary: dict, ctx: dict, app_urls: list[str]) -> dict:
    if contact_summary.get("best_email_kind") == "personal":
        channel = "email_named_person"
    elif contact_summary.get("best_email"):
        channel = "email_generic_inbox"
    elif app_urls:
        channel = "portal_form"
    elif row.get("source") == "linkedin":
        channel = "linkedin_posting"
    else:
        channel = "source_page"
    lang = "de" if (row.get("posting_language") != "en" or fit["german_risk"] in ("blocking_unless_b2_c1", "likely_blocking")) else "en"
    named = next((c for c in contacts if c.get("person_name")), None)
    company = row.get("company") or row.get("company_raw")
    hooks = []
    n_other = ctx["employer_postings"].get((row.get("company_norm") or "").lower(), 0)
    if n_other > 1:
        hooks.append(f"{company} had {n_other} data postings in the 2026-09-16 snapshot")
    top = fit["cv_keywords_ranked"][:4]
    if top:
        hooks.append("Ad names " + ", ".join(top) + " — all on the CV")
    if row.get("is_graz_area"):
        hooks.append("Graz area: no relocation needed, on-site from day one")
    elif row.get("remote_type") in ("remote", "hybrid", "hybrid_or_flexible"):
        hooks.append(f"Ad states {row.get('remote_type')} work model")
    if row.get("posting_language") == "en":
        hooks.append("Ad written in English")
    if fit["gaps_structural"][:3]:
        hooks.append("Known gaps to address up front: " + ", ".join(fit["gaps_structural"][:3]))
    return {
        "channel": channel, "language": lang,
        "to_email": contact_summary.get("best_email"),
        "to_person": (named or {}).get("person_name"),
        "to_person_position": (named or {}).get("person_position"),
        "salutation": salutation_line(named, lang),
        "apply_urls": app_urls, "source_url": row.get("source_url"),
        "personalization_hooks": hooks,
        "template_slots": {"role_title": row.get("title"), "company": company, "location": row.get("city") or row.get("location_text"),
                           "evidence_line": "; ".join(top), "gap_line": ", ".join(fit["gaps_structural"][:2]),
                           "language_line": {"de": "Deutsch A2–B1, Englisch fließend", "en": "English fluent, German A2–B1 and improving"}[lang]},
        "compliance_note": "Applying to a contact address stated in an advertisement is the advertised purpose; do not reuse these addresses for bulk marketing (DSGVO / TKG §174).",
    }


def salutation_line(named: dict | None, lang: str) -> str:
    if not named or not named.get("person_name"):
        return "Sehr geehrte Damen und Herren" if lang == "de" else "Dear Hiring Team"
    parts = named["person_name"].split()
    if lang == "en":
        return f"Dear {parts[0]}"
    sal = (named.get("salutation") or "").lower()
    if sal.startswith("frau"):
        return f"Sehr geehrte Frau {parts[-1]}"
    if sal.startswith("herr"):
        return f"Sehr geehrter Herr {parts[-1]}"
    return f"Sehr geehrte/r {named['person_name']}"  # the ad did not state a form of address


PIPELINE_DEFAULT = {"status": "new", "stage": "identified", "priority_tier": None, "applied_at": None, "cv_variant": None,
                    "cover_letter_variant": None, "outreach_sent_at": None, "follow_up_due": None, "last_touch": None,
                    "outcome": None, "notes": [], "history": []}


def lead_from_posting(row: dict, ctx: dict, run_day: date) -> dict:
    text = _txt(row.get("description_text")) or strip_html(_txt(row.get("description_html")))
    html = _txt(row.get("description_html"))
    company = row.get("company") or row.get("company_raw") or ""
    contacts, csum = build_contacts(text, html, company, _txt(row.get("company_url")))
    app_urls = find_application_urls(text, html, _txt(row.get("source_url")))
    fit = fit_block(row, ctx)
    scoring = scoring_block(row, fit, csum, ctx)
    pipe = dict(PIPELINE_DEFAULT, priority_tier=scoring["priority_tier"])
    return {
        "lead_id": row.get("posting_uid"),
        "record_type": "posting",
        "company": {"name": company or None, "name_norm": row.get("company_norm"), "url": _clean(row.get("company_url")),
                    "size_raw": _clean(row.get("company_size_raw")), "main_location": _clean(row.get("company_main_location")),
                    "industry_raw": _clean(row.get("industry_raw")),
                    "postings_in_snapshot": ctx["employer_postings"].get((row.get("company_norm") or "").lower(), 1),
                    "is_anonymous": not bool(company)},
        "contacts": [{k: v for k, v in c.items() if not k.startswith("_")} for c in contacts],
        "contact_summary": csum,
        "job": {"title": _clean(row.get("title")), "normalized_title": row.get("normalized_title"), "role_family": row.get("role_family"),
                "seniority": row.get("seniority"), "employment_type": row.get("employment_type"),
                "is_internship_student": _clean(row.get("is_internship_student")), "is_temporary_or_contract": _clean(row.get("is_temporary_or_contract")),
                "posting_language": row.get("posting_language"),
                "description_text": text or None, "description_length": _clean(row.get("description_length")),
                "esco_occupation_uris": _as_list(row.get("esco_occupation_uris"))},
        "status": open_status(row, run_day),
        "source": {"source": row.get("source"), "source_type": row.get("source_type"), "source_url": _clean(row.get("source_url")),
                   "source_id": _clean(row.get("source_id")), "collected_at": _clean(row.get("collected_at")),
                   "also_seen_on": _as_list(row.get("sources_in_group")), "dedupe_group_size": _clean(row.get("dedupe_group_size")),
                   "surfaced_by_queries": _as_list(row.get("queries"))},
        "location": {"location_text": _clean(row.get("location_text")), "city": row.get("city"), "state": row.get("state"),
                     "region_labels": _as_list(row.get("region_labels")), "is_styria": _clean(row.get("is_styria")),
                     "is_graz_area": _clean(row.get("is_graz_area")), "is_vienna": _clean(row.get("is_vienna")),
                     "is_austria_wide": _clean(row.get("is_austria_wide")), "multi_location": _clean(row.get("multi_location")),
                     "remote_type": row.get("remote_type"), "home_office_days_per_week": _clean(row.get("home_office_days_per_week"))},
        "salary": {"min_annual_eur": _clean(row.get("salary_min_annual_eur")), "max_annual_eur": _clean(row.get("salary_max_annual_eur")),
                   "basis": row.get("salary_basis"), "transparency": row.get("salary_transparency"), "period_detected": row.get("salary_period"),
                   "kv_minimum_mention": _clean(row.get("salary_kv_mention")), "overpay_mention": _clean(row.get("salary_overpay_mention")),
                   "all_in_mention": _clean(row.get("salary_all_in_mention")), "bonus_mention": _clean(row.get("salary_bonus_mention")),
                   "part_time_basis_risk": _clean(row.get("salary_part_time_basis_risk")), "snippet": _clean(row.get("salary_snippet")),
                   "note": "Advertised figure, usually the collective-agreement minimum — a floor, not pay."},
        "requirements": {"german_requirement": row.get("german_requirement"), "german_level_stated": _clean(row.get("german_level_stated")),
                         "german_level_bucket": row.get("german_level_bucket"), "german_snippet": _clean(row.get("german_snippet")),
                         "english_requirement": row.get("english_requirement"), "english_level_bucket": row.get("english_level_bucket"),
                         "other_languages": _as_list(row.get("other_languages")),
                         "experience_min_years": _clean(row.get("experience_min_years")), "experience_max_years": _clean(row.get("experience_max_years")),
                         "experience_text": _clean(row.get("experience_text")), "degree_requirement": row.get("degree_requirement"),
                         "degree_levels": _as_list(row.get("degree_levels")), "degree_fields": _as_list(row.get("degree_fields")),
                         "degree_or_equivalent": _clean(row.get("degree_or_equivalent")),
                         "skills": {f.replace("skills_", ""): _as_list(row.get(f)) for f in SKILL_FIELDS}},
        "fit": fit,
        "outreach": outreach_block(row, fit, contacts, csum, ctx, app_urls),
        "scoring": scoring,
        "pipeline": pipe,
    }


def lead_from_employer(row: dict, ctx: dict) -> dict:
    fams = [f.strip() for f in str(row.get("families") or "").split(",") if f.strip()]
    states = [s.strip() for s in str(row.get("states") or "").split(",") if s.strip()]
    srcs = [s.strip() for s in str(row.get("sources") or "").split(",") if s.strip()]
    main_fam = min(fams, key=lambda f: ctx["family_rank"].get(f, 9)) if fams else None
    name = row.get("example_company") or row.get("company_norm")
    n = int(row.get("postings") or 0)
    styria = int(row.get("styria") or 0)
    graz = int(row.get("graz_area") or 0)
    loc_score = 1.0 if graz else (0.9 if styria else (0.55 if "Wien" in states else 0.4))
    fam_rank = ctx["family_rank"].get(main_fam, 8)
    comp = {"skill_overlap": round(30 * ctx["family_overlap"].get(main_fam, 0.5), 1),
            "language": round(25 * 0.5, 1),
            "location": round(20 * loc_score, 1),
            "family_priority": round(15 * (1 - (fam_rank - 1) / 7), 1),
            "contactability": 3.5}
    total = round(sum(comp.values()), 1)
    tier = "A" if total >= 65 else ("B" if total >= 48 else "C")
    return {
        "lead_id": f"employer:{row.get('company_norm')}",
        "record_type": "employer_aggregate",
        "company": {"name": name, "name_norm": row.get("company_norm"), "url": None, "size_raw": None, "main_location": states[0] if states else None,
                    "industry_raw": None, "postings_in_snapshot": n, "is_anonymous": False, "is_agency": bool(row.get("is_agency"))},
        "contacts": [],
        "contact_summary": {"status": "not_collected", "n_contacts": 0, "best_email": None, "best_email_kind": None,
                            "has_personal_email": False, "has_named_person": False, "phones": [],
                            "note": "Employer-level record built from aggregated tables: the per-posting advertisement text that carries contact data is not in this checkout (see meta.mode_explanation).",
                            "discovery": {"search_queries": [f"{name} Karriere", f"{name} Jobs Data", f"{name} Impressum E-Mail", f"{name} LinkedIn HR"],
                                          "suggested_sources": ["company careers page", "Impressum (Austrian sites must publish a contact address)", "LinkedIn company page → People → HR/Recruiting"]}},
        "opportunity": {"postings_in_snapshot": n, "role_families": fams, "states": states, "styria_postings": styria,
                        "graz_area_postings": graz, "seen_on_sources": srcs, "is_agency": bool(row.get("is_agency")),
                        "snapshot_note": "Counts are open ads on 2026-09-16, one day — not annual hiring."},
        "market_context": ctx["family_context"].get(main_fam, {}),
        "fit": {"dominant_family": main_fam, "family_profile_overlap_top15": ctx["family_overlap"].get(main_fam),
                "family_top_skills": (ctx["family_context"].get(main_fam) or {}).get("top_tech_skills"),
                "german_required_share_family": (ctx["family_context"].get(main_fam) or {}).get("german_required_share"),
                "location_fit": "graz_area" if graz else ("styria" if styria else ("vienna" if "Wien" in states else "other_region"))},
        "outreach": {"channel": "research_then_contact", "language": "de", "to_email": None, "to_person": None,
                     "apply_urls": [], "source_url": None,
                     "personalization_hooks": [f"{n} data-role ad(s) in the 2026-09-16 snapshot across {', '.join(fams) or 'n/a'}"] + ([f"{graz} of them in the Graz area"] if graz else []),
                     "compliance_note": "Speculative applications to a published company address are permitted; do not build a bulk marketing list from this file."},
        "scoring": {"apply_priority_score": total, "score_components": comp, "score_max": 100, "priority_tier": tier,
                    "weights_note": "Same weights as posting mode; language and contactability are placeholders because no ad text is available here."},
        "pipeline": dict(PIPELINE_DEFAULT, priority_tier=tier),
    }


# ------------------------------------------------------------------ context
def load_context() -> dict:
    prof = json.load(open(CFG / "profile.json", encoding="utf-8"))
    ctx = {"have": set(prof["have"]), "developing": set(prof["developing"]), "structural": set(prof["structural"]), "profile": prof}
    st = pd.read_csv(TAB / "T05_skills_all_tech.csv")
    ctx["skill_rank"] = {s: i for i, s in enumerate(st.skill.tolist())}
    sal = pd.read_csv(TAB / "T09b_salary_by_role_family.csv")
    ctx["family_salary"] = {r.role_family: (None if pd.isna(r.min_median) else float(r.min_median)) for r in sal.itertuples()}
    d01 = pd.read_csv(TAB / "D01_decision_matrix.csv")
    ctx["family_rank"] = {r.role_family: int(r.rank_default) for r in d01.itertuples() if not pd.isna(r.rank_default)}
    ctx["family_overlap"] = {r.role_family: float(r.V5_profile_overlap_top15) for r in d01.itertuples()}
    t14 = pd.read_csv(TAB / "T14_family_profiles.csv")
    ctx["family_context"] = {r.role_family: {"n_postings_in_snapshot": int(r.n_with_description), "top_tech_skills": r.top15_skills if hasattr(r, "top15_skills") else r.top_tech_skills,
                                             "top_business_context": r.top_business, "german_required_share": float(r.german_required_share),
                                             "english_posting_share": float(r.english_posting_share), "degree_required_share": float(r.degree_required_share),
                                             "median_min_salary_eur": None if pd.isna(r.median_min_salary) else float(r.median_min_salary),
                                             "styria_share": float(r.styria_share)} for r in t14.itertuples()}
    emp = pd.read_csv(TAB / "T04_employers.csv")
    ctx["employer_postings"] = {str(r.company_norm).lower(): int(r.postings) for r in emp.itertuples()}
    ctx["employers_df"] = emp
    return ctx


def read_postings(path: Path) -> list[dict]:
    if path.suffix == ".parquet":
        return pd.read_parquet(path).to_dict("records")
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def preserve_pipeline(leads: list[dict], out_path: Path) -> int:
    """Keep tracking state (status, dates, notes) from a previous run of this file."""
    if not out_path.exists():
        return 0
    try:
        prev = json.load(open(out_path, encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    old = {l["lead_id"]: l.get("pipeline") for l in prev.get("leads", []) if l.get("lead_id")}
    kept = 0
    for l in leads:
        p = old.get(l["lead_id"])
        if p and p != dict(PIPELINE_DEFAULT, priority_tier=p.get("priority_tier")):
            l["pipeline"] = p
            kept += 1
    return kept


FIELD_DICTIONARY = {
    "lead_id": "posting_uid (<source>:<source_id>) in posting mode, 'employer:<company_norm>' in employer mode",
    "record_type": "posting | employer_aggregate",
    "contacts[]": "one per e-mail found, plus named persons without an e-mail; email_kind = personal|generic|unknown; confidence = high|medium|low; evidence = the text it was read from; verified = set true yourself after checking the ad",
    "contact_summary.best_email": "preferred address: personal over generic, company domain preferred",
    "status.is_open": "true|false|null — null means the snapshot cannot tell; always re-check status.reverify_url before applying",
    "fit": "profile match for CV tailoring: matched/gap skills, cv_keywords_ranked (employer wording ordered by national frequency), german_risk, location_fit",
    "outreach": "channel, language, salutation and template_slots for a cold e-mail or cover letter",
    "scoring.apply_priority_score": "0-100 transparent weighted sum for triage (skills 30 / language 25 / location 20 / family 15 / contactability 10)",
    "pipeline": "your tracking state; preserved across re-runs by lead_id",
}

USAGE_NOTES = [
    "Advertised salary figures are collective-agreement floors, not pay.",
    "The snapshot is one day (2026-09-16): re-check every posting's status.reverify_url before applying — many will be closed.",
    "Contact fields are regex extractions from ad text: read contacts[].evidence before using an address, and set verified=true once checked.",
    "Use contact addresses for the purpose they were published for (applications). Bulk unsolicited commercial mail to them is a separate matter under DSGVO / TKG §174.",
    "Do not re-run the posting collectors to refresh this file; see DECISION_LOG.md D-013.",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=DEFAULT_IN, help="postings_dedup.jsonl / .parquet (private)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output JSON (must stay git-ignored)")
    ap.add_argument("--mode", choices=["auto", "postings", "employers"], default="auto")
    ap.add_argument("--include-adjacent", action="store_true", help="also include ai_software_engineering / other_data titles")
    ap.add_argument("--all-postings", action="store_true", help="no role-family filter at all")
    ap.add_argument("--min-score", type=float, default=None, help="drop leads below this apply_priority_score")
    args = ap.parse_args(argv)

    run_day = date.today()
    ctx = load_context()
    mode = args.mode
    if mode == "auto":
        mode = "postings" if args.input.exists() else "employers"
    if mode == "postings" and not args.input.exists():
        print(f"ERROR: {args.input} not found (it is private data).", file=sys.stderr)
        return 2

    warnings: list[str] = []
    if mode == "postings":
        rows = read_postings(args.input)
        fams = set(CORE_FAMILIES) | (set(ADJACENT_FAMILIES) if args.include_adjacent else set())
        rows = [r for r in rows if (r.get("is_canonical") in (True, "True", 1, None)) and (args.all_postings or r.get("role_family") in fams)]
        leads = [lead_from_posting(r, ctx, run_day) for r in rows]
        mode_explanation = f"Per-posting leads built from {args.input.relative_to(ROOT) if args.input.is_relative_to(ROOT) else args.input}."
        n_contact = sum(1 for l in leads if l["contact_summary"]["best_email"])
        if n_contact == 0 and leads:
            warnings.append("No e-mail address was found in any advertisement text — check that description_text is populated.")
    else:
        emp = ctx["employers_df"]
        leads = [lead_from_employer(r._asdict(), ctx) for r in emp.itertuples(index=False)]
        mode_explanation = (
            "EMPLOYER MODE (fallback). data/processed/postings_dedup.jsonl is not in this checkout: advertisement text, "
            "source URLs and the contact persons/e-mails inside the ads are private data (README 'What is in this repository', "
            "PUBLICATION_DECISION.md). These leads are therefore employer-level, built from outputs/tables/T04_employers.csv, "
            "and carry no contact data. Run this script where the private data lives to get per-posting leads with e-mails."
        )
        warnings.append("No contact data: run with --input pointing at the private postings_dedup.jsonl to populate contacts.")
        n_contact = 0

    if args.min_score is not None:
        leads = [l for l in leads if l["scoring"]["apply_priority_score"] >= args.min_score]
    leads.sort(key=lambda l: -l["scoring"]["apply_priority_score"])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    kept = preserve_pipeline(leads, args.out)

    tiers: dict[str, int] = {}
    for l in leads:
        tiers[l["scoring"]["priority_tier"]] = tiers.get(l["scoring"]["priority_tier"], 0) + 1
    market = json.load(open(OUT_JSON / "market_summary.json", encoding="utf-8"))
    doc = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "generator": "src/pipeline/build_application_leads.py",
            "mode": mode,
            "mode_explanation": mode_explanation,
            "input": str(args.input) if mode == "postings" else "outputs/tables/T04_employers.csv",
            "snapshot_vintage": market["collected_at_range"],
            "snapshot_age_days": (run_day - _as_date(market["collected_at_range"]["max"])).days,
            "counts": {"leads": len(leads), "with_email": n_contact, "by_tier": tiers, "pipeline_states_preserved": kept},
            "privacy": "Contains advertisement text, source URLs and (in posting mode) contact persons' names, e-mails and phone numbers. Git-ignored on purpose — never commit or publish this file.",
            "usage_notes": USAGE_NOTES,
            "warnings": warnings,
        },
        "field_dictionary": FIELD_DICTIONARY,
        "profile": ctx["profile"],
        "market_context": {
            "families": ctx["family_context"],
            "family_rank_default": ctx["family_rank"],
            "family_median_min_salary_eur": ctx["family_salary"],
            "top_skills_national": [{"skill": s, "rank": i + 1} for s, i in list(ctx["skill_rank"].items())[:40]],
            "source": "outputs/tables (T05, T09b, T14, D01); see AGENT_CONTEXT.md for the reading rules.",
        },
        "leads": leads,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print(f"{args.out}: {len(leads)} leads ({mode} mode), {n_contact} with an e-mail, tiers {tiers}, {kept} pipeline states preserved")
    for w in warnings:
        print(f"  warning: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
