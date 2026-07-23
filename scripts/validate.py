#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from common import SCHEMA_DIR, all_families, all_instances, load_all_data

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


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_schema_registry() -> Registry:
    """Registers every schema/*.schema.json file by its own $id, so a $ref like
    'family_common.schema.json#/$defs/influence' (used by primitive_families
    and mode_families to share definitions instead of duplicating them, e.g.
    the influence-edge rule) resolves locally instead of jsonschema trying --
    and failing -- to fetch the https://example.org/... $id over the network.
    """
    resources = []
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resources.append((contents["$id"], Resource.from_contents(contents)))
    return Registry().with_resources(resources)


def validate_schema(doc: dict, schema_path: Path, label: str, registry: Registry) -> bool:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, registry=registry)
    errors = sorted(validator.iter_errors(doc), key=lambda e: e.path)
    if errors:
        for error in errors:
            location = "/".join(str(p) for p in error.path)
            print(f"SCHEMA ERROR [{label}] at '{location}': {error.message}")
        return False
    return True


def main() -> None:
    data = load_all_data()
    primitive_families_doc = data["primitive_families"]
    mode_families_doc      = data["mode_families"]
    components_doc         = data["components"]
    primitive_constructions_doc = data["primitive_constructions"]
    mode_constructions_doc  = data["mode_constructions"]
    rounds_doc              = data["rounds"]
    primitive_types_doc     = data["primitive_types"]
    mode_types_doc          = data["mode_types"]
    references_doc          = data["references"]
    processes_doc           = data["processes"]

    registry = build_schema_registry()
    ok = True
    ok &= validate_schema(primitive_families_doc, SCHEMA_DIR / "primitive_families.schema.json", "primitive_families", registry)
    ok &= validate_schema(mode_families_doc,      SCHEMA_DIR / "mode_families.schema.json",      "mode_families", registry)
    ok &= validate_schema(components_doc,         SCHEMA_DIR / "components.schema.json",         "components", registry)
    ok &= validate_schema(primitive_constructions_doc, SCHEMA_DIR / "primitive_constructions.schema.json", "primitive_constructions", registry)
    ok &= validate_schema(mode_constructions_doc,  SCHEMA_DIR / "mode_constructions.schema.json", "mode_constructions", registry)
    ok &= validate_schema(rounds_doc,              SCHEMA_DIR / "rounds.schema.json",             "rounds", registry)
    ok &= validate_schema(primitive_types_doc,     SCHEMA_DIR / "primitive_types.schema.json",     "primitive_types", registry)
    ok &= validate_schema(mode_types_doc,          SCHEMA_DIR / "mode_types.schema.json",          "mode_types", registry)
    ok &= validate_schema(references_doc,          SCHEMA_DIR / "references.schema.json",          "references", registry)
    ok &= validate_schema(processes_doc,           SCHEMA_DIR / "processes.schema.json",           "processes", registry)
    if not ok:
        raise SystemExit(1)

    family_common_schema = load_json(SCHEMA_DIR / "family_common.schema.json")
    known_relations = set(
        family_common_schema["$defs"]["influence"]["properties"]["relations"]["items"]["enum"]
    )

    reference_ids = {r["id"] for r in references_doc.get("references", [])}
    standard_reference_ids = {
        r["id"]
        for r in references_doc.get("references", [])
        if "standard" in str(r.get("kind", "")).lower()
    }
    process_ids     = {p["id"] for p in processes_doc.get("processes", [])}
    component_ids   = {c["id"] for c in components_doc.get("components", [])}
    primitive_construction_ids = {c["id"] for c in primitive_constructions_doc.get("primitive_constructions", [])}
    mode_construction_ids      = {c["id"] for c in mode_constructions_doc.get("mode_constructions", [])}
    round_ids       = {r["id"] for r in rounds_doc.get("rounds", [])}
    primitive_type_ids = {t["id"] for t in primitive_types_doc.get("primitive_types", [])}
    mode_type_ids       = {t["id"] for t in mode_types_doc.get("mode_types", [])}

    families = all_families(data)
    family_ids = {f["id"] for f in families}
    instances = all_instances(families)
    instance_ids = {i["id"] for i in instances}

    family_innovation_ids: dict[str, set[str]] = {}
    standardized_profile_family_ids: set[str] = set()

    # Validate special_case_of self-references in components
    errors_found = False
    for comp in components_doc.get("components", []):
        ref = comp.get("special_case_of")
        if ref and ref not in component_ids:
            print(f"REFERENCE ERROR: component '{comp['id']}' has unknown special_case_of '{ref}'")
            errors_found = True

    for construction in primitive_constructions_doc.get("primitive_constructions", []):
        ref = construction.get("special_case_of")
        if ref and ref not in primitive_construction_ids:
            print(
                f"REFERENCE ERROR: primitive construction '{construction['id']}' has unknown special_case_of '{ref}'"
            )
            errors_found = True

    for construction in mode_constructions_doc.get("mode_constructions", []):
        ref = construction.get("special_case_of")
        if ref and ref not in mode_construction_ids:
            print(
                f"REFERENCE ERROR: mode construction '{construction['id']}' has unknown special_case_of '{ref}'"
            )
            errors_found = True

    # Enforce a two-level construction taxonomy: every construction is either a
    # root (no special_case_of) or a direct child of a root (special_case_of
    # points at a construction that itself has no special_case_of). This keeps
    # the taxonomy exactly two levels deep so it renders as a simple
    # parent-header/child-checkbox filter on the site, with no deeper nesting.
    for label, doc, key in (
        ("primitive", primitive_constructions_doc, "primitive_constructions"),
        ("mode", mode_constructions_doc, "mode_constructions"),
    ):
        by_id = {c["id"]: c for c in doc.get(key, [])}
        for construction in doc.get(key, []):
            parent_id = construction.get("special_case_of")
            if not parent_id:
                continue
            parent = by_id.get(parent_id)
            if parent is not None and parent.get("special_case_of"):
                print(
                    f"TAXONOMY ERROR: {label} construction '{construction['id']}' has special_case_of "
                    f"'{parent_id}', which itself has special_case_of '{parent['special_case_of']}' -- "
                    "construction taxonomy must be exactly two levels deep (re-parent to the root instead)"
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

    # Pass 1: collect each family's innovative_idea ids first, since influence
    # edges can cite ideas on a family defined later in iteration order (the
    # tier split means source/target no longer share one file-order list).
    for family in families:
        fid = family["id"]
        idea_ids: set[str] = set()
        for idea in family.get("innovative_ideas", []):
            idea_id = idea["id"]
            if idea_id in idea_ids:
                print(f"REFERENCE ERROR: family '{fid}' has duplicate innovative idea id '{idea_id}'")
                errors_found = True
            idea_ids.add(idea_id)
        family_innovation_ids[fid] = idea_ids

    # Pass 2: validate families (both tiers together)
    for family in families:
        fid = family["id"]
        tier = family["_tier"]
        construction_ids = primitive_construction_ids if tier == "primitive" else mode_construction_ids
        construction_label = "primitive" if tier == "primitive" else "mode"

        for construction_id in family.get("construction_ids", []):
            if construction_id not in construction_ids:
                print(
                    f"REFERENCE ERROR: {tier} family '{fid}' references unknown {construction_label}"
                    f" construction '{construction_id}'"
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
        for ref in family.get("underlying_primitive_ids", []):
            if ref not in instance_ids:
                print(f"REFERENCE ERROR: mode family '{fid}' has unknown underlying_primitive_id '{ref}'")
                errors_found = True
        for pp in family.get("process_participations", []):
            proc_id = pp["process_id"]
            if proc_id not in process_ids:
                print(f"REFERENCE ERROR: family '{fid}' references unknown process '{proc_id}'")
                errors_found = True
            else:
                valid_stage_ids = {
                    s["id"]
                    for p in processes_doc.get("processes", [])
                    if p["id"] == proc_id
                    for s in p.get("stages", [])
                }
                for sid in pp.get("stage_ids", []):
                    if sid not in valid_stage_ids:
                        print(
                            f"REFERENCE ERROR: family '{fid}' references unknown"
                            f" stage '{sid}' in process '{proc_id}'"
                        )
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
                if rel not in known_relations:
                    print(f"REFERENCE ERROR: family '{fid}' has unknown influence relation '{rel}'")
                    errors_found = True
            if "standardization_of" in relations:
                standardized_profile_family_ids.add(fid)
            for idea_id in edge.get("innovative_idea_ids", []):
                if idea_id not in family_innovation_ids.get(src, set()):
                    print(
                        f"REFERENCE ERROR: family '{fid}' influence from '{src}' references unknown innovative idea '{idea_id}'"
                    )
                    errors_found = True
        if fid in standardized_profile_family_ids:
            family_standard_ids = set(family.get("reference_ids", [])) & standard_reference_ids
            if not family_standard_ids:
                print(
                    f"REFERENCE ERROR: standardized profile family '{fid}' has no standard reference"
                )
                errors_found = True
        for comp_ref in family.get("characteristics", {}).get("components", []):
            cid = comp_ref["id"]
            if cid not in component_ids:
                print(f"REFERENCE ERROR: family '{fid}' references unknown component '{cid}'")
                errors_found = True

    # Validate instances (both tiers together)
    for instance in instances:
        pid = instance["id"]
        tier = instance["_tier"]
        type_ids = primitive_type_ids if tier == "primitive" else mode_type_ids
        type_label = "primitive_type" if tier == "primitive" else "mode_type"
        characteristics = instance.get("characteristics", {})
        if instance["type"] not in type_ids:
            print(
                f"REFERENCE ERROR: instance '{pid}' has unknown {type_label} '{instance['type']}'"
            )
            errors_found = True
        for ref in instance.get("reference_ids", []):
            if ref not in reference_ids:
                print(f"REFERENCE ERROR: instance '{pid}' has unknown reference '{ref}'")
                errors_found = True
        if instance["family_id"] in standardized_profile_family_ids:
            instance_standard_ids = set(instance.get("reference_ids", [])) & standard_reference_ids
            if not instance_standard_ids:
                print(
                    f"REFERENCE ERROR: standardized profile instance '{pid}' has no standard reference"
                )
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
            "output_size_bits",
            "tag_size_bits",
        ]
        for base_field in range_base_fields:
            for error in validate_range_field(characteristics, base_field, pid):
                print(error)
                errors_found = True

    # Validate process stage participant family_ids
    for process in processes_doc.get("processes", []):
        pid = process["id"]
        for stage in process.get("stages", []):
            sid = stage["id"]
            for participant in stage.get("participants", []):
                fid = participant.get("family_id")
                if fid and fid not in family_ids:
                    print(
                        f"REFERENCE ERROR: process '{pid}' stage '{sid}'"
                        f" references unknown family_id '{fid}'"
                    )
                    errors_found = True

    if errors_found:
        raise SystemExit(1)

    print(
        f"Validation successful — {len(family_ids)} families "
        f"({sum(1 for f in families if f['_tier'] == 'primitive')} primitive, "
        f"{sum(1 for f in families if f['_tier'] == 'mode')} mode), "
        f"{len(instance_ids)} instances."
    )


if __name__ == "__main__":
    main()
