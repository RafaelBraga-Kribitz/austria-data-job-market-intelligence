"""Layer 2 collector: public GitHub profiles and repositories of users located in Austria.

Source: GitHub REST API v3 (documented, authenticated with the owner's `gh` CLI token). GitHub's
Acceptable Use Policies §7 allow researchers to use public information from the Service for research
whose publications are open access, and prohibit use for spamming or selling personal information to
recruiters; the API terms prohibit abusive request rates. This collector stays within the published
rate limits (search 30/min, core 5,000/h), sends a descriptive User-Agent, never fetches e-mail
addresses or names, and writes everything to data/raw/github_supply/<date>/ which is PRIVATE
(see docs/legal-and-publication-audit.md §10). Only aggregates are published.

Stages (each resumable; re-running skips work already on disk):
  search    user search over the sampling frames in config/supply_taxonomy.json -> users_search.jsonl,
            one search_summary.jsonl row per finished query
  profiles  GET /users/{login} for every unique login                            -> profiles.jsonl
  repos     GET /users/{login}/repos (owner, up to 300) for every user           -> repos.jsonl, repos_done.jsonl
  readmes   README text + top-level file tree for repositories classified as data repositories
            (classification rules in src/pipeline/build_supply.py, applied here for selection only)
                                                                                -> readmes.jsonl (README and tree
                                                                                   in one row per repository)
  social    GET /users/{login}/social_accounts for users with any data signal    -> social.jsonl

Failures. A unit of work is recorded as done only on HTTP 200 or a definitive client error (404, 451,
409 empty repository, ...). Transient outcomes (403/429 throttling, 5xx, network errors, reported as
599 after six attempts) are not written to the stage file; they are appended to retry.jsonl for the
record and fetched again by the next run of the stage.

Credentials. The token comes from GH_TOKEN or GITHUB_TOKEN if set, otherwise from `gh auth token`
(GitHub CLI, https://cli.github.com, after `gh auth login`). Without either the collector exits with
a message saying so.

Usage:  python src/acquisition/collect_github_supply.py [search|profiles|repos|readmes|social|all]
        --date YYYY-MM-DD (default: today in Europe/Vienna, via common.today()) to continue a collection
        folder. The 2026-09-17 folder was named by the collecting machine's local day.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import date_arg, is_transient, today  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
with open(ROOT / "config" / "supply_taxonomy.json", encoding="utf-8") as _f:
    CFG = json.load(_f)
API = "https://api.github.com"
UA = "austria-data-job-market-intelligence research collector (non-commercial labour-market research; contact via repository)"


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def token() -> str:
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(var, "").strip():
            return os.environ[var].strip()
    try:
        p = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("no GitHub token: the GitHub CLI `gh` is not installed or not on PATH. Install it from "
                 "https://cli.github.com and run `gh auth login`, or set GH_TOKEN / GITHUB_TOKEN.")
    t = p.stdout.strip()
    if p.returncode != 0 or not t:
        why = (p.stderr or "").strip().splitlines()[:1] or ["empty output"]
        sys.exit(f"no GitHub token: `gh auth token` failed ({why[0][:200]}). Run `gh auth login` or set GH_TOKEN / GITHUB_TOKEN.")
    return t


class Client:
    def __init__(self, out: Path):
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token()}", "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": UA})
        self.log = open(out / "query_log.jsonl", "a", encoding="utf-8")
        self.n = 0
        self.n_errors = 0  # network exceptions and unparseable 200 bodies (each retried)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self) -> None:
        self.log.close()
        self.s.close()

    def _log(self, **fields) -> None:
        self.log.write(json.dumps({"t": now_utc(), **fields}) + "\n")
        self.log.flush()

    def get(self, path: str, params: dict | None = None, kind: str = "core") -> tuple[int, object, dict]:
        url = path if path.startswith("http") else API + path
        for attempt in range(6):
            try:
                r = self.s.get(url, params=params, timeout=60)
            except requests.RequestException as e:
                self.n_errors += 1
                self._log(url=url, status=None, error=e.__class__.__name__)
                print(f"  [err] {e.__class__.__name__}: {url[:90]}", flush=True)
                time.sleep(5 * (attempt + 1))
                continue
            self.n += 1
            rem = r.headers.get("X-RateLimit-Remaining")
            reset = r.headers.get("X-RateLimit-Reset")
            self._log(url=r.url, status=r.status_code, remaining=rem)
            if r.status_code == 200:
                try:
                    js = r.json()
                except ValueError:
                    self.n_errors += 1
                    time.sleep(5 * (attempt + 1))
                    continue
                if rem is not None and int(rem) < (3 if kind == "search" else 50):
                    wait = max(1, int(reset or time.time()) - int(time.time()) + 2)
                    print(f"  rate limit ({kind}); sleeping {wait}s", flush=True)
                    time.sleep(wait)
                elif kind == "search":
                    time.sleep(2.1)  # 30/min
                else:
                    time.sleep(0.72)  # ~5,000/h core limit; the remaining-count check above sleeps until reset when it gets close
                return 200, js, r.headers
            if r.status_code in (403, 429) and ("rate limit" in r.text.lower() or r.headers.get("Retry-After")):
                wait = int(r.headers.get("Retry-After") or max(5, int(reset or 0) - int(time.time()) + 2))
                print(f"  throttled ({r.status_code}); sleeping {min(wait, 900)}s", flush=True)
                time.sleep(min(wait, 900))
                continue
            if r.status_code in (404, 451, 409, 422, 301):
                return r.status_code, None, r.headers
            if r.status_code >= 500:
                time.sleep(5 * (attempt + 1))
                continue
            return r.status_code, None, r.headers
        return 599, None, {}


def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def append_jsonl(p: Path, rows) -> None:
    if isinstance(rows, dict):
        rows = [rows]
    with open(p, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def note_retry(out: Path, stage: str, key: str, status) -> None:
    """Record a transient failure; the unit is not marked done, so the next run of the stage retries it."""
    append_jsonl(out / "retry.jsonl", {"stage": stage, "key": key, "status": status, "collected_at": now_utc()})


# ------------------------------------------------------------------ stage: search
def _search_users(c: Client, q: str, frame: str, out: Path, cap: int | None = None, have_pages: set | frozenset = frozenset()) -> bool:
    """Run one user search, all pages up to the 1,000-result API cap (or `cap`), append rows.

    Returns True when the query is finished (search_summary.jsonl row written). A transient failure
    writes no summary row, so the query is re-run next time; `have_pages` are pages whose rows an
    interrupted earlier run already stored, which are re-read but not appended again."""
    got = 0
    page = 1
    total = None
    status = 200
    while True:
        st, js, _ = c.get("/search/users", {"q": q, "per_page": 100, "page": page, "sort": "joined", "order": "asc"}, kind="search")
        if st != 200 or js is None:
            status = st
            print(f"  search failed {st}: {q}", flush=True)
            break
        total = js.get("total_count")
        items = js.get("items", [])
        if page not in have_pages:
            rows = [{"login": u["login"], "id": u["id"], "type": u["type"], "query": q, "frame": frame, "total_count": total,
                     "page": page, "collected_at": now_utc()} for u in items]
            append_jsonl(out / "users_search.jsonl", rows)
        got += len(items)
        if not items or got >= min(1000, cap or 1000) or got >= (total or 0):
            break
        page += 1
    if is_transient(status):
        note_retry(out, "search", q, status)
        return False
    summary = {"query": q, "frame": frame, "total_count": total, "retrieved": got}
    if status != 200:
        summary["status"] = status  # definitive failure (e.g. 422 invalid query): recorded, not retried
    append_jsonl(out / "search_summary.jsonl", summary)
    print(f"  {frame:2} {total!s:>6} -> {got:4}  {q}", flush=True)
    return True


FRAME_B_EDGES = (2, 5, 10, 20, 40, 80)  # upper bounds of the repo-count slices


def frame_b_slices(minr: int) -> list[str]:
    """Repo-count slices from `minr` upwards; for minr=1: repos:1..2, 3..5, 6..10, 11..20, 21..40, 41..80, >=81."""
    out, lo = [], minr
    for hi in FRAME_B_EDGES:
        if hi >= lo:
            out.append(f"repos:{lo}..{hi}")
            lo = hi + 1
    out.append(f"repos:>={lo}")
    return out


def stage_search(c: Client, out: Path) -> None:
    done = {r["query"] for r in read_jsonl(out / "search_summary.jsonl")}
    pages: dict[str, set] = {}
    for r in read_jsonl(out / "users_search.jsonl"):
        if r["query"] not in done:
            pages.setdefault(r["query"], set()).add(r["page"])
    gs = CFG["github_search"]
    n_retry = 0

    def run(q: str, frame: str, cap: int | None = None) -> None:
        nonlocal n_retry
        if q not in done and not _search_users(c, q, frame, out, cap=cap, have_pages=pages.get(q, frozenset())):
            n_retry += 1

    # Frame A: bio keyword × Austrian location token (keywords carry their own quoting)
    for loc in gs["frame_a_tokens"]:
        for kw in gs["bio_keywords"]:
            run(f'{kw} in:bio location:"{loc}" type:user', "A")
    # Frame B: complete Styrian population with >=1 public repo; slice by repo count so no slice exceeds 1,000
    minr = gs["search_min_repos_frames_bc"]
    for loc in gs["location_tokens_styria"]:
        base = f'location:"{loc}" type:user'
        probe_q = f"{base} repos:>={minr}"
        sliced = [f"{base} {sl}" for sl in frame_b_slices(minr)]
        if probe_q in done or all(q in done for q in sliced):
            continue
        st, js, _ = c.get("/search/users", {"q": probe_q, "per_page": 1}, kind="search")
        if st != 200 or js is None:  # never fall back to an unsliced query that may be capped at 1,000
            print(f"  B probe failed ({st}) for {loc}: token skipped, retried next run", flush=True)
            note_retry(out, "search_probe", probe_q, st)
            n_retry += 1
            continue
        for q in ([probe_q] if (js.get("total_count") or 0) <= 1000 else sliced):
            run(q, "B")
    # Frame C: base-rate sample for other regions, sliced by created-year windows, capped per slice
    br = gs["base_rate_sample"]
    for loc in br["tokens"]:
        for a, b in br["created_windows"]:
            run(f'location:"{loc}" type:user repos:>={minr} created:{a}..{b}', "C", cap=br["per_slice_cap"])
    if n_retry:
        print(f"search: {n_retry} queries left for retry (retry.jsonl)", flush=True)


# ------------------------------------------------------------------ stage: profiles
PROFILE_FIELDS = ["login", "id", "type", "company", "blog", "location", "hireable", "bio", "twitter_username",
                  "public_repos", "public_gists", "followers", "following", "created_at", "updated_at"]


def stage_profiles(c: Client, out: Path) -> None:
    logins = sorted({r["login"] for r in read_jsonl(out / "users_search.jsonl") if r.get("type") == "User"})
    done = {r["login"] for r in read_jsonl(out / "profiles.jsonl") if r.get("id") or not is_transient(r.get("status"))}
    todo = [l for l in logins if l not in done]
    print(f"profiles: {len(logins)} unique logins, {len(todo)} to fetch", flush=True)
    buf = []
    n_retry = 0
    try:
        for i, login in enumerate(todo, 1):
            st, js, _ = c.get(f"/users/{login}")
            if st == 200 and js:
                row = {k: js.get(k) for k in PROFILE_FIELDS}  # name and email are deliberately not stored
            elif is_transient(st):
                note_retry(out, "profiles", login, st)
                n_retry += 1
                continue
            else:
                row = {"login": login, "status": st}  # definitive (e.g. 404 account deleted)
            row["collected_at"] = now_utc()
            buf.append(row)
            if len(buf) >= 25:
                append_jsonl(out / "profiles.jsonl", buf); buf = []
            if i % 200 == 0:
                print(f"  profiles {i}/{len(todo)}", flush=True)
    finally:  # an exception or Ctrl-C must not lose up to 24 fetched rows
        append_jsonl(out / "profiles.jsonl", buf)
    if n_retry:
        print(f"profiles: {n_retry} left for retry (retry.jsonl)", flush=True)


# ------------------------------------------------------------------ stage: repos
REPO_FIELDS = ["id", "name", "full_name", "description", "fork", "archived", "disabled", "language", "topics", "homepage",
               "stargazers_count", "forks_count", "watchers_count", "open_issues_count", "size", "has_pages", "has_wiki",
               "has_issues", "license", "created_at", "updated_at", "pushed_at", "default_branch", "is_template"]


def stage_repos(c: Client, out: Path, max_pages: int = 3) -> None:
    profiles = [r for r in read_jsonl(out / "profiles.jsonl") if r.get("id")]
    done = {r["login"] for r in read_jsonl(out / "repos_done.jsonl") if not is_transient(r.get("status", 200))}
    todo = [p for p in profiles if p["login"] not in done and (p.get("public_repos") or 0) > 0]
    print(f"repos: {len(profiles)} profiles, {len(todo)} users with repos to fetch", flush=True)
    n_retry = 0
    for i, p in enumerate(todo, 1):
        rows = []
        status = 200
        for page in range(1, max_pages + 1):
            st, js, _ = c.get(f"/users/{p['login']}/repos", {"type": "owner", "per_page": 100, "page": page, "sort": "pushed"})
            if st != 200:
                status = st
                break
            if not js:
                break
            for r in js:
                row = {k: r.get(k) for k in REPO_FIELDS}
                row["license"] = (r.get("license") or {}).get("key")
                row["owner_login"] = p["login"]
                rows.append(row)
            if len(js) < 100:
                break
        if is_transient(status):  # all or nothing per user: partial pages are not written
            note_retry(out, "repos", p["login"], status)
            n_retry += 1
            continue
        append_jsonl(out / "repos.jsonl", rows)
        done_row = {"login": p["login"], "n": len(rows), "public_repos": p.get("public_repos"), "truncated": len(rows) >= 100 * max_pages}
        if status != 200:
            done_row["status"] = status
        append_jsonl(out / "repos_done.jsonl", [done_row])
        if i % 200 == 0:
            print(f"  repos {i}/{len(todo)}", flush=True)
    if n_retry:
        print(f"repos: {n_retry} users left for retry (retry.jsonl)", flush=True)


# ------------------------------------------------------------------ stage: readmes + trees (data repos only)
def _data_repo_selector():
    lex = CFG["data_repo_lexicon"]
    kw = re.compile("|".join(lex["keywords"]), re.I)
    ex = re.compile("|".join(lex["exclude"]), re.I)
    topics = set(lex["topics"])
    langs = set(lex["data_languages"])

    def is_data(r: dict) -> bool:
        if r.get("fork"):
            return False
        text = f"{r.get('name') or ''} {r.get('description') or ''} " + " ".join(r.get("topics") or [])
        if ex.search(text) and not (set(r.get("topics") or []) & topics):
            return False
        return (r.get("language") in langs) or bool(kw.search(text)) or bool(set(r.get("topics") or []) & topics)
    return is_data


def stage_readmes(c: Client, out: Path, max_chars: int = 40000, max_per_owner: int = 15) -> None:
    is_data = _data_repo_selector()
    repos = [r for r in read_jsonl(out / "repos.jsonl") if is_data(r)]
    # cap per owner: the 15 most recently pushed data repositories (repos.jsonl is ordered by pushed_at desc per owner);
    # prolific accounts would otherwise dominate the README budget without changing candidate-level measures
    per_owner: dict[str, int] = {}
    capped = []
    for r in repos:
        k = per_owner.get(r["owner_login"], 0)
        if k < max_per_owner:
            capped.append(r); per_owner[r["owner_login"]] = k + 1
    repos = capped
    done = {r["full_name"] for r in read_jsonl(out / "readmes.jsonl")
            if not is_transient(r.get("readme_status")) and not is_transient(r.get("tree_status"))}
    todo = [r for r in repos if r["full_name"] not in done]
    print(f"readmes/trees: {len(repos)} data repositories, {len(todo)} to fetch", flush=True)
    n_retry = 0
    for i, r in enumerate(todo, 1):
        fn = r["full_name"]
        st, js, _ = c.get(f"/repos/{fn}/readme")
        if is_transient(st):
            note_retry(out, "readmes", fn, st); n_retry += 1
            continue
        row = {"full_name": fn, "owner_login": r["owner_login"], "readme_status": st, "readme_name": None, "readme_size": None, "readme_text": None}
        if st == 200 and js:
            try:
                txt = base64.b64decode(js.get("content") or "").decode("utf-8", "ignore")
            except ValueError:  # binascii.Error: malformed base64
                txt = ""
                row["readme_decode_error"] = True
            row.update({"readme_name": js.get("name"), "readme_size": js.get("size"), "readme_text": txt[:max_chars], "readme_truncated": len(txt) > max_chars})
        st2, js2, _ = c.get(f"/repos/{fn}/git/trees/{r.get('default_branch') or 'HEAD'}")
        if is_transient(st2):
            note_retry(out, "trees", fn, st2); n_retry += 1
            continue
        tree = None
        if st2 == 200 and js2:
            tree = [{"path": e.get("path"), "type": e.get("type"), "size": e.get("size")} for e in js2.get("tree", [])][:400]
        row["tree_status"] = st2
        row["tree"] = tree
        row["collected_at"] = now_utc()
        append_jsonl(out / "readmes.jsonl", [row])
        if i % 200 == 0:
            print(f"  readmes {i}/{len(todo)}", flush=True)
    if n_retry:
        print(f"readmes: {n_retry} repositories left for retry (retry.jsonl)", flush=True)


# ------------------------------------------------------------------ stage: social accounts (data-signal users)
def stage_social(c: Client, out: Path) -> None:
    is_data = _data_repo_selector()
    users_with_data_repo = {r["owner_login"] for r in read_jsonl(out / "repos.jsonl") if is_data(r)}
    kw = re.compile(r"data|analy|machine learning|\bml\b|\bai\b|statist|scien|engineer|\bbi\b|intelligence|quant", re.I)
    profiles = [p for p in read_jsonl(out / "profiles.jsonl") if p.get("id")]
    todo_logins = [p["login"] for p in profiles if p["login"] in users_with_data_repo or kw.search(p.get("bio") or "")]
    done = {r["login"] for r in read_jsonl(out / "social.jsonl") if not is_transient(r.get("status"))}
    todo = [l for l in todo_logins if l not in done]
    print(f"social: {len(todo_logins)} data-signal users, {len(todo)} to fetch", flush=True)
    n_retry = 0
    for i, login in enumerate(todo, 1):
        st, js, _ = c.get(f"/users/{login}/social_accounts")
        if is_transient(st):
            note_retry(out, "social", login, st); n_retry += 1
            continue
        accts = [{"provider": a.get("provider"), "url": a.get("url")} for a in (js or [])] if st == 200 else None
        append_jsonl(out / "social.jsonl", [{"login": login, "status": st, "accounts": accts, "collected_at": now_utc()}])
        if i % 500 == 0:
            print(f"  social {i}/{len(todo)}", flush=True)
    if n_retry:
        print(f"social: {n_retry} left for retry (retry.jsonl)", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", nargs="?", default="all", choices=["search", "profiles", "repos", "readmes", "social", "all"])
    ap.add_argument("--date", type=date_arg, default=None, help="collection folder (default: today in Europe/Vienna)")
    a = ap.parse_args()
    date = a.date or today()
    out = ROOT / "data" / "raw" / "github_supply" / date
    out.mkdir(parents=True, exist_ok=True)
    stages = ["search", "profiles", "repos", "readmes", "social"] if a.stage == "all" else [a.stage]
    with Client(out) as c:
        for s in stages:
            print(f"== stage {s} ({date}) ==", flush=True)
            {"search": stage_search, "profiles": stage_profiles, "repos": stage_repos, "readmes": stage_readmes, "social": stage_social}[s](c, out)
        print(f"done; {c.n} requests this run, {c.n_errors} network/parse errors (retried)", flush=True)


if __name__ == "__main__":
    main()
