"""Collector helpers (src/acquisition): dates, resume sets, retry and done-marking rules. No network.

Every test redirects RawWriter / the GitHub stages to tmp_path and replaces the HTTP layer with fakes,
so nothing is written under data/ and no request leaves the machine.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
import requests

import collect_github_supply as gh
import common


# The posting-board collectors (karriere, LinkedIn jobs, EURES) are not in the public export
# (src/publish/export_public.py EXCLUDE_ACQUISITION); their tests skip there instead of breaking collection.
@pytest.fixture
def karriere():
    return pytest.importorskip("collect_karriere", reason="private collector, not in the public export")


@pytest.fixture
def linkedin():
    return pytest.importorskip("collect_linkedin", reason="private collector, not in the public export")


@pytest.fixture
def eures():
    return pytest.importorskip("collect_eures", reason="private collector, not in the public export")


# ------------------------------------------------------------------ fakes
class FakeResponse:
    def __init__(self, status: int = 200, text: str = "", payload=None, url: str = "https://example.invalid/"):
        self.status_code = status
        self.text = text
        self.url = url
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class ScriptedSession:
    """Stands in for common.Session inside a collector: returns scripted responses, counts nothing real."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.n_requests = self.n_errors = self.n_failed = 0

    def get(self, url, **kw):
        self.calls.append((url, kw))
        return self.responses.pop(0)

    post = get

    def summary(self) -> str:
        return "fake"


@pytest.fixture
def raw(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "RAW", tmp_path)
    return tmp_path


def read(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")] if p.exists() else []


# ------------------------------------------------------------------ dates
def _frozen(monkeypatch, utc_iso: str):
    fixed = datetime.fromisoformat(utc_iso).replace(tzinfo=timezone.utc)

    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)

    monkeypatch.setattr(common, "datetime", Frozen)


def test_today_uses_vienna_local_day(monkeypatch):
    _frozen(monkeypatch, "2026-09-16T22:24:09")  # the Eurostat JVS fetch: 00:24 in Vienna (CEST, UTC+2)
    assert common.today() == "2026-09-17"
    _frozen(monkeypatch, "2026-09-16T17:00:00")
    assert common.today() == "2026-09-16"
    _frozen(monkeypatch, "2026-12-31T23:30:00")  # CET, UTC+1
    assert common.today() == "2027-01-01"


def test_date_arg_accepts_dates_and_suffixes_only():
    assert common.date_arg("2026-09-16") == "2026-09-16"
    assert common.date_arg("2026-09-17_subset") == "2026-09-17_subset"
    for bad in ("16.09.2026", "2026-9-16", "../2026-09-16", "2026-09-16/x"):
        with pytest.raises(Exception):
            common.date_arg(bad)


def test_rawwriter_honours_run_date(raw):
    w = common.RawWriter("karriere", "2026-09-16")
    assert w.dir == raw / "karriere" / "2026-09-16"


# ------------------------------------------------------------------ resume helpers
def test_existing_ids_counts_and_reports_skipped_lines(raw, capsys):
    w = common.RawWriter("src", "2026-01-01")
    lines = [json.dumps({"record": {"id": "a"}}), "{not json", json.dumps({"record": {}}), "", json.dumps({"record": {"id": "b"}})]
    (w.dir / "listings.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    ids = w.existing_ids("listings", lambda e: e["record"]["id"])
    assert ids == {"a", "b"}
    assert w.skipped["listings"] == 2  # one unparseable line, one without the id; blank lines are not counted
    out = capsys.readouterr().out
    assert "1 unparseable line(s)" in out and "1 line(s) without the resume id" in out


def test_detail_done_excludes_transient_statuses(raw):
    w = common.RawWriter("src", "2026-01-01")
    rows = [{"listing_id": i, "record": {"status": s}} for i, s in enumerate([200, 404, 410, 403, 429, 500, 503])]
    (w.dir / "details.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    assert w.existing_ids("details", lambda e: e["listing_id"], keep=common.detail_done) == {0, 1, 2}


def test_is_transient():
    assert all(common.is_transient(s) for s in (None, 403, 408, 429, 500, 502, 503, 504, 599))
    assert not any(common.is_transient(s) for s in (200, 301, 404, 409, 410, 422, 451))


def test_completed_queries_flag_and_legacy_rule(raw, linkedin):
    w = common.RawWriter("linkedin", "2026-01-01")
    for e in [
        {"keyword": "a", "location": "X", "start": 0, "status": 200, "returned": 10, "complete": False},
        {"keyword": "a", "location": "X", "start": 10, "status": 200, "returned": 3, "complete": True, "truncated": False},
        {"keyword": "b", "location": "X", "start": 0, "status": 200, "returned": 10, "complete": False},
        {"keyword": "b", "location": "X", "start": 10, "status": 503, "error": True},
        # legacy entries (2026-09-16 format, no complete flag)
        {"keyword": "c", "location": "X", "start": 40, "status": 200, "returned": 7},   # one short page: not proof
        {"keyword": "d", "location": "X", "start": 40, "status": 200, "returned": 0},   # empty page: complete
        {"keyword": "e", "location": "X", "start": 990, "status": 200, "returned": 10},  # start cap: complete
        {"detail_id": "123", "status": None, "error": True},
    ]:
        w.log_query(**e)
    assert w.completed_queries(("keyword", "location")) == {("a", "X")}
    assert w.completed_queries(("keyword", "location"), legacy=linkedin._legacy_complete) == {("a", "X"), ("d", "X"), ("e", "X")}


def test_end_of_sweep_logs_truncation_only_for_a_full_capped_page(raw):
    w = common.RawWriter("src", "2026-01-01")
    assert not common.end_of_sweep(w, False, 1, 3, True, keyword="k", page=1)
    assert common.end_of_sweep(w, True, 2, 3, False, keyword="k", page=2)
    assert common.end_of_sweep(w, False, 3, 3, True, keyword="k", page=3)
    log = read(w.query_log)
    assert [e["complete"] for e in log] == [False, True, True]
    assert "truncated" not in log[0] and log[1]["truncated"] is False and log[2]["truncated"] is True


# ------------------------------------------------------------------ Session retry behaviour
def _session(monkeypatch, outcomes, max_retries=4):
    sleeps = []
    monkeypatch.setattr(common.time, "sleep", sleeps.append)
    s = common.Session(delay=0, max_retries=max_retries)
    seq = list(outcomes)

    def fake_request(method, url, **kw):
        o = seq.pop(0)
        if isinstance(o, Exception):
            raise o
        return FakeResponse(o)

    monkeypatch.setattr(s.s, "request", fake_request)
    return s, sleeps


def test_session_returns_last_status_and_does_not_sleep_after_final_attempt(monkeypatch):
    s, sleeps = _session(monkeypatch, [503, 503, 429, 503])
    r = s.get("https://example.invalid/")
    assert r is not None and r.status_code == 503
    backoffs = [x for x in sleeps if x >= 20]
    assert backoffs == [20, 40, 80]  # no 160 s sleep after the 4th attempt
    assert (s.n_requests, s.n_errors, s.n_failed) == (4, 4, 1)


def test_session_recovers_and_passes_through_non_retry_statuses(monkeypatch):
    s, _ = _session(monkeypatch, [429, 200])
    assert s.get("u").status_code == 200 and s.n_failed == 0 and s.n_errors == 1
    s, _ = _session(monkeypatch, [404])
    assert s.get("u").status_code == 404 and s.n_errors == 0


def test_session_returns_none_when_every_attempt_raises(monkeypatch):
    s, sleeps = _session(monkeypatch, [requests.ConnectionError("x")] * 3, max_retries=3)
    assert s.get("u") is None
    assert (s.n_errors, s.n_failed) == (3, 1)
    assert [x for x in sleeps if x >= 5] == [5, 10]  # no sleep after the last attempt


# ------------------------------------------------------------------ LinkedIn sweep completion (L25)
def _cards(n: int, first: int) -> str:
    return "".join(f'<li><div data-entity-urn="urn:li:jobPosting:{first + i}"></div></li>' for i in range(n))


def _run_linkedin(linkedin, monkeypatch, raw, pages):
    fake = ScriptedSession([FakeResponse(200, _cards(n, 1000 * k)) for k, n in enumerate(pages)])
    monkeypatch.setattr(linkedin, "Session", lambda **kw: fake)
    monkeypatch.setattr(linkedin, "load_queries", lambda: {"linkedin_locations": ["Austria"], "linkedin_keywords": ["data"]})
    linkedin.main("2026-01-01")
    return fake, read(raw / "linkedin" / "2026-01-01" / "query_log.jsonl")


def test_linkedin_single_short_page_does_not_end_sweep(monkeypatch, raw, linkedin):
    fake, log = _run_linkedin(linkedin, monkeypatch, raw, [10, 7, 10, 0])
    assert len(fake.calls) == 4
    assert [e["complete"] for e in log] == [False, False, False, True]


def test_linkedin_two_consecutive_short_pages_end_sweep(monkeypatch, raw, linkedin):
    fake, log = _run_linkedin(linkedin, monkeypatch, raw, [10, 4, 2])
    assert len(fake.calls) == 3 and log[-1]["complete"] is True and log[-1]["truncated"] is False


def test_linkedin_resume_skips_completed_sweep(monkeypatch, raw, linkedin):
    _run_linkedin(linkedin, monkeypatch, raw, [3, 0])
    fake, _ = _run_linkedin(linkedin, monkeypatch, raw, [])
    assert fake.calls == []


# ------------------------------------------------------------------ karriere payload guard (L22)
def test_karriere_schema_change_is_logged_not_raised(monkeypatch, raw, karriere):
    payload = {"data": {"jobsSearchList": {"jobsListHeader": {"count": 5}, "activeItems": {}}}}  # items key missing
    fake = ScriptedSession([FakeResponse(200, payload=payload)])
    monkeypatch.setattr(karriere, "Session", lambda **kw: fake)
    monkeypatch.setattr(karriere, "load_queries", lambda: {"karriere_locations": ["Steiermark"], "title_keywords": ["data"]})
    karriere.main("2026-01-01")
    log = read(raw / "karriere" / "2026-01-01" / "query_log.jsonl")
    assert log[-1]["error"] == "schema"


def test_karriere_sweep_logs_pages_and_completion(monkeypatch, raw, karriere):
    def page(ids, more):
        return FakeResponse(200, payload={"data": {"jobsSearchList": {
            "jobsListHeader": {"count": 3}, "activeItems": {"items": [{"jobsItem": {"id": i}} for i in ids]},
            "loadMoreJobsButton": {"active": more}}}})
    fake = ScriptedSession([page([1, 2], True), page([3], False)])
    monkeypatch.setattr(karriere, "Session", lambda **kw: fake)
    monkeypatch.setattr(karriere, "load_queries", lambda: {"karriere_locations": ["Steiermark"], "title_keywords": ["data"]})
    karriere.main("2026-01-01")
    log = read(raw / "karriere" / "2026-01-01" / "query_log.jsonl")
    assert [(e["page"], e["returned"], e["complete"]) for e in log] == [(1, 2, False), (2, 1, True)]
    assert log[-1]["truncated"] is False


def test_eures_page_cap_is_logged_as_truncated(monkeypatch, raw, eures):
    monkeypatch.setattr(eures, "MAX_PAGES", 2)
    full = lambda k: FakeResponse(200, payload={"numberRecords": 999, "jvs": [{"id": f"{k}-{i}"} for i in range(eures.PAGE_SIZE)]})
    fake = ScriptedSession([full(1), full(2)])
    monkeypatch.setattr(eures, "Session", lambda **kw: fake)
    monkeypatch.setattr(eures, "load_queries", lambda: {"title_keywords": ["data"]})
    eures.main("2026-01-01")
    log = read(raw / "eures" / "2026-01-01" / "query_log.jsonl")
    assert log[-1]["complete"] is True and log[-1]["truncated"] is True


def test_eures_details_resume_keys_on_listing_id(monkeypatch, raw, eures):
    w = common.RawWriter("eures", "2026-01-01")
    w.write("listings", {"id": "A"}); w.write("listings", {"id": "B"})
    w.write("details", {"reference": "no top-level id"}, listing_id="A")
    w.close()
    fake = ScriptedSession([FakeResponse(200, payload={"id": "B"})])
    monkeypatch.setattr(eures, "Session", lambda **kw: fake)
    eures.details("2026-01-01")
    assert len(fake.calls) == 1 and "/jv/id/B" in fake.calls[0][0]


# ------------------------------------------------------------------ GitHub done-marking (M16, M17, L27, L29, L6)
class FakeGitHub:
    def __init__(self, table):
        self.table = table  # path -> (status, json) or a list of them (consumed in order), or an exception
        self.calls = []

    def get(self, path, params=None, kind="core"):
        self.calls.append((path, params))
        v = self.table[path]
        if isinstance(v, list):
            v = v.pop(0)
        if isinstance(v, BaseException):
            raise v
        return v[0], v[1], {}


def _users(out, logins):
    gh.append_jsonl(out / "users_search.jsonl", [{"login": l, "type": "User", "query": "q", "frame": "A", "page": 1} for l in logins])


def test_github_profiles_mark_done_only_on_200_or_definitive(tmp_path):
    _users(tmp_path, ["ok", "gone", "busy", "down"])
    c = FakeGitHub({"/users/ok": (200, {"login": "ok", "id": 1}), "/users/gone": (404, None),
                    "/users/busy": (403, None), "/users/down": (599, None)})
    gh.stage_profiles(c, tmp_path)
    prof = read(tmp_path / "profiles.jsonl")
    assert {r["login"] for r in prof} == {"ok", "gone"}
    assert {(r["key"], r["status"]) for r in read(tmp_path / "retry.jsonl")} == {("busy", 403), ("down", 599)}
    c2 = FakeGitHub({"/users/busy": (200, {"login": "busy", "id": 3}), "/users/down": (200, {"login": "down", "id": 4})})
    gh.stage_profiles(c2, tmp_path)
    assert sorted(p for p, _ in c2.calls) == ["/users/busy", "/users/down"]


def test_github_profiles_flush_buffer_on_exception(tmp_path):
    _users(tmp_path, ["a", "b", "c"])
    c = FakeGitHub({"/users/a": (200, {"login": "a", "id": 1}), "/users/b": (200, {"login": "b", "id": 2}),
                    "/users/c": KeyboardInterrupt()})
    with pytest.raises(KeyboardInterrupt):
        gh.stage_profiles(c, tmp_path)
    assert [r["login"] for r in read(tmp_path / "profiles.jsonl")] == ["a", "b"]


def test_github_repos_transient_failure_writes_nothing(tmp_path):
    gh.append_jsonl(tmp_path / "profiles.jsonl", [{"login": "u", "id": 1, "public_repos": 150}])
    page1 = [{"name": f"r{i}", "full_name": f"u/r{i}"} for i in range(100)]
    c = FakeGitHub({"/users/u/repos": [(200, page1), (502, None)]})
    gh.stage_repos(c, tmp_path)
    assert read(tmp_path / "repos.jsonl") == [] and read(tmp_path / "repos_done.jsonl") == []
    assert read(tmp_path / "retry.jsonl")[0]["stage"] == "repos"


def test_github_search_failure_writes_no_summary_and_retry_skips_stored_pages(tmp_path):
    items = [{"login": f"u{i}", "id": i, "type": "User"} for i in range(100)]
    c = FakeGitHub({"/search/users": [(200, {"total_count": 150, "items": items}), (599, None)]})
    assert gh._search_users(c, "q", "A", tmp_path) is False
    assert read(tmp_path / "search_summary.jsonl") == []
    assert len(read(tmp_path / "users_search.jsonl")) == 100
    c2 = FakeGitHub({"/search/users": [(200, {"total_count": 150, "items": items}), (200, {"total_count": 150, "items": items[:50]})]})
    assert gh._search_users(c2, "q", "A", tmp_path, have_pages={1}) is True
    assert len(read(tmp_path / "users_search.jsonl")) == 150  # page 1 not appended twice
    assert read(tmp_path / "search_summary.jsonl") == [{"query": "q", "frame": "A", "total_count": 150, "retrieved": 150}]


def test_frame_b_slices_derive_from_min_repos():
    assert gh.frame_b_slices(1) == ["repos:1..2", "repos:3..5", "repos:6..10", "repos:11..20", "repos:21..40", "repos:41..80", "repos:>=81"]
    assert gh.frame_b_slices(3) == ["repos:3..5", "repos:6..10", "repos:11..20", "repos:21..40", "repos:41..80", "repos:>=81"]
    assert gh.frame_b_slices(100) == ["repos:>=100"]


def test_frame_b_probe_failure_skips_token_instead_of_unsliced_query(tmp_path, monkeypatch):
    cfg = {"github_search": {"frame_a_tokens": [], "bio_keywords": [], "search_min_repos_frames_bc": 1,
                             "location_tokens_styria": ["Graz"], "base_rate_sample": {"tokens": [], "created_windows": [], "per_slice_cap": 10}}}
    monkeypatch.setattr(gh, "CFG", cfg)
    c = FakeGitHub({"/search/users": [(599, None)]})
    gh.stage_search(c, tmp_path)
    assert len(c.calls) == 1  # the probe only
    assert read(tmp_path / "retry.jsonl")[0]["stage"] == "search_probe"


def test_github_readme_decode_error_is_flagged(tmp_path):
    gh.append_jsonl(tmp_path / "repos.jsonl", [{"full_name": "u/r", "name": "r", "owner_login": "u", "language": "Jupyter Notebook", "default_branch": "main"}])
    c = FakeGitHub({"/repos/u/r/readme": (200, {"content": "abc", "name": "README.md", "size": 3}),
                    "/repos/u/r/git/trees/main": (200, {"tree": []})})
    gh.stage_readmes(c, tmp_path)
    row = read(tmp_path / "readmes.jsonl")[0]
    assert row["readme_decode_error"] is True and row["readme_text"] == ""


def test_github_token_missing_gh_cli_exits_with_message(monkeypatch):
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        monkeypatch.delenv(var, raising=False)

    def no_gh(*a, **kw):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(gh.subprocess, "run", no_gh)
    with pytest.raises(SystemExit) as e:
        gh.token()
    assert "gh" in str(e.value) and "GH_TOKEN" in str(e.value)
    monkeypatch.setenv("GH_TOKEN", " abc ")
    assert gh.token() == "abc"
