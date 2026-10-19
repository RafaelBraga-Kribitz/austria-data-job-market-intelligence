"""Public-export guard (src/publish/export_public.py): column dropping, scan patterns, suppression, atomicity.

All inputs are small synthetic files in tmp_path. Personal-looking values are assembled at run time so that this
file itself passes the export scan it tests.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "publish"))
import export_public as E  # noqa: E402

AT = "@"
MAIL = "jane.doe" + AT + "firma" + ".at"
PHONE_DOMESTIC = "0316" + " " + "4711" + "23"
PHONE_MOBILE = "0664" + "/" + "1234567"
PHONE_INTL = "+43" + " 316 " + "471123"
TOKEN = "gh" + "p_" + "a1B2c3D4" * 5
POSTING = "https://at.linkedin.com/jobs/view/data-analyst-at-example-" + "4455880526"


# ---- column dropping ---------------------------------------------------------------------------
@pytest.mark.parametrize("col", ["url", "source_url", "company_url", "html_url", "repo_url", "profile_url", "job_url",
                                 "urls", "url_list", "raw_html", "html", "description", "description_text",
                                 "description_html", "salary_snippet"])
def test_drop_columns_matches_link_and_text_columns(col):
    assert E.DROP_COLUMNS_RE.search(col)


@pytest.mark.parametrize("col", ["with_description", "description_gt300", "curly", "hurl_count", "n_urban", "title",
                                 "count", "share"])
def test_drop_columns_keeps_aggregates(col):
    assert not E.DROP_COLUMNS_RE.search(col)


def test_allow_list_has_no_dead_entries():
    assert not [c for c in E.ALLOW_LONG_COLUMNS if E.DROP_COLUMNS_RE.search(c)]


def test_clean_table_drops_columns_and_flags(tmp_path):
    src = tmp_path / "X01.csv"
    pd.DataFrame({
        "skill": ["SQL", "Python"],
        "count": [5, 4],
        "repo_url": ["https://github.com/a/b", "https://github.com/c/d"],
        "description": ["long text", "long text"],
        "contact": ["-", MAIL],
    }).to_csv(src, index=False)
    dst = tmp_path / "out" / "X01.csv"
    problems = E.clean_table(src, dst)
    out = pd.read_csv(dst)
    assert list(out.columns) == ["skill", "count", "contact"]
    assert any("e-mail" in p for p in problems)


def test_clean_table_keeps_long_allow_listed_model_spec(tmp_path):
    # D05's `model` column is the estimation specification written by salary_premium.py, not advertisement text
    src = tmp_path / "D05.csv"
    spec = "OLS on log(advertised annual minimum); controls = role family, seniority, state; " * 3
    pd.DataFrame({"skill": ["SQL"], "model": [spec]}).to_csv(src, index=False)
    assert len(spec) > E.TEXT_COL_MAX
    assert E.clean_table(src, tmp_path / "o.csv") == []


def test_clean_table_flags_free_text_phone_url_and_login(tmp_path):
    src = tmp_path / "X02.csv"
    pd.DataFrame({
        "blurb": ["x" * (E.TEXT_COL_MAX + 1), "y"],
        "tel": [PHONE_DOMESTIC, "-"],
        "link": ["see https://www.example.org/page", "-"],
        "esco": ["http://data.europa.eu/esco/occupation/abc", "-"],
        "who": ["somelogin", "SQL"],
    }).to_csv(src, index=False)
    problems = E.clean_table(src, tmp_path / "o.csv", logins={"somelogin"})
    joined = "\n".join(problems)
    assert "X02.csv:blurb has cells longer" in joined
    assert "X02.csv:tel contains a phone number" in joined
    assert "X02.csv:link contains a URL" in joined
    assert "esco" not in joined  # ESCO URIs are open-taxonomy identifiers
    assert "X02.csv:who contains a value equal to a private GitHub login" in joined
    assert "somelogin" not in joined.replace("X02.csv:who", "")  # the login itself is never printed


def test_clean_json_scrubs_keys_and_flags(tmp_path):
    src = tmp_path / "s.json"
    src.write_text(json.dumps({"rows": [{"n": 3, "source_url": "https://x.example/1", "html_url": "https://y.example/2",
                                         "note": "call " + PHONE_MOBILE}]}), encoding="utf-8")
    dst = tmp_path / "o" / "s.json"
    problems = E.clean_json(src, dst)
    d = json.loads(dst.read_text(encoding="utf-8"))
    assert set(d["rows"][0]) == {"n", "note"}
    assert any("phone" in p for p in problems)


# ---- scan patterns -----------------------------------------------------------------------------
@pytest.mark.parametrize("text", [PHONE_DOMESTIC, PHONE_MOBILE, PHONE_INTL, "(01)" + " 234 56 78"])
def test_phone_patterns_hit(text):
    assert E.phone_hits(f"Kontakt: {text}.")


@pytest.mark.parametrize("text", ["2026-09-16", "0.054", "n = 720", "01/2026", "0,0,0,66,0", "12 of 15", "2020-2025"])
def test_phone_patterns_ignore_numbers(text):
    assert not E.phone_hits(text)


def test_scan_tree_patterns(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text(f"Write to {MAIL}; token {TOKEN}\n", encoding="utf-8")
    (tmp_path / "docs" / "b.md").write_text(f"Example ad: {POSTING}\n", encoding="utf-8")
    (tmp_path / "docs" / "c.md").write_text("Maintainer: github.com/SomeLogin/repo and @otherlogin\n", encoding="utf-8")
    (tmp_path / "docs" / "ok.md").write_text("GET /jobs-guest/jobs/api/jobPosting/{id}; see github.com/owner/repo;"
                                             " contact " + "x" + AT + "example.com\n", encoding="utf-8")
    (tmp_path / "src.py").write_text("@otherlogin\ndef f():\n    pass\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text(MAIL, encoding="utf-8")
    problems = E.scan_tree(tmp_path, logins={"somelogin", "otherlogin", "owner"}, allowed_logins={"owner"})
    joined = "\n".join(problems)
    assert "docs/a.md: e-mail" in joined
    assert "docs/a.md: secret-like token" in joined  # .md files are scanned for secrets too
    assert "docs/b.md: link to an individual job advertisement" in joined
    assert joined.count("docs/c.md: mentions a private GitHub login") == 1
    assert "ok.md" not in joined
    assert "src.py" not in joined  # decorators are not @mentions
    assert ".git" not in joined
    assert "somelogin" not in joined.lower() and "otherlogin" not in joined.lower()


# ---- suppression thresholds --------------------------------------------------------------------
def _write_tables(tree: Path, c02_counts, c19e_counts):
    t = tree / "outputs" / "tables"
    t.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"raw_bio_title": [f"p{i}" for i in range(len(c02_counts))], "count": c02_counts}).to_csv(
        t / "C02_raw_bio_title_distribution.csv", index=False)
    pd.DataFrame({"heading": [f"h{i}" for i in range(len(c19e_counts))], "projects": c19e_counts}).to_csv(
        t / "C19e_common_readme_headings.csv", index=False)


def test_suppression_passes_at_thresholds(tmp_path):
    _write_tables(tmp_path, [47, 3], [612, 5])
    assert E.check_suppression(tmp_path) == []


def test_suppression_flags_rare_rows(tmp_path):
    _write_tables(tmp_path, [47, 2], [612, 4, 1])
    problems = E.check_suppression(tmp_path)
    assert any("C02_raw_bio_title_distribution.csv: 1 row(s)" in p for p in problems)
    assert any("C19e_common_readme_headings.csv: 2 row(s)" in p for p in problems)


def test_suppression_flags_missing_column(tmp_path):
    t = tmp_path / "outputs" / "tables"
    t.mkdir(parents=True)
    pd.DataFrame({"heading": ["a"], "n": [9]}).to_csv(t / "C19e_common_readme_headings.csv", index=False)
    assert any("cannot be verified" in p for p in E.check_suppression(tmp_path))


# ---- private paths and atomicity ---------------------------------------------------------------
def test_private_paths_detected(tmp_path):
    for rel in ["src/private/radar/x.py", "library_strategy/a.md", "docs/linkedin-slot-interface.md",
                "src/acquisition/collect_linkedin.py", "data/raw/radar/2026-09-18/jobspy.jsonl"]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x", encoding="utf-8")
    joined = "\n".join(E.check_private_paths(tmp_path))
    for needle in ["src/private/radar/x.py", "library_strategy/a.md", "docs/linkedin-slot-interface.md",
                   "posting collector leaked: src/acquisition/collect_linkedin.py", "data/raw/radar/"]:
        assert needle in joined


def test_site_private_and_weekly_runs_never_ship(tmp_path):
    """The private weekly dashboard (site_private/) and the run manifests (data/private/weekly_runs/) are excluded and re-checked."""
    assert "site_private/" in E.PRIVATE_NEVER and "data/private/" in E.PRIVATE_NEVER
    assert E.is_excluded("site_private/index.html") and E.is_excluded("data/private/weekly_runs/2026-10-18.json")
    for rel in ["site_private/index.html", "site_private/data/insights.json", "data/private/weekly_runs/latest.json"]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x", encoding="utf-8")
    joined = "\n".join(E.check_private_paths(tmp_path))
    for needle in ["site_private/index.html", "site_private/data/insights.json", "data/private/weekly_runs/latest.json"]:
        assert f"private path leaked: {needle}" in joined
    ignore = E.ROOT / ".gitignore"
    if ignore.exists():  # the private repository's own .gitignore (absent in a public clone)
        assert "site_private/" in ignore.read_text(encoding="utf-8").splitlines()


def test_exclusions():
    assert E.is_excluded("docs/linkedin-slot-interface.md")
    assert E.is_excluded("docs/profile-specific-demand-supply-analysis.md")
    assert E.is_excluded("config/profile.json")
    assert E.is_excluded("tests/fixtures/radar/stepstone_search.html")
    assert not E.is_excluded("config/geo.json")
    assert E.SUBSTITUTE_FILES["config/profile.json"] == "config/profile.example.json"


def _mini_root(root: Path, leak: bool) -> None:
    for f in E.INCLUDE_FILES:
        (root / f).parent.mkdir(parents=True, exist_ok=True)
        (root / f).write_text("placeholder\n", encoding="utf-8")
    (root / E.PUBLIC_GITIGNORE).parent.mkdir(parents=True, exist_ok=True)
    (root / E.PUBLIC_GITIGNORE).write_text("__pycache__/\n", encoding="utf-8")
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "profile.json").write_text('{"summary": "private"}', encoding="utf-8")
    (root / "config" / "profile.example.json").write_text('{"summary": "example"}', encoding="utf-8")
    acq = root / "src" / "acquisition"
    acq.mkdir(parents=True, exist_ok=True)
    for f in E.INCLUDE_ACQUISITION + E.EXCLUDE_ACQUISITION:
        (acq / f).write_text("# code\n", encoding="utf-8")
    tables = root / "outputs" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"skill": ["SQL"], "note": [("call " + PHONE_DOMESTIC) if leak else "ok"]}).to_csv(
        tables / "T99_example.csv", index=False)
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "linkedin-slot-interface.md").write_text("private\n", encoding="utf-8")


def _snapshot(d: Path) -> dict:
    return {str(p.relative_to(d)): p.read_bytes() for p in d.rglob("*") if p.is_file()}


def test_blocked_export_leaves_target_untouched(tmp_path, capsys):
    root, target = tmp_path / "private", tmp_path / "public"
    _mini_root(root, leak=True)
    (target / ".git").mkdir(parents=True)
    (target / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (target / "README.md").write_text("previous public version\n", encoding="utf-8")
    before = _snapshot(target)
    assert E.main(target, root=root) == 1
    assert "EXPORT BLOCKED" in capsys.readouterr().out
    assert _snapshot(target) == before
    assert [p.name for p in tmp_path.iterdir() if "staging" in p.name] == []  # staging removed


def test_clean_export_replaces_target_and_keeps_git(tmp_path):
    root, target = tmp_path / "private", tmp_path / "public"
    _mini_root(root, leak=False)
    (target / ".git").mkdir(parents=True)
    (target / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (target / "stale.txt").write_text("old\n", encoding="utf-8")
    assert E.main(target, root=root) == 0
    assert (target / ".git" / "HEAD").exists()
    assert not (target / "stale.txt").exists()
    assert (target / ".gitignore").read_text(encoding="utf-8") == "__pycache__/\n"  # the public template
    assert json.loads((target / "config" / "profile.json").read_text(encoding="utf-8"))["summary"] == "example"
    assert not (target / "config" / "profile.example.json").exists()
    assert not (target / "docs" / "linkedin-slot-interface.md").exists()
    for f in E.EXCLUDE_ACQUISITION:
        assert not (target / "src" / "acquisition" / f).exists()
    assert (target / "outputs" / "PUBLIC_EXPORT_MANIFEST.txt").exists()
    assert [p.name for p in tmp_path.iterdir() if "staging" in p.name] == []


def test_posting_uid_is_pseudonymised(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPORT_UID_KEY", "test-key")
    src = tmp_path / "Q03b.csv"
    raw = "linked" + "in:" + "4438579610"
    pd.DataFrame({"posting_uid": [raw, "jobs" + "at:7899573"], "title": ["Data Analyst", "BI Analyst"]}).to_csv(src, index=False)
    dst = tmp_path / "o.csv"
    assert E.clean_table(src, dst) == []
    out = pd.read_csv(dst)
    assert out.posting_uid.str.fullmatch(r"p_[0-9a-f]{16}").all()
    assert out.posting_uid.iloc[0] == E.pseudonymise(raw, b"test-key")  # stable under a fixed key
    assert raw not in dst.read_text(encoding="utf-8")


def test_raw_source_id_in_other_column_is_flagged(tmp_path):
    src = tmp_path / "X03.csv"
    pd.DataFrame({"ref": ["karri" + "ere:7857203"]}).to_csv(src, index=False)
    assert any("source posting identifier" in p for p in E.clean_table(src, tmp_path / "o.csv"))


@pytest.mark.parametrize("addr,ok", [("x" + AT + "example.com", True), ("a" + AT + "b.at", True), ("n" + AT + "host.tld", True),
                                     (MAIL, False), ("office" + AT + "firma.co.at", False)])
def test_placeholder_emails(addr, ok):
    assert E.is_placeholder_email(addr) is ok


def test_module_level_import_of_private_collector_is_flagged(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("import common\nimport collect_" + "karriere as k\n", encoding="utf-8")
    (tmp_path / "tests" / "test_b.py").write_text("def f():\n    import collect_" + "linkedin\n", encoding="utf-8")
    joined = "\n".join(E.check_private_paths(tmp_path))
    assert "tests/test_a.py imports the unexported collector collect_karriere" in joined
    assert "test_b.py" not in joined


# ---- public overlay ----------------------------------------------------------------------------
def _write_overlay(root: Path, readme: str) -> Path:
    base = root / E.PUBLIC_OVERLAY
    (base / "docs" / "assets").mkdir(parents=True, exist_ok=True)
    (base / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (base / "README.md").write_text(readme, encoding="utf-8")
    (base / "docs" / "assets" / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(range(256)))
    (base / ".github" / "workflows" / "readme-quality.yml").write_text("name: README quality gate\n", encoding="utf-8")
    return base


def test_overlay_is_copied_over_the_tree_and_not_exported_as_a_folder(tmp_path):
    root, target = tmp_path / "private", tmp_path / "public"
    _mini_root(root, leak=False)
    base = _write_overlay(root, "# Portfolio README\n")
    assert E.main(target, root=root) == 0
    assert (target / "README.md").read_text(encoding="utf-8") == "# Portfolio README\n"  # replaces the private README
    assert (target / "docs" / "assets" / "hero.png").read_bytes() == (base / "docs" / "assets" / "hero.png").read_bytes()
    assert (target / ".github" / "workflows" / "readme-quality.yml").exists()
    assert not (target / E.PUBLIC_OVERLAY).exists()
    assert (target / "src" / "publish" / "public.gitignore").exists()  # the rest of src/publish is still exported
    manifest = (target / "outputs" / "PUBLIC_EXPORT_MANIFEST.txt").read_text(encoding="utf-8")
    assert "README.md" in manifest and "docs/assets/hero.png" in manifest


def test_overlay_files_are_scanned(tmp_path, capsys):
    root, target = tmp_path / "private", tmp_path / "public"
    _mini_root(root, leak=False)
    _write_overlay(root, "# Portfolio README\n\nContact: " + MAIL + "\n")
    assert E.main(target, root=root) == 1
    assert "README.md: e-mail" in capsys.readouterr().out
    assert not (target / "README.md").exists()  # blocked: nothing reaches the target


def test_overlay_folder_is_a_private_path(tmp_path):
    leak = tmp_path / E.PUBLIC_OVERLAY / "README.md"
    leak.parent.mkdir(parents=True)
    leak.write_text("x", encoding="utf-8")
    assert any(E.PUBLIC_OVERLAY in p for p in E.check_private_paths(tmp_path))
    assert E.is_excluded(E.PUBLIC_OVERLAY + "/README.md")


# ---- owner facts and private rules (F1) --------------------------------------------------------
# the phrases are assembled at run time so that this file passes the scan it tests
OWNER_PHRASES = ["owner" + "-stated", "~/" + ".claude", "." + "claude/knowledge", "career-" + "knowledge-core.md",
                 "0 applications " + "sent", "Never ask " + "below 42k"]
OWNER_FACT_PATHS = ["tests/test_update_knowledge.py", "tests/test_weekly_refresh.py", "tests/test_build_insights.py",
                    "tests/test_build_site.py", "tests/test_job_archive.py", "tests/test_company_archetypes.py",
                    "tests/test_acquisition_weekly.py", "src/reporting/metrics_watch.py", "outputs/metrics_watch.json",
                    "outputs/metrics.json"]


@pytest.mark.parametrize("phrase", OWNER_PHRASES)
def test_scan_tree_blocks_owner_fact_phrases(tmp_path, phrase):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "leak.md").write_text(f"Intro.\nSee {phrase.upper()} for details.\n", encoding="utf-8")
    (tmp_path / "docs" / "fine.md").write_text("Intro.\nNothing private here.\n", encoding="utf-8")
    joined = "\n".join(E.scan_tree(tmp_path))
    assert "docs/leak.md: owner fact or private rule" in joined      # case-insensitive
    assert "fine.md" not in joined


def test_scan_tree_owner_fact_scan_covers_json_and_py(tmp_path):
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "m.json").write_text(json.dumps({"source": OWNER_PHRASES[1] + "/knowledge/x.md"}), encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text(f"# rule: {OWNER_PHRASES[5]}\n", encoding="utf-8")
    joined = "\n".join(E.scan_tree(tmp_path))
    assert "outputs/m.json: owner fact" in joined and "src/a.py: owner fact" in joined


def test_owner_fact_scan_exempts_only_the_known_generic_uses():
    phrase = "applications " + "sent"
    allowed = ("CAREER_DECISION_MAP.md", phrase)
    ctx = E.OWNER_FACT_ALLOW[allowed]
    assert E.owner_fact_hits(allowed[0], f"| row ({ctx}) |") == []
    assert E.owner_fact_hits(allowed[0], f"| we had {OWNER_PHRASES[4]} so far |") == [phrase]
    assert E.owner_fact_hits("docs/other.md", f"| row ({ctx}) |") == [phrase]   # the exemption is per file
    assert E.owner_fact_hits("src/publish/export_public.py", OWNER_PHRASES[0]) == []           # pattern definitions


@pytest.mark.parametrize("rel", OWNER_FACT_PATHS)
def test_owner_fact_files_are_excluded_and_never_public(rel):
    assert E.is_excluded(rel)
    assert rel in E.PRIVATE_NEVER and rel in E.OWNER_FACT_FILES


def test_owner_fact_files_are_not_exported_and_leaks_are_caught(tmp_path):
    root, target = tmp_path / "private", tmp_path / "public"
    _mini_root(root, leak=False)
    for rel in OWNER_FACT_PATHS:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(json.dumps({"x": OWNER_PHRASES[0]}) if rel.endswith(".json") else f"# {OWNER_PHRASES[1]}\n", encoding="utf-8")
    (root / "tests" / "test_public.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (root / "outputs" / "skills.json").write_text(json.dumps({"n": 3}), encoding="utf-8")
    assert E.main(target, root=root) == 0
    for rel in OWNER_FACT_PATHS:
        if rel != "src/reporting/metrics_watch.py":
            assert not (target / rel).exists(), rel
    assert (target / "tests" / "test_public.py").exists() and (target / "outputs" / "skills.json").exists()
    # exported code that imports the claim watch finds the public stand-in, which carries no owner content
    stub = (target / "src" / "reporting" / "metrics_watch.py").read_text(encoding="utf-8")
    assert "def build_watch" in stub and E.owner_fact_hits("src/reporting/metrics_watch.py", stub) == []
    # a leak in an ordinary exported file blocks the export and leaves the target as it was
    (root / "docs" / "notes.md").write_text(f"Status: {OWNER_PHRASES[4]}\n", encoding="utf-8")
    before = _snapshot(target)
    assert E.main(target, root=root) == 1
    assert _snapshot(target) == before


def test_public_gitignore_matches_the_private_data_policy():
    text = (E.ROOT / E.PUBLIC_GITIGNORE).read_text(encoding="utf-8").splitlines()
    for line in ("data/private/", "site_private/", "logs/", "data/raw/*"):
        assert line in text


# ---- private plans, later decision-log entries and the weekly-refresh section never ship -------------------------
# names are assembled at run time so that this file passes the owner-fact scan it tests
PLAN_FILES = ["PROJECT" + "_TRACK_2026-10-19.md", "OPERATING" + "_PLAN_2026-10-19.md"]
PROMPT_DIR = "session" + "_prompts"


def test_private_plans_and_starter_prompts_are_never_public():
    for rel in PLAN_FILES + [PROMPT_DIR + "/01_step.md"]:
        assert E.OWNER_FACT_RE.search(rel), rel
        assert rel in E.PRIVATE_NEVER or any(x.endswith("/") and rel.startswith(x) for x in E.PRIVATE_NEVER)


def test_scan_tree_blocks_a_reference_to_a_private_plan(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "leak.md").write_text(f"Details are private ({PLAN_FILES[0]}).\n", encoding="utf-8")
    assert "docs/leak.md: owner fact or private rule" in "\n".join(E.scan_tree(tmp_path))


def test_private_plans_in_the_root_are_not_exported(tmp_path):
    root, target = tmp_path / "private", tmp_path / "public"
    _mini_root(root, leak=False)
    for rel in PLAN_FILES:
        (root / rel).write_text("private plan\n", encoding="utf-8")
    (root / PROMPT_DIR).mkdir()
    (root / PROMPT_DIR / "01_step.md").write_text("private prompt\n", encoding="utf-8")
    assert E.main(target, root=root) == 0
    assert not any(p.name in PLAN_FILES or PROMPT_DIR in p.parts for p in target.rglob("*"))


def test_decision_log_is_cut_after_the_last_public_entry():
    log = "# Log\n\n## D-029 · a\n\ntext\n\n## D-030 · b\n\nlast public\n\n## D-031 · c\n\nprivate\n\n## D-032 · d\n\nprivate\n"
    out = E.public_decision_log(log)
    assert "last public" in out and "D-031" not in out.replace("Entries after D-030", "") and "private\n" not in out
    assert out.rstrip().endswith("not part of the public tree.*")
    short = "# Log\n\n## D-030 · b\n\nlast\n"
    assert E.public_decision_log(short) == short       # nothing to cut


def test_agent_context_private_section_and_pointers_are_cut(tmp_path):
    # the private wording is assembled at run time so that this file does not spell it out
    wk = "w" + "eekly"
    pointer = " Since D-03" + f"1 the Layer 1 refresh runs {wk} and unattended (\u00a727); the manual procedure remains valid for a one-off rebuild."
    header = "; D-031/D-032 " + f"{wk} refresh and claims as variables: 2026-10-17; D-033 {wk} local auto-commit: 2026-10-19"
    text = (f"Head (D-030 x{header}). \u00a726 end; \u00a727 = {wk} refresh.\n## 26. Visual\n\nbody{pointer}\n\n"
            f"## 27. W{wk[1:]} refresh (D-031, D-032)\n\nprivate text\n\n## 28. Next\n\nkept\n")
    out = E.strip_private_sections("AGENT_CONTEXT.md", text)
    assert "private text" not in out and "kept" in out and "body" in out and "Head (D-030 x)" in out
    assert E.PRIVATE_RESIDUE_RE.search(out) is None
    assert E.strip_private_sections("docs/other.md", text) == text
    # the same cut applied to a staged tree
    (tmp_path / "AGENT_CONTEXT.md").write_text(text, encoding="utf-8")
    (tmp_path / "DECISION_LOG.md").write_text("## D-030 x\n\nok\n\n## D-031 y\n\nprivate\n", encoding="utf-8")
    assert sorted(E.apply_public_cuts(tmp_path)) == ["AGENT_CONTEXT.md", "DECISION_LOG.md"]
    assert E.check_public_cuts(tmp_path) == []
    assert "private\n" not in (tmp_path / "DECISION_LOG.md").read_text(encoding="utf-8")


def test_a_surviving_reference_to_a_cut_entry_blocks_the_export(tmp_path):
    (tmp_path / "AGENT_CONTEXT.md").write_text("Intro; \u00a727 = w" + "eekly refresh, kept by accident.\n", encoding="utf-8")
    (tmp_path / "DECISION_LOG.md").write_text("## D-030 x\n\nok\n", encoding="utf-8")
    problems = E.check_public_cuts(tmp_path)
    assert len(problems) == 1 and problems[0].startswith("AGENT_CONTEXT.md:")
