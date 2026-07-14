#!/usr/bin/env python3
"""Test: the influences graph has no cycles.

The genealogy visualization (Genealogy tab, radial layout in particular)
builds a spanning tree from the influence edges and recurses over it; a
cycle causes unbounded recursion and the plot silently fails to render
(only noticeable once a year-range filter happens to cut the cycle).

A cycle usually means either an edge was attached to the wrong family (e.g.
a "vN" split exists and the edge belongs on the later version, not the
original — see subterranean vs subterranean_2_0), or two edges recording
the same relationship were added in opposite directions.
"""
from __future__ import annotations

from collections import defaultdict

from common import all_families, load_all_data


def find_cycle(adj: dict[str, list[str]]) -> list[str] | None:
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = defaultdict(int)

    def dfs(u: str, path: list[str], path_set: set[str]) -> list[str] | None:
        color[u] = GRAY
        path.append(u)
        path_set.add(u)
        for v in adj.get(u, []):
            if v in path_set:
                idx = path.index(v)
                return path[idx:] + [v]
            if color[v] == WHITE:
                found = dfs(v, path, path_set)
                if found:
                    return found
        path.pop()
        path_set.discard(u)
        color[u] = BLACK
        return None

    for node in list(adj):
        if color[node] == WHITE:
            found = dfs(node, [], set())
            if found:
                return found
    return None


def main() -> None:
    data = load_all_data(["primitive_families", "mode_families"])
    families = all_families(data)

    adj: dict[str, list[str]] = defaultdict(list)
    for f in families:
        for inf in f.get("influences", []):
            adj[inf["source_family_id"]].append(f["id"])

    cycle = find_cycle(adj)
    if cycle:
        print("INFLUENCES CYCLE DETECTED:")
        print(f"  {' -> '.join(cycle)}")
        print("  This breaks the radial genealogy plot (unbounded recursion). "
              "Remove or redirect one of these edges.")
        raise SystemExit(1)

    print(f"Influences acyclic OK — checked {sum(len(v) for v in adj.values())} edges "
          f"across {len(families)} families.")


if __name__ == "__main__":
    main()
