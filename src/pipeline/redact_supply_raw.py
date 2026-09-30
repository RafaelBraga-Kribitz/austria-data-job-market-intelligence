"""Retention step of docs/legal-and-publication-audit.md §10.5: once the Layer 2 analysis is frozen, keep only pseudonymous ids
and derived fields of one collection date and drop the personal free text. Irreversible — run deliberately, after the review
samples are audited and every analysis script that reads free text (supply_analysis.py, supply_quality.py) has been run.

Usage:
  python src/pipeline/redact_supply_raw.py --source {github,linkedin,all} --date YYYY-MM-DD            dry run (default)
  python src/pipeline/redact_supply_raw.py --source github --date 2026-09-17 --confirm                  redact
The dry run lists every file the confirm run would touch, with row and cell counts; nothing outside --source and --date is
touched (processed rows are selected by source and collection_date).

--source github (data/raw/github_supply/<date>/ and the processed rows of source github, collection_date <date>):
  profiles.jsonl        login -> pseudonym; bio, blog, company, location, twitter_username -> null
  users_search.jsonl    login -> pseudonym            repos_done.jsonl  login -> pseudonym
  repos.jsonl           owner_login, full_name -> pseudonym; name, description, homepage -> null
  readmes.jsonl         owner_login, full_name -> pseudonym; readme_text -> null (readme_redacted); tree paths -> null (tree_n kept)
  social.jsonl          login -> pseudonym; account URLs -> provider only
  query_log.jsonl       logins / repository names inside request URLs -> pseudonym;  search_summary.jsonl kept (query counts)
  supply_candidates.{jsonl,parquet}  bio, location_text, company, blog, login -> null (has_blog derived first); redacted = true
  supply_projects.{jsonl,parquet}    projects of those candidates: repo_full_name -> pseudonym; name, description -> null;
                                     readme_heading_list keeps headings used >= 5 times in the table (C19e reproduces); redacted = true
  supply_skill_evidence.parquet      kept (ids and derived flags only)
  supply_quality_* files (only when supply_build_manifest.json is of <date>): free-text columns blanked, ids / derived fields /
                                     labels kept; supply_quality_frameB_nonstyria_locations.csv (location text only) deleted
--source linkedin (data/raw/linkedin_supply/<date>/ and processed rows of collection_date <date>):
  profiles_manual.csv, supply_linkedin_profiles.csv  headline, transition_wording -> "[redacted]" when filled (presence stays
                                     visible, so transition_explicit survives a rebuild); notes -> sampling tokens (k=, pages=,
                                     stratum=, rank=, block=) only. current_title and the coded fields are kept.
  state.json            cockpit draft (every key), last_error, last_message cleared; observer, token, paste_field kept
  search_counts.csv, grid.csv, facets.json, keywords.json, sample_queue.json: no personal free text by construction
                        (generated notes, People-search URLs without member ids, title keywords); scanned for profile URLs /
                        e-mails and reported, never rewritten
  candidate rows (source linkedin_manual) carry no free text (bio = coded current_title): reported, untouched
Each confirmed source writes REDACTED.json into its raw folder (status in_progress -> complete); a second confirm run on a
complete folder is refused, rows already flagged redacted are skipped (a crashed run resumes), and build_supply.py refuses a
full rebuild of a redacted GitHub folder (the next build would otherwise regenerate the tables from redacted inputs).

Pseudonyms are sha1("<kind>:<value>")[:16], the scheme of candidate_id: consistent across files, so joins survive, but a
lookup against GitHub reverses them — the files are pseudonymised, not anonymised, and stay private.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PERSONAL_FIELDS = ["bio", "location_text", "company", "blog", "login"]  # processed candidate rows
PROJECT_TEXT = ["name", "description"]
HEADING_MIN = 5  # C19e publishes headings used in >= 5 documented projects; rarer headings are dropped
REVIEW_TEXT = {"supply_quality_bio_review_sample.csv": ["bio"], "supply_quality_bio_precision_labels.csv": ["bio"],
               "supply_quality_repo_review_sample.csv": PROJECT_TEXT, "supply_quality_repo_precision_labels.csv": PROJECT_TEXT}
REVIEW_DELETE = ["supply_quality_frameB_nonstyria_locations.csv"]
LI_MARK = ["headline", "transition_wording"]  # free text -> "[redacted]" (presence kept)
LI_PLACEHOLDER = "[redacted]"
LI_SCAN = ["search_counts.csv", "grid.csv", "facets.json", "keywords.json", "sample_queue.json"]
SAMPLING_TOKEN = re.compile(r"^(?:k|pages|stratum|rank|block)=[^@]*$")
LEAK = re.compile(r"linkedin\.com/in/|@", re.I)


def pseud(kind: str, value) -> str | None:
    if value is None or str(value) == "":
        return None
    return hashlib.sha1(f"{kind}:{value}".encode()).hexdigest()[:16]


class Report:
    def __init__(self, confirm: bool, root: Path):
        self.confirm = confirm
        self.root = root
        self.lines: list[str] = []

    def add(self, path: Path, what: str) -> None:
        try:
            path = path.relative_to(self.root)
        except ValueError:
            pass
        self.lines.append(f"  {path.as_posix()}: {what}")

    def print(self, title: str) -> None:
        print(title)
        for line in self.lines or ["  (nothing found)"]:
            print(line)


def _replace(tmp: Path, path: Path) -> None:
    os.replace(tmp, path)


def _nonempty(v) -> bool:
    return v is not None and not (isinstance(v, float) and pd.isna(v)) and str(v).strip() != ""


# ------------------------------------------------------------------ GitHub raw (streamed; files reach 80 MB)
def _set(r: dict, key: str, value) -> int:
    old = r.get(key)
    if key not in r and value is None:
        return 0
    r[key] = value
    return int(_nonempty(old))


def raw_profiles(r: dict) -> int:
    n = _set(r, "login", pseud("github_login", r.get("login")))
    return n + sum(_set(r, k, None) for k in ("bio", "blog", "company", "location", "twitter_username"))


def raw_login(r: dict) -> int:
    return _set(r, "login", pseud("github_login", r.get("login")))


def raw_repos(r: dict) -> int:
    n = _set(r, "owner_login", pseud("github_login", r.get("owner_login"))) + _set(r, "full_name", pseud("github_repo", r.get("full_name")))
    return n + sum(_set(r, k, None) for k in ("name", "description", "homepage"))


def raw_readmes(r: dict) -> int:
    n = _set(r, "owner_login", pseud("github_login", r.get("owner_login"))) + _set(r, "full_name", pseud("github_repo", r.get("full_name")))
    if r.get("readme_text") is not None:
        r["readme_text"] = None; r["readme_redacted"] = True; n += 1
    if isinstance(r.get("tree"), list):
        r["tree_n"] = len(r["tree"]); r["tree"] = None; n += 1
    return n


def raw_social(r: dict) -> int:
    n = raw_login(r)
    accounts = r.get("accounts") or []
    if any("url" in a for a in accounts if isinstance(a, dict)):
        r["accounts"] = [{"provider": a.get("provider")} for a in accounts if isinstance(a, dict)]; n += 1
    return n


URL_USER = re.compile(r"(/users/)([^/?#]+)")
URL_REPO = re.compile(r"(/repos/)([^/?#]+/[^/?#]+)")


def raw_query_log(r: dict) -> int:
    url = r.get("url") or ""
    new = URL_REPO.sub(lambda m: m.group(1) + pseud("github_repo", m.group(2)), url)
    new = URL_USER.sub(lambda m: m.group(1) + pseud("github_login", m.group(2)), new)
    if new != url:
        r["url"] = new
        return 1
    return 0


RAW_GITHUB = [("profiles.jsonl", raw_profiles, "login -> pseudonym; bio/blog/company/location/twitter -> null"),
              ("users_search.jsonl", raw_login, "login -> pseudonym"),
              ("repos.jsonl", raw_repos, "owner_login/full_name -> pseudonym; name/description/homepage -> null"),
              ("readmes.jsonl", raw_readmes, "owner_login/full_name -> pseudonym; readme_text -> null; tree paths -> null"),
              ("social.jsonl", raw_social, "login -> pseudonym; account URLs -> provider only"),
              ("repos_done.jsonl", raw_login, "login -> pseudonym"),
              ("query_log.jsonl", raw_query_log, "logins/repository names in request URLs -> pseudonym")]


def rewrite_jsonl(path: Path, fn, confirm: bool) -> tuple[int, int, int]:
    """Apply fn to every row not yet flagged redacted. Returns (rows, rows touched, non-empty values replaced)."""
    rows = touched = cells = 0
    tmp = path.with_name(path.name + ".tmp")
    out = open(tmp, "w", encoding="utf-8") if confirm else None
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line); rows += 1
                if not r.get("redacted"):
                    cells += fn(r); touched += 1
                    r["redacted"] = True
                if out:
                    out.write(json.dumps(r, ensure_ascii=False) + "\n")
    finally:
        if out:
            out.close()
    if confirm:
        _replace(tmp, path)
    return rows, touched, cells


# ------------------------------------------------------------------ GitHub processed
def _read_rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def _write_rows(path: Path, rows: list[dict]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    _replace(tmp, path)


def _write_parquet(path: Path, df: pd.DataFrame) -> None:
    tmp = path.with_name(path.name + ".tmp")
    df.to_parquet(tmp, index=False)
    _replace(tmp, path)


def _is_target(source, collection_date, redacted, date: str) -> bool:
    return source == "github" and str(collection_date) == date and not (redacted is True)


def redact_candidates(proc: Path, date: str, rep: Report) -> set[str]:
    """Returns the candidate ids of source github / collection_date <date> (already redacted ones included)."""
    j = proc / "supply_candidates.jsonl"
    if not j.exists():
        rep.add(j, "missing; skipped")
        return set()
    rows = _read_rows(j)
    ids = {r["candidate_id"] for r in rows if r.get("source") == "github" and str(r.get("collection_date")) == date}
    cells = touched = 0
    for r in rows:
        if not _is_target(r.get("source"), r.get("collection_date"), r.get("redacted"), date):
            continue
        touched += 1
        if "has_blog" not in r:
            r["has_blog"] = _nonempty(r.get("blog"))
        for k in PERSONAL_FIELDS:
            cells += int(_nonempty(r.get(k)))
            r[k] = None
        r["redacted"] = True
    rep.add(j, f"{len(rows)} rows, {touched} of source github / {date} redacted ({cells} non-empty personal values -> null), "
               f"{len(rows) - len(ids)} rows of other sources/dates untouched")
    if rep.confirm and touched:
        _write_rows(j, rows)
    pq = proc / "supply_candidates.parquet"
    if pq.exists():
        df = pd.read_parquet(pq)
        red = df["redacted"] if "redacted" in df.columns else pd.Series(False, index=df.index)
        mask = (df["source"] == "github") & (df["collection_date"].astype(str) == date) & ~red.fillna(False).astype(bool)
        if "has_blog" not in df.columns:
            df["has_blog"] = df["blog"].fillna("").astype(str).str.strip().ne("") if "blog" in df.columns else False
        for k in PERSONAL_FIELDS:
            if k in df.columns:
                df[k] = df[k].astype(object)
                df.loc[mask, k] = None
        df["redacted"] = red.fillna(False).astype(bool) | mask
        rep.add(pq, f"{int(mask.sum())} rows redacted, same fields; redacted flag written")
        if rep.confirm and mask.any():
            _write_parquet(pq, df)
    return ids


def _headings(v) -> list:
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            return []
    return list(v) if isinstance(v, (list, tuple)) or hasattr(v, "tolist") else []


def redact_projects(proc: Path, ids: set[str], rep: Report) -> None:
    j = proc / "supply_projects.jsonl"
    if not j.exists():
        rep.add(j, "missing; skipped")
        return
    if not ids:
        rep.add(j, "no GitHub candidates of this date; untouched")
        return
    rows = _read_rows(j)
    common = {h for h, k in Counter(h for r in rows for h in (r.get("readme_heading_list") or [])).items() if k >= HEADING_MIN}
    touched = cells = dropped = 0
    for r in rows:
        if r.get("candidate_id") not in ids or r.get("redacted"):
            continue
        touched += 1
        cells += int(_nonempty(r.get("repo_full_name"))) + sum(int(_nonempty(r.get(k))) for k in PROJECT_TEXT)
        r["repo_full_name"] = pseud("github_repo", r.get("repo_full_name"))
        for k in PROJECT_TEXT:
            r[k] = None
        hl = r.get("readme_heading_list") or []
        kept = [h for h in hl if h in common]
        dropped += len(hl) - len(kept)
        r["readme_heading_list"] = kept
        r["redacted"] = True
    rep.add(j, f"{len(rows)} rows, {touched} redacted (repo_full_name -> pseudonym, name/description -> null: {cells} values; "
               f"{dropped} rare README headings dropped, {len(common)} headings used >= {HEADING_MIN} times kept)")
    if rep.confirm and touched:
        _write_rows(j, rows)
    pq = proc / "supply_projects.parquet"
    if pq.exists():
        df = pd.read_parquet(pq)
        red = df["redacted"].fillna(False).astype(bool) if "redacted" in df.columns else pd.Series(False, index=df.index)
        mask = df["candidate_id"].isin(ids) & ~red
        if "repo_full_name" in df.columns:
            df.loc[mask, "repo_full_name"] = df.loc[mask, "repo_full_name"].map(lambda v: pseud("github_repo", v))
        for k in PROJECT_TEXT:
            if k in df.columns:
                df[k] = df[k].astype(object)
                df.loc[mask, k] = None
        if "readme_heading_list" in df.columns:
            df.loc[mask, "readme_heading_list"] = df.loc[mask, "readme_heading_list"].map(
                lambda v: json.dumps([h for h in _headings(v) if h in common], ensure_ascii=False))
        df["redacted"] = red | mask
        rep.add(pq, f"{int(mask.sum())} rows redacted, same fields; redacted flag written")
        if rep.confirm and mask.any():
            _write_parquet(pq, df)


def redact_review_files(proc: Path, date: str, rep: Report) -> None:
    man = proc / "supply_build_manifest.json"
    built = json.loads(man.read_text(encoding="utf-8")).get("collection_date") if man.exists() else None
    if built != date:
        rep.add(proc / "supply_quality_*", f"review/label files belong to build {built}, not {date}; untouched")
        return
    for name, cols in REVIEW_TEXT.items():
        p = proc / name
        if not p.exists():
            continue
        df = pd.read_csv(p, dtype=str, keep_default_na=False)
        cols = [c for c in cols if c in df.columns]
        cells = int(sum((df[c].str.strip() != "").sum() for c in cols))
        for c in cols:
            df[c] = ""
        rep.add(p, f"{len(df)} rows; {cells} free-text cells in {cols} blanked; ids, derived fields and labels kept")
        if rep.confirm and cells:
            tmp = p.with_name(p.name + ".tmp"); df.to_csv(tmp, index=False); _replace(tmp, p)
    for name in REVIEW_DELETE:
        p = proc / name
        if p.exists():
            rep.add(p, "deleted (location text only)")
            if rep.confirm:
                p.unlink()
    rep.add(proc / "supply_skill_evidence.parquet", "kept (candidate ids, skills and derived flags only)")


def _marker(folder: Path, source: str, date: str, status: str, lines: list[str]) -> None:
    (folder / "REDACTED.json").write_text(json.dumps({"source": source, "date": date, "status": status,
                                                      "redacted_at": dt.datetime.now().isoformat(timespec="seconds"),
                                                      "script": "src/pipeline/redact_supply_raw.py", "report": lines}, indent=1),
                                          encoding="utf-8")


def _marker_status(folder: Path) -> str | None:
    m = folder / "REDACTED.json"
    return json.loads(m.read_text(encoding="utf-8")).get("status") if m.exists() else None


def redact_github(root: Path, date: str, confirm: bool) -> Report:
    rep = Report(confirm, root)
    raw = root / "data" / "raw" / "github_supply" / date
    proc = root / "data" / "processed"
    if _marker_status(raw) == "complete":
        rep.add(raw / "REDACTED.json", "already complete; nothing to do (a second pass would re-hash pseudonyms)")
        return rep
    if confirm and raw.exists():
        _marker(raw, "github", date, "in_progress", [])
    if not raw.exists():
        rep.add(raw, "missing; raw files skipped")
    for name, fn, what in RAW_GITHUB:
        p = raw / name
        if p.exists():
            rows, touched, cells = rewrite_jsonl(p, fn, confirm)
            rep.add(p, f"{rows} rows, {touched} redacted ({cells} values): {what}")
    if (raw / "search_summary.jsonl").exists():
        rep.add(raw / "search_summary.jsonl", "kept (query-level counts, no account data)")
    ids = redact_candidates(proc, date, rep)
    redact_projects(proc, ids, rep)
    redact_review_files(proc, date, rep)
    if confirm and raw.exists():
        _marker(raw, "github", date, "complete", rep.lines)
        rep.add(raw / "REDACTED.json", "written; build_supply.py now refuses a full rebuild of this folder")
    elif raw.exists():
        rep.add(raw / "REDACTED.json", "would be written (build_supply.py then refuses a full rebuild of this folder)")
    return rep


# ------------------------------------------------------------------ LinkedIn slot
def sampling_tokens(notes: str) -> str:
    return "; ".join(p.strip() for p in str(notes or "").split(";") if SAMPLING_TOKEN.match(p.strip()))


def redact_li_frame(df: pd.DataFrame, mask: pd.Series) -> int:
    cells = 0
    for col in LI_MARK:
        if col in df.columns:
            hit = mask & df[col].str.strip().ne("") & df[col].ne(LI_PLACEHOLDER)
            cells += int(hit.sum()); df.loc[hit, col] = LI_PLACEHOLDER
    if "notes" in df.columns:
        new = df.loc[mask, "notes"].map(sampling_tokens)
        cells += int((new != df.loc[mask, "notes"]).sum()); df.loc[mask, "notes"] = new
    return cells


def redact_linkedin(root: Path, date: str, confirm: bool) -> Report:
    rep = Report(confirm, root)
    folder = root / "data" / "raw" / "linkedin_supply" / date
    proc = root / "data" / "processed"
    if _marker_status(folder) == "complete":
        rep.add(folder / "REDACTED.json", "already complete; the confirm run re-applies the (idempotent) LinkedIn rules")
    if not folder.exists():
        rep.add(folder, "missing; raw files skipped")
    raw = folder / "profiles_manual.csv"
    if raw.exists():
        df = pd.read_csv(raw, dtype=str, keep_default_na=False)
        n = redact_li_frame(df, pd.Series(True, index=df.index))
        rep.add(raw, f"{len(df)} rows; {n} cells redacted (headline/transition_wording -> {LI_PLACEHOLDER}, notes -> sampling tokens)")
        if confirm and n:
            tmp = raw.with_name(raw.name + ".tmp"); df.to_csv(tmp, index=False); _replace(tmp, raw)
    state = folder / "state.json"
    if state.exists():
        payload = json.loads(state.read_text(encoding="utf-8"))
        draft = payload.get("draft") or {}
        pending = sum(1 for v in draft.values() if str(v or "").strip())
        msgs = sum(1 for k in ("last_error", "last_message") if str(payload.get(k) or "").strip())
        rep.add(state, f"cockpit draft: {pending} filled field(s) of {len(draft)} cleared; {msgs} status message(s) cleared; "
                       "observer, token, paste_field kept")
        if confirm and (draft or msgs):
            payload.update(draft={}, last_error="", last_message="")
            state.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    for name in LI_SCAN:
        p = folder / name
        if p.exists():
            hits = len(LEAK.findall(p.read_text(encoding="utf-8")))
            rep.add(p, "kept (no personal free text by construction); " +
                    (f"WARNING {hits} profile-URL/e-mail pattern(s) found — review by hand" if hits else "0 profile-URL/e-mail patterns"))
    proc_li = proc / "supply_linkedin_profiles.csv"
    if proc_li.exists():
        df = pd.read_csv(proc_li, dtype=str, keep_default_na=False)
        mask = df["collection_date"] == date if "collection_date" in df.columns else pd.Series(True, index=df.index)
        n = redact_li_frame(df, mask)
        rep.add(proc_li, f"{int(mask.sum())} of {len(df)} rows of {date}; {n} cells redacted (same rules)")
        if confirm and n:
            tmp = proc_li.with_name(proc_li.name + ".tmp"); df.to_csv(tmp, index=False); _replace(tmp, proc_li)
    j = proc / "supply_candidates.jsonl"
    if j.exists():
        n = sum(1 for r in _read_rows(j) if r.get("source") == "linkedin_manual" and str(r.get("collection_date")) == date)
        rep.add(j, f"{n} linkedin_manual rows of {date}: kept (bio = coded current_title; no free text is copied into candidates)")
    if confirm and folder.exists():
        _marker(folder, "linkedin", date, "complete", rep.lines)
        rep.add(folder / "REDACTED.json", "written")
    elif folder.exists():
        rep.add(folder / "REDACTED.json", "would be written")
    return rep


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description="Layer 2 retention step (legal audit §10.5). Dry run unless --confirm.")
    ap.add_argument("--source", required=True, choices=("github", "linkedin", "all"))
    ap.add_argument("--date", required=True, help="collection date YYYY-MM-DD (the raw folder name)")
    ap.add_argument("--confirm", action="store_true", help="apply the redaction (irreversible)")
    a = ap.parse_args(argv)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.date):
        print(f"--date must be YYYY-MM-DD, got {a.date!r}")
        return 1
    mode = "REDACTED" if a.confirm else "DRY RUN — nothing written; --confirm would do the following"
    if a.source in ("github", "all"):
        redact_github(root, a.date, a.confirm).print(f"[github {a.date}] {mode}:")
    if a.source in ("linkedin", "all"):
        redact_linkedin(root, a.date, a.confirm).print(f"[linkedin {a.date}] {mode}:")
    if not a.confirm:
        print("add --confirm to apply (irreversible)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
