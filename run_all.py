"""Single cross-platform entry point for the reproduction order (README "Reproduction", docs/methodology.md §9).

    python run_all.py --list                     targets, steps, inputs, one-off tools
    python run_all.py all                        layer1 -> layer2 -> layer3 -> visual -> digest -> tests
    python run_all.py layer1                     any single target: layer1 layer2 layer3 visual digest tests
    python run_all.py all --from demand_supply   resume: skip the steps before demand_supply
    python run_all.py all --dry-run              preflight + the exact commands, nothing is run
    python run_all.py collect                    PRINT the collection commands (network; never run from here)
    python run_all.py tools                      PRINT the one-off tools (redaction, precision audit, publication)

Every step runs as a subprocess of the same interpreter from the repository root, in the order below, and the run stops
at the first failing step. Before anything runs, a preflight checks the external inputs of every selected step (private
raw data, hand-maintained tables) so a missing folder fails in a second, not after twenty minutes. Optional steps whose
private inputs are absent (supplement_radar without the hunter DB, official_supply without the Stack Overflow extract)
are skipped with a loud notice; their previously published outputs stay as they are.

Output: console + logs/run_<timestamp>.log (logs/ is gitignored) and outputs/run_manifest.json (tracked): Python
version, platform, installed versions of every requirement, git commit (and whether the tree was dirty), run date,
target, and every step with its status and duration. The manifest is written for any run that executed a step that
writes outputs, including a failed one (its status says where it stopped).

Collection is not part of `all`: collectors hit the network, are dark/private where the source terms require it
(DECISION_LOG D-013/D-022), and are not bit-reproducible. `collect` prints them in order with their prerequisites.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata as md
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
MANIFEST = ROOT / "outputs" / "run_manifest.json"
TARGETS = ("layer1", "layer2", "layer3", "visual", "digest", "tests")
L1_RAW = ["data/raw/eures", "data/raw/karriere", "data/raw/linkedin", "data/raw/willhaben", "data/raw/jobsat"]


@dataclass
class Step:
    name: str
    target: str
    script: str                                      # path relative to ROOT, or "-m" for a module call
    args: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)       # external inputs that must all exist (not made by earlier steps)
    requires_any: list[str] = field(default_factory=list)   # at least one must exist
    optional: bool = False                           # missing inputs -> skip with a notice instead of failing the run
    if_script_exists: bool = False                   # planned step: included only when its script is present
    writes_outputs: bool = True
    note: str = ""

    def command(self) -> list[str]:
        if self.script == "-m":
            return [sys.executable, "-m", *self.args]
        return [sys.executable, self.script, *self.args]

    def display(self) -> str:
        return " ".join(["python", *self.command()[1:]])


# The global order is the README order; a target selects a subset and never changes the order.
STEPS: list[Step] = [
    # ---------------- Layer 1: employer demand (needs the private raw collection of 2026-09-16)
    Step("build_interim", "layer1", "src/pipeline/build_interim.py", requires=L1_RAW,
         note="unify the five posting sources; newest dated folder per source"),
    Step("normalize", "layer1", "src/pipeline/normalize.py", note="rule-based features from config/*.json"),
    Step("dedupe", "layer1", "src/pipeline/dedupe.py", note="union-find duplicate groups, canonical row per group"),
    Step("redact_layer1_contacts", "layer1", "src/pipeline/redact_layer1_contacts.py", args=["--confirm"], if_script_exists=True,
         note="remove e-mail addresses / phone numbers from the processed postings right after dedupe (skipped if the script is absent)"),
    Step("run_analysis", "layer1", "src/analysis/run_analysis.py", note="T01-T14, T17, market_summary.json"),
    Step("cluster_requirements", "layer1", "src/analysis/cluster_requirements.py", note="T15, clusters.json"),
    Step("data_quality", "layer1", "src/analysis/data_quality.py", note="Q01-Q09, data_quality.json"),
    Step("jobbarometer_analysis", "layer1", "src/analysis/jobbarometer_analysis.py", requires=["data/raw/jobbarometer"],
         note="JB01-JB05 (make_figures reads JB01)"),
    Step("adjacent_demand", "layer1", "src/analysis/adjacent_demand.py", requires=["data/raw/eures_textsearch"],
         note="T16 (made by collect_eures_styria_text.py)"),
    Step("build_decision_matrix", "layer1", "src/analysis/build_decision_matrix.py", note="D01-D04b from T tables + config/profile.json"),
    Step("make_figures", "layer1", "src/analysis/make_figures.py", note="F01-F14 png"),
    Step("export_agent_json", "layer1", "src/analysis/export_agent_json.py", note="skills/roles/locations/languages/salaries.json"),
    Step("seasonality", "layer1", "src/analysis/seasonality.py", requires=["data/raw/eurostat_jvs"], note="S01-S06, seasonality.json (F13 retired: BQ03 answers it)"),
    Step("salary_premium", "layer1", "src/analysis/salary_premium.py", note="D05 (needs the private per-posting file)"),
    Step("supplement_radar", "layer1", "src/analysis/supplement_radar.py", optional=True,
         requires_any=["src/private/radar/jobs.db", "jobs.db"],
         note="T19 dated supplement; needs the private hunter DB (python src/private/radar/job_radar.py)"),
    # ---------------- Layer 2: observed candidate supply (needs the private GitHub collection)
    Step("build_supply", "layer2", "src/pipeline/build_supply.py", requires=["data/raw/github_supply"],
         note="candidate / project / skill-evidence tables (private)"),
    Step("official_supply", "layer2", "src/analysis/official_supply.py", optional=True,
         requires=["data/external/stackoverflow_survey", "data/raw/eurostat_supply"],
         note="O01-O08, supply_official.json; needs the private Stack Overflow extract"),
    Step("supply_analysis", "layer2", "src/analysis/supply_analysis.py", note="C01-C13, C22, C23, supply_*.json"),
    Step("project_analysis", "layer2", "src/analysis/project_analysis.py", note="C14-C21, C24"),
    # ---------------- Layer 3: demand x supply
    Step("demand_supply", "layer3", "src/analysis/demand_supply.py",
         note="DS01-DS13; reads supply_official.json, C23 and the Layer 1 T tables"),
    Step("supply_quality", "layer2", "src/analysis/supply_quality.py", note="SQ01-SQ11 (README order: after demand_supply)"),
    Step("supply_figures", "layer3", "src/analysis/supply_figures.py", note="SF01, SF02, SF05-SF16, DSF01-DSF08 from C/DS/O tables"),
    Step("export_supply_json", "layer3", "src/analysis/export_supply_json.py",
         note="project_evidence_map.json, operational_career_context.json"),
    # ---------------- visual decision layer
    Step("make_visual_layer", "visual", "src/analysis/make_visual_layer.py",
         requires=["outputs/tables/S06_season_vs_cycle.csv", "outputs/tables/Q03c_precision_summary.csv"],
         note="BQ01-BQ45 + visual_questions.json + FIGURE-MANIFEST.yaml; S06 comes from seasonality, Q03c from precision_audit"),
    Step("embed_figures", "visual", "src/analysis/embed_figures.py", note="attach each BQ figure to the passage it answers"),
    # ---------------- validation
    Step("digest", "digest", "src/reporting/digest.py", args=["--strict"],
         requires=["outputs/tables/S06_season_vs_cycle.csv", "outputs/tables/SQ10_bio_classification_precision.csv",
                   "outputs/tables/SQ11_project_classification_precision.csv"],
         note="outputs/reports/digest.txt (S06 from seasonality, SQ10/SQ11 from supply_quality)"),
    Step("pytest", "tests", "-m", args=["pytest", "tests", "-q"], writes_outputs=False, note="unit + integrity + value checks"),
]

COLLECT = """\
Collection commands (NOT run by run_all.py: network access, private/dark collectors, not bit-reproducible).
Read DECISION_LOG D-013/D-022 first; a new collection goes into a new dated folder and is never merged with an older one.

Layer 1 posting collectors (private, gitignored raw; D-022: only when the owner asks):
  python src/acquisition/collect_eures.py && python src/acquisition/collect_eures.py details
  python src/acquisition/collect_karriere.py && python src/acquisition/collect_karriere.py details
  python src/acquisition/collect_linkedin.py && python src/acquisition/collect_linkedin.py details
  python src/acquisition/collect_willhaben.py && python src/acquisition/collect_willhaben.py details
  python src/acquisition/collect_jobsat.py && python src/acquisition/collect_jobsat.py details
  python src/acquisition/collect_eures_styria_text.py       # data/raw/eures_textsearch, input of adjacent_demand (T16)
Layer 1 official / public series:
  python src/acquisition/collect_jobbarometer.py            # AMS JobBarometer (JB tables)
  python src/acquisition/collect_eurostat_jvs.py            # Eurostat JVS (seasonality)
Dated supplement (never merged into the 2026-09-16 snapshot):
  python src/acquisition/collect_arbeitnow.py
  python src/private/radar/job_radar.py                     # private hunter (gitignored) -> src/private/radar/jobs.db
Layer 2:
  python src/acquisition/collect_github_supply.py all       # ~5-7 hours at the API rate limits
      prerequisite: a GitHub token, from GH_TOKEN or GITHUB_TOKEN if set, otherwise from the GitHub CLI
      (`gh` from https://cli.github.com, logged in with `gh auth login`; read with `gh auth token`)
  python src/acquisition/collect_eurostat_supply.py
  python src/acquisition/ingest_stackoverflow_survey.py <path-to-survey-zip>
  python src/acquisition/ingest_linkedin_manual.py --templates   # then fill by hand (docs/supply-methodology.md §7)
  python src/acquisition/ingest_linkedin_manual.py
"""

TOOLS = """\
One-off tools (documented; NOT part of `all`):
  python src/pipeline/redact_supply_raw.py --source github --date YYYY-MM-DD [--confirm]
      Irreversible retention step (docs/legal-and-publication-audit.md §10.5). Dry run without --confirm. Run only after
      layer2 + layer3 (supply_analysis, supply_quality read the free text) and after the review samples are audited;
      afterwards build_supply can no longer be re-run from that raw folder.
  python src/analysis/precision_audit.py [data/processed/_pre_D012/postings_dedup.parquet]
      Q03c manual precision audit of the role taxonomy (D-012); its Q03c tables feed BQ28 of the visual layer.
  python src/pipeline/migrations/patch_configs_2026-09-16_audit.py
      Historical config patch of the 2026-09-16 audit (D-012); idempotent, already applied to config/.
  python src/publish/export_public.py [../austria-data-job-market-intelligence-public]
      Build the sanitised public tree after `all` has passed.
  python src/pipeline/snapshot_tracking.py --snapshot <postings_dedup.parquet> --date YYYY-MM-DD
      Fold one Layer 1 snapshot into the private posting history (only when a second dated collection exists).
  python src/analysis/labelling_audit.py {sample,sample-projects,score,score-applications,init-application-log} ...
      Hand-labelling audits (docs/labelling-protocol.md): draw blind samples, then score the filled sheets (Q10-Q12).
S06 (seasonality.py) and SQ10/SQ11 (supply_quality.py) are regenerated by their steps; SQ10/SQ11 need the
hand-labelled precision files in data/processed, so they cannot be rebuilt after the Layer 2 redaction.
"""


# ---------------------------------------------------------------- selection and preflight
def select(target: str, from_step: str | None = None, steps: list[Step] | None = None) -> list[Step]:
    steps = STEPS if steps is None else steps
    chosen = [s for s in steps if target == "all" or s.target == target]
    if from_step:
        names = [s.name for s in chosen]
        if from_step not in names:
            raise SystemExit(f"run_all: --from {from_step!r} is not a step of target {target!r}; steps: {', '.join(names)}")
        chosen = chosen[names.index(from_step):]
    return chosen


def check(step: Step, root: Path = ROOT) -> tuple[str, str]:
    """('run' | 'skip' | 'fail', reason) for one step, from its external inputs only."""
    if step.if_script_exists and not (root / step.script).exists():
        return "skip", f"planned step, {step.script} not present"
    if step.script != "-m" and not (root / step.script).exists():
        return "fail", f"script {step.script} not found"
    missing = [p for p in step.requires if not (root / p).exists()]
    if step.requires_any and not any((root / p).exists() for p in step.requires_any):
        missing.append(" or ".join(step.requires_any))
    if missing:
        return ("skip" if step.optional else "fail"), "missing input: " + ", ".join(missing)
    return "run", ""


# ---------------------------------------------------------------- environment record (L9)
def _git(*args: str) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def requirement_names(path: Path = ROOT / "requirements.txt") -> list[tuple[str, str | None]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        m = re.match(r"^([A-Za-z0-9_.\-\[\]]+)\s*(?:==\s*([^\s;]+))?", line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def environment() -> dict:
    installed, mismatches = {}, []
    for name, pinned in requirement_names():
        try:
            version = md.version(name)
        except md.PackageNotFoundError:
            version = None
        installed[name] = version
        if pinned and version != pinned:
            mismatches.append(f"{name}: pinned {pinned}, installed {version}")
    status = _git("status", "--porcelain")
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "requirements_installed": installed,
        "requirements_mismatches": mismatches,
        "git_commit": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": bool(status) if status is not None else None,
    }


# ---------------------------------------------------------------- execution
class Tee:
    def __init__(self, path: Path | None):
        self.f = open(path, "w", encoding="utf-8", newline="\n") if path else None

    def __call__(self, line: str = ""):
        print(line, flush=True)
        if self.f:
            self.f.write(line + "\n"); self.f.flush()

    def close(self):
        if self.f:
            self.f.close()


def run_step(step: Step, log: Tee, root: Path = ROOT) -> int:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", MPLBACKEND="Agg")
    proc = subprocess.Popen(step.command(), cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    assert proc.stdout is not None
    for line in proc.stdout:
        log("    " + line.rstrip("\n"))
    return proc.wait()


def run(steps: list[Step], *, target: str, from_step: str | None, dry_run: bool, root: Path = ROOT,
        log_dir: Path = LOG_DIR, manifest: Path = MANIFEST) -> int:
    started = dt.datetime.now(dt.timezone.utc)
    plan = [(s, *check(s, root)) for s in steps]
    log_path = None if dry_run else log_dir / f"run_{started.astimezone():%Y%m%d-%H%M%S}.log"
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    log = Tee(log_path)
    try:
        if sys.version_info[:2] != (3, 12):
            log(f"WARNING: tested with Python 3.12; this is {platform.python_version()}")
        log(f"run_all {target}{f' --from {from_step}' if from_step else ''}  ({len(steps)} steps)  root={root.name}")
        log(f"note: collection is not part of this run; Layer 2 collection (collect_github_supply.py) needs a GitHub "
            f"token: {github_token_status()}")
        failures = [(s, why) for s, verdict, why in plan if verdict == "fail"]
        for s, verdict, why in plan:
            tag = {"run": "  ok ", "skip": " SKIP", "fail": " FAIL"}[verdict]
            log(f"{tag}  {s.name:<24} {s.display()}" + (f"   <- {why}" if why else ""))
        for s, verdict, why in plan:
            if verdict == "skip" and not s.if_script_exists:
                log("")
                log(f"!!! OPTIONAL STEP SKIPPED: {s.name} - {why}")
                log(f"!!! its published outputs are NOT regenerated in this run ({s.note})")
        if failures:
            log("")
            log("PREFLIGHT FAILED - nothing was run. Missing inputs (private data is not part of a public clone):")
            for s, why in failures:
                log(f"  {s.name}: {why}")
            return 2
        if dry_run:
            log("dry run: nothing executed")
            return 0

        env = environment()
        if env["requirements_mismatches"]:
            log("WARNING: installed versions differ from requirements.txt: " + "; ".join(env["requirements_mismatches"]))
        records, status, code = [], "ok", 0
        for s, verdict, why in plan:
            if verdict == "skip":
                records.append({"step": s.name, "target": s.target, "command": s.display(), "status": "skipped", "reason": why})
                continue
            log("")
            log(f"==> {s.name}  ({s.display()})")
            t0 = time.perf_counter()
            rc = run_step(s, log, root)
            secs = round(time.perf_counter() - t0, 1)
            records.append({"step": s.name, "target": s.target, "command": s.display(),
                            "status": "ok" if rc == 0 else "failed", "returncode": rc, "seconds": secs})
            log(f"<== {s.name}: {'ok' if rc == 0 else f'FAILED (exit {rc})'} in {secs}s")
            if rc != 0:
                status, code = f"failed at {s.name}", 1
                break
        finished = dt.datetime.now(dt.timezone.utc)
        executed = [r for r in records if r["status"] in ("ok", "failed")]
        wrote = any(s.writes_outputs for s in steps if s.name in {r["step"] for r in executed})
        if wrote:
            payload = {"run_started": started.isoformat(timespec="seconds"), "run_finished": finished.isoformat(timespec="seconds"),
                       "target": target, "from_step": from_step, "status": status,
                       "seconds_total": round((finished - started).total_seconds(), 1),
                       "log": log_path.relative_to(root).as_posix() if log_path and log_path.is_relative_to(root) else str(log_path),
                       "environment": env, "steps": records}
            manifest.parent.mkdir(parents=True, exist_ok=True)
            tmp = manifest.with_name(manifest.name + ".tmp")
            tmp.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
            os.replace(tmp, manifest)
            log(f"manifest: {manifest.relative_to(root).as_posix() if manifest.is_relative_to(root) else manifest}")
        log(f"log: {log_path}")
        log(f"run_all {target}: {status.upper()} ({round((finished - started).total_seconds())}s)")
        return code
    finally:
        log.close()


def github_token_status() -> str:
    """Where collect_github_supply.py would get its token from; the token itself is never read or printed here."""
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(var):
            return f"{var} is set"
    if shutil.which("gh"):
        return "GH_TOKEN / GITHUB_TOKEN not set; GitHub CLI `gh` found (needs `gh auth login`)"
    return "MISSING: set GH_TOKEN or GITHUB_TOKEN, or install the GitHub CLI and run `gh auth login`"


def list_all() -> str:
    lines = ["Targets (run in this global order; `all` = every target):", ""]
    for t in TARGETS:
        lines.append(f"{t}:")
        for s in STEPS:
            if s.target == t:
                flag = " [optional]" if s.optional else (" [planned, if present]" if s.if_script_exists else "")
                inputs = ", ".join(s.requires + ([" or ".join(s.requires_any)] if s.requires_any else []))
                lines.append(f"  {s.name:<24}{flag}  {s.display()}")
                lines.append(f"  {'':<24}  {s.note}" + (f"  | inputs: {inputs}" if inputs else ""))
        lines.append("")
    lines.append(f"collect: prints the collection commands; Layer 2 collection needs a GitHub token ({github_token_status()})")
    lines.append("tools:   prints the one-off tools and the hand-maintained tables")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the reproduction pipeline in order (see module docstring).")
    ap.add_argument("target", nargs="?", choices=("all", *TARGETS, "collect", "tools"), help="what to run")
    ap.add_argument("--list", action="store_true", help="list targets and steps")
    ap.add_argument("--from", dest="from_step", metavar="STEP", help="start at this step (earlier steps of the target are skipped)")
    ap.add_argument("--dry-run", action="store_true", help="preflight and print the commands; run nothing")
    a = ap.parse_args(argv)
    if a.list or a.target is None:
        print(list_all())
        return 0
    if a.target == "collect":
        print(COLLECT)
        print(f"GitHub token for collect_github_supply.py: {github_token_status()}")
        return 0
    if a.target == "tools":
        print(TOOLS)
        return 0
    return run(select(a.target, a.from_step), target=a.target, from_step=a.from_step, dry_run=a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
