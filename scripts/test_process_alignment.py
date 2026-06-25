#!/usr/bin/env python3
"""Test: bidirectional consistency between processes.yaml stages and families.yaml process_participations.

Rules checked:
  A. Every family_id listed as a participant in a process stage must appear in families.yaml.
  B. Every stage_id in a family's process_participations must exist as a stage in the
     corresponding process.
  C. Every family that lists a process in process_participations must appear as a participant
     (family_id) in at least one stage of that process (when the process has stages defined).
  D. Every family_id participant in a process stage must have a matching process_participation
     entry pointing to that process.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    families_doc = load_yaml(DATA_DIR / "families.yaml")
    processes_doc = load_yaml(DATA_DIR / "processes.yaml")

    family_ids = {f["id"] for f in families_doc.get("families", [])}

    # Index: family_id → set of (process_id, frozenset of stage_ids)
    family_participation: dict[str, dict[str, frozenset[str]]] = {}
    for fam in families_doc.get("families", []):
        fid = fam["id"]
        family_participation[fid] = {}
        for pp in fam.get("process_participations", []):
            proc_id = pp["process_id"]
            stage_ids = frozenset(pp.get("stage_ids", []))
            family_participation[fid][proc_id] = stage_ids

    # Index: process_id → {stage_id → set of family_ids}
    process_stage_families: dict[str, dict[str, set[str]]] = {}
    # Index: process_id → set of stage_ids
    process_stage_ids: dict[str, set[str]] = {}

    for proc in processes_doc.get("processes", []):
        pid = proc["id"]
        process_stage_families[pid] = {}
        process_stage_ids[pid] = set()
        for stage in proc.get("stages", []):
            sid = stage["id"]
            process_stage_ids[pid].add(sid)
            process_stage_families[pid][sid] = set()
            for participant in stage.get("participants", []):
                fid = participant.get("family_id")
                if fid:
                    process_stage_families[pid][sid].add(fid)

    errors: list[str] = []

    # Rule A: family_id in stage participants must exist in families.yaml
    for proc in processes_doc.get("processes", []):
        pid = proc["id"]
        for stage in proc.get("stages", []):
            sid = stage["id"]
            for participant in stage.get("participants", []):
                fid = participant.get("family_id")
                if fid and fid not in family_ids:
                    errors.append(
                        f"[A] process '{pid}' stage '{sid}' lists unknown family_id '{fid}'"
                    )

    # Rule B: stage_ids in family process_participations must exist in that process
    for fam in families_doc.get("families", []):
        fid = fam["id"]
        for pp in fam.get("process_participations", []):
            proc_id = pp["process_id"]
            valid_stages = process_stage_ids.get(proc_id, set())
            if not valid_stages:
                continue  # process has no stages defined — skip
            for sid in pp.get("stage_ids", []):
                if sid not in valid_stages:
                    errors.append(
                        f"[B] family '{fid}' references unknown stage '{sid}'"
                        f" in process '{proc_id}'"
                    )

    # Rule C: if a family claims process X, it must appear as a participant
    #          in at least one stage of process X (when stages are defined)
    for fam in families_doc.get("families", []):
        fid = fam["id"]
        for pp in fam.get("process_participations", []):
            proc_id = pp["process_id"]
            stages = process_stage_families.get(proc_id, {})
            if not stages:
                continue  # no stages defined — skip
            appears_in_any_stage = any(
                fid in stage_fids for stage_fids in stages.values()
            )
            if not appears_in_any_stage:
                errors.append(
                    f"[C] family '{fid}' claims process '{proc_id}' but is not listed"
                    f" as a participant (family_id) in any stage of that process"
                )

    # Rule D: every family_id participant in a process stage must have a
    #          process_participation entry for that process
    for proc in processes_doc.get("processes", []):
        pid = proc["id"]
        for stage in proc.get("stages", []):
            sid = stage["id"]
            for participant in stage.get("participants", []):
                fid = participant.get("family_id")
                if not fid:
                    continue
                if fid not in family_ids:
                    continue  # already caught by rule A
                if pid not in family_participation.get(fid, {}):
                    errors.append(
                        f"[D] process '{pid}' stage '{sid}' lists family '{fid}'"
                        f" but that family has no process_participations entry for '{pid}'"
                    )

    if errors:
        print(f"ALIGNMENT ERRORS ({len(errors)}):")
        for e in sorted(errors):
            print(f"  {e}")
        raise SystemExit(1)

    print(f"Process alignment OK — checked {len(families_doc['families'])} families"
          f" and {len(processes_doc['processes'])} processes.")


if __name__ == "__main__":
    main()
