"""Step 1: unify raw source dumps into one interim table (one row per source posting).

Input : data/raw/<source>/<date>/listings.jsonl (+ details.jsonl)
Output: data/processed/interim_postings.parquet + .jsonl
        (raw-ish: source-native fields mapped to a common schema, no
        interpretation yet; description kept in full)
        data/processed/interim_build_manifest.json (run folder used per
        source, row counts, skipped malformed JSON lines)

Usage: python src/pipeline/build_interim.py [--date YYYY-MM-DD]
  Without --date the newest folder named exactly YYYY-MM-DD is used per source;
  folders with a suffix (e.g. a test subset "2026-09-16_test") are never picked
  automatically. With --date every source must have that folder.

No posting is dropped here. Duplicates across queries are collapsed per source
(same source_id) keeping the earliest collected envelope and the list of
queries that surfaced the posting (used for query-coverage analysis). Raw lines
that are not valid JSON are skipped, counted per file, printed and recorded in
the manifest.

Scope: the five Layer 1 job-board sources (eures, karriere, linkedin,
willhaben, jobsat). Arbeitnow and the radar feed (data/raw/arbeitnow,
data/raw/radar; D-022/D-023) are intentionally a separate supplement
(src/analysis/supplement_radar.py) and do not go through normalize/dedupe.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
RUN_DIR_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
RUN_DATE: str | None = None          # set by --date; None = newest dated folder
SKIPPED_LINES: dict[str, int] = defaultdict(int)   # file -> malformed JSON lines
RUNS_USED: dict[str, str | None] = {}


def strip_html(s: str | None) -> str | None:
    if not s:
        return None
    s = re.sub(r"<\s*(br|/p|/li|/div|/h\d|/tr)\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "\n- ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def read_jsonl(p: Path):
    if not p.exists():
        return
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    SKIPPED_LINES[p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p)] += 1
                    continue


def latest_run(source: str) -> Path | None:
    """Run folder for a source: RAW/<source>/<RUN_DATE> when --date is given
    (missing folder = error), else the newest folder named exactly YYYY-MM-DD."""
    d = RAW / source
    if RUN_DATE:
        run = d / RUN_DATE
        if not run.is_dir():
            raise SystemExit(f"build_interim: --date {RUN_DATE} given but {run} does not exist")
        RUNS_USED[source] = run.name
        return run
    if not d.exists():
        RUNS_USED[source] = None
        return None
    runs = sorted(p for p in d.iterdir() if p.is_dir() and RUN_DIR_RE.fullmatch(p.name))
    RUNS_USED[source] = runs[-1].name if runs else None
    return runs[-1] if runs else None


def ms_to_date(ms):
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return None


def de_date(s):
    """'8.9.2026' -> 2026-09-08"""
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", str(s or ""))
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


# ----------------------------------------------------------------------------
def build_eures():
    run = latest_run("eures")
    if not run:
        return []
    details = {}
    for env in read_jsonl(run / "details.jsonl"):
        details[env["record"]["id"]] = env["record"]
    rows, queries = {}, defaultdict(set)
    for env in read_jsonl(run / "listings.jsonl"):
        r = env["record"]
        jid = r["id"]
        queries[jid].add(env.get("query"))
        if jid in rows:
            continue
        lang = (r.get("availableLanguages") or ["de"])[0]
        tr = (r.get("translations") or {}).get(lang) or {}
        desc_html = tr.get("description") or r.get("description")
        det = details.get(jid, {})
        emp = r.get("employer") or {}
        loc = r.get("locationMap") or {}
        nuts = sorted({c for cs in loc.values() for c in (cs or []) if c}) if isinstance(loc, dict) else []
        rows[jid] = {
            "source": "eures", "source_id": jid,
            "source_url": f"https://europa.eu/eures/portal/jv-se/jv-details/{jid}?lang=en",
            "source_type": "public_employment_service_mirror",
            "source_connection_point": det.get("connectionPointId"),
            "source_feed": det.get("source"),
            "source_reference": det.get("reference"),
            "title": tr.get("title") or r.get("title"),
            "company": emp.get("name") if emp.get("name") not in (None, "siehe Beschreibung", "see description") else None,
            "company_raw": emp.get("name"),
            # EURES geography comes from NUTS codes only: the search record has no
            # place name and details.jsonl carries a city/postcode for ~3 % of
            # postings (139 of 4,569 on 2026-09-16), so location_text stays empty
            "location_text": None,
            "nuts_codes": nuts,
            "country_codes": list(loc.keys()) if isinstance(loc, dict) else [],
            "posted_date": ms_to_date(r.get("creationDate")),
            "modified_date": ms_to_date(r.get("lastModificationDate")),
            "description_html": desc_html,
            "description_text": strip_html(desc_html),
            "description_language": lang,
            "employment_type_raw": ",".join(r.get("positionScheduleCodes") or []),
            "contract_type_raw": r.get("positionOfferingCode"),
            "salary_text_raw": None, "salary_min_raw": None, "salary_max_raw": None, "salary_period_raw": None,
            "remote_flag_raw": None,
            "esco_occupation_uris": r.get("jobCategoriesCodes") or [],
            "number_of_posts": r.get("numberOfPosts"),
            "company_size_raw": emp.get("organisationSizeCode"),
            "industry_raw": ",".join(emp.get("sectorCodes") or []) or None,
            "collected_at": env.get("collected_at"),
        }
    for jid in rows:
        rows[jid]["queries"] = sorted(q for q in queries[jid] if q)
    return list(rows.values())


def build_karriere():
    run = latest_run("karriere")
    if not run:
        return []
    details = {}
    for env in read_jsonl(run / "details.jsonl"):
        details[env["listing_id"]] = env["record"]
    rows, queries = {}, defaultdict(set)
    for env in read_jsonl(run / "listings.jsonl"):
        it = env["record"]["jobsItem"]
        jid = it["id"]
        queries[jid].add(env.get("query"))
        if jid in rows:
            continue
        det = details.get(jid, {})
        ld = det.get("ld_json") or {}
        locs = [l.get("name") for l in it.get("locations") or [] if l.get("name")]
        bs = ld.get("baseSalary") or {}
        val = bs.get("value") or {}
        jl = ld.get("jobLocation") or []
        if isinstance(jl, dict):
            jl = [jl]
        addr = [(j.get("address") or {}) for j in jl]
        rows[jid] = {
            "source": "karriere", "source_id": jid, "source_url": it.get("link"),
            "source_type": "job_board",
            "title": ld.get("title") or it.get("title"),
            "company": (it.get("company") or {}).get("name") or (ld.get("hiringOrganization") or {}).get("name"),
            "company_raw": (it.get("company") or {}).get("name"),
            "company_size_raw": (it.get("company") or {}).get("employees"),
            "company_main_location": (it.get("company") or {}).get("mainLocation"),
            "location_text": "; ".join(locs) or "; ".join(a.get("addressLocality", "") for a in addr),
            "location_regions": sorted({a.get("addressRegion") for a in addr if a.get("addressRegion")}),
            "nuts_codes": [], "country_codes": sorted({a.get("addressCountry") for a in addr if a.get("addressCountry")}),
            "posted_date": (ld.get("datePosted") or "")[:10] or de_date(it.get("date")),
            "valid_through": (ld.get("validThrough") or "")[:10] or None,
            "description_html": ld.get("description"),
            "description_text": strip_html(ld.get("description")) if ld.get("description") else it.get("summary"),
            "description_language": None,
            "employment_type_raw": (",".join(ld["employmentType"]) if isinstance(ld.get("employmentType"), list) else ld.get("employmentType")) or it.get("employmentTypes"),
            "salary_text_raw": it.get("salary"),
            "salary_min_raw": val.get("minValue"), "salary_max_raw": val.get("maxValue"),
            "salary_period_raw": val.get("unitText"), "salary_currency_raw": bs.get("currency"),
            "remote_flag_raw": "home_office" if it.get("isHomeOffice") else None,
            "job_location_type_raw": ld.get("jobLocationType"),
            "has_detail": bool(ld),
            "detail_status": det.get("status"),
            "collected_at": env.get("collected_at"),
        }
    for jid in rows:
        rows[jid]["queries"] = sorted(q for q in queries[jid] if q)
    return list(rows.values())


def build_linkedin():
    run = latest_run("linkedin")
    if not run:
        return []
    details = {}
    for env in read_jsonl(run / "details.jsonl"):
        details[env["listing_id"]] = env["record"]
    rows, queries, qlocs = {}, defaultdict(set), defaultdict(set)
    for env in read_jsonl(run / "listings.jsonl"):
        c = env["record"]
        jid = c["id"]
        queries[jid].add(env.get("query"))
        qlocs[jid].add(env.get("location"))
        if jid in rows:
            continue
        det = details.get(jid, {})
        crit = det.get("criteria") or {}
        rows[jid] = {
            "source": "linkedin", "source_id": jid, "source_url": c.get("url") or f"https://www.linkedin.com/jobs/view/{jid}",
            "source_type": "professional_network",
            "title": det.get("title") or c.get("title"),
            "company": det.get("company") or c.get("company"),
            "company_raw": c.get("company"), "company_url": c.get("company_url"),
            "location_text": det.get("location") or c.get("location"),
            "nuts_codes": [], "country_codes": [],
            "posted_date": c.get("posted_date"),
            "description_html": det.get("description_html"),
            "description_text": det.get("description_text"),
            "description_language": None,
            "employment_type_raw": crit.get("Beschäftigungsverhältnis") or crit.get("Employment type"),
            "seniority_raw": crit.get("Karrierestufe") or crit.get("Seniority level"),
            "job_function_raw": crit.get("Tätigkeitsbereich") or crit.get("Job function"),
            "industry_raw": crit.get("Branchen") or crit.get("Industries"),
            "applicants_text": det.get("applicants_text"),
            "salary_text_raw": c.get("salary_text"),
            "salary_min_raw": None, "salary_max_raw": None, "salary_period_raw": None,
            "remote_flag_raw": None,
            "has_detail": bool(det.get("description_text")),
            "detail_status": det.get("status"),
            "collected_at": env.get("collected_at"),
        }
    for jid in rows:
        rows[jid]["queries"] = sorted(q for q in queries[jid] if q)
        rows[jid]["query_locations"] = sorted(q for q in qlocs[jid] if q)
    return list(rows.values())


def build_willhaben():
    run = latest_run("willhaben")
    if not run:
        return []
    details = {}
    for env in read_jsonl(run / "details.jsonl"):
        details[env["listing_id"]] = env["record"]
    rows, queries = {}, defaultdict(set)
    for env in read_jsonl(run / "listings.jsonl"):
        e = env["record"]
        jid = e["id"]
        queries[jid].add(env.get("query"))
        if jid in rows:
            continue
        det = (details.get(jid) or {}).get("data") or {}
        locs = e.get("jobLocations") or []
        loc_names = []
        for l in locs:
            if isinstance(l, dict):
                loc_names.append(l.get("name") or l.get("city") or l.get("label") or json.dumps(l, ensure_ascii=False)[:60])
            else:
                loc_names.append(str(l))
        modes = e.get("employmentModes") or []
        modes = [m.get("name") if isinstance(m, dict) else str(m) for m in modes]
        rows[jid] = {
            "source": "willhaben", "source_id": str(jid),
            "source_url": f"https://www.willhaben.at/jobs/job/{e.get('slugTitle','job')}/{jid}",
            "source_type": "job_board",
            "title": e.get("title"),
            "company": (e.get("company") or {}).get("title"),
            "company_raw": (e.get("company") or {}).get("title"),
            "location_text": "; ".join(loc_names),
            "nuts_codes": [], "country_codes": [],
            "posted_date": (e.get("firstPublishDate") or e.get("creationDate") or "")[:10] or None,
            "modified_date": (e.get("lastModifiedDate") or "")[:10] or None,
            "description_html": None,
            "description_text": det.get("description"),
            "description_language": None,
            "employment_type_raw": ",".join(modes),
            "position_raw": e.get("position"),
            "salary_text_raw": (f"{e.get('salary')} {e.get('salaryTimeFrame') or ''}".strip() if e.get("salary") else None),
            "salary_min_raw": e.get("salary"), "salary_max_raw": None,
            "salary_period_raw": e.get("salaryTimeFrame"),
            "salary_overpay_flag": e.get("overpay"),
            "remote_flag_raw": None,
            "willhaben_detail_keys": sorted(det.keys()) if det else None,
            "willhaben_detail": det or None,
            "has_detail": bool(det),
            "collected_at": env.get("collected_at"),
        }
    for jid in rows:
        rows[jid]["queries"] = sorted(q for q in queries[jid] if q)
    return list(rows.values())


def build_jobsat():
    run = latest_run("jobsat")
    if not run:
        return []
    details = {}
    for env in read_jsonl(run / "details.jsonl"):
        details[env["listing_id"]] = env["record"]
    rows, queries = {}, defaultdict(set)
    for env in read_jsonl(run / "listings.jsonl"):
        c = env["record"]
        jid = c["id"]
        queries[jid].add(env.get("query"))
        if jid in rows:
            continue
        det = details.get(jid, {})
        md = det.get("meta_description") or ""
        m = re.search(r" in (.+?) bei der Firma (.+?) \(Job-NR", md)
        rows[jid] = {
            "source": "jobsat", "source_id": jid, "source_url": c.get("url"), "source_type": "job_board",
            "title": det.get("title") or c.get("title"),
            "company": det.get("company") or (m.group(2) if m else None),
            "company_raw": m.group(2) if m else None,
            "location_text": m.group(1) if m else None,
            "nuts_codes": [], "country_codes": [],
            "posted_date": datetime.fromtimestamp(int(c["date_epoch"]), tz=timezone.utc).strftime("%Y-%m-%d") if c.get("date_epoch") else None,
            "description_html": det.get("description_html"),
            "description_text": det.get("description_text"),
            "description_language": None,
            "employment_type_raw": det.get("meta"),
            "salary_text_raw": None, "salary_min_raw": None, "salary_max_raw": None, "salary_period_raw": None,
            "remote_flag_raw": None,
            "has_detail": bool(det.get("description_text")),
            "detail_status": det.get("status"),
            "collected_at": env.get("collected_at"),
        }
    for jid in rows:
        rows[jid]["queries"] = sorted(q for q in queries[jid] if q)
    return list(rows.values())


def main(argv: list[str] | None = None):
    global RUN_DATE
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", help="run folder date YYYY-MM-DD used for every source (default: newest per source)")
    args = ap.parse_args(argv)
    if args.date and not RUN_DIR_RE.fullmatch(args.date):
        raise SystemExit(f"build_interim: --date must be YYYY-MM-DD, got {args.date!r}")
    RUN_DATE = args.date
    all_rows, per_source = [], {}
    for fn in (build_eures, build_karriere, build_linkedin, build_willhaben, build_jobsat):
        rows = fn()
        print(f"{fn.__name__}: {len(rows)} unique postings")
        per_source[fn.__name__.removeprefix("build_")] = len(rows)
        all_rows.extend(rows)
    for f, k in sorted(SKIPPED_LINES.items()):
        print(f"WARNING: skipped {k} malformed JSON line(s) in {f}")
    if not all_rows:
        raise SystemExit(f"build_interim: no postings found under {RAW} (runs used: {RUNS_USED}); nothing written")
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(all_rows)
    df["posting_uid"] = df["source"] + ":" + df["source_id"].astype(str)
    df.to_json(OUT / "interim_postings.jsonl", orient="records", lines=True, force_ascii=False)
    # parquet needs homogeneous list columns -> serialise complex columns as JSON strings
    df2 = df.copy()
    for c in df2.columns:
        if df2[c].apply(lambda x: isinstance(x, (list, dict))).any():
            df2[c] = df2[c].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else x)
    df2.to_parquet(OUT / "interim_postings.parquet", index=False)
    manifest = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requested_date": RUN_DATE,
        "run_folders": {s: (f"data/raw/{s}/{d}" if d else None) for s, d in RUNS_USED.items()},
        "unique_postings_per_source": per_source,
        "rows_total": len(df),
        "skipped_malformed_json_lines": dict(sorted(SKIPPED_LINES.items())),
    }
    (OUT / "interim_build_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("total rows:", len(df), "->", OUT / "interim_postings.parquet")
    print(df.groupby("source").agg(n=("source_id", "count"), with_desc=("description_text", lambda s: s.notna().sum())))


if __name__ == "__main__":
    main()
