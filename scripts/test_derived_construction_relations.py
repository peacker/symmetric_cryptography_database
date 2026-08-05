#!/usr/bin/env python3
"""Test: derived construction-sharing edges are well-formed.

These edges are not hand-curated (see data/*_families.yaml) -- they are
computed at build time (scripts/common.py: compute_construction_sharing_edges)
from families sharing the same construction id, level-1 root or level-2 leaf
alike: the earliest-year family is credited as that id's origin and every
later family sharing it is linked directly to it (a star, older -> newer,
not a chronological chain). This test recomputes them directly from the YAML
sources (the same function scripts/build_db.py calls) and checks the
invariants the derivation is supposed to guarantee, so a future change to the
YAML data or the derivation logic can't silently produce a malformed edge.
"""
from __future__ import annotations

from collections import defaultdict

from common import (
    all_families,
    compute_construction_sharing_edges,
    family_year,
    load_all_data,
)


def main() -> None:
    data = load_all_data([
        "primitive_families", "mode_families",
        "primitive_constructions", "mode_constructions", "references",
    ])
    families = all_families(data)
    family_ids = {f["id"] for f in families}
    references_by_id = {r["id"]: r for r in data["references"].get("references", [])}
    years = {f["id"]: family_year(f, references_by_id) for f in families}

    known_construction_ids = {
        construction["id"]
        for key in ("primitive_constructions", "mode_constructions")
        for construction in data[key].get(key, [])
    }
    edges = compute_construction_sharing_edges(families, references_by_id)

    errors: list[str] = []

    for source_id, target_id, construction_id in edges:
        if source_id not in family_ids:
            errors.append(f"edge references unknown source family '{source_id}'")
        if target_id not in family_ids:
            errors.append(f"edge references unknown target family '{target_id}'")
        if source_id == target_id:
            errors.append(f"self-loop on family '{source_id}' via construction '{construction_id}'")
        if construction_id not in known_construction_ids:
            errors.append(
                f"edge {source_id} -> {target_id} uses '{construction_id}', which is not a "
                "known primitive/mode construction id"
            )
        source_year, target_year = years.get(source_id), years.get(target_id)
        if source_year is not None and target_year is not None and source_year > target_year:
            errors.append(
                f"edge {source_id} ({source_year}) -> {target_id} ({target_year}) "
                "runs newer -> older, expected older -> newer"
            )

    # The derivation is a per-construction-id star (origin -> every later
    # member) built from a total order (year, id) with cycle-guarded edge
    # acceptance, so it cannot contain a cycle by construction; check anyway
    # in case a future refactor of compute_construction_sharing_edges breaks
    # that.
    adj: dict[str, list[str]] = defaultdict(list)
    for source_id, target_id, _ in edges:
        adj[source_id].append(target_id)

    def has_cycle() -> bool:
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = defaultdict(int)

        def dfs(u: str, stack: set[str]) -> bool:
            color[u] = GRAY
            stack.add(u)
            for v in adj.get(u, []):
                if v in stack:
                    return True
                if color[v] == WHITE and dfs(v, stack):
                    return True
            stack.discard(u)
            color[u] = BLACK
            return False

        return any(color[node] == WHITE and dfs(node, set()) for node in list(adj))

    if has_cycle():
        errors.append("derived construction-sharing edges contain a cycle")

    if errors:
        print("DERIVED CONSTRUCTION RELATION ERRORS:")
        for err in errors:
            print(f"  {err}")
        raise SystemExit(1)

    distinct_construction_ids = {construction_id for _, _, construction_id in edges}
    print(f"Derived construction relations OK — {len(edges)} edges across "
          f"{len(distinct_construction_ids)} construction ids.")


if __name__ == "__main__":
    main()
