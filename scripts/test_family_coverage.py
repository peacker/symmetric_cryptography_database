#!/usr/bin/env python3
"""Test: family ids and instance ids are globally unique across both tiers.

Every family already requires >=1 instance via the JSON schema (minItems on
"instances"), so the old "family has zero instances" check is now enforced
structurally. What schema validation can't catch is id collisions between
primitive_families and mode_families (they share one namespace: influence
edges and underlying_primitive_ids can point at either tier).
"""
from __future__ import annotations

from collections import Counter

from common import all_families, all_instances, load_all_data


def main() -> None:
    data = load_all_data(["primitive_families", "mode_families"])
    families = all_families(data)
    instances = all_instances(families)

    family_id_counts = Counter(f["id"] for f in families)
    dup_families = [fid for fid, n in family_id_counts.items() if n > 1]

    instance_id_counts = Counter(i["id"] for i in instances)
    dup_instances = [iid for iid, n in instance_id_counts.items() if n > 1]

    errors: list[str] = []
    for fid in sorted(dup_families):
        errors.append(f"family id '{fid}' is used {family_id_counts[fid]} times across primitive/mode families")
    for iid in sorted(dup_instances):
        errors.append(f"instance id '{iid}' is used {instance_id_counts[iid]} times across primitive/mode families")

    if errors:
        print(f"FAMILY COVERAGE ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
        raise SystemExit(1)

    print(f"Family coverage OK — checked {len(families)} families "
          f"against {len(instances)} instances, no id collisions.")


if __name__ == "__main__":
    main()
