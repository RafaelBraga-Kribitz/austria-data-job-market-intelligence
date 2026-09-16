"""Step 2: normalization + feature extraction.

Input : data/processed/interim_postings.jsonl
Output: data/processed/postings_normalized.jsonl (+ .parquet)

Every derived field is rule-based and traceable to config/*.json. For each
posting we keep the original text and add:
  title_clean, normalized_title, role_family, role_rule, seniority, seniority_source
  locations, city, state, region_label, is_styria, is_graz_area, is_austria_wide, multi_location
  remote_type, remote_evidence, home_office_days
  employment_type, is_internship_student
  salary_*  (advertised, normalised to annual gross EUR with the 14-salary convention)
  german_requirement, german_level_stated, german_level_bucket, english_requirement, ...
  posting_language (de/en, from stopword ratio)
  experience_min_years, experience_max_years, experience_text
  degree_required, degree_levels, degree_fields
  skills_<category> lists (controlled vocabulary in config/skills_taxonomy.json)
  company_norm
Confidence flags are attached where a heuristic was used.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config"
PROC = ROOT / "data" / "processed"

ROLE = json.load(open(CFG / "role_taxonomy.json", encoding="utf-8"))
SKILLS = json.load(open(CFG / "skills_taxonomy.json", encoding="utf-8"))
GEO = json.load(open(CFG / "geo.json", encoding="utf-8"))


def _rx(p):
    return re.compile(p, re.I)


# ---------------------------------------------------------------- titles
GENDER_RE = _rx(r"\(\s*(?:m|w|f|d|x|h|a|all genders|alle geschlechter|gn|div)(?:\s*[/|,]\s*(?:m|w|f|d|x|h|a|i|div|gn|\*))*\s*\)|\b(?:m|w|f)\s*/\s*(?:m|w|f|d|x)(?:\s*/\s*(?:d|x|i|m|w|f))?\b|\(all genders\)|\ball genders\b|\(?\bw/m/d\b\)?|\bm/w/d\b|\bm/f/d\b|\bf/m/x\b|\bm/w/x\b|\bd/m/w\b|\bw/m/x\b|\(?gn\)?")
SUFFIX_RE = _rx(r"(?<=[a-zäöü])(?:\*in(?:nen)?|:in(?:nen)?|_in(?:nen)?|/in(?:nen)?|\(in\)|/-in|·in|innen)\b")
AMS_OCC_RE = _rx(r"\(([^()]*(?:/in|analyst|entwickler|techniker|ingenieur|informatiker|berater|manager|scientist|engineer)[^()]*)\)\s*$")
NOISE_RE = _rx(r"\b(?:ab sofort|vollzeit|teilzeit|full[- ]?time|part[- ]?time|befristet|unbefristet|karenzvertretung|\d{1,2}[,.]?\d?\s*(?:h|std|stunden|wochenstunden|h/woche|std\./woche)|bis zu|ab \d{1,2}\s*h|remote|hybrid|home ?office|\d+\s*%|standort[^,]*|dienstort[^,]*|arbeitsort[^,]*|in (?:wien|graz|linz|salzburg|innsbruck|klagenfurt|österreich)|wien|graz|linz|salzburg|innsbruck|klagenfurt|österreich|austria|vienna|at\b|deutschland|germany)\b")


def clean_title(t: str | None) -> tuple[str, str | None]:
    if not t:
        return "", None
    s = str(t)
    ams = None
    m = AMS_OCC_RE.search(s)
    if m:
        ams = m.group(1).strip()
        s = s[: m.start()]
    s = GENDER_RE.sub(" ", s)
    s = SUFFIX_RE.sub("", s)
    s = re.sub(r"[\[\]{}\"“”„']", " ", s)
    s = re.sub(r"\((?:[^()]*)\)", lambda mm: " " + mm.group(0)[1:-1] + " ", s)  # keep parenthetical words
    s = s.lower()
    s = NOISE_RE.sub(" ", s)
    s = re.sub(r"[|•·]+", " ", s)
    # hyphenated compounds -> spaces ("data-analyst" -> "data analyst"); standalone dashes dropped
    s = re.sub(r"(?<=[a-zäöüß0-9])[-–—](?=[a-zäöüß0-9])", " ", s)
    s = re.sub(r"\s*[-–—]\s*", " ", s)
    s = re.sub(r"\s*[/,:;&+]\s*", lambda mm: " " + mm.group(0).strip() + " ", s)
    s = re.sub(r"\s+", " ", s).strip(" -–—,:;/")
    return s, ams


ACADEMIC_RE = _rx(r"\bphd\b|postdoc|post-doc|doktorand|dissertant|professur|professor|universitätsassistent|university assistant|wissenschaftliche[r]? mitarbeiter|research (?:associate|fellow|assistant)|tenure|habilit|\bprae[- ]?doc\b|\bpost[- ]?doc\b")


ROLE_RULES = [(r["family"], r["normalized"], [_rx(p) for p in r["patterns"]]) for r in ROLE["rules"]]
OOS = [_rx(p) for p in ROLE["out_of_scope_overrides"]["patterns"]]
HARD_OOS = [_rx(p) for p in [r"data entry", r"datenerfass", r"dateneingabe", r"data ?cent(?:er|re)", r"rechenzentrum", r"data typist",
                             # added 2026-09-16 audit (D-012): security/SOC analysts, embedded/hardware AI, laboratory analysts,
                             # regulatory/financial reporting without a data word, thesis/academic positions, "Bi-Static" radar
                             r"\bsecurity\b|\bsicherheit|\bcyber|\bsoc\b|\bthreat\b|penetration",
                             r"\bembedded\b|\bfpga\b|firmware|microcontroller",
                             r"\blabor|\bhplc\b|qualitätskontrolle|\bchemi(?:e|ker|sche)\b",
                             r"^(?!.*(?:data|daten|\bbi\b|analy|power ?bi)).*(?:regulatory|non-financial|financial|esg|edi|sustainability|treasury|konzern|ifrs|nachhaltigkeits?|meldewesen)[- ]?reporting",
                             r"master thesis|bachelor thesis|masterarbeit|bachelorarbeit|diplomarbeit|\bthesis\b",
                             r"\bbi[- ]static\b|bistatic",
                             r"datenschutz|data protection|privacy officer|\bdsgvo\b|\bgdpr\b"]]
SENIORITY = {k: [_rx(p) for p in v] for k, v in ROLE["seniority_patterns"].items()}


def classify_role(title_clean: str, title_orig: str | None = None) -> dict:
    fam, norm, rule = None, None, None
    for f, n, pats in ROLE_RULES:
        for p in pats:
            if p.search(title_clean):
                fam, norm, rule = f, n, p.pattern
                break
        if fam:
            break
    oos_reason = None
    for p in HARD_OOS:
        if p.search(title_clean):
            oos_reason = p.pattern
            break
    if not oos_reason and fam in (None, "other_data"):
        for p in OOS:
            if p.search(title_clean):
                oos_reason = p.pattern
                break
    if oos_reason:
        return {"role_family": "out_of_scope", "normalized_title": None, "role_rule": rule, "role_oos_reason": oos_reason,
                "role_family_prelim": fam}
    if not fam:
        return {"role_family": "out_of_scope", "normalized_title": None, "role_rule": None, "role_oos_reason": "no_rule_matched", "role_family_prelim": None}
    return {"role_family": fam, "normalized_title": norm, "role_rule": rule, "role_oos_reason": None, "role_family_prelim": fam}


def seniority_from_title(title_clean: str) -> str | None:
    for level in ("intern_student", "trainee_junior", "lead_head", "senior"):
        for p in SENIORITY[level]:
            if p.search(title_clean):
                return level
    return None


# ---------------------------------------------------------------- geography
CITIES = sorted(GEO["cities"].keys(), key=len, reverse=True)
CITIES = [c for c in CITIES if not c.startswith("_")]
CITY_RE = {c: _rx(r"(?<![a-zäöüß])" + re.escape(c) + r"(?![a-zäöüß])") for c in CITIES}
STATE_ALIASES = GEO["state_aliases"]
GRAZ_SET = set(GEO["graz_commute"]["places"])
NUTS = GEO["nuts3"]
AUSTRIA_WIDE_RE = _rx(r"österreichweit|austria[- ]wide|ganz österreich|bundesweit|in ganz österreich|all over austria|anywhere in austria|remote \(austria\)|remote in austria|throughout austria")
WORKPLACE_RE = _rx(r"(?:arbeitsort|dienstort|standort|einsatzort|arbeitsplatz|location|ort|place of work|based in|work location|sitz)\s*[:\-–]?\s*([A-ZÄÖÜ][^\n,;.]{2,60})")
POSTCODE_RE = re.compile(r"\b(?:A-?)?([1-9]\d{3})\s+([A-ZÄÖÜ][a-zäöüß\-. ]{2,40})")


def state_from_postcode(pc: str) -> str | None:
    d = int(pc[0])
    return {1: "Wien", 2: "Niederösterreich", 3: "Niederösterreich", 4: "Oberösterreich", 5: "Salzburg", 6: "Tirol", 7: "Burgenland", 8: "Steiermark", 9: "Kärnten"}.get(d)


def find_cities(text: str) -> list[str]:
    if not text:
        return []
    found = []
    low = text.lower()
    for c in CITIES:
        if c in low and CITY_RE[c].search(text):
            found.append(c)
    # remove cities that are substrings of a longer found city (e.g. 'graz' inside 'hart bei graz')
    out = []
    for c in found:
        if not any(c != o and c in o for o in found):
            out.append(c)
    return out


def normalize_location(row: dict) -> dict:
    cities, states, evidence = [], [], []
    # 1) explicit fields
    lt = row.get("location_text") or ""
    for part in re.split(r"[;|/]|\s-\s|, ", lt):
        p = part.strip().lower()
        if not p:
            continue
        if p in STATE_ALIASES:
            states.append(STATE_ALIASES[p])
        for c in find_cities(part):
            cities.append(c)
    if lt:
        evidence.append("location_text")
    for r in row.get("location_regions") or []:
        if str(r).lower() in STATE_ALIASES:
            states.append(STATE_ALIASES[str(r).lower()])
    # 2) NUTS codes (EURES)
    nuts = row.get("nuts_codes") or []
    region_labels = []
    for n in nuts:
        if n in NUTS:
            states.append(NUTS[n][0]); region_labels.append(NUTS[n][1])
            if n == "AT221":
                cities.append("graz")
            evidence.append("nuts")
    # 3) description text (workplace lines, postcodes, city mentions) – only if nothing found yet
    desc = row.get("description_text") or ""
    if not cities:
        head = desc[:1500] + "\n" + desc[-1500:]
        for m in WORKPLACE_RE.finditer(head):
            for c in find_cities(m.group(1)):
                cities.append(c); evidence.append("workplace_line")
        if not cities:
            for m in POSTCODE_RE.finditer(head):
                st = state_from_postcode(m.group(1))
                cs = find_cities(m.group(2))
                if cs:
                    cities.extend(cs); evidence.append("postcode")
                if st:
                    states.append(st)
        if not cities and not states:
            title_cities = find_cities(row.get("title") or "")
            if title_cities:
                cities.extend(title_cities); evidence.append("title")
    # dedupe preserving order
    cities = list(dict.fromkeys(cities))
    for c in cities:
        st = GEO["cities"].get(c)
        if st:
            states.append(st)
    states = [s for s in dict.fromkeys(states) if s and not s.startswith("Österreich")]
    austria_wide = bool(AUSTRIA_WIDE_RE.search(lt)) or bool(AUSTRIA_WIDE_RE.search(desc[:3000]))
    unspecified_at = any(n in ("AT", "AT-NS", "ATZ", "ATZZ", "ATZZZ") for n in nuts)
    city = cities[0] if cities else None
    state = states[0] if states else None
    return {
        "locations": cities, "city": city.title() if city else None, "state": state,
        "states_all": states, "region_labels": region_labels,
        "is_styria": "Steiermark" in states, "is_graz_area": any(c in GRAZ_SET for c in cities),
        "is_graz_city": "graz" in cities,
        "is_vienna": "Wien" in states, "is_austria_wide": austria_wide or unspecified_at,
        "multi_location": len(states) > 1 or len(cities) > 1,
        "location_evidence": ",".join(dict.fromkeys(evidence)) or None,
        "location_confidence": "high" if ("location_text" in evidence or "nuts" in evidence) else ("medium" if evidence else "none"),
    }


# ---------------------------------------------------------------- work model
REMOTE_FULL_RE = _rx(r"100\s?%\s?(?:remote|home ?office)|full(?:y)?[- ]remote|vollständig remote|komplett remote|remote[- ]first|remote[- ]only|ausschließlich remote|(?:work|arbeiten) (?:from|von) (?:anywhere|überall)|voll(?:ständig)? im home ?office|remote (?:position|job|role|stelle)\b|\bremote\s*\(")
HYBRID_RE = _rx(r"\bhybrid|(\d)\s*(?:-|bis|to)?\s*(\d)?\s*(?:tage|days?)\s*(?:pro |per |/ ?|die |a )?(?:woche|week)?\s*(?:im |in |from |of )?(?:home ?office|remote|homeoffice|mobiles? arbeiten|wfh)|(?:home ?office|remote|mobiles? arbeiten)\s*(?:an |für |bis zu |up to |von |for )?\s*(\d)\s*(?:-|bis|to)?\s*(\d)?\s*(?:tage|days?)|(?:bis zu|up to)\s*(\d{1,3})\s?%\s*(?:home ?office|remote)|(\d{1,3})\s?%\s*(?:home ?office|remote|mobiles arbeiten)|(?:home ?office|remote)[- ](?:anteil|share|möglich|possible|option|möglichkeit|tage|days|regelung|vereinbarung)|teilweise (?:remote|home ?office)|partially remote|mix of (?:remote|home)")
HO_MENTION_RE = _rx(r"home ?office|homeoffice|\bremote\b|mobiles? arbeiten|mobile work(?:ing)?|telearbeit|work from home|\bwfh\b|ortsunabhängig|hybrides? arbeiten")
ONSITE_RE = _rx(r"vor ort\b|on[- ]site|onsite|präsenz|kein home ?office|no remote|not remote|office[- ]based|in-office|100\s?%\s?(?:vor ort|office|on-site)")
REMOTE_RESTRICT_RE = _rx(r"(?:remote|home ?office)[^.\n]{0,60}(?:innerhalb|within|nur in|only in|aus)\s+(?:österreich|austria|der eu|the eu)|(?:wohnsitz|residence)[^.\n]{0,40}(?:österreich|austria)|(?:österreich|austria)[- ]?(?:weit|wide) remote")


def classify_remote(row: dict) -> dict:
    text = (row.get("description_text") or "")
    title = row.get("title") or ""
    full = title + "\n" + text
    days = None
    m = HYBRID_RE.search(full)
    if m:
        nums = [g for g in m.groups() if g]
        if nums:
            try:
                days = int(nums[0])
            except ValueError:
                days = None
    ev = []
    if REMOTE_FULL_RE.search(full):
        rt = "remote"; ev.append("full_remote_phrase")
    elif m:
        rt = "hybrid"; ev.append("hybrid_phrase")
    elif HO_MENTION_RE.search(full) or row.get("remote_flag_raw") == "home_office" or (row.get("job_location_type_raw") == "TELECOMMUTE"):
        rt = "hybrid_or_flexible"; ev.append("home_office_mentioned" if HO_MENTION_RE.search(full) else "source_flag")
    elif ONSITE_RE.search(full):
        rt = "on_site"; ev.append("onsite_phrase")
    else:
        rt = "unknown"
    if row.get("remote_flag_raw") == "home_office":
        ev.append("karriere_home_office_flag")
    return {"remote_type": rt, "remote_evidence": ",".join(ev) or None, "home_office_days_per_week": days if (days and days <= 5) else None,
            "remote_austria_restricted": bool(REMOTE_RESTRICT_RE.search(full))}


# ---------------------------------------------------------------- employment type
PT_RE = _rx(r"teilzeit|part[- ]time|geringfügig|\b(?:20|25|30)\s*(?:h|std|stunden|wochenstunden|hours)\b")
FT_RE = _rx(r"vollzeit|full[- ]time|\b(?:38[.,]5|40|37[.,]5|38)\s*(?:h|std|stunden|wochenstunden|hours)\b")
INTERN_RE = _rx(r"praktik|\bintern(?:ship)?\b|werkstudent|working student|studentische|ferialjob|ferialpraktik|\btrainee\b|masterarbeit|bachelorarbeit|diplomarbeit|abschlussarbeit|\bthesis\b|\bstudent (?:job|position)|\bstudierende")
TEMP_RE = _rx(r"befristet|fixed[- ]term|temporary|karenzvertretung|maternity cover|leiharbeit|arbeitskräfteüberlassung|zeitarbeit|freelance|freiberuflich|werkvertrag|contractor|interim")


def employment(row: dict) -> dict:
    raw = (row.get("employment_type_raw") or "").lower()
    text = (row.get("title") or "") + "\n" + (row.get("description_text") or "")[:4000]
    pt = bool(PT_RE.search(raw)) or bool(PT_RE.search(text))
    ft = bool(FT_RE.search(raw)) or bool(FT_RE.search(text)) or "fulltime" in raw or "full_time" in raw or "vollzeit" in raw
    if ft and pt:
        et = "full_or_part_time"
    elif ft:
        et = "full_time"
    elif pt:
        et = "part_time"
    else:
        et = "unknown"
    return {"employment_type": et, "is_internship_student": bool(INTERN_RE.search(row.get("title") or "")) or bool(INTERN_RE.search(text[:1500])),
            "is_temporary_or_contract": bool(TEMP_RE.search(raw + " " + text))}


# ---------------------------------------------------------------- salary (Austrian conventions)
NUM = r"(?:€|eur(?:o)?)?\s*(\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?|\d{4,6}(?:[.,]\d{1,2})?|\d{1,3},\d{3}(?:\.\d{2})?)\s*(?:,--?|,-|€|eur(?:o)?|\b)"
SAL_CTX_RE = _rx(r"(gehalt|salary|entgelt|bezahlung|vergütung|verdienst|brutto|gross|kollektivvertrag|\bkv\b|mindestgehalt|jahresgehalt|monatsgehalt|jahresbrutto|monatsbrutto|entlohnung|remuneration|compensation|pay\b|einstufung)")
YEAR_RE = _rx(r"jahr|jährlich|annual|per year|p\.\s?a\.|/ ?jahr|per annum|yearly|/year|a year|jahresbrutto|jahresgehalt|jahresbezug")
MONTH_RE = _rx(r"monat|monthly|per month|/ ?monat|/month|mtl\.|monatlich|monatsbrutto|monatsgehalt|a month|14\s?[x×]|14 mal|x\s?14|pro monat")
KV_RE = _rx(r"kollektivvertrag|\bkv\b|mindestgehalt|mindestentgelt|mindestgrundgehalt|kv[- ]minimum|collective (?:bargaining )?agreement|einstufung|mindestbezug|grundgehalt")
OVERPAY_RE = _rx(r"überzahlung|bereitschaft zur überzahlung|overpay|deutlich (?:darüber|höher)|marktkonform|je nach (?:qualifikation|erfahrung)|depending on (?:qualification|experience)|abhängig von (?:qualifikation|erfahrung)|attraktive überbezahlung|überbezahlung")
HOURS_BASIS_RE = _rx(r"(?:auf |on |bei |basis )?(?:einer |a )?(?:vollzeit|full[- ]time)[- ]?(?:basis)?|(?:38[.,]5|40|37[.,]5|38|30|20|25)\s*(?:h|std|stunden|wochenstunden|hours)")


def _to_float(s: str) -> float | None:
    s = s.strip().replace(" ", "")
    # German format 3.500,50 ; English 3,500.50 ; plain 3500
    if re.match(r"^\d{1,3}(\.\d{3})+(,\d{1,2})?$", s):
        s = s.replace(".", "").replace(",", ".")
    elif re.match(r"^\d{1,3}(,\d{3})+(\.\d{1,2})?$", s):
        s = s.replace(",", "")
    elif re.match(r"^\d+,\d{1,2}$", s):
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_salary_text(text: str) -> dict:
    """Find salary figures in a posting's text near salary context words."""
    out = {"salary_figures": [], "salary_snippet": None, "salary_period_detected": None, "salary_kv_mention": False, "salary_overpay_mention": False}
    if not text:
        return out
    out["salary_kv_mention"] = bool(KV_RE.search(text))
    out["salary_overpay_mention"] = bool(OVERPAY_RE.search(text))
    figs = []
    for m in re.finditer(NUM, text, flags=re.I):
        val = _to_float(m.group(1))
        if val is None:
            continue
        ctx = text[max(0, m.start() - 160): m.end() + 120]
        if not SAL_CTX_RE.search(ctx):
            continue
        if not (900 <= val <= 300000):
            continue
        # skip years, hours, percentages, phone numbers, postcodes, reference numbers
        after = text[m.end(): m.end() + 4]
        before = text[max(0, m.start() - 40): m.start()]
        if re.match(r"\s*%", after) or re.match(r"^(19|20)\d{2}$", m.group(1)):
            continue
        if re.search(r"tel|phone|fax|\+43|\b0\d{2,4}\s*$|\d\s*$|nr\.?\s*$|ref|kennzahl|job-?id|inserat", before, re.I):
            continue
        if re.match(r"^\d{4,6}$", m.group(1)) and not re.search(r"€|eur|brutto|gross|gehalt|salary|jahr|monat|annum|year|month|entgelt|bezahlung|vergütung", text[max(0, m.start() - 50): m.end() + 50], re.I):
            continue
        near = text[max(0, m.start() - 80): m.end() + 80]
        if MONTH_RE.search(near):
            per = "month"
        elif YEAR_RE.search(near):
            per = "year"
        else:
            per = "month" if val < 12000 else "year"
        figs.append({"value": val, "period": per, "period_source": "context" if (MONTH_RE.search(near) or YEAR_RE.search(near)) else "magnitude", "pos": m.start()})
        if out["salary_snippet"] is None:
            out["salary_snippet"] = re.sub(r"\s+", " ", ctx)[:300]
    out["salary_figures"] = figs
    if figs:
        out["salary_period_detected"] = figs[0]["period"]
    return out


def normalize_salary(row: dict) -> dict:
    text = row.get("description_text") or ""
    p = parse_salary_text(text)
    smin = row.get("salary_min_raw"); smax = row.get("salary_max_raw"); per = (row.get("salary_period_raw") or "").lower()
    basis, source = None, None
    if smin not in (None, "", 0) and str(smin).replace(".", "").isdigit():
        smin = float(smin); smax = float(smax) if smax not in (None, "") else None
        period = "year" if per.startswith("year") or "jahr" in per or "jähr" in per else ("month" if per.startswith("month") or "monat" in per else None)
        if period is None:
            period = "month" if smin < 12000 else "year"
        source = "structured"
    else:
        figs = [f for f in p["salary_figures"]]
        if figs:
            # take figures with the dominant period; min/max
            per_counts = {}
            for f in figs:
                per_counts[f["period"]] = per_counts.get(f["period"], 0) + 1
            period = max(per_counts, key=per_counts.get)
            vals = [f["value"] for f in figs if f["period"] == period]
            smin, smax = min(vals), (max(vals) if len(vals) > 1 and max(vals) > min(vals) else None)
            source = "text"
        else:
            return {"salary_min_annual_eur": None, "salary_max_annual_eur": None, "salary_period": None, "salary_source": None,
                    "salary_basis": "none", "salary_transparency": "none", "salary_snippet": None,
                    "salary_kv_mention": p["salary_kv_mention"], "salary_overpay_mention": p["salary_overpay_mention"], "salary_conversion_note": None}
    # plausibility filters
    if period == "month" and (smin < 900 or smin > 20000):
        return {"salary_min_annual_eur": None, "salary_max_annual_eur": None, "salary_period": period, "salary_source": source,
                "salary_basis": "implausible", "salary_transparency": "unparsed", "salary_snippet": p["salary_snippet"],
                "salary_kv_mention": p["salary_kv_mention"], "salary_overpay_mention": p["salary_overpay_mention"], "salary_conversion_note": "implausible monthly value"}
    if period == "year" and (smin < 12000 or smin > 300000):
        return {"salary_min_annual_eur": None, "salary_max_annual_eur": None, "salary_period": period, "salary_source": source,
                "salary_basis": "implausible", "salary_transparency": "unparsed", "salary_snippet": p["salary_snippet"],
                "salary_kv_mention": p["salary_kv_mention"], "salary_overpay_mention": p["salary_overpay_mention"], "salary_conversion_note": "implausible annual value"}
    factor = 14 if period == "month" else 1
    note = "monthly gross x14 (Austrian 14-salary convention)" if period == "month" else "annual gross as stated"
    if smax is not None and smax < smin:
        smin, smax = smax, smin
    # drop implausible upper ends (parsing artefacts such as reference numbers or company revenue figures)
    if smax is not None and (smax * factor > 300000 or smax > 3 * smin):
        smax = None
        note += "; max dropped as implausible"
    basis = "range" if smax else ("minimum_only")
    transparency = "range" if smax else ("kv_minimum" if (p["salary_kv_mention"] or row.get("source") in ("eures",)) else "single_figure")
    return {"salary_min_annual_eur": round(smin * factor), "salary_max_annual_eur": round(smax * factor) if smax else None,
            "salary_period": period, "salary_source": source, "salary_basis": basis, "salary_transparency": transparency,
            "salary_snippet": p["salary_snippet"] or (row.get("salary_text_raw")),
            "salary_kv_mention": p["salary_kv_mention"], "salary_overpay_mention": p["salary_overpay_mention"], "salary_conversion_note": note}


# ---------------------------------------------------------------- languages
DE_STOP = {"und", "der", "die", "das", "mit", "für", "wir", "sie", "nicht", "eine", "einen", "bei", "auf", "von", "zu", "ist", "sind", "werden", "oder", "auch", "dich", "du"}
EN_STOP = {"and", "the", "with", "for", "we", "you", "our", "are", "will", "your", "of", "to", "in", "on", "is", "as", "be", "that", "this", "or"}


def posting_language(text: str) -> tuple[str, float]:
    if not text:
        return "unknown", 0.0
    words = re.findall(r"[a-zäöüß]+", text.lower())
    if len(words) < 30:
        return "unknown", 0.0
    de = sum(w in DE_STOP for w in words); en = sum(w in EN_STOP for w in words)
    tot = de + en
    if tot == 0:
        return "unknown", 0.0
    share_de = de / tot
    if share_de >= 0.6:
        return "de", share_de
    if share_de <= 0.4:
        return "en", 1 - share_de
    return "mixed", max(share_de, 1 - share_de)


CEFR_RE = _rx(r"\b([ABC][12])\b")
LEVEL_WORDS = [
    ("native", _rx(r"muttersprach|native|first language|mother tongue")),
    ("fluent", _rx(r"verhandlungssicher|fließend|fliessend|fluent|ausgezeichnet|excellent|exzellent|sehr gut|very good|perfekt|perfect|proficien|business[- ]fluent|full professional|hervorragend")),
    ("good", _rx(r"\bgut(?:e|es|en)?\b|\bgood\b|solid|sicher|kommunikationssicher|conversational|professional working|working knowledge|advanced|fortgeschritten")),
    ("basic", _rx(r"grundkenntnis|grundlegend|basic|basis|elementary|beginner|anfänger|erste kenntnisse|some knowledge")),
]
GER_RE = _rx(r"\bdeutsch(?:kenntnisse|sprachig|e sprache|es|er|e)?\b|\bgerman(?:[- ]speaking| language| skills| proficiency)?\b|\bdeutsch\b")
ENG_RE = _rx(r"\benglisch(?:kenntnisse|sprachig|e sprache|es|er|e)?\b|\benglish(?:[- ]speaking| language| skills| proficiency)?\b|\benglisch\b")
PREF_RE = _rx(r"von vorteil|vorteilhaft|wünschenswert|erwünscht|ideally|ideal(?:erweise)?|plus\b|advantage|asset|nice[- ]to[- ]have|bonus|preferred|preferably|willingness to learn|bereitschaft.{0,20}(?:zu lernen|zum erlernen)|optional|not required|nicht (?:erforderlich|notwendig|zwingend)|kein muss|no (?:german|requirement)|helpful|hilfreich|beneficial")
REQ_RE = _rx(r"erforderlich|vorausgesetzt|voraussetzung|required|requirement|must|mandatory|zwingend|notwendig|essential|unbedingt|setzen wir voraus|\bmuss\b|\bneed|benötig|erwarten|expect|mindestens|at least|minimum|\bmin\.")
ALT_RE = _rx(r"deutsch(?:kenntnisse)?\s*(?:oder|or|/)\s*englisch|german\s*(?:or|/)\s*english|english\s*(?:or|/)\s*german|englisch\s*(?:oder|/)\s*deutsch")
NO_GERMAN_RE = _rx(r"(?:no|without|keine?)\s+(?:german|deutsch)(?:kenntnisse)?\s*(?:required|necessary|needed|erforderlich|notwendig|nötig)|german (?:is )?not (?:required|necessary|mandatory|a must)|deutsch(?:kenntnisse)? (?:sind |ist )?(?:nicht|keine) (?:erforderlich|voraussetzung|notwendig)|english[- ]speaking (?:team|environment|company|workplace)|(?:working|company) language (?:is )?english|unternehmenssprache (?:ist )?englisch|englisch als (?:unternehmens|arbeits|konzern)sprache|english as (?:our )?(?:corporate|working|company) language|english[- ]only")


def language_requirements(text: str, title: str, post_lang: str) -> dict:
    out = {"german_requirement": "not_mentioned", "german_level_stated": None, "german_level_bucket": None, "german_snippet": None,
           "english_requirement": "not_mentioned", "english_level_stated": None, "english_level_bucket": None, "english_snippet": None,
           "language_german_or_english": False, "explicit_no_german": False, "other_languages": []}
    if not text:
        return out
    t = text
    out["language_german_or_english"] = bool(ALT_RE.search(t))
    out["explicit_no_german"] = bool(NO_GERMAN_RE.search(t))
    for lang, rx in (("german", GER_RE), ("english", ENG_RE)):
        best = None
        for m in rx.finditer(t):
            s, e = max(0, m.start() - 120), min(len(t), m.end() + 120)
            ctx = t[s:e]
            # skip mentions that are about the posting language / company description, e.g. "deutsche Firma"
            if re.search(r"deutsche[rsn]? (?:firma|unternehmen|konzern|markt|tochter|niederlassung|mutter)|german (?:company|market|subsidiary|group|customers|speaking countries|-speaking markets)|deutschland|germany|deutschsprachigen raum|dach[- ]region|dach[- ]raum", ctx, re.I) and not re.search(r"kenntnis|skills|level|niveau|sprach|language|fluent|fließend|verhandlungssicher|[ABC][12]", ctx, re.I):
                continue
            cef = None
            mm = CEFR_RE.search(ctx)
            if mm:
                cef = mm.group(1).upper()
            level = None
            for name, lrx in LEVEL_WORDS:
                if lrx.search(ctx):
                    level = name
                    break
            req = "required"
            near = t[max(0, m.start() - 100): m.end() + 100]
            if PREF_RE.search(near):
                req = "preferred"
            elif REQ_RE.search(near):
                req = "required"
            elif level or cef:
                req = "required_implied"
            else:
                req = "mentioned"
            score = (3 if req == "required" else 2 if req == "required_implied" else 1 if req == "preferred" else 0) + (1 if (cef or level) else 0)
            cand = {"req": req, "cef": cef, "level": level, "snippet": re.sub(r"\s+", " ", ctx)[:260], "score": score}
            if best is None or cand["score"] > best["score"]:
                best = cand
        if best:
            bucket = None
            if best["cef"]:
                bucket = {"C2": "C2/native", "C1": "C1/fluent", "B2": "B2/good", "B1": "B1", "A2": "A1-A2", "A1": "A1-A2"}[best["cef"]]
            elif best["level"]:
                bucket = {"native": "C2/native", "fluent": "C1/fluent", "good": "B2/good", "basic": "A1-A2"}[best["level"]]
            out[f"{lang}_requirement"] = best["req"]
            out[f"{lang}_level_stated"] = best["cef"] or best["level"]
            out[f"{lang}_level_bucket"] = bucket
            out[f"{lang}_snippet"] = best["snippet"]
    if out["explicit_no_german"] and out["german_requirement"] in ("not_mentioned", "mentioned", "preferred"):
        out["german_requirement"] = "explicitly_not_required"
    if out["language_german_or_english"] and out["german_requirement"] in ("required", "required_implied"):
        out["german_requirement"] = "german_or_english"
    others = []
    for name, rx in (("French", _rx(r"französisch|\bfrench\b")), ("Italian", _rx(r"italienisch|\bitalian\b")), ("Spanish", _rx(r"spanisch|\bspanish\b")), ("Slovenian/Croatian/Hungarian", _rx(r"slowenisch|slovenian|kroatisch|croatian|ungarisch|hungarian")), ("Czech/Slovak/Polish", _rx(r"tschechisch|czech|slowakisch|slovak|polnisch|polish"))):
        if rx.search(t) and re.search(r"kenntnis|skills|sprache|language|von vorteil|advantage", t, re.I):
            others.append(name)
    out["other_languages"] = others
    return out


# ---------------------------------------------------------------- experience
EXP_RE = _rx(r"(?:mindestens|mind\.|min\.|at least|minimum(?: of)?|über|more than|mehr als|ab|\+)?\s*(\d{1,2})\s*(?:\+|-|–|bis|to|or more)?\s*(\d{1,2})?\s*\+?\s*(?:jahre?n?|years?|yrs?)\s*(?:an\s+)?(?:einschlägige[rn]?\s+|relevante[rn]?\s+|nachweisliche[rn]?\s+|professional\s+|relevant\s+|of\s+|praktische[rn]?\s+|fundierte[rn]?\s+|hands-on\s+|proven\s+|solid\s+|industry\s+|work(?:ing)?\s+)?(?:berufs|praxis|projekt|arbeits|work|industry|professional|hands-on)?[- ]?(?:erfahrung|experience|expertise|tätigkeit|background)")
EXP2_RE = _rx(r"(?:erfahrung|experience)[^.\n]{0,40}?(?:von |of |mindestens |at least |min\. |minimum )?(\d{1,2})\s*(?:\+|-|–|bis|to)?\s*(\d{1,2})?\s*\+?\s*(?:jahre?n?|years?|yrs?)")
MULTI_YEAR_RE = _rx(r"mehrjährig|langjährig|several years|multi-year|many years|extensive experience|umfangreiche erfahrung|fundierte berufserfahrung|einschlägige berufserfahrung|proven track record|nachweisliche erfahrung")
ENTRY_RE = _rx(r"berufseinsteiger|einsteiger|entry[- ]level|keine berufserfahrung|no (?:prior |previous )?experience|erste (?:berufs)?erfahrung|first (?:professional )?experience|absolvent|graduates?\b|young professional|frisch von der uni|auch für (?:absolventen|einsteiger)|quereinsteiger|career changer")


def experience(text: str) -> dict:
    out = {"experience_min_years": None, "experience_max_years": None, "experience_text": None, "experience_multi_year_phrase": False, "experience_entry_level_phrase": False}
    if not text:
        return out
    out["experience_multi_year_phrase"] = bool(MULTI_YEAR_RE.search(text))
    out["experience_entry_level_phrase"] = bool(ENTRY_RE.search(text))
    m = EXP_RE.search(text) or EXP2_RE.search(text)
    if m:
        a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else None
        if 0 <= a <= 20:
            out["experience_min_years"] = a
            out["experience_max_years"] = b if (b and a <= b <= 25) else None
            out["experience_text"] = re.sub(r"\s+", " ", text[max(0, m.start() - 40): m.end() + 40])[:200]
    return out


# ---------------------------------------------------------------- education
EDU = {k: [_rx(p) for p in v] for k, v in SKILLS["education"].items()}
DEGREE_REQ_RE = _rx(r"abgeschlossene[sn]?\s+(?:\w+\s+){0,3}(?:studium|hochschul|universitäts|fh-|master|bachelor)|(?:completed|finished)\s+(?:\w+\s+){0,3}(?:degree|studies|university)|(?:university|master'?s?|bachelor'?s?|academic)\s+degree\s+(?:in|required|is required)|(?:degree|abschluss)\s+(?:required|erforderlich|vorausgesetzt)|studienabschluss|hochschulabschluss|(?:msc|bsc|phd)\s+(?:in|required)|(?:master|bachelor|phd|doktorat)\s+(?:in|of|der|im)\b|studium (?:der|im|in)\b|abgeschlossenes? (?:\w+ ){0,2}(?:master|bachelor)")
DEGREE_OR_EQUIV_RE = _rx(r"oder (?:eine )?(?:vergleichbare|gleichwertige|ähnliche|entsprechende)|or (?:equivalent|comparable|similar|relevant)\s+(?:qualification|experience|education|training|background)|(?:htl|hak|matura)\s*(?:oder|or|/)|equivalent (?:practical )?experience|gleichwertige (?:ausbildung|qualifikation|berufserfahrung)|vergleichbare (?:ausbildung|qualifikation)|alternativ")


DEGREE_PREF_RE = _rx(r"(?:idealerweise|vorzugsweise|von vorteil|wünschenswert|preferably|ideally|is a plus|nice to have|bevorzugt|advantage|desirable|plus:)[^.\n]{0,80}(?:studium|degree|abschluss|bachelor|master|phd|hochschul)|(?:studium|degree|abschluss|bachelor|master|phd|hochschul)[^.\n]{0,80}(?:von vorteil|wünschenswert|is a plus|nice to have|an advantage|desirable|bevorzugt|preferred)")
DEGREE_MENTION_RE = _rx(r"studium|studien|degree|hochschul|universit|bachelor|master|\bphd\b|\bfh\b|\bhtl\b|matura")


def education(text: str) -> dict:
    out = {"degree_required": False, "degree_or_equivalent": False, "degree_requirement": "none", "degree_levels": [], "degree_fields": [], "education_snippet": None}
    if not text:
        return out
    out["degree_required"] = bool(DEGREE_REQ_RE.search(text))
    out["degree_or_equivalent"] = bool(DEGREE_OR_EQUIV_RE.search(text))
    # 4-way requirement strength (D-012): required phrase > preferred phrase > mentioned > none.
    # "required" = a completed-degree / degree-required phrase; "preferred" = degree wording next to
    # advantage/ideally wording and no required phrase; "mentioned" = education word present only.
    pref = bool(DEGREE_PREF_RE.search(text))
    if out["degree_required"] and not pref:
        out["degree_requirement"] = "required"
    elif out["degree_required"] and pref:
        # both wordings present (e.g. "abgeschlossenes Studium ... von Vorteil"): the softer reading wins
        out["degree_requirement"] = "preferred"
    elif pref:
        out["degree_requirement"] = "preferred"
    elif DEGREE_MENTION_RE.search(text):
        out["degree_requirement"] = "mentioned"
    m = DEGREE_REQ_RE.search(text)
    if m:
        out["education_snippet"] = re.sub(r"\s+", " ", text[max(0, m.start() - 60): m.end() + 160])[:260]
    levels, fields = [], []
    # restrict level/field detection to windows around education words so that e.g.
    # "software engineering" in the task list does not count as an engineering degree
    windows = [text[max(0, mm.start() - 160): mm.end() + 220] for mm in re.finditer(r"studium|studien|degree|abschluss|ausbildung|bachelor|master|phd|doktor|diplom|\bhtl\b|\bfh\b|universit|hochschul|graduate|education|qualification", text, re.I)]
    edu_text = "\n".join(windows) if windows else ""
    for k, pats in EDU.items():
        hit = any(p.search(edu_text) for p in pats)
        if not hit:
            continue
        if k.startswith("Field:"):
            fields.append(k[7:])
        elif k in ("Bachelor", "Master", "PhD", "Degree (generic)", "HTL/Matura", "MINT/STEM"):
            levels.append(k)
    out["degree_levels"] = levels
    out["degree_fields"] = fields
    return out


# ---------------------------------------------------------------- skills
SKILL_CATS = [c for c in SKILLS.keys() if not c.startswith("_") and c not in ("education",)]
SKILL_RX = {c: {name: [_rx(p) for p in pats] for name, pats in SKILLS[c].items()} for c in SKILL_CATS}


def extract_skills(text: str, title: str) -> dict:
    out = {}
    full = (title or "") + "\n" + (text or "")
    for c in SKILL_CATS:
        hits = []
        for name, pats in SKILL_RX[c].items():
            for p in pats:
                if p.search(full):
                    hits.append(name)
                    break
        out[f"skills_{c}"] = hits
    # convenience flags for the most decision-relevant items
    prog = set(out.get("skills_programming_languages", []))
    bi = set(out.get("skills_bi_tools", []))
    out["has_python"] = "Python" in prog
    out["has_sql"] = "SQL" in prog
    out["has_r"] = "R" in prog
    out["has_power_bi"] = "Power BI" in bi
    out["has_tableau"] = "Tableau" in bi
    out["has_excel"] = "Excel" in bi
    return out


# ---------------------------------------------------------------- company
COMPANY_SUFFIX_RE = _rx(r"\b(?:gmbh|ges\.?m\.?b\.?h\.?|ag|se|kg|og|e\.u\.|eu|ltd\.?|inc\.?|llc|gesellschaft m\.?b\.?h\.?|& co\.? kg|co\.? kg|& co\.?|holding|group|gruppe|austria|österreich|gmbh & co kg|nfg|stiftung|reg\.? gen\.? m\.? b\.? h\.?|international|europe|central europe)\b")


def company_norm(name: str | None) -> str | None:
    if not name:
        return None
    s = name.lower()
    s = re.sub(r"[.,()\"'’]", " ", s)
    s = COMPANY_SUFFIX_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip(" -&")
    return s or None


# ---------------------------------------------------------------- main
def normalize_row(row: dict) -> dict:
    out = dict(row)
    tc, ams = clean_title(row.get("title"))
    out["title_clean"] = tc
    out["ams_occupation_label"] = ams
    out["is_academic"] = bool(ACADEMIC_RE.search(tc))
    out.update(classify_role(tc, row.get("title")))
    sen = seniority_from_title(tc)
    text = row.get("description_text") or ""
    exp = experience(text)
    out.update(exp)
    if sen is None:
        lraw = (row.get("seniority_raw") or "").lower()
        if lraw:
            sen_map = {"berufseinstieg": "trainee_junior", "entry level": "trainee_junior", "praktikum": "intern_student", "internship": "intern_student",
                       "management": "lead_head", "direktor": "lead_head", "director": "lead_head", "geschäftsführer": "lead_head", "executive": "lead_head",
                       "mid-senior level": "senior_or_mid_source", "mittleres berufsniveau": "senior_or_mid_source", "associate": "mid_source"}
            for k, v in sen_map.items():
                if k in lraw:
                    sen = v; break
        if sen is None and out["is_internship_student"] if "is_internship_student" in out else False:
            sen = "intern_student"
    out["seniority"] = sen or "unspecified"
    out["seniority_source"] = "title" if seniority_from_title(tc) else ("source_field" if sen else "none")
    out.update(normalize_location(row))
    out.update(classify_remote(row))
    out.update(employment(row))
    if out["seniority"] == "unspecified" and out["is_internship_student"]:
        out["seniority"] = "intern_student"; out["seniority_source"] = "text"
    out.update(normalize_salary(row))
    # D-012 audit flags: "all-in" contracts and part-time bases change how a stated monthly figure should be read
    out["salary_all_in_mention"] = bool(re.search(r"all[- ]in", text, re.I))
    out["salary_bonus_mention"] = bool(re.search(r"\bbonus|\bprämie|variable[rs]? (?:gehalts)?anteil|variable (?:pay|compensation)", text, re.I))
    snippet = out.get("salary_snippet") or ""
    out["salary_part_time_basis_risk"] = bool(re.search(r"teilzeit|part[- ]time|\b(?:20|25|30)\s*(?:h\b|std|stunden|wochenstunden|hours)", snippet, re.I))
    pl, conf = posting_language(text)
    out["posting_language"] = pl
    out["posting_language_confidence"] = round(conf, 2)
    out.update(language_requirements(text, row.get("title") or "", pl))
    out.update(education(text))
    out.update(extract_skills(text, row.get("title") or ""))
    out["company_norm"] = company_norm(row.get("company"))
    out["description_length"] = len(text)
    out["has_full_description"] = len(text) > 600
    return out


def main():
    src = PROC / "interim_postings.jsonl"
    rows = [json.loads(l) for l in open(src, encoding="utf-8")]
    print(f"normalizing {len(rows)} rows")
    outrows = [normalize_row(r) for r in rows]
    df = pd.DataFrame(outrows)
    df.to_json(PROC / "postings_normalized.jsonl", orient="records", lines=True, force_ascii=False)
    df2 = df.copy()
    for c in df2.columns:
        if df2[c].apply(lambda x: isinstance(x, (list, dict))).any():
            df2[c] = df2[c].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else x)
    df2.to_parquet(PROC / "postings_normalized.parquet", index=False)
    print(df["role_family"].value_counts())
    print(df.groupby("source")["role_family"].apply(lambda s: (s != "out_of_scope").sum()))


if __name__ == "__main__":
    main()
