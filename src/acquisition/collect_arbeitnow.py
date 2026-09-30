"""Collect Arbeitnow's documented public job-board API (no key).

Source: https://www.arbeitnow.com/api/job-board-api
Blog (fetched 2026-09-18): ATS feeds (Greenhouse, Personio, SmartRecruiters, …), Europe/DACH-heavy.
This collector is PUBLIC code (documented API, same class as GitHub/Eurostat). Raw records stay
gitignored under data/raw/arbeitnow/<date>/ (third-party JD text). Results are a dated supplement
and must NOT be merged into the 2026-09-16 Layer 1 snapshot (D-023).

Usage: python src/acquisition/collect_arbeitnow.py [--pages N] [--date YYYY-MM-DD]
  --date defaults to today in Europe/Vienna. The feed is not resumable: a second run into the same
  folder appends the pages again (a warning is printed), so de-duplicate by slug downstream.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RawWriter, Session, cli, status_of  # noqa: E402

API = "https://www.arbeitnow.com/api/job-board-api"
AT_RE = re.compile(
    r"\b(austria|österreich|oesterreich|wien|vienna|graz|linz|salzburg|innsbruck|"
    r"klagenfurt|villach|wels|st\.?\s*pölten|sankt pölten|bregenz|eisenstadt|"
    r"steiermark|styria|oberösterreich|niederösterreich|kärnten|tirol|vorarlberg|"
    r"burgenland)\b",
    re.I,
)


def is_austria(location: str) -> bool:
    return bool(AT_RE.search(location or ""))


def clean_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def main() -> None:
    args = cli(__doc__, pages={"type": int, "default": 12, "help": "max API pages (each ~100 jobs)"})
    w = RawWriter("arbeitnow", args.date)
    if (w.dir / "listings.jsonl").exists():
        print(f"[arbeitnow] warning: {w.dir / 'listings.jsonl'} exists; this run appends to it")
    sess = Session(delay=1.2)
    n_all = n_at = 0
    for page in range(1, args.pages + 1):
        r = sess.get(API, params={"page": page})
        if r is None or r.status_code != 200:
            print(f"[arbeitnow] stop at page {page}: {status_of(r)}")
            w.log_query(page=page, status=status_of(r), returned=0, error=True)
            break
        try:
            data = r.json().get("data") or []
        except (ValueError, AttributeError):
            print(f"[arbeitnow] stop at page {page}: unexpected payload")
            w.log_query(page=page, status=r.status_code, returned=0, error="schema")
            break
        if not data:
            w.log_query(page=page, status=r.status_code, returned=0)
            break
        for j in data:
            n_all += 1
            loc = str(j.get("location") or "")
            rec = {
                "slug": j.get("slug"),
                "title": j.get("title"),
                "company_name": j.get("company_name"),
                "location": loc,
                "url": j.get("url") or (f"https://www.arbeitnow.com/jobs/{j.get('slug', '')}" if j.get("slug") else ""),
                "created_at": j.get("created_at"),
                "remote": j.get("remote"),
                "tags": j.get("tags") or [],
                "description_text": clean_html(j.get("description") or ""),
                "is_austria_location": is_austria(loc),
            }
            w.write("listings", rec, query=f"page={page}")
            if rec["is_austria_location"]:
                n_at += 1
        w.log_query(page=page, status=r.status_code, returned=len(data), austria_so_far=n_at,
                    **({"truncated": True} if page == args.pages else {}))
        print(f"[arbeitnow] page {page}: {len(data)} jobs (Austria location so far: {n_at})")
        if page == args.pages:
            print(f"[arbeitnow] page cap {args.pages} reached on a non-empty page: feed may be truncated")
    w.close()
    print(f"done. {n_all} listings, {n_at} with Austria location signal → {w.dir} ({sess.summary()})")


if __name__ == "__main__":
    main()
