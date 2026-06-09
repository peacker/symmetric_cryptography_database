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
            SELECT p.id AS primitive_id, p.name, f.year,
                   f.id AS family_id, f.name AS family_name,
                     pt.name AS primitive_type,
                   p.fixed_input_bits, p.fixed_output_bits
            FROM primitives p
            JOIN families f ON f.id = p.family_id
                 JOIN primitive_types pt ON pt.id = p.primitive_type
            ORDER BY f.year, p.name
            """,
            VIZ_DIR / "timeline_primitives.csv",
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
            SELECT p.id AS primitive_id, p.name, t.target
            FROM primitives p
            JOIN families f ON f.id = p.family_id
            JOIN family_targets t ON t.family_id = f.id
            ORDER BY p.name, t.target
            """,
            VIZ_DIR / "primitive_targets.csv",
        )

        # Instance-level standards
        export_query(
            conn,
            """
                 SELECT p.id AS primitive_id, p.name,
                     ref.id AS standard_id, ref.title AS standard_name
            FROM primitives p
            JOIN primitive_standards ps ON ps.primitive_id = p.id
                JOIN "references" ref ON ref.id = ps.standard_id
                 ORDER BY p.name, ref.title
            """,
            VIZ_DIR / "primitive_standards.csv",
        )

        # Processes per instance (via family)
        export_query(
            conn,
            """
            SELECT p.id AS primitive_id, p.name,
                   pr.id AS process_id, pr.name AS process_name
            FROM primitives p
            JOIN families f ON f.id = p.family_id
            JOIN family_processes fp ON fp.family_id = f.id
            JOIN processes pr ON pr.id = fp.process_id
            ORDER BY p.name, pr.name
            """,
            VIZ_DIR / "primitive_processes.csv",
        )

        # Family summary
        export_query(
            conn,
            """
            SELECT f.id AS family_id, f.name AS family_name,
                  f.year,
                  CASE WHEN COUNT(DISTINCT p.primitive_type) = 1
                      THEN MAX(pt.name)
                      ELSE 'Mixed'
                  END AS primitive_type,
                 GROUP_CONCAT(DISTINCT c.name) AS constructions,
                   COUNT(p.id) AS instance_count
            FROM families f
            LEFT JOIN primitives p ON p.family_id = f.id
              LEFT JOIN primitive_types pt ON pt.id = p.primitive_type
              LEFT JOIN family_constructions fc ON fc.family_id = f.id
              LEFT JOIN constructions c ON c.id = fc.construction_id
            GROUP BY f.id
            ORDER BY f.year, f.name
            """,
            VIZ_DIR / "families.csv",
        )

        print(f"Visualization exports created in: {VIZ_DIR}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
