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
        export_query(
            conn,
            """
            SELECT id AS primitive_id, name, year, primitive_type,
                   fixed_input_bits, fixed_output_bits
            FROM primitives
            ORDER BY year, name
            """,
            VIZ_DIR / "timeline_primitives.csv",
        )

        export_query(
            conn,
            """
            SELECT source_primitive_id, target_primitive_id, relation, note
            FROM primitive_influences
            ORDER BY source_primitive_id, target_primitive_id
            """,
            VIZ_DIR / "influence_edges.csv",
        )

        export_query(
            conn,
            """
            SELECT p.id AS primitive_id, p.name, t.target
            FROM primitives p
            JOIN primitive_targets t ON t.primitive_id = p.id
            ORDER BY p.name, t.target
            """,
            VIZ_DIR / "primitive_targets.csv",
        )

        export_query(
            conn,
            """
            SELECT p.id AS primitive_id, p.name, s.id AS standard_id, s.name AS standard_name
            FROM primitives p
            JOIN primitive_standards ps ON ps.primitive_id = p.id
            JOIN standards s ON s.id = ps.standard_id
            ORDER BY p.name, s.name
            """,
            VIZ_DIR / "primitive_standards.csv",
        )

        export_query(
            conn,
            """
            SELECT p.id AS primitive_id, p.name, pr.id AS process_id, pr.name AS process_name
            FROM primitives p
            JOIN primitive_processes pp ON pp.primitive_id = p.id
            JOIN processes pr ON pr.id = pp.process_id
            ORDER BY p.name, pr.name
            """,
            VIZ_DIR / "primitive_processes.csv",
        )

        print(f"Visualization exports created in: {VIZ_DIR}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
