"""Layer 2 pipeline: normalise the private GitHub supply collection (and manual LinkedIn records, if any) into the
candidate / project / skill-evidence tables defined in schemas/supply_schema.md.

Input : data/raw/github_supply/<date>/{users_search,profiles,repos,readmes,social}.jsonl
        data/processed/supply_linkedin_profiles.csv (optional, from src/acquisition/ingest_linkedin_manual.py)
Output: data/processed/supply_candidates.{jsonl,parquet}, supply_projects.{jsonl,parquet}, supply_skill_evidence.parquet,
        supply_build_manifest.json   — all PRIVATE (individual-level; see PUBLICATION_DECISION.md)

Every derived field is rule-based and traceable to config/supply_taxonomy.json, config/capability_map.json and the Layer 1
configs (role_taxonomy, skills_taxonomy, geo) which are reused unchanged: bios go through the Layer 1 title cleaner and
role rules after the bio-specific overrides; skills use the Layer 1 controlled vocabulary; locations use geo.json.
Personal names and e-mail addresses are never read; logins are kept only in the private files for traceability.

Redaction is terminal (src/pipeline/redact_supply_raw.py): once a GitHub collection folder carries REDACTED.json (or
README bodies flagged readme_redacted), a full build refuses to run, because it would silently regenerate the candidate and
project tables from redacted inputs. `--linkedin-only` refreshes just the LinkedIn slot rows of the existing candidate table
and works on redacted collections.

Usage: python src/pipeline/build_supply.py [--date 2026-09-17] [--linkedin-only]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
import normalize as N  # noqa: E402  (Layer 1 rules; same folder, or the pytest pythonpath)

CFG = json.load(open(ROOT / "config" / "supply_taxonomy.json", encoding="utf-8"))
CAP = json.load(open(ROOT / "config" / "capability_map.json", encoding="utf-8"))["capabilities"]
CORE_FAMILIES = {"data_analytics", "bi", "data_science", "data_engineering", "data_governance", "marketing_analytics", "product_analytics", "business_analysis"}
ADJACENT_FAMILIES = set(CFG.get("families_adjacent", []))
GEO = N.GEO
SKILLS = N.SKILLS


def _rx(p: str) -> re.Pattern:
    return re.compile(p, re.I)


def _rxs(lst: list[str]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in lst), re.I)


def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def cid(source: str, key) -> str:
    return hashlib.sha1(f"{source}:{key}".encode()).hexdigest()[:16]


# ------------------------------------------------------------------ bio → role / seniority / student / transition
BR = CFG["bio_role_overrides"]
BIO_RULES = [(r["family"], r["normalized"], _rxs(r["patterns"])) for r in BR["rules"]]
STUDENT_RE = _rxs(BR["student_patterns"])
ACADEMIC_RE = _rxs(BR["academic_patterns"])
SEN_RE = {k: _rxs(v) for k, v in BR["seniority_bio"].items()}
TR = BR["transition_patterns"]
TR_EXPLICIT = _rxs(TR["explicit"])
TR_FROM = {k[5:]: _rxs(v) for k, v in TR.items() if k.startswith("from_")}


TR_SPLIT = _rx(r"\bturned\b|\bnow\b|\btransition(?:ing|ed)? (?:to|into)\b|\bmoved (?:to|into)\b|\bswitch(?:ed|ing)? to\b|\bbecame\b|\bcurrently\b|\bthese days\b|\bjetzt\b|→|->")


def bio_role(bio: str) -> dict:
    b = (bio or "").lower()
    if not b.strip():
        return {"bio_role_family": None, "bio_normalized_title": None, "bio_role_rule": None}
    # transition wording: classify the segment AFTER the last transition word first ("marketing manager turned data analyst")
    parts = TR_SPLIT.split(b)
    if len(parts) > 1 and parts[-1].strip():
        r = bio_role(parts[-1])
        if r["bio_role_family"]:
            r["bio_role_rule"] = "after_transition:" + r["bio_role_rule"]
            return r
    for fam, norm, rx in BIO_RULES:
        m = rx.search(b)
        if m:
            return {"bio_role_family": fam, "bio_normalized_title": norm, "bio_role_rule": "override:" + m.group(0)}
    tc, _ = N.clean_title(bio)
    r = N.classify_role(tc)
    fam = r["role_family"]
    if fam in ("out_of_scope",):
        return {"bio_role_family": None, "bio_normalized_title": None, "bio_role_rule": r.get("role_oos_reason")}
    return {"bio_role_family": fam, "bio_normalized_title": r["normalized_title"], "bio_role_rule": "layer1:" + str(r.get("role_rule"))}


def bio_seniority(bio: str) -> str:
    b = (bio or "").lower()
    if not b.strip():
        return "unknown"
    if STUDENT_RE.search(b):
        return "student"
    for lvl in ("lead_head", "senior", "junior"):
        if SEN_RE[lvl].search(b):
            return lvl
    return "unlabelled"


def transitions(bio: str) -> dict:
    b = (bio or "").lower()
    froms = [k for k, rx in TR_FROM.items() if rx.search(b)]
    return {"transition_explicit": bool(TR_EXPLICIT.search(b)) if b else False, "prior_domains": froms}


DE_SHORT = {"und", "der", "die", "das", "mit", "für", "fuer", "ich", "bin", "bei", "von", "zu", "im", "nicht", "ein", "eine", "aus", "auf", "wir", "sind", "oder", "über", "zur", "zum", "student*in", "studentin", "wissenschaftler", "mitarbeiter", "berater", "entwickler", "daten"}
EN_SHORT = {"and", "the", "with", "for", "i", "am", "at", "of", "in", "to", "a", "an", "from", "on", "is", "my", "about", "who", "into", "by", "student", "engineer", "scientist", "developer", "researcher", "based", "working", "interested", "passionate", "enthusiast", "love", "building"}


def short_text_language(text: str) -> str | None:
    """de / en / mixed for short self-descriptions (bios): counts language-specific function words and role nouns; None when no signal."""
    toks = re.findall(r"[a-zäöüß*]+", (text or "").lower())
    if len(toks) < 3:
        return None
    de = sum(t in DE_SHORT for t in toks); en = sum(t in EN_SHORT for t in toks)
    if de == 0 and en == 0:
        return None
    if de > en:
        return "de"
    if en > de:
        return "en"
    return "mixed"


# ------------------------------------------------------------------ education / certification (bio + readme)
ED = CFG["education_bio_patterns"]
ED_LEVEL = {k: _rxs(v) for k, v in ED["levels"].items()}
ED_FIELD = {k: _rxs(v) for k, v in ED["fields"].items()}
ED_INST = {k: _rxs(v) for k, v in ED["institutions"].items() if not k.startswith("_")}
CERT = {k: _rxs(v) for k, v in CFG["certification_patterns"].items() if not k.startswith("_")}
L1_CERT = {k: [_rx(p) for p in v] for k, v in SKILLS["certifications"].items()}


def education(text: str) -> dict:
    t = (text or "").lower()
    lv = [k for k, rx in ED_LEVEL.items() if rx.search(t)]
    fd = [k for k, rx in ED_FIELD.items() if rx.search(t)]
    inst = [k for k, rx in ED_INST.items() if rx.search(t)]
    return {"edu_levels": lv, "edu_fields": fd, "edu_institutions": inst}


def certifications(text: str) -> list[str]:
    t = (text or "")
    out = [k for k, rx in CERT.items() if rx.search(t)]
    for k, pats in L1_CERT.items():
        if k not in out and any(p.search(t) for p in pats):
            out.append(k)
    return out


# ------------------------------------------------------------------ geography (reuse geo.json)
STATE_ALIASES = {k.lower(): v for k, v in GEO["state_aliases"].items()}
CITY_STATE = {k: v for k, v in GEO["cities"].items() if not k.startswith("_")}
CITIES_SORTED = sorted(CITY_STATE, key=len, reverse=True)
GRAZ_SET = set(GEO["graz_commute"]["places"])
EXTRA_CITY_STATE = {"villach": "Kärnten", "wels": "Oberösterreich", "steyr": "Oberösterreich", "dornbirn": "Vorarlberg", "bregenz": "Vorarlberg",
                    "feldkirch": "Vorarlberg", "st. pölten": "Niederösterreich", "sankt pölten": "Niederösterreich", "st pölten": "Niederösterreich",
                    "wiener neustadt": "Niederösterreich", "krems": "Niederösterreich", "eisenstadt": "Burgenland", "leoben": "Steiermark",
                    "kapfenberg": "Steiermark", "hagenberg": "Oberösterreich", "leonding": "Oberösterreich", "traun": "Oberösterreich",
                    "baden": "Niederösterreich", "mödling": "Niederösterreich", "klosterneuburg": "Niederösterreich", "tulln": "Niederösterreich",
                    "amstetten": "Niederösterreich", "wolfsberg": "Kärnten", "spittal": "Kärnten", "lienz": "Tirol", "kufstein": "Tirol", "schwaz": "Tirol",
                    "hallein": "Salzburg", "zell am see": "Salzburg", "bruck an der mur": "Steiermark", "weiz": "Steiermark", "gleisdorf": "Steiermark",
                    "leibnitz": "Steiermark", "deutschlandsberg": "Steiermark", "feldbach": "Steiermark", "judenburg": "Steiermark", "knittelfeld": "Steiermark",
                    "hartberg": "Steiermark", "fürstenfeld": "Steiermark", "liezen": "Steiermark", "voitsberg": "Steiermark", "köflach": "Steiermark",
                    "murau": "Steiermark", "mürzzuschlag": "Steiermark", "trofaiach": "Steiermark", "schladming": "Steiermark", "bad radkersburg": "Steiermark",
                    "innsbruck": "Tirol", "klagenfurt": "Kärnten", "linz": "Oberösterreich", "salzburg": "Salzburg"}
AUSTRIA_RE = _rx(r"\b(?:austria|österreich|oesterreich|autriche|áustria|\bat\b|🇦🇹)\b|austria|österreich")
FOREIGN_RE = _rx(r"\b(?:germany|deutschland|switzerland|schweiz|usa|united states|uk|united kingdom|london|berlin|munich|münchen|zurich|zürich|netherlands|amsterdam|paris|france|italy|italia|spain|españa|poland|czech|prague|hungary|budapest|slovakia|slovenia|croatia|romania|bulgaria|serbia|turkey|india|china|japan|canada|australia|brazil|mexico|remote)\b")
MULTI_RE = _rx(r"[/&|,+]|\band\b|\bund\b|\bor\b|\boder\b")


def geo(location: str | None) -> dict:
    loc = (location or "").strip()
    low = loc.lower()
    states, cities = [], []
    for part in re.split(r"[;,/|&+]|\s-\s|\band\b|\bund\b", low):
        p = part.strip(" .")
        if p in STATE_ALIASES:
            states.append(STATE_ALIASES[p])
    for c in CITIES_SORTED:
        if re.search(r"(?<![a-zäöüß])" + re.escape(c) + r"(?![a-zäöüß])", low):
            cities.append(c); states.append(CITY_STATE[c] if isinstance(CITY_STATE[c], str) else None)
    for c, st in EXTRA_CITY_STATE.items():
        if c not in cities and re.search(r"(?<![a-zäöüß])" + re.escape(c) + r"(?![a-zäöüß])", low):
            cities.append(c); states.append(st)
    states = [s for s in states if s]
    state = Counter(states).most_common(1)[0][0] if states else None
    city = cities[0] if cities else None
    austria_named = bool(AUSTRIA_RE.search(low))
    foreign = bool(FOREIGN_RE.search(low))
    multi = bool(MULTI_RE.search(loc)) and (len(set(states)) > 1 or foreign)
    if state is None and austria_named:
        state = "unspecified (Austria)"
    conf = "state_and_city" if (city and state) else "state_only" if state and state != "unspecified (Austria)" else "austria_only" if austria_named else "none"
    is_graz_area = bool(city and (city == "graz" or city in GRAZ_SET))
    return {"location_text": loc, "state": state, "city": city, "is_styria": state == "Steiermark", "is_graz_area": is_graz_area,
            "is_graz_city": city == "graz", "is_vienna": state == "Wien", "austria_named": austria_named, "foreign_place_named": foreign,
            "multi_location": multi, "geo_confidence": conf}


# ------------------------------------------------------------------ skills (Layer 1 vocabulary) + language-field mapping
SKILL_CATS = N.SKILL_CATS
SKILL_RX = N.SKILL_RX
LANG_TO_SKILL = {"Python": "Python", "R": "R", "Jupyter Notebook": "Jupyter", "SQL": "SQL", "TSQL": "SQL", "PLpgSQL": "SQL", "PLSQL": "SQL",
                 "Scala": "Scala", "Java": "Java", "JavaScript": "JavaScript", "TypeScript": "JavaScript", "C#": "C#", "C++": "C/C++", "C": "C/C++",
                 "Julia": "Julia", "MATLAB": "MATLAB", "SAS": "SAS", "Shell": "Bash/Shell", "PowerShell": "Bash/Shell", "Go": "Go", "Rust": "Rust",
                 "HCL": "Terraform/IaC", "Dockerfile": "Docker", "VBA": "VBA", "Visual Basic .NET": "VBA", "TeX": None, "HTML": None, "CSS": None}
SKILL_TO_CAT = {name: c for c in SKILL_CATS for name in SKILL_RX[c]}


def skills_in(text: str) -> set[str]:
    found = set()
    if not text:
        return found
    for c in SKILL_CATS:
        if c in ("work_model", "soft_skills"):
            continue
        for name, pats in SKILL_RX[c].items():
            if any(p.search(text) for p in pats):
                found.add(name)
    return found


RSR = CFG.get("readme_skill_rules", {})
README_STRICT = {k: _rx(v) for k, v in RSR.get("strict", {}).items()}
README_MIN2 = set(RSR.get("min2", []))
README_EXCLUDED = set(RSR.get("excluded", []))
ED_README_LEVEL = {k: _rxs(v) for k, v in ED.get("readme_levels", ED["levels"]).items()}


def skills_in_readme(text: str) -> set[str]:
    """README-derived skill evidence with the stricter rules of config/supply_taxonomy.json -> readme_skill_rules."""
    found = set()
    if not text:
        return found
    for c in SKILL_CATS:
        if c in ("work_model", "soft_skills"):
            continue
        for name, pats in SKILL_RX[c].items():
            if name in README_EXCLUDED:
                continue
            if name in README_STRICT:
                if README_STRICT[name].search(text):
                    found.add(name)
                continue
            n_hits = sum(len(p.findall(text)) for p in pats)
            if n_hits >= (2 if name in README_MIN2 else 1):
                found.add(name)
    return found


def education_readme(text: str) -> dict:
    t = (text or "").lower()
    lv = [k for k, rx in ED_README_LEVEL.items() if rx.search(t)]
    inst = [k for k, rx in ED_INST.items() if rx.search(t)]
    return {"edu_levels": lv, "edu_fields": [], "edu_institutions": inst}


def soft_in(text: str) -> set[str]:
    return {name for name, pats in SKILL_RX["soft_skills"].items() if text and any(p.search(text) for p in pats)}


# ------------------------------------------------------------------ repositories → data classification, themes, formats, README
LEX = CFG["data_repo_lexicon"]
DATA_KW = _rxs(LEX["keywords"]); DATA_EX = _rxs(LEX["exclude"]); DATA_TOPICS = set(LEX["topics"]); DATA_LANGS = set(LEX["data_languages"])
EDU_RE = _rxs(LEX["educational_patterns"]["patterns"])
THEMES = {grp: {k: [_rx(p) for p in v] for k, v in d.items()} for grp, d in CFG["project_topics"].items() if not grp.startswith("_")}
FMT = {}
for k, d in CFG["project_formats"].items():
    if k.startswith("_"):
        continue
    FMT[k] = {"languages": set(d.get("languages", [])), "tree": [_rx(p) for p in d.get("tree", [])], "text": _rxs(d["text"]) if d.get("text") else None,
              "homepage": _rxs(d["homepage"]) if d.get("homepage") else None}
RD = CFG["readme_features"]
RD_HEAD = {k: _rxs(v) for k, v in RD["headings"].items()}
RD_CONTENT = {k: _rxs(v) for k, v in RD["content"].items()}
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$|^([^\n]+)\n\s*(?:=+|-{3,})\s*$", re.M)
XPLAT = {k: _rxs(v) for k, v in CFG["cross_platform_domains"].items() if not k.startswith("_")}


def is_data_repo(r: dict) -> tuple[bool, str]:
    text = f"{r.get('name') or ''} {r.get('description') or ''} " + " ".join(r.get("topics") or [])
    topic_hit = bool(set(r.get("topics") or []) & DATA_TOPICS)
    if DATA_EX.search(text) and not topic_hit:
        return False, "excluded"
    if r.get("language") in DATA_LANGS:
        return True, "language"
    if topic_hit:
        return True, "topic"
    m = DATA_KW.search(text)
    if m:
        return True, "keyword:" + m.group(0).lower()
    return False, "none"


def readme_features(text: str | None) -> dict:
    t = text or ""
    heads = [(m.group(1) or m.group(2) or "").strip().lower() for m in HEADING_RE.finditer(t)]
    heads = [h for h in heads if 0 < len(h) < 120 and "`" not in h and not h.startswith(("|", "-", "="))]
    hs = {f"rd_h_{k}": any(rx.search(h) for h in heads) for k, rx in RD_HEAD.items()}
    cs = {f"rd_{k}": bool(rx.search(t)) for k, rx in RD_CONTENT.items()}
    n = len(t)
    bucket = next((lab for lo, hi, lab in RD["length_buckets"] if lo <= n < hi), None)
    lang, _ = N.posting_language(t) if n > 200 else (None, None)
    return {"readme_chars": n, "readme_words": len(t.split()), "readme_headings": len(heads), "readme_length_bucket": bucket,
            "readme_language": lang, "readme_heading_list": heads[:40], **hs, **cs}


def formats_for(r: dict, tree: list[dict] | None, readme_text: str | None) -> list[str]:
    names = [(e.get("path") or "") for e in (tree or [])]
    text = f"{r.get('name') or ''} {r.get('description') or ''} " + " ".join(r.get("topics") or []) + " " + (readme_text or "")[:20000]
    out = []
    for k, d in FMT.items():
        hit = (r.get("language") in d["languages"]) or any(p.search(nm) for p in d["tree"] for nm in names)
        if not hit and d["text"] is not None and k not in ("data_included", "license", "makefile_scripts", "sql_files"):
            hit = bool(d["text"].search(text))
        if not hit and d["homepage"] is not None and r.get("homepage"):
            hit = bool(d["homepage"].search(r["homepage"]))
        if hit:
            out.append(k)
    return out


def themes_for(meta_text: str, readme_text: str = "") -> dict:
    """A theme counts when any pattern matches the repository name/description/topics, or when >= 2 distinct patterns of
    the theme match the README (single generic README hits are ignored, 2026-09-18 rule)."""
    out = {}
    for grp, d in THEMES.items():
        hits = []
        for k, pats in d.items():
            if any(p.search(meta_text) for p in pats) or sum(1 for p in pats if p.search(readme_text)) >= 2:
                hits.append(k)
        out[f"themes_{grp}"] = hits
    return out


ARCH_ORDER = CFG["repo_archetypes"]["order"]


def archetype(p: dict) -> str:
    fmts = set(p["formats"]); th_eng = set(p["themes_engineering"]); th_ds = set(p["themes_ds_method"]); th_ai = set(p["themes_ai"])
    if p["months_since_push"] is not None and p["months_since_push"] > 36 and p["stars"] == 0:
        return "inactive_archive"
    if p.get("is_contribution_like"):
        return "open_source_contribution"
    if p["is_educational"]:
        return "educational_tutorial"
    ml = bool(th_ai) or bool({"classification", "regression", "nlp", "computer_vision", "recommendation", "anomaly_detection", "forecasting", "reinforcement_learning", "clustering"} & th_ds)
    prod = {"docker", "tests", "ci", "api", "web_app", "streamlit_gradio_app"} & fmts
    is_prod = len(prod) >= 2 or ({"docker", "ci"} & fmts and {"api", "web_app", "streamlit_gradio_app", "python_package_or_src"} & fmts)
    if ml:
        return "ml_project"  # (an ML project can also be production-style; the 'formats' field keeps that information)
    if is_prod:
        return "production_style_application"
    if {"pipeline_project"} & fmts or {"etl_pipeline", "orchestration", "streaming", "warehouse_modelling"} & th_eng:
        return "data_engineering_project"
    if "dashboard_bi" in fmts:
        return "dashboard_project"
    if p["readme_chars"] >= 1000 and (p["themes_analytics_domain"] or {"descriptive_eda", "experimentation", "causal_inference", "bayesian", "optimization"} & th_ds):
        return "analytics_project"
    if "notebook" in fmts:
        return "notebook_portfolio"
    return "other_data"


# ------------------------------------------------------------------ LinkedIn slot rows (optional, private)
LI_TRUE = ("true", "1", "1.0", "yes", "y")  # the ingest writes true/false; the rest keeps pre-2026-09-30 processed files readable
LI_BOOLS = ("has_featured_section", "open_to_work_signal", "consultant_freelance_signal")


def _li_bool(v: str) -> bool | None:
    v = (v or "").strip().lower()
    return None if v == "" else v in LI_TRUE


def _li_int(v: str) -> int | None:
    try:
        return int(float(v)) if (v or "").strip() else None
    except ValueError:
        return None


def linkedin_candidates(path: Path) -> list[dict]:
    """Candidate rows for data/processed/supply_linkedin_profiles.csv. Read as strings (blank = not stated, never 'nan').
    `bio` is the coded current_title only; the headline, transition wording and notes are free text and never leave the
    private profile table (transition wording only as the transition_explicit flag). GitHub-only counters are 0/False/empty
    by construction: GitHub-evidence tables must filter source == 'github'."""
    if not path.exists():
        return []
    ldf = pd.read_csv(path, dtype=str, keep_default_na=False)
    out = []
    for row in ldf.to_dict("records"):
        g = lambda k: str(row.get(k) or "").strip()  # noqa: E731
        title = g("current_title")
        tc, _ = N.clean_title(title); rr = N.classify_role(tc)
        fam = rr["role_family"] if rr["role_family"] not in ("out_of_scope", None) else None
        certs = [x.strip() for x in g("certifications").split(";") if x.strip()]
        skills_text = g("skills_listed").replace(";", ", ")
        skills = sorted(skills_in(skills_text))
        edu_level = g("education_level")
        links = [k for k, f in (("github", "has_github_link"), ("kaggle", "has_kaggle_link"), ("personal_site_custom", "has_portfolio_link")) if _li_bool(g(f))]
        c = {"candidate_id": cid("linkedin_manual", g("pseudo_id")), "source": "linkedin_manual", "source_quality": g("source_quality") or "C",
             "login": None, "collection_date": g("collection_date") or None, "frames": ["L"], "n_search_hits": 0,
             "bio": title, "bio_chars": len(title), "has_bio": bool(title), "company": None, "has_company": False, "blog": None, "has_blog": False,
             "hireable": False, "twitter": False, "public_repos": 0, "public_gists": 0, "followers": 0, "following": 0,
             "account_created": None, "account_age_years": None, "profile_updated": None,
             "bio_role_family": fam, "bio_normalized_title": rr["normalized_title"] if fam else None, "bio_role_rule": "linkedin_current_title" if fam else None,
             "seniority_bio": g("seniority_label") or "unknown", "is_student": g("seniority_label") == "student", "is_academic": False,
             "transition_explicit": bool(g("transition_wording")), "prior_domains": [g("prior_domain")] if g("prior_domain") else [],
             "bio_language": None, "bio_edu_levels": [edu_level] if edu_level and edu_level != "none_stated" else [],
             "bio_edu_fields": [g("education_field")] if g("education_field") else [], "bio_edu_institutions": [],
             "bio_certifications": certs, "bio_skills": skills, "bio_soft": sorted(soft_in(skills_text)),
             "links_profile": links, "has_personal_site": "personal_site_custom" in links, "social_accounts_fetched": False,
             "n_repos_listed": 0, "n_repos_owned": 0, "n_forks": 0, "repos_truncated": False, "repo_languages": {}, "last_push": None,
             "n_active_12m": 0, "stars_total": 0, "max_stars": 0, "n_data_repos": 0, "n_projects": 0, "n_documented_projects": 0,
             "n_substantive_projects": 0, "n_educational_repos": 0, "archetypes": {}, "project_themes": {}, "project_formats": {},
             "readme_languages": {}, "subst_themes": {}, "subst_formats": {}, "project_certifications": [], "project_edu_levels": [],
             "project_edu_institutions": []}
        c.update(geo(g("location_text")))
        c["certifications_any"] = certs
        c["edu_levels_any"] = c["bio_edu_levels"]; c["edu_fields_any"] = c["bio_edu_fields"]; c["edu_institutions_any"] = []
        c["links_any"] = links
        c["skills_used"] = []; c["skills_demonstrated"] = []; c["skills_project_demonstrated"] = []; c["skills_any"] = skills
        c["data_tier"] = "T1_bio_declared" if fam else "T0_none"
        c["bio_family_adjacent"] = fam in ADJACENT_FAMILIES
        c["is_data_signal"] = c["data_tier"] == "T1_bio_declared"
        # slot-only coded fields (no GitHub equivalent)
        c["acquisition_method"] = g("acquisition_method") or None
        c["languages_stated"] = g("languages_stated") or None
        c["years_experience_explicit"] = _li_int(g("years_experience_explicit"))
        c["n_projects_listed"] = _li_int(g("n_projects_listed"))
        c["industry_stated"] = g("industry_stated") or None
        for f in LI_BOOLS:
            c[f] = _li_bool(g(f))
        out.append(c)
    return out


# ------------------------------------------------------------------ redaction guard, folder selection, writing
def redaction_state(raw: Path, readmes: dict | None = None) -> str | None:
    """Why a full build must not run on this GitHub collection folder (None = not redacted)."""
    marker = raw / "REDACTED.json"
    if marker.exists():
        info = json.loads(marker.read_text(encoding="utf-8"))
        return f"{marker} (status {info.get('status')}, {info.get('redacted_at')})"
    if readmes and any(r.get("readme_redacted") for r in readmes.values()):
        return f"{raw / 'readmes.jsonl'} holds README bodies flagged readme_redacted"
    return None


def latest_github_folder(base: Path) -> str | None:
    """Latest folder named exactly YYYY-MM-DD that holds profiles.jsonl; suffixed test/partial folders are never picked."""
    if not base.exists():
        return None
    names = sorted(p.name for p in base.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name) and (p / "profiles.jsonl").exists())
    return names[-1] if names else None


def write_table(df: pd.DataFrame, out: Path, name: str) -> None:
    with open(out / f"{name}.jsonl", "w", encoding="utf-8") as f:
        for rec in df.to_dict("records"):
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    df2 = df.copy()
    for col in df2.columns:
        if df2[col].map(lambda v: isinstance(v, (list, dict, set))).any():
            df2[col] = df2[col].map(lambda v: json.dumps(v, ensure_ascii=False, default=str) if isinstance(v, (list, dict, set)) else v)
    df2.to_parquet(out / f"{name}.parquet", index=False)


def refresh_linkedin(out: Path = ROOT / "data" / "processed") -> dict:
    """Replace only the LinkedIn slot rows of the existing candidate table (GitHub rows, incl. redacted ones, stay as stored)."""
    rows = read_jsonl(out / "supply_candidates.jsonl")
    if not rows:
        raise SystemExit("--linkedin-only needs an existing data/processed/supply_candidates.jsonl; run a full build first")
    li = linkedin_candidates(out / "supply_linkedin_profiles.csv")
    cdf = pd.DataFrame([r for r in rows if r.get("source") != "linkedin_manual"] + li)
    write_table(cdf, out, "supply_candidates")
    man_path = out / "supply_build_manifest.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
    manifest.update({"linkedin_refreshed_at": dt.datetime.now().isoformat(), "n_candidates_linkedin_manual": len(li),
                     "linkedin_collection_dates": sorted({c["collection_date"] for c in li if c["collection_date"]}),
                     "tiers": cdf["data_tier"].value_counts().to_dict()})
    man_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


# ------------------------------------------------------------------ main build
def build(date: str) -> None:
    raw = ROOT / "data" / "raw" / "github_supply" / date
    collected = dt.datetime.fromisoformat(date[:10])  # folder names may carry a suffix (e.g. a test subset)
    readmes = {r["full_name"]: r for r in read_jsonl(raw / "readmes.jsonl")}
    why = redaction_state(raw, readmes)
    if why:
        raise SystemExit(f"refusing to rebuild from a redacted collection: {why}. The processed tables were redacted with it and "
                         "a rebuild would regenerate them from incomplete inputs. Use --linkedin-only to refresh the LinkedIn rows.")
    search = read_jsonl(raw / "users_search.jsonl")
    profiles = [p for p in read_jsonl(raw / "profiles.jsonl") if p.get("id")]
    repos = read_jsonl(raw / "repos.jsonl")
    social = {r["login"]: r for r in read_jsonl(raw / "social.jsonl")}
    frames = defaultdict(set); nq = Counter()
    for s in search:
        frames[s["login"]].add(s["frame"]); nq[s["login"]] += 1
    repos_by = defaultdict(list)
    for r in repos:
        repos_by[r["owner_login"]].append(r)
    seen_repo_ids = set()

    cands, projects, evidence = [], [], []
    for p in profiles:
        login = p["login"]
        if p.get("type") != "User" or re.search(r"(?:\[bot\]|-bot$|bot$)", login, re.I):
            continue
        bio = p.get("bio") or ""
        c = {"candidate_id": cid("github", p["id"]), "source": "github", "source_quality": "B", "login": login, "collection_date": date,
             "frames": sorted(frames.get(login, [])), "n_search_hits": nq.get(login, 0),
             "bio": bio, "bio_chars": len(bio), "has_bio": bool(bio.strip()), "company": p.get("company"), "has_company": bool((p.get("company") or "").strip()),
             "blog": p.get("blog"), "has_blog": bool((p.get("blog") or "").strip()), "hireable": bool(p.get("hireable")), "twitter": bool(p.get("twitter_username")),
             "public_repos": p.get("public_repos") or 0, "public_gists": p.get("public_gists") or 0, "followers": p.get("followers") or 0, "following": p.get("following") or 0,
             "account_created": p.get("created_at"), "account_age_years": round((collected - dt.datetime.fromisoformat(p["created_at"].replace("Z", ""))).days / 365.25, 1) if p.get("created_at") else None,
             "profile_updated": p.get("updated_at")}
        c.update(geo(p.get("location")))
        c.update(bio_role(bio))
        c["seniority_bio"] = bio_seniority(bio)
        c["is_student"] = bool(STUDENT_RE.search(bio.lower())) if bio else False
        c["is_academic"] = bool(ACADEMIC_RE.search(bio.lower())) if bio else False
        c.update(transitions(bio))
        c["bio_language"] = short_text_language(bio)
        ed = education(bio); c.update({"bio_" + k: v for k, v in ed.items()})
        c["bio_certifications"] = certifications(bio)
        bio_sk = skills_in(bio); c["bio_skills"] = sorted(bio_sk); c["bio_soft"] = sorted(soft_in(bio))
        # cross-platform links
        links = [p.get("blog") or ""] + [a.get("url") or "" for a in ((social.get(login) or {}).get("accounts") or [])]
        if p.get("twitter_username"):
            links.append("twitter.com/x")
        xp = {k for k, rx in XPLAT.items() for u in links if u and rx.search(u)}
        c["links_profile"] = sorted(xp)
        c["has_personal_site"] = bool(p.get("blog")) and not any(k in xp for k in ("linkedin", "kaggle", "twitter_x", "medium_blog", "youtube", "xing", "mastodon_bluesky"))
        c["social_accounts_fetched"] = login in social
        # repositories
        owned = [r for r in repos_by.get(login, []) if not r.get("fork")]
        forks = [r for r in repos_by.get(login, []) if r.get("fork")]
        c["n_repos_listed"] = len(repos_by.get(login, [])); c["n_repos_owned"] = len(owned); c["n_forks"] = len(forks)
        c["repos_truncated"] = c["n_repos_listed"] >= 300
        used_sk, demo_sk, proj_sk = set(), set(), set()
        for r in owned:
            for s in skills_in(f"{r.get('name') or ''} {r.get('description') or ''} " + " ".join(r.get("topics") or [])):
                used_sk.add(s)
            ls = LANG_TO_SKILL.get(r.get("language") or "")
            if ls:
                used_sk.add(ls)
        used_sk -= README_EXCLUDED  # Git is true by construction for every GitHub account
        langs = Counter(r.get("language") for r in owned if r.get("language"))
        c["repo_languages"] = dict(langs.most_common(10))
        pushes = [r["pushed_at"] for r in owned if r.get("pushed_at")]
        c["last_push"] = max(pushes) if pushes else None
        c["n_active_12m"] = sum(1 for r in owned if r.get("pushed_at") and (collected - dt.datetime.fromisoformat(r["pushed_at"].replace("Z", ""))).days <= 365)
        c["stars_total"] = sum(r.get("stargazers_count") or 0 for r in owned)
        c["max_stars"] = max([r.get("stargazers_count") or 0 for r in owned], default=0)
        # projects
        n_data, n_proj, n_doc, n_subst, n_edu, arche = 0, 0, 0, 0, 0, Counter()
        max_data_stars = 0
        proj_themes = Counter(); proj_formats = Counter(); readme_langs = Counter(); proj_certs = set(); proj_edu = {"levels": set(), "fields": set(), "inst": set()}
        subst_themes = Counter(); subst_formats = Counter()
        for r in owned:
            ok, why = is_data_repo(r)
            if not ok:
                continue
            n_data += 1
            if r["id"] in seen_repo_ids:
                continue
            seen_repo_ids.add(r["id"])
            rd = readmes.get(r["full_name"]) or {}
            rtext = rd.get("readme_text") or ""
            tree = rd.get("tree")
            meta_text = f"{r.get('name') or ''} {r.get('description') or ''} " + " ".join(r.get("topics") or [])
            full_text = meta_text + "\n" + rtext
            pr = {"project_id": cid("ghrepo", r["id"]), "candidate_id": c["candidate_id"], "source": "github", "repo_full_name": r["full_name"],
                  "name": r.get("name"), "description": r.get("description"), "topics": r.get("topics") or [], "language": r.get("language"),
                  "stars": r.get("stargazers_count") or 0, "forks": r.get("forks_count") or 0, "size_kb": r.get("size") or 0, "archived": bool(r.get("archived")),
                  "license": r.get("license"), "has_homepage": bool(r.get("homepage")), "has_pages": bool(r.get("has_pages")),
                  "created_at": r.get("created_at"), "pushed_at": r.get("pushed_at"), "data_reason": why,
                  "months_since_push": round((collected - dt.datetime.fromisoformat(r["pushed_at"].replace("Z", ""))).days / 30.4, 1) if r.get("pushed_at") else None,
                  "readme_fetched": bool(rd), "readme_status": rd.get("readme_status"), "tree_entries": len(tree or []) if tree is not None else None,
                  "is_educational": bool(EDU_RE.search(meta_text)) or bool(rtext and EDU_RE.search(rtext[:3000]) and len(rtext) < 3000)}
            pr.update(readme_features(rtext))
            pr["formats"] = formats_for(r, tree, rtext)
            pr.update(themes_for(meta_text, rtext))
            sk = (skills_in(meta_text) | skills_in_readme(rtext) | {LANG_TO_SKILL.get(r.get("language") or "")}) - {None} - README_EXCLUDED
            pr["skills"] = sorted(sk)
            pr["certifications"] = certifications(full_text)
            ped = education_readme(rtext[:5000]); pr["readme_edu_levels"] = ped["edu_levels"]; pr["readme_edu_institutions"] = ped["edu_institutions"]
            pr["links_readme"] = sorted({k for k, rx in XPLAT.items() if rtext and rx.search(rtext)})
            pr["is_contribution_like"] = False
            pr["is_project"] = (not pr["archived"] or True) and (pr["readme_chars"] >= 300 or pr["stars"] >= 1 or bool((r.get("description") or "").strip()))
            pr["is_documented"] = pr["readme_chars"] >= CFG["evidence_rules"]["documented_readme_min_chars"]
            pr["is_substantive"] = pr["is_documented"] and not pr["is_educational"]
            pr["archetype"] = archetype(pr)
            pr["is_active_12m"] = pr["months_since_push"] is not None and pr["months_since_push"] <= 12
            projects.append(pr)
            if pr["is_project"]:
                n_proj += 1
            if pr["is_documented"]:
                n_doc += 1; demo_sk |= sk
            if pr["is_substantive"]:
                n_subst += 1; proj_sk |= sk
            if pr["is_educational"]:
                n_edu += 1
            max_data_stars = max(max_data_stars, pr["stars"])
            arche[pr["archetype"]] += 1
            for grp in ("analytics_domain", "ds_method", "engineering", "ai"):
                for t in pr[f"themes_{grp}"]:
                    proj_themes[f"{grp}:{t}"] += 1
                    if pr["is_substantive"]:
                        subst_themes[f"{grp}:{t}"] += 1
            for f in pr["formats"]:
                proj_formats[f] += 1
                if pr["is_substantive"]:
                    subst_formats[f] += 1
            if pr["readme_language"]:
                readme_langs[pr["readme_language"]] += 1
            proj_certs |= set(pr["certifications"])
            proj_edu["levels"] |= set(ped["edu_levels"]); proj_edu["inst"] |= set(ped["edu_institutions"])
        c.update({"n_data_repos": n_data, "n_projects": n_proj, "n_documented_projects": n_doc, "n_substantive_projects": n_subst, "n_educational_repos": n_edu,
                  "archetypes": dict(arche), "project_themes": dict(proj_themes), "project_formats": dict(proj_formats), "readme_languages": dict(readme_langs),
                  "subst_themes": dict(subst_themes), "subst_formats": dict(subst_formats),
                  "project_certifications": sorted(proj_certs), "project_edu_levels": sorted(proj_edu["levels"]), "project_edu_institutions": sorted(proj_edu["inst"])})
        c["certifications_any"] = sorted(set(c["bio_certifications"]) | proj_certs)
        c["edu_levels_any"] = sorted(set(c["bio_edu_levels"]) | proj_edu["levels"])
        c["edu_fields_any"] = sorted(set(c["bio_edu_fields"]))
        c["edu_institutions_any"] = sorted(set(c["bio_edu_institutions"]) | proj_edu["inst"])
        c["links_any"] = sorted(set(c["links_profile"]) | {l for pr in projects if pr["candidate_id"] == c["candidate_id"] for l in pr["links_readme"]})
        c["skills_used"] = sorted(used_sk); c["skills_demonstrated"] = sorted(demo_sk); c["skills_project_demonstrated"] = sorted(proj_sk)
        c["skills_any"] = sorted(bio_sk | used_sk | demo_sk)
        # tiers
        if c["bio_role_family"] in CORE_FAMILIES:
            tier = "T1_bio_declared"
        elif (n_doc >= 1 and n_data >= 2) or (n_subst >= 1 and max_data_stars >= 3):
            tier = "T2_repo_evidenced"
        elif n_data >= 1:
            tier = "T3_weak_repo_signal"
        else:
            tier = "T0_none"
        c["data_tier"] = tier
        c["bio_family_adjacent"] = c["bio_role_family"] in ADJACENT_FAMILIES
        c["is_data_signal"] = tier in ("T1_bio_declared", "T2_repo_evidenced")
        # evidence long table
        for s in bio_sk | used_sk | demo_sk:
            evidence.append({"candidate_id": c["candidate_id"], "skill": s, "category": SKILL_TO_CAT.get(s), "mentioned": s in bio_sk,
                             "used": s in used_sk, "demonstrated": s in demo_sk, "project_demonstrated": s in proj_sk, "data_tier": tier})
        cands.append(c)

    # LinkedIn slot records (optional, private)
    li = linkedin_candidates(ROOT / "data" / "processed" / "supply_linkedin_profiles.csv")
    n_li = len(li)
    cands.extend(li)

    out = ROOT / "data" / "processed"
    cdf = pd.DataFrame(cands); pdf = pd.DataFrame(projects); edf = pd.DataFrame(evidence)
    write_table(cdf, out, "supply_candidates")
    write_table(pdf, out, "supply_projects")
    edf.to_parquet(out / "supply_skill_evidence.parquet", index=False)
    manifest = {"built_at": dt.datetime.now().isoformat(), "collection_date": date, "taxonomy_version": CFG["version"],
                "n_search_rows": len(search), "n_profiles": len(profiles), "n_candidates_github": int((cdf["source"] == "github").sum()),
                "n_candidates_linkedin_manual": n_li, "linkedin_collection_dates": sorted({c["collection_date"] for c in li if c["collection_date"]}),
                "n_repos_listed": len(repos), "n_data_repos": len(pdf), "n_readmes_fetched": len(readmes),
                "tiers": cdf["data_tier"].value_counts().to_dict()}
    (out / "supply_build_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="GitHub collection folder (default: latest YYYY-MM-DD folder with profiles.jsonl)")
    ap.add_argument("--linkedin-only", action="store_true", help="refresh only the LinkedIn slot rows of the existing candidate table")
    a = ap.parse_args()
    if a.linkedin_only:
        print(json.dumps(refresh_linkedin(), indent=1))
        sys.exit(0)
    d = a.date or latest_github_folder(ROOT / "data" / "raw" / "github_supply")
    if d is None:
        sys.exit("no GitHub collection folder (YYYY-MM-DD with profiles.jsonl) under data/raw/github_supply/; pass --date")
    print(f"building from data/raw/github_supply/{d}")
    build(d)
