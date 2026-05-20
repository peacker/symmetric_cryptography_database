#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SCHEMA_FILE = ROOT / "schema" / "primitives.schema.json"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    primitives_doc = load_yaml(DATA_DIR / "primitives.yaml")
    publications_doc = load_yaml(DATA_DIR / "publications.yaml")
    standards_doc = load_yaml(DATA_DIR / "standards.yaml")
    processes_doc = load_yaml(DATA_DIR / "processes.yaml")

    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(primitives_doc), key=lambda e: e.path)
    if errors:
        for error in errors:
            location = "/".join(str(p) for p in error.path)
            print(f"SCHEMA ERROR at '{location}': {error.message}")
        raise SystemExit(1)

    publication_ids = {p["id"] for p in publications_doc.get("publications", [])}
    standard_ids = {s["id"] for s in standards_doc.get("standards", [])}
    process_ids = {p["id"] for p in processes_doc.get("processes", [])}
    primitive_ids = {p["id"] for p in primitives_doc.get("primitives", [])}

    errors_found = False
    for primitive in primitives_doc.get("primitives", []):
        pid = primitive["id"]

        for ref in primitive.get("publication_ids", []):
            if ref not in publication_ids:
                print(f"REFERENCE ERROR: primitive '{pid}' has unknown publication '{ref}'")
                errors_found = True

        for ref in primitive.get("standard_ids", []):
            if ref not in standard_ids:
                print(f"REFERENCE ERROR: primitive '{pid}' has unknown standard '{ref}'")
                errors_found = True

        for ref in primitive.get("process_ids", []):
            if ref not in process_ids:
                print(f"REFERENCE ERROR: primitive '{pid}' has unknown process '{ref}'")
                errors_found = True

        for edge in primitive.get("influences", []):
            src = edge["source_primitive_id"]
            if src not in primitive_ids:
                print(f"REFERENCE ERROR: primitive '{pid}' has unknown influence source '{src}'")
                errors_found = True

    if errors_found:
        raise SystemExit(1)

    print("Validation successful.")


if __name__ == "__main__":
    main()
