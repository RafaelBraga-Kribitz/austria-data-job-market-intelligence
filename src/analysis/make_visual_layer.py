"""Step V1: render the visual decision layer -> outputs/figures/BQ*.{svg,png}.

One business question per figure, built from the published tables
in `outputs/tables/`. Every answer sentence is computed from the table at render
time, so a figure caption cannot drift away from the data the way a hand-typed
number can.

Writes, besides the figures:
  outputs/figures/FIGURE-MANIFEST.yaml   DSX-style ledger: chart_id, relationship,
                                         mark, data signature, source tables and a
                                         SHA-256 seal of the SVG bytes
  outputs/visual_questions.json          machine-readable contract consumed by
                                         src/analysis/embed_figures.py and by agents

Run:  python src/analysis/make_visual_layer.py
Then: python src/analysis/embed_figures.py      (attaches each figure to its text)
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

import matplotlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "viz"))
sys.path.insert(0, str(ROOT / "src" / "analysis"))

from engine import FIGURES, SNAPSHOT, save  # noqa: E402

import visual_questions_demand as demand  # noqa: E402
import visual_questions_evidence as evidence  # noqa: E402
import visual_questions_followup as followup  # noqa: E402
import visual_questions_supply as supply  # noqa: E402

RUN_ID = "austria-visual-decision-layer"
# SNAPSHOT ("demand <date> / supply <date>") comes from engine, which reads market_summary.json and
# data/processed/supply_build_manifest.json, so the manifest vintage follows a re-collection (M81/L135).
MANIFEST = FIGURES / "FIGURE-MANIFEST.yaml"
CONTRACT = ROOT / "outputs" / "visual_questions.json"


def yaml_escape(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_manifest(specs) -> None:
    lines = [
        "# FIGURE-MANIFEST - the visual decision layer.",
        "#",
        "# One entry per figure. `relationship` and `mark` follow the GSD-DSX chart",
        "# catalogue (references/chart-catalog.md): the relationship is named first and",
        "# the mark must be admissible for it. `svg_sha256` seals the rendered bytes, so",
        "# a figure that no longer matches its declaration is detectable without opening it.",
        "#",
        "# Regenerate with: python src/analysis/make_visual_layer.py",
        "",
        "manifest_version: 1",
        f'matplotlib_version: "{matplotlib.__version__}"',
        f'run_id: "{RUN_ID}"',
        f'data_vintage: "{SNAPSHOT}"',
        f'generated: "{date.today().isoformat()}"',
        "generator: src/analysis/make_visual_layer.py",
        "style: src/viz/styles/dsx-urban.mplstyle",
        "figures:",
    ]
    for spec in specs:
        lines += [
            f"  - chart_id: {spec.chart_id}",
            f"    path: outputs/figures/{spec.svg}",
            f"    png: outputs/figures/{spec.png}",
            f"    question: {yaml_escape(spec.question)}",
            f"    answer: {yaml_escape(spec.answer)}",
            f"    relationship: {yaml_escape(spec.relationship)}",
            f"    mark: {spec.mark}",
            f"    data_signature: {spec.data_signature}",
            f"    units: {yaml_escape(spec.units)}",
            f"    tables: [{', '.join(spec.tables)}]",
            f"    caveat: {yaml_escape(spec.caveat)}",
            f"    svg_sha256: {spec.svg_sha256}",
            "    anchors:",
        ]
        for doc, mode, key in spec.anchors:
            lines.append(f"      - {{ doc: {doc}, mode: {mode}, key: {yaml_escape(key)} }}")
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_contract(specs) -> None:
    payload = {
        "run_id": RUN_ID,
        "data_vintage": SNAPSHOT,
        "generated": date.today().isoformat(),
        "generator": "src/analysis/make_visual_layer.py",
        "purpose": "One business question per figure; the answer is computed from the named tables at render time.",
        # png/svg are properties, not fields: asdict() would drop them.
        "figures": [{**asdict(spec), "png": spec.png, "svg": spec.svg} for spec in specs],
    }
    CONTRACT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    specs = []
    failures = []
    for builder in demand.BUILDERS + supply.BUILDERS + evidence.BUILDERS + followup.BUILDERS:
        try:
            spec, fig = builder()
            specs.append(save(fig, spec))
            print(f"  {spec.chart_id:32s} {spec.mark:16s} {spec.svg_sha256[:19]}…")
        except Exception as exc:  # a broken figure must be loud, not silently missing
            failures.append((builder.__name__, repr(exc)))
            print(f"  FAILED {builder.__name__}: {exc}", file=sys.stderr)
    write_manifest(specs)
    write_contract(specs)
    print(f"\n{len(specs)} figures -> {FIGURES}")
    print(f"manifest -> {MANIFEST.relative_to(ROOT)}")
    print(f"contract -> {CONTRACT.relative_to(ROOT)}")
    if failures:
        raise SystemExit(f"{len(failures)} figure(s) failed: {failures}")


if __name__ == "__main__":
    main()
