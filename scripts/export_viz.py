#!/usr/bin/env python3

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "build" / "symmetric_primitives.db"
VIZ_DIR = ROOT / "build" / "viz"


def export_query(conn: sqlite3.Connection, query: str, out_path: Path) -> None:
    rows = conn.execute(query).fetchall()
    headers = [d[0] for d in conn.execute(query).description]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit("Database not found. Run scripts/build_db.py first.")

    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        # Instances enriched with family metadata for timeline / scatter
        export_query(
            conn,
            """
            SELECT i.id AS instance_id, i.name, f.year,
                   f.id AS family_id, f.name AS family_name, f.tier,
                   COALESCE(pt.name, mt.name) AS type_name,
                   i.block_size_bits, i.output_size_bits
            FROM instances i
            JOIN families f ON f.id = i.family_id
            LEFT JOIN primitive_types pt ON pt.id = i.type_id
            LEFT JOIN mode_types mt ON mt.id = i.type_id
            ORDER BY f.year, i.name
            """,
            VIZ_DIR / "timeline_instances.csv",
        )

        # Family-level influence edges
        export_query(
            conn,
            """
            SELECT fi.source_family_id,
                   sf.name AS source_name,
                   fi.target_family_id,
                   tf.name AS target_name,
                 fi.relation, fi.relations_json, fi.innovative_idea_ids_json, fi.note
            FROM family_influences fi
            JOIN families sf ON sf.id = fi.source_family_id
            JOIN families tf ON tf.id = fi.target_family_id
            ORDER BY fi.source_family_id, fi.target_family_id
            """,
            VIZ_DIR / "influence_edges.csv",
        )

        # Applications per instance (via family)
        export_query(
            conn,
            """
            SELECT i.id AS instance_id, i.name, t.target
            FROM instances i
            JOIN families f ON f.id = i.family_id
            JOIN family_targets t ON t.family_id = f.id
            ORDER BY i.name, t.target
            """,
            VIZ_DIR / "instance_targets.csv",
        )

        # Instance-level standards
        export_query(
            conn,
            """
            SELECT i.id AS instance_id, i.name,
                   ref.id AS standard_id, ref.title AS standard_name
            FROM instances i
            JOIN instance_standards ist ON ist.instance_id = i.id
            JOIN "references" ref ON ref.id = ist.standard_id
            ORDER BY i.name, ref.title
            """,
            VIZ_DIR / "instance_standards.csv",
        )

        # Processes per instance (via family)
        export_query(
            conn,
            """
            SELECT i.id AS instance_id, i.name,
                   pr.id AS process_id, pr.name AS process_name
            FROM instances i
            JOIN families f ON f.id = i.family_id
            JOIN family_processes fp ON fp.family_id = f.id
            JOIN processes pr ON pr.id = fp.process_id
            ORDER BY i.name, pr.name
            """,
            VIZ_DIR / "instance_processes.csv",
        )

        # Family summary
        export_query(
            conn,
            """
            SELECT f.id AS family_id, f.name AS family_name,
                  f.year, f.tier,
                  CASE WHEN COUNT(DISTINCT i.type_id) = 1
                      THEN MAX(COALESCE(pt.name, mt.name))
                      ELSE 'Mixed'
                  END AS type_name,
                 GROUP_CONCAT(DISTINCT COALESCE(pc.name, mc.name)) AS constructions,
                   COUNT(i.id) AS instance_count
            FROM families f
            LEFT JOIN instances i ON i.family_id = f.id
              LEFT JOIN primitive_types pt ON pt.id = i.type_id
              LEFT JOIN mode_types mt ON mt.id = i.type_id
              LEFT JOIN family_constructions fc ON fc.family_id = f.id
              LEFT JOIN primitive_constructions pc ON pc.id = fc.construction_id
              LEFT JOIN mode_constructions mc ON mc.id = fc.construction_id
            GROUP BY f.id
            ORDER BY f.year, f.name
            """,
            VIZ_DIR / "families.csv",
        )

        # Family process participations with status
        export_query(
            conn,
            """
            SELECT f.id AS family_id, f.name AS family_name,
                   pr.id AS process_id, pr.name AS process_name,
                   fp.status, fp.stage_ids_json
            FROM family_processes fp
            JOIN families f  ON f.id  = fp.family_id
            JOIN processes pr ON pr.id = fp.process_id
            ORDER BY pr.name, fp.status, f.name
            """,
            VIZ_DIR / "family_processes.csv",
        )

        # Process stage participants (family_id and name entries combined)
        export_query(
            conn,
            """
            SELECT pr.id AS process_id, pr.name AS process_name,
                   ps.stage_id, ps.label AS stage_label, ps.kind AS stage_kind,
                   psp.family_id, f.name AS family_name,
                   psp.name AS external_name, psp.note
            FROM process_stage_participants psp
            JOIN process_stages ps ON ps.process_id = psp.process_id AND ps.stage_id = psp.stage_id
            JOIN processes pr ON pr.id = psp.process_id
            LEFT JOIN families f ON f.id = psp.family_id
            ORDER BY pr.name, ps.stage_id, COALESCE(f.name, psp.name)
            """,
            VIZ_DIR / "process_stage_participants.csv",
        )

        print(f"Visualization exports created in: {VIZ_DIR}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
