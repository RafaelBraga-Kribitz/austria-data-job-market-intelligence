"""Validate every JSON file of the Power BI project in dashboards/ against the schema it declares.

    python src/reporting/validate_pbip.py --schemas DIR      validate against an offline copy of Microsoft's JSON schemas
    python src/reporting/validate_pbip.py                    no schema folder given: print a notice and exit 0
    python src/reporting/validate_pbip.py --schemas DIR --project PATH   another project folder (default dashboards/)

Every PBIR / PBIP JSON file names its schema in "$schema" (https://developer.microsoft.com/json-schemas/fabric/...).
DIR is a local mirror of that tree (a clone of github.com/microsoft/json-schemas: DIR/fabric/item/report/definition/
<type>/<version>/schema.json ...). The URLs are mapped onto DIR, cross-file "$ref"s are resolved inside DIR through a
`referencing` registry, so the check needs no network. CI does not pass a folder (the public test suite stays offline);
tests/test_dashboards.py checks the model <-> report integrity instead. Needs `jsonschema` (not a pipeline dependency):
without it the script also exits 0 with a notice.

Exit code 1 if any file fails its schema, names a schema that is not in DIR, or does not parse.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "https://developer.microsoft.com/json-schemas/"
SUFFIXES = {".json", ".pbir", ".pbism", ".pbip", ".platform"}


def project_files(project: Path) -> list[Path]:
    return sorted(p for p in project.rglob("*") if p.is_file() and (p.suffix in SUFFIXES or p.name == ".platform")
                  and ".pbi" not in p.parts and "html" not in p.relative_to(project).parts[:1])


def validate(project: Path, schemas: Path) -> list[str]:
    from jsonschema import Draft7Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7

    def retrieve(uri: str):
        if not uri.startswith(PREFIX):
            raise LookupError(f"schema outside {PREFIX}: {uri}")
        path = schemas / uri[len(PREFIX):].split("#", 1)[0]
        return Resource.from_contents(json.loads(path.read_text(encoding="utf-8")), default_specification=DRAFT7)

    registry = Registry(retrieve=retrieve)
    problems: list[str] = []
    checked = 0
    for path in project_files(project):
        rel = path.relative_to(project).as_posix()
        try:
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
        except ValueError as exc:
            problems.append(f"{rel}: does not parse ({exc})")
            continue
        if path.read_bytes()[:3] == b"\xef\xbb\xbf":
            problems.append(f"{rel}: has a UTF-8 BOM (Power BI Desktop may reject it)")
        url = doc.get("$schema") if isinstance(doc, dict) else None
        if not url:
            continue   # the theme file (StaticResources) declares no schema
        local = schemas / url[len(PREFIX):] if url.startswith(PREFIX) else None
        if local is None or not local.exists():
            problems.append(f"{rel}: schema not found offline: {url}")
            continue
        schema = json.loads(local.read_text(encoding="utf-8"))
        validator = Draft7Validator(schema, registry=registry)
        errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
        checked += 1
        for err in errors[:20]:
            where = "/".join(str(p) for p in err.absolute_path) or "(root)"
            problems.append(f"{rel}: {where}: {err.message[:300]}")
    print(f"validate_pbip: {checked} files checked against their declared schemas, {len(problems)} problem(s)")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate the PBIP JSON files against their declared JSON schemas (offline).")
    ap.add_argument("--schemas", type=Path, help="local mirror of https://developer.microsoft.com/json-schemas/ (the folder that holds fabric/)")
    ap.add_argument("--project", type=Path, default=ROOT / "dashboards", help="folder that holds the .pbip (default dashboards/)")
    args = ap.parse_args(argv)
    if not args.schemas:
        print("validate_pbip: no --schemas folder given; schema validation skipped (needs an offline copy of "
              "the Microsoft json-schemas tree). The model<->report integrity test (tests/test_dashboards.py) still runs.")
        return 0
    try:
        import jsonschema  # noqa: F401
        import referencing  # noqa: F401
    except ImportError:
        print("validate_pbip: jsonschema/referencing not installed; schema validation skipped (pip install jsonschema)")
        return 0
    if not (args.schemas / "fabric").is_dir():
        print(f"validate_pbip: {args.schemas} has no fabric/ folder; point --schemas at the json-schemas root")
        return 1
    problems = validate(args.project, args.schemas)
    for p in problems:
        print("  " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
