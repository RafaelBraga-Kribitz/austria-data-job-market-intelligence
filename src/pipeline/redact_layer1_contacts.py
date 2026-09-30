"""Layer 1 contact redaction (docs/legal-and-publication-audit.md §4.1 and §8.1).

Removes e-mail addresses and phone numbers from the free-text columns of the
processed Layer 1 posting files, so that contact blocks copied from job ads do
not persist in data/processed. Runs right after dedupe.py; no analysis step
reads contact data, and the replacement tokens contain no digits or "@", so
skills, salary and language extraction (all done earlier in normalize.py) are
unaffected. Raw envelopes in data/raw stay untouched (private provenance).

Files : data/processed/interim_postings.{jsonl,parquet}
        data/processed/postings_*.{jsonl,parquet}
Fields: description_text, description_html, every *_snippet / *_text column
        and string values inside willhaben_detail; the willhaben contact block
        (willhaben_detail.contact: first name, salutation) is dropped.

Idempotent: a second run finds nothing to change. Dry run by default:

    python src/pipeline/redact_layer1_contacts.py            # report only
    python src/pipeline/redact_layer1_contacts.py --confirm  # rewrite files in place
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"

EMAIL_TOKEN = "[e-mail removed]"
PHONE_TOKEN = "[phone removed]"

# name@host.tld, plus the common obfuscations name(at)host.tld / name [at] host [dot] tld
EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+(?:@|\s?(?:\(at\)|\[at\]|\{at\})\s?)[A-Za-z0-9\-]+"
    r"(?:(?:\.|\s?(?:\(dot\)|\[dot\])\s?)[A-Za-z0-9\-]+)*(?:\.|\s?(?:\(dot\)|\[dot\])\s?)[A-Za-z]{2,}(?!\w)", re.I)
# separators inside a number never include a line break (the next line may start with another figure);
# \u00a0/\u202f are (narrow) no-break spaces, \u2013 an en dash, \u00bf a mis-decoded dash seen in some texts
SEP = r"[ \t\u00a0\u202f\-/.\u2013\u00bf]"
# international: +43 / 0043 (also other countries' +NN), optional "(0)", then digit groups. "+" may follow a
# letter ("T+43 ...") and may be doubled ("++43"); "00" may follow a letter only as "0043"
INTL_PHONE_RE = re.compile(
    rf"(?:(?<![\d+])0043|(?<![\w+])00[1-9]\d{{0,2}}|(?<!\+)\+\+?[1-9]\d{{0,2}})"
    rf"{SEP}*(?:\(0\){SEP}*)?\(?\d{{1,5}}\)?(?:{SEP}*\d{{1,8}}){{0,6}}(?!\d)")
# Austrian domestic after a phone keyword: "Tel.: 0316 / 877-1234", "Mobil 0664 1234567", "T 01 234 56 78"
KEYWORD_PHONE_RE = re.compile(
    r"(?P<kw>\b(?:tel(?:efon|ephone|\.|:)?|phone|mobil(?:e|telefon)?|handy|fax|durchwahl|t|m|f)\b[ \t]*[.:]?[ \t]*)"
    rf"(?P<num>\(?0\d{{1,4}}\)?(?:{SEP}*\d{{1,8}}){{1,5}})(?!\d)", re.I)
# Austrian mobile numbers without a keyword: 0650-0699 prefixes ("0664 123 45 67", "0676/1234567")
MOBILE_RE = re.compile(r"(?<![\w/.\-])\(?06[5-9]\d\)?[ \t\-/]*\d{3,4}(?:[ \t\-]?\d{2,4}){0,3}(?![\w/]|\.\d)")
# Austrian landline without a keyword, only in the slash/dash form "0316/877-1234", "01/53120-0", "(0732)/7720-0"
LANDLINE_RE = re.compile(r"(?<![\w/.\-])(?:\(0[1-9]\d{0,3}\)|0[1-9]\d{0,3}) ?[/\-] ?\d{2,}(?:[ \t\-]\d{1,6}){0,3}(?![\w/]|\.\d)")
MONTH_YEAR_RE = re.compile(r"^\(?0?[1-9]\)?\s?[/\-]\s?(?:19|20)\d\d\b")   # "01/2026" is a date, not a number

TEXT_COLUMNS = {"description_text", "description_html", "salary_text_raw", "applicants_text", "willhaben_detail"}


def _digits(s: str) -> int:
    return sum(ch.isdigit() for ch in s)


def _phone_ok(s: str) -> bool:
    # 7..20 digits: extensions and "(0)" push written Austrian numbers past the 15-digit E.164 limit
    return 7 <= _digits(s) <= 20 and not MONTH_YEAR_RE.match(s)


def redact_text(s, counts: Counter | None = None):
    """Return s with e-mail addresses and phone numbers replaced; non-strings pass through."""
    if not isinstance(s, str) or not s:
        return s
    counts = counts if counts is not None else Counter()

    def email(m):
        counts["email"] += 1
        return EMAIL_TOKEN

    def phone(m):
        if not _phone_ok(m.group(0)):
            return m.group(0)
        counts["phone"] += 1
        return PHONE_TOKEN

    def kw_phone(m):
        if not _phone_ok(m.group("num")):
            return m.group(0)
        counts["phone"] += 1
        return m.group("kw") + PHONE_TOKEN

    # repeat until nothing changes, so that numbers written back to back are all
    # caught and a second run of the script is a no-op
    for _ in range(5):
        before = s
        s = EMAIL_RE.sub(email, s)
        s = INTL_PHONE_RE.sub(phone, s)
        s = KEYWORD_PHONE_RE.sub(kw_phone, s)
        s = MOBILE_RE.sub(phone, s)
        s = LANDLINE_RE.sub(phone, s)
        if s == before:
            break
    return s


def redact_value(v, counts: Counter):
    """Recursive redaction for dict/list values (willhaben_detail); drops the contact block."""
    if isinstance(v, str):
        return redact_text(v, counts)
    if isinstance(v, list):
        return [redact_value(x, counts) for x in v]
    if isinstance(v, dict):
        if "contact" in v and v["contact"]:
            counts["contact_block"] += 1
        return {k: (None if k == "contact" else redact_value(x, counts)) for k, x in v.items()}
    return v


def text_columns(cols) -> list[str]:
    return [c for c in cols if c in TEXT_COLUMNS or c.endswith("_snippet") or (c.endswith("_text") and c != "location_text")]


def redact_record(rec: dict, counts: Counter) -> dict:
    for c in text_columns(rec.keys()):
        v = rec[c]
        if c == "willhaben_detail" and isinstance(v, str) and v.startswith("{"):
            try:
                before = sum(counts.values())
                red = redact_value(json.loads(v), counts)
                # re-serialise only when something was removed, so untouched cells keep their bytes
                if sum(counts.values()) != before:
                    rec[c] = json.dumps(red, ensure_ascii=False)
                continue
            except json.JSONDecodeError:
                pass
        rec[c] = redact_value(v, counts)
    return rec


def _replace(tmp: Path, target: Path) -> None:
    os.replace(tmp, target)


def process_jsonl(p: Path, confirm: bool) -> Counter:
    counts, changed = Counter(), 0
    tmp = p.with_suffix(p.suffix + ".redact_tmp")
    out = open(tmp, "w", encoding="utf-8", newline="\n") if confirm else None
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    if out:
                        out.write(line)
                    continue
                before = sum(counts.values())
                rec = redact_record(json.loads(line), counts)
                if sum(counts.values()) != before:
                    changed += 1
                if out:
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    finally:
        if out:
            out.close()
    if confirm:
        if changed:
            _replace(tmp, p)
        else:
            tmp.unlink()
    counts["rows_changed"] = changed
    return counts


def process_parquet(p: Path, confirm: bool) -> Counter:
    counts = Counter()
    df = pd.read_parquet(p)
    changed = pd.Series(False, index=df.index)
    for c in text_columns(df.columns):
        before = df[c].copy()
        if c == "willhaben_detail":
            df[c] = df[c].map(lambda v: redact_record({c: v}, counts)[c])
        else:
            df[c] = df[c].map(lambda v: redact_text(v, counts))
        changed |= ~(before.fillna("\0").astype(str) == df[c].fillna("\0").astype(str))
    counts["rows_changed"] = int(changed.sum())
    if confirm and counts["rows_changed"]:
        tmp = p.with_suffix(p.suffix + ".redact_tmp")
        df.to_parquet(tmp, index=False)
        _replace(tmp, p)
    return counts


def targets(proc: Path = PROC) -> list[Path]:
    names = sorted(proc.glob("postings_*.jsonl")) + sorted(proc.glob("postings_*.parquet"))
    names += [proc / "interim_postings.jsonl", proc / "interim_postings.parquet"]
    return [p for p in names if p.exists()]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Remove e-mail addresses and phone numbers from Layer 1 processed postings")
    ap.add_argument("--confirm", action="store_true", help="rewrite the files in place (default: dry run)")
    ap.add_argument("--proc", default=str(PROC), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    proc = Path(a.proc)
    files = targets(proc)
    if not files:
        print(f"redact_layer1_contacts: no postings files under {proc}")
        return
    verb = "removed" if a.confirm else "would be removed"
    for p in files:
        c = process_jsonl(p, a.confirm) if p.suffix == ".jsonl" else process_parquet(p, a.confirm)
        print(f"{p.name}: {c['email']} e-mail, {c['phone']} phone, {c['contact_block']} contact block(s) {verb} "
              f"in {c['rows_changed']} rows")
    older = [q for q in proc.rglob("postings_*") if q.parent != proc]
    if older:
        print(f"note: {len(older)} postings file(s) in sub-folders (e.g. {older[0].parent.name}/) are archives and were not touched")
    if not a.confirm:
        print("dry run: add --confirm to rewrite the files")


if __name__ == "__main__":
    main()
