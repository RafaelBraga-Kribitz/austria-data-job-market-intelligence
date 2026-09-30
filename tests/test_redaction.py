"""Layer 2 redaction (src/pipeline/redact_supply_raw.py) on a synthetic tmp_path tree: source/date scoping, dry run, flags in
both formats, pseudonymised projects and raw files, persistence against rebuilds. Nothing under data/ is read or written.
Run: python -m pytest tests -q
"""
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

import build_supply as B
import redact_supply_raw as R

GH, LI = "2026-09-17", "2026-09-21"


def jl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def to_parquet(recs: list[dict], path: Path) -> None:
    df = pd.DataFrame(recs)
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, (list, dict))).any():
            df[col] = df[col].map(lambda v: json.dumps(v) if isinstance(v, (list, dict)) else v)
    df.to_parquet(path, index=False)


def digest(root: Path) -> dict:
    return {str(p.relative_to(root)): hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.fixture
def tree(tmp_path) -> Path:
    raw = tmp_path / "data" / "raw" / "github_supply" / GH
    jl(raw / "profiles.jsonl", [{"id": 1, "login": "anna-graz", "type": "User", "bio": "Data analyst at ACME", "blog": "https://anna.at",
                                 "company": "ACME", "location": "Graz", "twitter_username": "anna", "public_repos": 3}])
    jl(raw / "users_search.jsonl", [{"id": 1, "login": "anna-graz", "frame": "B", "query": "location:Graz"}])
    jl(raw / "repos.jsonl", [{"id": 10, "owner_login": "anna-graz", "full_name": "anna-graz/thesis", "name": "thesis",
                              "description": "My thesis", "homepage": "https://anna.at/thesis", "language": "Python", "fork": False}])
    jl(raw / "readmes.jsonl", [{"full_name": "anna-graz/thesis", "owner_login": "anna-graz", "readme_text": "# Anna's thesis",
                                "tree": [{"path": "anna_cv.pdf", "type": "blob"}]}])
    jl(raw / "social.jsonl", [{"login": "anna-graz", "accounts": [{"provider": "linkedin", "url": "https://linkedin.com/in/anna"}]}])
    jl(raw / "repos_done.jsonl", [{"login": "anna-graz", "n": 1}])
    jl(raw / "query_log.jsonl", [{"url": "https://api.github.com/users/anna-graz/repos?page=1"},
                                 {"url": "https://api.github.com/repos/anna-graz/thesis/readme"},
                                 {"url": "https://api.github.com/search/users?q=location%3AGraz"}])
    jl(raw / "search_summary.jsonl", [{"query": "location:Graz", "total_count": 1}])
    proc = tmp_path / "data" / "processed"
    cands = [{"candidate_id": "c1", "source": "github", "collection_date": GH, "login": "anna-graz", "bio": "Data analyst at ACME",
              "blog": "https://anna.at", "company": "ACME", "location_text": "Graz", "bio_role_family": "data_analytics", "frames": ["B"]},
             {"candidate_id": "c2", "source": "github", "collection_date": "2026-01-01", "login": "old", "bio": "old bio",
              "blog": None, "company": None, "location_text": "Wien", "bio_role_family": None, "frames": ["C"]},
             {"candidate_id": "l1", "source": "linkedin_manual", "collection_date": LI, "login": None, "bio": "Data Analyst",
              "blog": None, "company": None, "location_text": None, "bio_role_family": "data_analytics", "frames": ["L"]}]
    jl(proc / "supply_candidates.jsonl", cands); to_parquet(cands, proc / "supply_candidates.parquet")
    heads = ["introduction", "installation"]
    projs = [{"project_id": f"p{i}", "candidate_id": "c1" if i == 0 else "c2", "repo_full_name": f"anna-graz/thesis{i}", "name": "thesis",
              "description": "My thesis", "readme_heading_list": heads + (["anna's secret section"] if i == 0 else [])} for i in range(5)]
    jl(proc / "supply_projects.jsonl", projs); to_parquet(projs, proc / "supply_projects.parquet")
    (proc / "supply_build_manifest.json").write_text(json.dumps({"collection_date": GH}), encoding="utf-8")
    pd.DataFrame({"sample": ["T1"], "candidate_id": ["c1"], "bio": ["Data analyst at ACME"], "bio_role_family": ["data_analytics"]}).to_csv(
        proc / "supply_quality_bio_review_sample.csv", index=False)
    pd.DataFrame({"i": [0], "project_id": ["p0"], "name": ["thesis"], "description": ["My thesis"], "strict_correct": [1]}).to_csv(
        proc / "supply_quality_repo_precision_labels.csv", index=False)
    pd.DataFrame({"location_text": ["Graz"], "accounts": [1]}).to_csv(proc / "supply_quality_frameB_nonstyria_locations.csv", index=False)
    pd.DataFrame({"candidate_id": ["c1"], "skill": ["SQL"]}).to_parquet(proc / "supply_skill_evidence.parquet", index=False)
    li = tmp_path / "data" / "raw" / "linkedin_supply" / LI
    li.mkdir(parents=True)
    prof = pd.DataFrame({"pseudo_id": ["AT-0001"], "headline": ["Turning data into decisions"], "current_title": ["Data Analyst"],
                         "transition_wording": [""], "notes": ["k=5; pages=1-5; stratum=Data Analyst|Graz; rank=5; met her at a meetup"]})
    prof.to_csv(li / "profiles_manual.csv", index=False)
    prof.assign(collection_date=LI, source="linkedin_manual").to_csv(proc / "supply_linkedin_profiles.csv", index=False)
    (li / "state.json").write_text(json.dumps({"observer": "RB", "token": "t0k3n", "paste_field": "headline",
                                               "draft": {"headline": "half-typed headline", "current_title": ""},
                                               "last_error": "Ingest check failed", "last_message": "", "profiles_started": True}), encoding="utf-8")
    (li / "grid.csv").write_text("cell_id,notes\n0,block=A\n", encoding="utf-8")
    (li / "facets.json").write_text(json.dumps({"Graz|none": "https://www.linkedin.com/search/results/people/?keywords=x"}), encoding="utf-8")
    return tmp_path


def test_source_is_required(tree):
    with pytest.raises(SystemExit):
        R.main(["--date", GH], root=tree)


def test_dry_run_writes_nothing_and_lists_every_file(tree, capsys):
    before = digest(tree)
    assert R.main(["--source", "all", "--date", GH], root=tree) == 0
    assert R.main(["--source", "linkedin", "--date", LI], root=tree) == 0
    assert digest(tree) == before
    out = capsys.readouterr().out
    for name in ("profiles.jsonl", "users_search.jsonl", "repos.jsonl", "readmes.jsonl", "social.jsonl", "repos_done.jsonl", "query_log.jsonl",
                 "search_summary.jsonl", "supply_candidates.jsonl", "supply_candidates.parquet", "supply_projects.jsonl", "supply_projects.parquet",
                 "supply_quality_bio_review_sample.csv", "supply_quality_frameB_nonstyria_locations.csv", "state.json", "grid.csv", "REDACTED.json"):
        assert name in out, name
    assert "DRY RUN" in out and "cockpit draft: 1 filled field(s) of 2" in out


def test_linkedin_call_never_touches_github(tree):
    gh_files = {k: v for k, v in digest(tree).items() if "github_supply" in k or "supply_candidates" in k or "supply_projects" in k
                or "supply_quality" in k}
    assert R.main(["--source", "linkedin", "--date", LI, "--confirm"], root=tree) == 0
    after = digest(tree)
    assert {k: after.get(k) for k in gh_files} == gh_files
    li = tree / "data" / "raw" / "linkedin_supply" / LI
    prof = pd.read_csv(li / "profiles_manual.csv", dtype=str, keep_default_na=False)
    assert prof.loc[0, "headline"] == "[redacted]" and prof.loc[0, "transition_wording"] == ""
    assert prof.loc[0, "notes"] == "k=5; pages=1-5; stratum=Data Analyst|Graz; rank=5" and prof.loc[0, "current_title"] == "Data Analyst"
    proc = pd.read_csv(tree / "data" / "processed" / "supply_linkedin_profiles.csv", dtype=str, keep_default_na=False)
    assert proc.loc[0, "headline"] == "[redacted]"
    state = json.loads((li / "state.json").read_text(encoding="utf-8"))
    assert state["draft"] == {} and state["last_error"] == "" and state["token"] == "t0k3n" and state["observer"] == "RB"
    assert json.loads((li / "REDACTED.json").read_text(encoding="utf-8"))["status"] == "complete"


def test_github_confirm_redacts_scoped_rows_in_both_formats(tree):
    assert R.main(["--source", "github", "--date", GH, "--confirm"], root=tree) == 0
    proc = tree / "data" / "processed"
    c = {r["candidate_id"]: r for r in rows(proc / "supply_candidates.jsonl")}
    assert all(c["c1"][k] is None for k in R.PERSONAL_FIELDS) and c["c1"]["redacted"] is True and c["c1"]["has_blog"] is True
    assert c["c1"]["bio_role_family"] == "data_analytics"  # derived fields stay
    assert c["c2"]["bio"] == "old bio" and not c["c2"].get("redacted")  # other collection date untouched
    assert c["l1"]["bio"] == "Data Analyst" and not c["l1"].get("redacted")  # LinkedIn rows untouched
    pq = pd.read_parquet(proc / "supply_candidates.parquet").set_index("candidate_id")
    assert pq.loc["c1", "bio"] is None and bool(pq.loc["c1", "redacted"]) and not bool(pq.loc["c2", "redacted"]) and pq.loc["c2", "bio"] == "old bio"
    p = {r["project_id"]: r for r in rows(proc / "supply_projects.jsonl")}
    assert p["p0"]["repo_full_name"] == R.pseud("github_repo", "anna-graz/thesis0") and p["p0"]["name"] is None and p["p0"]["redacted"]
    assert p["p0"]["readme_heading_list"] == ["introduction", "installation"]  # rare heading dropped, common ones kept
    assert p["p1"]["name"] == "thesis"  # project of the other date's candidate untouched
    ppq = pd.read_parquet(proc / "supply_projects.parquet").set_index("project_id")
    assert ppq.loc["p0", "name"] is None and bool(ppq.loc["p0", "redacted"]) and json.loads(ppq.loc["p0", "readme_heading_list"]) == ["introduction", "installation"]
    assert pd.read_csv(proc / "supply_quality_bio_review_sample.csv", keep_default_na=False).loc[0, "bio"] == ""
    labels = pd.read_csv(proc / "supply_quality_repo_precision_labels.csv", keep_default_na=False)
    assert labels.loc[0, "name"] == "" and labels.loc[0, "strict_correct"] == 1
    assert not (proc / "supply_quality_frameB_nonstyria_locations.csv").exists()
    raw = tree / "data" / "raw" / "github_supply" / GH
    blob = "".join(p.read_text(encoding="utf-8") for p in raw.glob("*.jsonl"))
    for secret in ("anna-graz", "ACME", "Anna's thesis", "anna.at", "anna_cv.pdf", "linkedin.com/in/anna", "My thesis"):
        assert secret not in blob, secret
    assert rows(raw / "repos.jsonl")[0]["full_name"] == rows(raw / "readmes.jsonl")[0]["full_name"] == R.pseud("github_repo", "anna-graz/thesis")
    assert rows(raw / "profiles.jsonl")[0]["login"] == rows(raw / "users_search.jsonl")[0]["login"]  # joins survive
    assert rows(raw / "readmes.jsonl")[0]["tree_n"] == 1 and rows(raw / "social.jsonl")[0]["accounts"] == [{"provider": "linkedin"}]
    assert "location%3AGraz" in rows(raw / "query_log.jsonl")[2]["url"]  # search URLs carry no account
    assert json.loads((raw / "REDACTED.json").read_text(encoding="utf-8"))["status"] == "complete"
    assert (tree / "data" / "raw" / "linkedin_supply" / LI / "profiles_manual.csv").read_text(encoding="utf-8").count("Turning data") == 1


def test_second_confirm_run_changes_nothing(tree):
    assert R.main(["--source", "github", "--date", GH, "--confirm"], root=tree) == 0
    before = digest(tree)
    assert R.main(["--source", "github", "--date", GH, "--confirm"], root=tree) == 0
    assert digest(tree) == before


def test_rebuild_is_refused_after_redaction(tree):
    raw = tree / "data" / "raw" / "github_supply" / GH
    assert B.redaction_state(raw) is None
    R.main(["--source", "github", "--date", GH, "--confirm"], root=tree)
    assert "REDACTED.json" in B.redaction_state(raw)
    (raw / "REDACTED.json").unlink()  # the per-row README flags alone still block a rebuild
    readmes = {r["full_name"]: r for r in rows(raw / "readmes.jsonl")}
    assert "readme_redacted" in B.redaction_state(raw, readmes)


def test_linkedin_only_refresh_keeps_redacted_github_rows(tree):
    R.main(["--source", "github", "--date", GH, "--confirm"], root=tree)
    proc = tree / "data" / "processed"
    pd.DataFrame([{"pseudo_id": "AT-0009", "current_title": "Data Engineer", "location_text": "Wien", "collection_date": LI,
                   "source": "linkedin_manual", "source_quality": "C"}]).to_csv(proc / "supply_linkedin_profiles.csv", index=False)
    man = B.refresh_linkedin(proc)
    c = {r["candidate_id"]: r for r in rows(proc / "supply_candidates.jsonl")}
    assert c["c1"]["redacted"] is True and c["c1"]["bio"] is None
    assert "l1" not in c and man["n_candidates_linkedin_manual"] == 1
    li = [r for r in c.values() if r["source"] == "linkedin_manual"]
    assert li[0]["bio"] == "Data Engineer" and li[0]["state"] == "Wien"
