#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SCHEMA_DIR = ROOT / "schema"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_schema(doc: dict, schema_path: Path, label: str) -> bool:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: e.path)
    if errors:
        for error in errors:
            location = "/".join(str(p) for p in error.path)
            print(f"SCHEMA ERROR [{label}] at '{location}': {error.message}")
        return False
    return True


def main() -> None:
    families_doc     = load_yaml(DATA_DIR / "families.yaml")
    primitives_doc   = load_yaml(DATA_DIR / "primitives.yaml")
    components_doc   = load_yaml(DATA_DIR / "components.yaml")
    constructions_doc = load_yaml(DATA_DIR / "constructions.yaml")
    primitive_types_doc = load_yaml(DATA_DIR / "primitive_types.yaml")
    publications_doc = load_yaml(DATA_DIR / "publications.yaml")
    processes_doc    = load_yaml(DATA_DIR / "processes.yaml")

    ok = True
    ok &= validate_schema(families_doc,   SCHEMA_DIR / "families.schema.json",   "families")
    ok &= validate_schema(primitives_doc, SCHEMA_DIR / "primitives.schema.json", "primitives")
    ok &= validate_schema(components_doc, SCHEMA_DIR / "components.schema.json", "components")
    ok &= validate_schema(constructions_doc, SCHEMA_DIR / "constructions.schema.json", "constructions")
    ok &= validate_schema(primitive_types_doc, SCHEMA_DIR / "primitive_types.schema.json", "primitive_types")
    if not ok:
        raise SystemExit(1)

    publication_ids = {p["id"] for p in publications_doc.get("publications", [])}
    process_ids     = {p["id"] for p in processes_doc.get("processes", [])}
    family_ids      = {f["id"] for f in families_doc.get("families", [])}
    component_ids   = {c["id"] for c in components_doc.get("components", [])}
    construction_ids = {c["id"] for c in constructions_doc.get("constructions", [])}
    primitive_type_ids = {t["id"] for t in primitive_types_doc.get("primitive_types", [])}

    # Validate special_case_of self-references in components
    errors_found = False
    for comp in components_doc.get("components", []):
        ref = comp.get("special_case_of")
        if ref and ref not in component_ids:
            print(f"REFERENCE ERROR: component '{comp['id']}' has unknown special_case_of '{ref}'")
            errors_found = True

    for construction in constructions_doc.get("constructions", []):
        ref = construction.get("special_case_of")
        if ref and ref not in construction_ids:
            print(
                f"REFERENCE ERROR: construction '{construction['id']}' has unknown special_case_of '{ref}'"
            )
            errors_found = True

    # Validate families
    for family in families_doc.get("families", []):
        fid = family["id"]
        if family["primitive_type"] not in primitive_type_ids:
            print(
                f"REFERENCE ERROR: family '{fid}' has unknown primitive_type '{family['primitive_type']}'"
            )
            errors_found = True
        for construction_id in family.get("construction_ids", []):
            if construction_id not in construction_ids:
                print(
                    f"REFERENCE ERROR: family '{fid}' references unknown construction '{construction_id}'"
                )
                errors_found = True
        for ref in family.get("publication_ids", []):
            if ref not in publication_ids:
                print(f"REFERENCE ERROR: family '{fid}' has unknown publication '{ref}'")
                errors_found = True
        for ref in family.get("standard_ids", []):
            if ref not in publication_ids:
                print(f"REFERENCE ERROR: family '{fid}' has unknown standard '{ref}' (not in publications)")
                errors_found = True
        for ref in family.get("process_ids", []):
            if ref not in process_ids:
                print(f"REFERENCE ERROR: family '{fid}' has unknown process '{ref}'")
                errors_found = True
        for edge in family.get("influences", []):
            src = edge["source_family_id"]
            if src not in family_ids:
                print(f"REFERENCE ERROR: family '{fid}' has unknown influence source family '{src}'")
                errors_found = True
        for comp_ref in family.get("characteristics", {}).get("components", []):
            cid = comp_ref["id"]
            if cid not in component_ids:
                print(f"REFERENCE ERROR: family '{fid}' references unknown component '{cid}'")
                errors_found = True

    # Validate primitive instances
    for primitive in primitives_doc.get("primitives", []):
        pid = primitive["id"]
        if primitive["family_id"] not in family_ids:
            print(f"REFERENCE ERROR: instance '{pid}' has unknown family_id '{primitive['family_id']}'")
            errors_found = True
        for ref in primitive.get("standard_ids", []):
            if ref not in publication_ids:
                print(f"REFERENCE ERROR: instance '{pid}' has unknown standard '{ref}' (not in publications)")
                errors_found = True

    if errors_found:
        raise SystemExit(1)

    print("Validation successful.")


if __name__ == "__main__":
    main()
