#!/usr/bin/env python3
"""Test: every family in families.yaml has at least one instance in primitives.yaml.

A family with zero primitive instances is either missing data entry work or a
leftover placeholder that should be removed.
"""
from __future__ import annotations

from common import load_all_data


def main() -> None:
    data = load_all_data(["families", "primitives"])
    families_doc = data["families"]
    primitives_doc = data["primitives"]

    family_ids = {f["id"] for f in families_doc.get("families", [])}
    covered_family_ids = {p["family_id"] for p in primitives_doc.get("primitives", [])}

    uncovered = family_ids - covered_family_ids

    if uncovered:
        print(f"FAMILY COVERAGE ERRORS ({len(uncovered)}):")
        for fid in sorted(uncovered):
            print(f"  family '{fid}' has no instance in primitives.yaml")
        raise SystemExit(1)

    print(f"Family coverage OK — checked {len(family_ids)} families"
          f" against {len(primitives_doc['primitives'])} primitive instances.")


if __name__ == "__main__":
    main()
