#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SCHEMA_DIR = ROOT / "schema"
TWEAKEY_EXPR_RE = re.compile(r"^([1-9][0-9]*)\s*-\s*key_size_bits$")


def validate_range_field(characteristics: dict, base_field: str, pid: str) -> list[str]:
    errors: list[str] = []
    min_field = f"{base_field}_min"
    max_field = f"{base_field}_max"

    min_value = characteristics.get(min_field)
    max_value = characteristics.get(max_field)
    has_min = min_value is not None
    has_max = max_value is not None

    if has_min != has_max:
        errors.append(
            f"REFERENCE ERROR: instance '{pid}' must define both {min_field} and {max_field} together"
        )
        return errors

    if has_min and has_max:
        if not isinstance(min_value, int) or min_value <= 0:
            errors.append(
                f"REFERENCE ERROR: instance '{pid}' has invalid {min_field}='{min_value}'"
            )
        if not isinstance(max_value, int) or max_value <= 0:
            errors.append(
                f"REFERENCE ERROR: instance '{pid}' has invalid {max_field}='{max_value}'"
            )
        if isinstance(min_value, int) and isinstance(max_value, int) and min_value > max_value:
            errors.append(
                f"REFERENCE ERROR: instance '{pid}' has {min_field}={min_value} > {max_field}={max_value}"
            )

    base_value = characteristics.get(base_field)
    if has_min and has_max and isinstance(base_value, int):
        if not (min_value <= base_value <= max_value):
            errors.append(
                f"REFERENCE ERROR: instance '{pid}' has {base_field}={base_value} outside [{min_value}, {max_value}]"
            )

    return errors


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
    rounds_doc       = load_yaml(DATA_DIR / "rounds.yaml")
    primitive_types_doc = load_yaml(DATA_DIR / "primitive_types.yaml")
    references_doc = load_yaml(DATA_DIR / "references.yaml")
    processes_doc    = load_yaml(DATA_DIR / "processes.yaml")

    ok = True
    ok &= validate_schema(families_doc,   SCHEMA_DIR / "families.schema.json",   "families")
    ok &= validate_schema(primitives_doc, SCHEMA_DIR / "primitives.schema.json", "primitives")
    ok &= validate_schema(components_doc, SCHEMA_DIR / "components.schema.json", "components")
    ok &= validate_schema(constructions_doc, SCHEMA_DIR / "constructions.schema.json", "constructions")
    ok &= validate_schema(rounds_doc, SCHEMA_DIR / "rounds.schema.json", "rounds")
    ok &= validate_schema(primitive_types_doc, SCHEMA_DIR / "primitive_types.schema.json", "primitive_types")
    ok &= validate_schema(references_doc, SCHEMA_DIR / "references.schema.json", "references")
    if not ok:
        raise SystemExit(1)

    reference_ids = {r["id"] for r in references_doc.get("references", [])}
    process_ids     = {p["id"] for p in processes_doc.get("processes", [])}
    family_ids      = {f["id"] for f in families_doc.get("families", [])}
    component_ids   = {c["id"] for c in components_doc.get("components", [])}
    construction_ids = {c["id"] for c in constructions_doc.get("constructions", [])}
    round_ids       = {r["id"] for r in rounds_doc.get("rounds", [])}
    primitive_type_ids = {t["id"] for t in primitive_types_doc.get("primitive_types", [])}
    family_innovation_ids: dict[str, set[str]] = {}

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

    for round_def in rounds_doc.get("rounds", []):
        for step in round_def.get("spec", {}).get("component_flow", []):
            component_id = step.get("component_id")
            if component_id and component_id not in component_ids:
                print(
                    f"REFERENCE ERROR: round '{round_def['id']}' references unknown component '{component_id}'"
                )
                errors_found = True

    # Validate families
    for family in families_doc.get("families", []):
        fid = family["id"]
        idea_ids: set[str] = set()
        for idea in family.get("innovative_ideas", []):
            idea_id = idea["id"]
            if idea_id in idea_ids:
                print(f"REFERENCE ERROR: family '{fid}' has duplicate innovative idea id '{idea_id}'")
                errors_found = True
            idea_ids.add(idea_id)
        family_innovation_ids[fid] = idea_ids
        for construction_id in family.get("construction_ids", []):
            if construction_id not in construction_ids:
                print(
                    f"REFERENCE ERROR: family '{fid}' references unknown construction '{construction_id}'"
                )
                errors_found = True
        for round_id in family.get("round_ids", []):
            if round_id not in round_ids:
                print(
                    f"REFERENCE ERROR: family '{fid}' references unknown round '{round_id}'"
                )
                errors_found = True
        for ref in family.get("reference_ids", []):
            if ref not in reference_ids:
                print(f"REFERENCE ERROR: family '{fid}' has unknown reference '{ref}'")
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
            relations = edge.get("relations") or ([edge["relation"]] if edge.get("relation") else [])
            if not relations:
                print(f"REFERENCE ERROR: family '{fid}' has influence from '{src}' without any relations")
                errors_found = True
            for rel in relations:
                if rel not in {
                    "selection_of_possible_configurations",
                    "same_sbox",
                    "same_sbox_size",
                    "same_key_schedule",
                    "same_state_layout",
                    "same_bit_based_permutation_layer",
                    "similar_bit_based_permutation_layer",
                    "same_mix_column",
                    "similar_mix_column",
                    "same_shift_row",
                    "similar_shift_row",
                    "same_round_function",
                    "same_round_constants",
                    "improved_diffusion",
                    "inherits_alpha_reflexivity_structure",
                    "inspired_by",
                    "improvement_of",
                    "variant_of",
                    "generalization_of",
                    "related_to",
                }:
                    print(f"REFERENCE ERROR: family '{fid}' has unknown influence relation '{rel}'")
                    errors_found = True
            for idea_id in edge.get("innovative_idea_ids", []):
                if idea_id not in family_innovation_ids.get(src, set()):
                    print(
                        f"REFERENCE ERROR: family '{fid}' influence from '{src}' references unknown innovative idea '{idea_id}'"
                    )
                    errors_found = True
        for comp_ref in family.get("characteristics", {}).get("components", []):
            cid = comp_ref["id"]
            if cid not in component_ids:
                print(f"REFERENCE ERROR: family '{fid}' references unknown component '{cid}'")
                errors_found = True

    # Validate primitive instances
    for primitive in primitives_doc.get("primitives", []):
        pid = primitive["id"]
        characteristics = primitive.get("characteristics", {})
        if primitive["family_id"] not in family_ids:
            print(f"REFERENCE ERROR: instance '{pid}' has unknown family_id '{primitive['family_id']}'")
            errors_found = True
        if primitive["primitive_type"] not in primitive_type_ids:
            print(
                f"REFERENCE ERROR: instance '{pid}' has unknown primitive_type '{primitive['primitive_type']}'"
            )
            errors_found = True
        for ref in primitive.get("reference_ids", []):
            if ref not in reference_ids:
                print(f"REFERENCE ERROR: instance '{pid}' has unknown reference '{ref}'")
                errors_found = True
        tweakey_size = characteristics.get("tweakey_size_bits")
        if isinstance(tweakey_size, str):
            expr_match = TWEAKEY_EXPR_RE.match(tweakey_size.strip())
            if not expr_match:
                print(
                    f"REFERENCE ERROR: instance '{pid}' has invalid tweakey_size_bits expression '{tweakey_size}'"
                )
                errors_found = True
            else:
                total_bits = int(expr_match.group(1))
                key_size = characteristics.get("key_size_bits")
                key_min = characteristics.get("key_size_bits_min")
                key_max = characteristics.get("key_size_bits_max")

                has_scalar = isinstance(key_size, int) and key_size > 0
                has_range = isinstance(key_min, int) and key_min > 0 and isinstance(key_max, int) and key_max > 0

                if not has_scalar and not has_range:
                    print(
                        f"REFERENCE ERROR: instance '{pid}' uses tweakey_size_bits expression but has neither key_size_bits nor key_size_bits_min/max"
                    )
                    errors_found = True

                if has_scalar and key_size > total_bits:
                    print(
                        f"REFERENCE ERROR: instance '{pid}' has key_size_bits={key_size} larger than tweakey total {total_bits}"
                    )
                    errors_found = True

                if has_range and key_max > total_bits:
                    print(
                        f"REFERENCE ERROR: instance '{pid}' has key_size_bits_max={key_max} larger than tweakey total {total_bits}"
                    )
                    errors_found = True

        range_base_fields = [
            "block_size_bits",
            "state_size_bits",
            "key_size_bits",
            "tweak_size_bits",
            "tweakey_size_bits",
            "iv_size_bits",
            "nonce_size_bits",
            "rounds",
            "fixed_input_bits",
            "fixed_output_bits",
        ]
        for base_field in range_base_fields:
            for error in validate_range_field(characteristics, base_field, pid):
                print(error)
                errors_found = True

    if errors_found:
        raise SystemExit(1)

    print("Validation successful.")


if __name__ == "__main__":
    main()
