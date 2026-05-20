#!/usr/bin/env python3

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BUILD_DIR = ROOT / "build"
DB_PATH = BUILD_DIR / "symmetric_primitives.db"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS primitives (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            year INTEGER NOT NULL,
            primitive_type TEXT NOT NULL,
            fixed_input_bits INTEGER NOT NULL,
            fixed_output_bits INTEGER NOT NULL,
            characteristics_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS publications (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            year INTEGER NOT NULL,
            venue TEXT,
            url TEXT,
            authors_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS standards (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            organization TEXT,
            year INTEGER,
            status TEXT
        );

        CREATE TABLE IF NOT EXISTS processes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            organizer TEXT,
            start_year INTEGER,
            end_year INTEGER,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS primitive_targets (
            primitive_id TEXT NOT NULL,
            target TEXT NOT NULL,
            PRIMARY KEY (primitive_id, target),
            FOREIGN KEY (primitive_id) REFERENCES primitives(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS primitive_operations (
            primitive_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            PRIMARY KEY (primitive_id, operation),
            FOREIGN KEY (primitive_id) REFERENCES primitives(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS primitive_components (
            primitive_id TEXT NOT NULL,
            component TEXT NOT NULL,
            PRIMARY KEY (primitive_id, component),
            FOREIGN KEY (primitive_id) REFERENCES primitives(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS primitive_publications (
            primitive_id TEXT NOT NULL,
            publication_id TEXT NOT NULL,
            PRIMARY KEY (primitive_id, publication_id),
            FOREIGN KEY (primitive_id) REFERENCES primitives(id) ON DELETE CASCADE,
            FOREIGN KEY (publication_id) REFERENCES publications(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS primitive_standards (
            primitive_id TEXT NOT NULL,
            standard_id TEXT NOT NULL,
            PRIMARY KEY (primitive_id, standard_id),
            FOREIGN KEY (primitive_id) REFERENCES primitives(id) ON DELETE CASCADE,
            FOREIGN KEY (standard_id) REFERENCES standards(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS primitive_processes (
            primitive_id TEXT NOT NULL,
            process_id TEXT NOT NULL,
            PRIMARY KEY (primitive_id, process_id),
            FOREIGN KEY (primitive_id) REFERENCES primitives(id) ON DELETE CASCADE,
            FOREIGN KEY (process_id) REFERENCES processes(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS primitive_influences (
            source_primitive_id TEXT NOT NULL,
            target_primitive_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            note TEXT NOT NULL,
            PRIMARY KEY (source_primitive_id, target_primitive_id, relation),
            FOREIGN KEY (source_primitive_id) REFERENCES primitives(id) ON DELETE CASCADE,
            FOREIGN KEY (target_primitive_id) REFERENCES primitives(id) ON DELETE CASCADE
        );
        """
    )


def clear_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DELETE FROM primitive_influences;
        DELETE FROM primitive_processes;
        DELETE FROM primitive_standards;
        DELETE FROM primitive_publications;
        DELETE FROM primitive_components;
        DELETE FROM primitive_operations;
        DELETE FROM primitive_targets;
        DELETE FROM processes;
        DELETE FROM standards;
        DELETE FROM publications;
        DELETE FROM primitives;
        """
    )


def main() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    primitives_doc = load_yaml(DATA_DIR / "primitives.yaml")
    publications_doc = load_yaml(DATA_DIR / "publications.yaml")
    standards_doc = load_yaml(DATA_DIR / "standards.yaml")
    processes_doc = load_yaml(DATA_DIR / "processes.yaml")

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_schema(conn)
        clear_tables(conn)

        for pub in publications_doc.get("publications", []):
            conn.execute(
                """
                INSERT INTO publications (id, kind, title, year, venue, url, authors_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pub["id"],
                    pub["kind"],
                    pub["title"],
                    pub["year"],
                    pub.get("venue"),
                    pub.get("url"),
                    json.dumps(pub.get("authors", []), ensure_ascii=True),
                ),
            )

        for std in standards_doc.get("standards", []):
            conn.execute(
                """
                INSERT INTO standards (id, name, organization, year, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    std["id"],
                    std["name"],
                    std.get("organization"),
                    std.get("year"),
                    std.get("status"),
                ),
            )

        for process in processes_doc.get("processes", []):
            conn.execute(
                """
                INSERT INTO processes (id, name, organizer, start_year, end_year, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    process["id"],
                    process["name"],
                    process.get("organizer"),
                    process.get("start_year"),
                    process.get("end_year"),
                    process.get("notes"),
                ),
            )

        for primitive in primitives_doc.get("primitives", []):
            c = primitive["characteristics"]
            conn.execute(
                """
                INSERT INTO primitives (
                    id, name, year, primitive_type,
                    fixed_input_bits, fixed_output_bits, characteristics_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    primitive["id"],
                    primitive["name"],
                    primitive["year"],
                    primitive["primitive_type"],
                    c["fixed_input_bits"],
                    c["fixed_output_bits"],
                    json.dumps(c, ensure_ascii=True),
                ),
            )

            for target in primitive.get("target_applications", []):
                conn.execute(
                    "INSERT INTO primitive_targets (primitive_id, target) VALUES (?, ?)",
                    (primitive["id"], target),
                )

            for op in c.get("operations", []):
                conn.execute(
                    "INSERT INTO primitive_operations (primitive_id, operation) VALUES (?, ?)",
                    (primitive["id"], op),
                )

            for component in c.get("components", []):
                conn.execute(
                    "INSERT INTO primitive_components (primitive_id, component) VALUES (?, ?)",
                    (primitive["id"], component),
                )

            for pub_id in primitive.get("publication_ids", []):
                conn.execute(
                    "INSERT INTO primitive_publications (primitive_id, publication_id) VALUES (?, ?)",
                    (primitive["id"], pub_id),
                )

            for std_id in primitive.get("standard_ids", []):
                conn.execute(
                    "INSERT INTO primitive_standards (primitive_id, standard_id) VALUES (?, ?)",
                    (primitive["id"], std_id),
                )

            for process_id in primitive.get("process_ids", []):
                conn.execute(
                    "INSERT INTO primitive_processes (primitive_id, process_id) VALUES (?, ?)",
                    (primitive["id"], process_id),
                )

            for edge in primitive.get("influences", []):
                conn.execute(
                    """
                    INSERT INTO primitive_influences (
                        source_primitive_id, target_primitive_id, relation, note
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        edge["source_primitive_id"],
                        primitive["id"],
                        edge["relation"],
                        edge["note"],
                    ),
                )

        conn.commit()
        print(f"Database built: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
