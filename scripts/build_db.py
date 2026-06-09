#!/usr/bin/env python3

from __future__ import annotations

import json
import hashlib
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

        -- Reference tables -------------------------------------------------
        CREATE TABLE IF NOT EXISTS "references" (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            year INTEGER NOT NULL,
            venue TEXT,
            url TEXT,
            authors_json TEXT NOT NULL,
            organization TEXT,
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

        CREATE TABLE IF NOT EXISTS components (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            special_case_of TEXT,
            parameters_json TEXT,
            notes TEXT,
            FOREIGN KEY (special_case_of) REFERENCES components(id)
        );

        CREATE TABLE IF NOT EXISTS primitive_types (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS constructions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            special_case_of TEXT,
            notes TEXT,
            FOREIGN KEY (special_case_of) REFERENCES constructions(id)
        );

        CREATE TABLE IF NOT EXISTS rounds (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            spec_json TEXT NOT NULL,
            round_hash TEXT NOT NULL,
            notes TEXT
        );

        -- Families ---------------------------------------------------------
        CREATE TABLE IF NOT EXISTS families (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            year INTEGER,
            notes TEXT,
            characteristics_json TEXT NOT NULL,
            innovative_ideas_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS family_targets (
            family_id TEXT NOT NULL,
            target TEXT NOT NULL,
            PRIMARY KEY (family_id, target),
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS family_components (
            family_id    TEXT NOT NULL,
            component_id TEXT NOT NULL,
            params_json  TEXT,
            PRIMARY KEY (family_id, component_id),
            FOREIGN KEY (family_id)    REFERENCES families(id)   ON DELETE CASCADE,
            FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS family_constructions (
            family_id TEXT NOT NULL,
            construction_id TEXT NOT NULL,
            PRIMARY KEY (family_id, construction_id),
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
            FOREIGN KEY (construction_id) REFERENCES constructions(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS family_rounds (
            family_id TEXT NOT NULL,
            round_id TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'primary',
            PRIMARY KEY (family_id, round_id),
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
            FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS family_references (
            family_id TEXT NOT NULL,
            reference_id TEXT NOT NULL,
            PRIMARY KEY (family_id, reference_id),
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
            FOREIGN KEY (reference_id) REFERENCES "references"(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS family_standards (
            family_id TEXT NOT NULL,
            standard_id TEXT NOT NULL,
            PRIMARY KEY (family_id, standard_id),
            FOREIGN KEY (family_id)   REFERENCES families(id)      ON DELETE CASCADE,
            FOREIGN KEY (standard_id) REFERENCES "references"(id)  ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS family_processes (
            family_id TEXT NOT NULL,
            process_id TEXT NOT NULL,
            PRIMARY KEY (family_id, process_id),
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
            FOREIGN KEY (process_id) REFERENCES processes(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS family_influences (
            source_family_id TEXT NOT NULL,
            target_family_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            relations_json TEXT NOT NULL,
            innovative_idea_ids_json TEXT,
            note TEXT NOT NULL,
            PRIMARY KEY (source_family_id, target_family_id),
            FOREIGN KEY (source_family_id) REFERENCES families(id) ON DELETE CASCADE,
            FOREIGN KEY (target_family_id) REFERENCES families(id) ON DELETE CASCADE
        );

        -- Primitive instances ----------------------------------------------
        CREATE TABLE IF NOT EXISTS primitives (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            family_id TEXT NOT NULL,
            primitive_type TEXT NOT NULL,
            fixed_input_bits INTEGER NOT NULL,
            fixed_output_bits INTEGER NOT NULL,
            characteristics_json TEXT NOT NULL,
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE RESTRICT,
            FOREIGN KEY (primitive_type) REFERENCES primitive_types(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS primitive_standards (
            primitive_id TEXT NOT NULL,
            standard_id TEXT NOT NULL,
            PRIMARY KEY (primitive_id, standard_id),
            FOREIGN KEY (primitive_id) REFERENCES primitives(id)   ON DELETE CASCADE,
            FOREIGN KEY (standard_id)  REFERENCES "references"(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS primitive_references (
            primitive_id TEXT NOT NULL,
            reference_id TEXT NOT NULL,
            PRIMARY KEY (primitive_id, reference_id),
            FOREIGN KEY (primitive_id) REFERENCES primitives(id)   ON DELETE CASCADE,
            FOREIGN KEY (reference_id) REFERENCES "references"(id) ON DELETE RESTRICT
        );
        """
    )


def clear_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DELETE FROM primitive_references;
        DELETE FROM primitive_standards;
        DELETE FROM primitives;
        DELETE FROM family_influences;
        DELETE FROM family_processes;
        DELETE FROM family_standards;
        DELETE FROM family_references;
        DELETE FROM family_constructions;
        DELETE FROM family_rounds;
        DELETE FROM family_components;
        DELETE FROM family_targets;
        DELETE FROM families;
        DELETE FROM rounds;
        DELETE FROM constructions;
        DELETE FROM primitive_types;
        DELETE FROM components;
        DELETE FROM processes;
        DELETE FROM "references";
        """
    )


def main() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.unlink(missing_ok=True)  # always rebuild from scratch

    families_doc     = load_yaml(DATA_DIR / "families.yaml")
    primitives_doc   = load_yaml(DATA_DIR / "primitives.yaml")
    components_doc   = load_yaml(DATA_DIR / "components.yaml")
    constructions_doc = load_yaml(DATA_DIR / "constructions.yaml")
    rounds_doc       = load_yaml(DATA_DIR / "rounds.yaml")
    primitive_types_doc = load_yaml(DATA_DIR / "primitive_types.yaml")
    references_doc = load_yaml(DATA_DIR / "references.yaml")
    processes_doc    = load_yaml(DATA_DIR / "processes.yaml")

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_schema(conn)
        clear_tables(conn)

        references_by_id = {r["id"]: r for r in references_doc.get("references", [])}

        for ref in references_doc.get("references", []):
            conn.execute(
                "INSERT INTO \"references\""
                " (id, kind, title, year, venue, url, authors_json, organization, status)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ref["id"],
                    ref["kind"],
                    ref["title"],
                    ref["year"],
                    ref.get("venue"),
                    ref.get("url"),
                    json.dumps(ref.get("authors", []), ensure_ascii=True),
                    ref.get("organization") or ref.get("publisher") or ref.get("institution"),
                    ref.get("status"),
                ),
            )

        family_reference_ids: dict[str, set[str]] = {}

        for process in processes_doc.get("processes", []):
            conn.execute(
                "INSERT INTO processes (id, name, organizer, start_year, end_year, notes)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (process["id"], process["name"], process.get("organizer"),
                 process.get("start_year"), process.get("end_year"), process.get("notes")),
            )

        for comp in components_doc.get("components", []):
            params = comp.get("parameters")
            conn.execute(
                "INSERT INTO components"
                " (id, name, category, special_case_of, parameters_json, notes)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (comp["id"], comp["name"], comp["category"],
                 comp.get("special_case_of"),
                 json.dumps(params, ensure_ascii=True) if params else None,
                 comp.get("notes")),
            )

        for primitive_type in primitive_types_doc.get("primitive_types", []):
            conn.execute(
                "INSERT INTO primitive_types (id, name, notes) VALUES (?, ?, ?)",
                (primitive_type["id"], primitive_type["name"], primitive_type.get("notes")),
            )

        for construction in constructions_doc.get("constructions", []):
            conn.execute(
                "INSERT INTO constructions (id, name, special_case_of, notes) VALUES (?, ?, ?, ?)",
                (
                    construction["id"],
                    construction["name"],
                    construction.get("special_case_of"),
                    construction.get("notes"),
                ),
            )

        for round_def in rounds_doc.get("rounds", []):
            spec = round_def.get("spec", {})
            spec_json = json.dumps(spec, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            round_hash = hashlib.sha256(spec_json.encode("utf-8")).hexdigest()
            conn.execute(
                "INSERT INTO rounds (id, name, kind, spec_json, round_hash, notes)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    round_def["id"],
                    round_def["name"],
                    round_def["kind"],
                    spec_json,
                    round_hash,
                    round_def.get("notes"),
                ),
            )

        for family in families_doc.get("families", []):
            c = family["characteristics"]
            innovative_ideas = family.get("innovative_ideas", [])
            ref_ids = family.get("reference_ids", [])
            family_year_candidates = [
                references_by_id[ref_id].get("year")
                for ref_id in ref_ids
                if ref_id in references_by_id and isinstance(references_by_id[ref_id].get("year"), int)
            ]
            family_year = min(family_year_candidates) if family_year_candidates else None

            conn.execute(
                "INSERT INTO families (id, name, year, notes, characteristics_json, innovative_ideas_json)"
                 " VALUES (?, ?, ?, ?, ?, ?)",
                 (family["id"], family["name"], family_year,
                  family.get("notes"), json.dumps(c, ensure_ascii=True),
                  json.dumps(innovative_ideas, ensure_ascii=True)),
            )
            for target in family.get("target_applications", []):
                conn.execute(
                    "INSERT INTO family_targets (family_id, target) VALUES (?, ?)",
                    (family["id"], target))
            for comp_ref in c.get("components", []):
                params = comp_ref.get("params")
                conn.execute(
                    "INSERT INTO family_components (family_id, component_id, params_json)"
                    " VALUES (?, ?, ?)",
                    (family["id"], comp_ref["id"],
                     json.dumps(params, ensure_ascii=True) if params else None))
            for construction_id in family.get("construction_ids", []):
                conn.execute(
                    "INSERT INTO family_constructions (family_id, construction_id) VALUES (?, ?)",
                    (family["id"], construction_id),
                )
            for round_id in family.get("round_ids", []):
                conn.execute(
                    "INSERT INTO family_rounds (family_id, round_id, role) VALUES (?, ?, ?)",
                    (family["id"], round_id, "primary"),
                )
            std_ids_for_family: set[str] = set()
            refs_for_family: set[str] = set()
            for ref_id in ref_ids:
                refs_for_family.add(ref_id)
                ref_kind = str(references_by_id.get(ref_id, {}).get("kind", "")).lower()
                if "standard" in ref_kind:
                    conn.execute(
                        "INSERT INTO family_standards (family_id, standard_id) VALUES (?, ?)",
                        (family["id"], ref_id),
                    )
                    std_ids_for_family.add(ref_id)
                else:
                    conn.execute(
                        "INSERT INTO family_references (family_id, reference_id) VALUES (?, ?)",
                        (family["id"], ref_id),
                    )
            family_reference_ids[family["id"]] = refs_for_family
            for process_id in family.get("process_ids", []):
                conn.execute(
                    "INSERT INTO family_processes (family_id, process_id) VALUES (?, ?)",
                    (family["id"], process_id))
            for edge in family.get("influences", []):
                relations = edge.get("relations") or ([edge["relation"]] if edge.get("relation") else [])
                innovative_idea_ids = edge.get("innovative_idea_ids", [])
                primary_relation = relations[0] if relations else "related_to"
                conn.execute(
                    "INSERT INTO family_influences"
                    " (source_family_id, target_family_id, relation, relations_json, innovative_idea_ids_json, note)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (edge["source_family_id"], family["id"],
                     primary_relation,
                     json.dumps(relations, ensure_ascii=True),
                     json.dumps(innovative_idea_ids, ensure_ascii=True) if innovative_idea_ids else None,
                     edge["note"]))

        for primitive in primitives_doc.get("primitives", []):
            c = primitive["characteristics"]
            primitive_ref_ids = set(primitive.get("reference_ids", []))
            if not primitive_ref_ids:
                primitive_ref_ids = set(family_reference_ids.get(primitive["family_id"], set()))

            conn.execute(
                "INSERT INTO primitives"
                " (id, name, family_id, primitive_type, fixed_input_bits, fixed_output_bits,"
                "  characteristics_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (primitive["id"], primitive["name"], primitive["family_id"], primitive["primitive_type"],
                 c["fixed_input_bits"], c["fixed_output_bits"],
                 json.dumps(c, ensure_ascii=True)),
            )

            for ref_id in sorted(primitive_ref_ids):
                conn.execute(
                    "INSERT INTO primitive_references (primitive_id, reference_id) VALUES (?, ?)",
                    (primitive["id"], ref_id),
                )

            for ref_id in sorted(primitive_ref_ids):
                ref_kind = str(references_by_id.get(ref_id, {}).get("kind", "")).lower()
                if "standard" not in ref_kind:
                    continue
                conn.execute(
                    "INSERT INTO primitive_standards (primitive_id, standard_id) VALUES (?, ?)",
                    (primitive["id"], ref_id),
                )

        conn.commit()
        print(f"Database built: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()



