#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BUILD_DIR = ROOT / "build"
SCHEMA_DIR = ROOT / "schema"
DB_PATH = BUILD_DIR / "symmetric_primitives.db"

DATA_FILES = {
    "primitive_families": "primitive_families.yaml",
    "mode_families": "mode_families.yaml",
    "components": "components.yaml",
    "primitive_constructions": "primitive_constructions.yaml",
    "mode_constructions": "mode_constructions.yaml",
    "rounds": "rounds.yaml",
    "primitive_types": "primitive_types.yaml",
    "mode_types": "mode_types.yaml",
    "references": "references.yaml",
    "processes": "processes.yaml",
    "timeline": "timeline.yaml",
}


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_data(names: list[str] | None = None) -> dict[str, dict]:
    """Load a subset (or all) of the standard data/*.yaml documents.

    Returns a dict keyed by the short names in DATA_FILES, e.g. "primitive_families" -> parsed doc.
    """
    keys = names if names is not None else list(DATA_FILES.keys())
    return {name: load_yaml(DATA_DIR / DATA_FILES[name]) for name in keys}


def all_families(data: dict[str, dict]) -> list[dict]:
    """Concatenate primitive_families and mode_families, each tagged with its tier.

    Family ids are unique across both tiers, so influence edges, process
    participation, and coverage checks can treat this as one flat namespace.
    """
    out = []
    for fam in data["primitive_families"].get("primitive_families", []):
        tagged = dict(fam)
        tagged["_tier"] = "primitive"
        out.append(tagged)
    for fam in data["mode_families"].get("mode_families", []):
        tagged = dict(fam)
        tagged["_tier"] = "mode"
        out.append(tagged)
    return out


def all_instances(families: list[dict]) -> list[dict]:
    """Flatten every family's nested instances into a flat list, injecting
    family_id/_tier back in so downstream code can treat it like the old
    flat primitives.yaml rows."""
    out = []
    for fam in families:
        for inst in fam.get("instances", []):
            flat = dict(inst)
            flat["family_id"] = fam["id"]
            flat["_tier"] = fam.get("_tier")
            out.append(flat)
    return out


def family_year(family: dict, references_by_id: dict[str, dict]) -> int | None:
    """Earliest integer year among a family's references, or None if unknown.

    This is the same "family year" shown in the genealogy visualization
    (see build_db.py), kept here so other scripts agree with what's displayed.
    """
    candidates = [
        references_by_id[ref_id]["year"]
        for ref_id in family.get("reference_ids", [])
        if ref_id in references_by_id and isinstance(references_by_id[ref_id].get("year"), int)
    ]
    return min(candidates) if candidates else None


def round_component_flow_signature(round_entry: dict) -> str:
    """Normalized signature of a round's component sequence, ignoring the
    per-step params (bit widths, moduli, ...).

    This is a coarser equivalence than the full-spec round_hash computed in
    build_db.py: two rounds with the same signature use the same sequence of
    component kinds (e.g. "xor|sbox|binary_matrix_mul") even if a parameter
    differs, whereas round_hash only matches byte-identical specs.
    """
    flow = ((round_entry.get("spec") or {}).get("component_flow")) or []
    return "|".join(str(step.get("component_id", "")) for step in flow)


def construction_leaf_ids(data: dict[str, dict]) -> set[str]:
    """Ids of every level-2 construction (one with special_case_of set), across
    both the primitive and mode construction catalogues.

    Only leaves participate in derived construction-sharing edges -- sharing a
    level-1 root (e.g. two families both merely tagged "spn" with no more
    specific leaf) is too broad to be a meaningful relation.
    """
    leaves: set[str] = set()
    for key in ("primitive_constructions", "mode_constructions"):
        for construction in data[key].get(key, []):
            if construction.get("special_case_of"):
                leaves.add(construction["id"])
    return leaves


def compute_construction_sharing_edges(
    families: list[dict],
    leaf_ids: set[str],
    references_by_id: dict[str, dict],
) -> list[tuple[str, str, str]]:
    """Derive (source_family_id, target_family_id, construction_id) edges from
    shared level-2 construction tags, direction older -> newer.

    For each construction leaf, every family tagged with it is chronologically
    ordered by family_year(); each family links only to its nearest earlier
    neighbor sharing that same leaf, forming a chronological chain per leaf
    rather than a fully-connected graph (which would be O(n^2) for a popular
    leaf like balanced_feistel). Families with no resolvable year are skipped
    since there is no defined direction for them.
    """
    by_leaf: dict[str, list[tuple[int, str]]] = {}
    for family in families:
        year = family_year(family, references_by_id)
        if year is None:
            continue
        for construction_id in family.get("construction_ids", []) or []:
            if construction_id in leaf_ids:
                by_leaf.setdefault(construction_id, []).append((year, family["id"]))

    edges: list[tuple[str, str, str]] = []
    for construction_id, members in by_leaf.items():
        members.sort(key=lambda pair: (pair[0], pair[1]))
        for (_, earlier_id), (_, later_id) in zip(members, members[1:]):
            if earlier_id == later_id:
                continue
            edges.append((earlier_id, later_id, construction_id))
    return edges
