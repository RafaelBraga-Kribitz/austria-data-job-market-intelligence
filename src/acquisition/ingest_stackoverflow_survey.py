"""Layer 2 self-reported supply lens: Stack Overflow Developer Survey (ODbL 1.0), Austrian respondents.

Provenance (2025 edition, the one used so far). The official download link on survey.stackoverflow.co
(…/datasets/stack-overflow-developer-survey-2025.zip) returned HTTP 404 on 2026-09-17; the identical 16.8 MB
zip (survey_results_public.csv, survey_results_schema.csv and the survey instrument PDF, 49,123 rows,
170 columns) was obtained from a public GitHub mirror (jz-ayp/so-survey-2025, committed 2025-11-06). The
Open Database License permits redistribution; the zip is a secondary copy and is tagged SOURCE_QUALITY B in
docs/supply-methodology.md. The zip and the Austrian extract are kept under data/external/
stackoverflow_survey/<year>/ (git-ignored: 140 MB CSV; ODbL share-alike would apply to the extract) — the
collector and every aggregate are public.

Integrity. manifest.json records the SHA-256 of the zip as ingested. A re-run checks the zip it is given
against the copy already in the folder and against the recorded hash, and stops on a mismatch rather than
silently mixing two different files. Nothing is downloaded by this script.

Usage: python src/acquisition/ingest_stackoverflow_survey.py <path-to-zip> [--year 2025]
         [--obtained-from TEXT] [--source-quality B]
  --obtained-from is required for any year other than 2025 (no provenance note is known for it).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXTERNAL = ROOT / "data" / "external" / "stackoverflow_survey"
PROVENANCE = {2025: "public GitHub mirror jz-ayp/so-survey-2025 (official URL 404 on 2026-09-17)"}
KEEP = ["ResponseId", "MainBranch", "Age", "EdLevel", "Employment", "WorkExp", "YearsCode", "YearsCodePro", "DevType", "OrgSize",
        "RemoteWork", "Industry", "Country", "LanguageHaveWorkedWith", "LanguageWantToWorkWith", "DatabaseHaveWorkedWith",
        "PlatformHaveWorkedWith", "WebframeHaveWorkedWith", "MiscTechHaveWorkedWith", "ToolsTechHaveWorkedWith",
        "AISelect", "AIToolCurrently Using", "AIToolCurrentlyUsing", "LearnCode", "CompTotal", "Currency", "ConvertedCompYearly",
        "ICorPM", "JobSat", "AIModelsHaveWorkedWith", "AIAgentsHaveWorkedWith", "NewRole"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(zip_path: Path, year: int = 2025, obtained_from: str | None = None, source_quality: str = "B") -> None:
    obtained_from = obtained_from or PROVENANCE.get(year)
    if not obtained_from:
        raise SystemExit(f"no provenance note known for {year}: pass --obtained-from")
    out = EXTERNAL / str(year)
    out.mkdir(parents=True, exist_ok=True)
    dst = out / zip_path.name
    sha_in = sha256_file(zip_path)
    if dst.exists() and dst.resolve() != zip_path.resolve() and sha256_file(dst) != sha_in:
        raise SystemExit(f"{dst} already exists with different content than {zip_path}; move one of them first")
    if not dst.exists():
        shutil.copy2(zip_path, dst)
    manifest = out / "manifest.json"
    if manifest.exists():
        old = json.loads(manifest.read_text(encoding="utf-8")).get("sha256")
        if old and old != sha_in:
            raise SystemExit(f"{zip_path} (sha256 {sha_in[:12]}…) differs from the zip recorded in {manifest} ({old[:12]}…)")
    with zipfile.ZipFile(dst) as z:
        names = z.namelist()
        csv = [n for n in names if n.endswith("survey_results_public.csv")][0]
        with z.open(csv) as f:
            df = pd.read_csv(f, low_memory=False)
        cols = [c for c in KEEP if c in df.columns]
        all_n = len(df)
        at = df.loc[df["Country"] == "Austria", cols].copy()
        at.to_csv(out / "survey_results_austria.csv", index=False)
        schema = [n for n in names if n.endswith("survey_results_schema.csv")]
        if schema:
            with z.open(schema[0]) as f:
                pd.read_csv(f).to_csv(out / "survey_results_schema.csv", index=False)
        members = [(i.filename, i.file_size) for i in z.infolist()]
    # country counts (aggregate, publishable) for the sample-bias discussion
    df["Country"].value_counts().rename_axis("country").reset_index(name="respondents").to_csv(out / "country_counts.csv", index=False)
    meta = {"zip": dst.name, "sha256": sha_in, "survey_year": year, "members": members, "rows_total": all_n,
            "rows_austria": len(at), "columns_kept": cols, "licence": f"ODbL 1.0 (stated on survey.stackoverflow.co/{year})",
            "obtained_from": obtained_from, "source_quality": source_quality}
    manifest.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in meta.items() if k != "columns_kept"}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("zip", type=Path, help="local path of the survey zip (not downloaded by this script)")
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--obtained-from", default=None, help="provenance note stored in manifest.json")
    ap.add_argument("--source-quality", default="B")
    a = ap.parse_args()
    main(a.zip, a.year, a.obtained_from, a.source_quality)
