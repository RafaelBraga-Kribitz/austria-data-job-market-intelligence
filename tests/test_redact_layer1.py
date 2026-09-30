"""Unit tests for src/pipeline/redact_layer1_contacts.py: patterns, false-positive guards, idempotency, dry run."""
import json

import pandas as pd
import pytest

import redact_layer1_contacts as R


@pytest.mark.parametrize("text", [
    "Mail: max.muster@firma.at",
    "bewerbung(at)firma.at",
    "jobs [at] firma [dot] com",
    "Tel.: +43 316 877-1234",
    "Telefon: +43 (0) 316 / 877 12 34",
    "0043 664 1234567",
    "T+43 1 53120-0",
    "Tel.: 0316 / 877-1234",
    "Mobil 0664 1234567",
    "Handy: 0676/123 45 67",
    "Rückfragen unter 0699 12345678.",
    "Kontakt: 0316/877-1234",
    "01/53120-0 (Zentrale)",
    "Frau X (+43 316 123 45 67)",
])
def test_contacts_are_removed(text):
    out = R.redact_text(text)
    assert "@" not in out and "(at)" not in out and "[at]" not in out
    assert sum(ch.isdigit() for ch in out) < 4, out


@pytest.mark.parametrize("text", [
    "Gehalt EUR 3.500 brutto, 14 Gehälter, 38,5 Stunden",
    "Start ab 01/2026, befristet bis 12/2027",
    "8010 Graz, Stadtplatz 13",
    "Job-ID 123456, Referenz 2026-0917",
    "https://example.com/careers?id=18386194-f012-4992-827f-51d91e785ada",
    "Python 3.12, ISO 27001, C++17",
    "Einstufung laut KV IT 2026, ab 01.10.2026",
])
def test_non_contacts_are_kept(text):
    assert R.redact_text(text) == text


def test_redaction_is_idempotent_and_counts():
    from collections import Counter
    src = "a@b.at, +43 316 1234567+43 664 7654321, Tel. 0316/877-1234"
    c1 = Counter()
    once = R.redact_text(src, c1)
    c2 = Counter()
    assert R.redact_text(once, c2) == once and not c2
    assert c1["email"] == 1 and c1["phone"] == 3


def test_willhaben_contact_block_is_dropped_in_dict_and_json_string():
    from collections import Counter
    c = Counter()
    rec = R.redact_record({"willhaben_detail": {"contact": {"firstname": "Anna"}, "description": "x@y.at"},
                           "title": "Data Analyst"}, c)
    assert rec["willhaben_detail"] == {"contact": None, "description": R.EMAIL_TOKEN}
    s = json.dumps({"contact": {"firstname": "Anna"}, "description": "Tel 0664 1234567"})
    out = json.loads(R.redact_record({"willhaben_detail": s}, c)["willhaben_detail"])
    assert out == {"contact": None, "description": "Tel " + R.PHONE_TOKEN}


def test_only_free_text_columns_are_touched():
    cols = ["description_text", "german_snippet", "experience_text", "location_text", "title", "source_url", "willhaben_detail"]
    assert R.text_columns(cols) == ["description_text", "german_snippet", "experience_text", "willhaben_detail"]


def _tree(tmp_path):
    rows = [{"posting_uid": "k:1", "title": "Data Analyst", "description_text": "Mail an hr@firma.at oder 0664 1234567",
             "german_snippet": "Deutsch C1", "source_url": "https://x.at/job/1"},
            {"posting_uid": "k:2", "title": "BI", "description_text": "Keine Kontakte hier.", "german_snippet": None,
             "source_url": "https://x.at/job/2"}]
    (tmp_path / "postings_dedup.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    pd.DataFrame(rows).to_parquet(tmp_path / "postings_dedup.parquet", index=False)
    (tmp_path / "interim_postings.jsonl").write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    return rows


def test_dry_run_changes_nothing(tmp_path, capsys):
    _tree(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    R.main(["--proc", str(tmp_path)])
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
    out = capsys.readouterr().out
    assert "would be removed" in out and "dry run" in out


def test_confirm_rewrites_files_and_second_run_is_a_no_op(tmp_path, capsys):
    _tree(tmp_path)
    R.main(["--proc", str(tmp_path), "--confirm"])
    rows = [json.loads(line) for line in (tmp_path / "postings_dedup.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows[0]["description_text"] == f"Mail an {R.EMAIL_TOKEN} oder {R.PHONE_TOKEN}"
    assert rows[1]["description_text"] == "Keine Kontakte hier."
    assert rows[0]["source_url"] == "https://x.at/job/1"
    pq = pd.read_parquet(tmp_path / "postings_dedup.parquet")
    assert pq.description_text.tolist() == [r["description_text"] for r in rows]
    assert not list(tmp_path.glob("*.redact_tmp"))
    snapshot = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    capsys.readouterr()
    R.main(["--proc", str(tmp_path), "--confirm"])
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == snapshot
    assert "in 0 rows" in capsys.readouterr().out
