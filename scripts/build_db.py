#!/usr/bin/env python3

from __future__ import annotations

import json
import hashlib
import sqlite3

from common import (
    BUILD_DIR,
    DB_PATH,
    all_families,
    all_instances,
    compute_construction_sharing_edges,
    construction_leaf_ids,
    family_year,
    load_all_data,
    round_component_flow_signature,
)


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

        CREATE TABLE IF NOT EXISTS process_stages (
            process_id TEXT NOT NULL,
            stage_id   TEXT NOT NULL,
            label      TEXT NOT NULL,
            kind       TEXT,
            parent_stage_id TEXT,
            PRIMARY KEY (process_id, stage_id),
            FOREIGN KEY (process_id) REFERENCES processes(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS process_stage_participants (
            process_id TEXT NOT NULL,
            stage_id   TEXT NOT NULL,
            family_id  TEXT,
            name       TEXT,
            note       TEXT,
            FOREIGN KEY (process_id, stage_id) REFERENCES process_stages(process_id, stage_id) ON DELETE CASCADE
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

        -- Type/construction catalogues, split by tier -----------------------
        CREATE TABLE IF NOT EXISTS primitive_types (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS mode_types (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS primitive_constructions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            special_case_of TEXT,
            notes TEXT,
            FOREIGN KEY (special_case_of) REFERENCES primitive_constructions(id)
        );

        CREATE TABLE IF NOT EXISTS mode_constructions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            special_case_of TEXT,
            notes TEXT,
            FOREIGN KEY (special_case_of) REFERENCES mode_constructions(id)
        );

        -- component_flow_signature and state_model_json are pulled out of
        -- spec_json into their own columns so the Custom Query Builder can
        -- filter/compare on them directly instead of parsing JSON client
        -- side. round_hash (full spec, exact match) and
        -- component_flow_signature (component-id sequence only, ignoring
        -- params -- a coarser equivalence) are two different granularities
        -- of "these rounds share a structure"; state_model_json is kept as
        -- raw JSON rather than split into columns since its shape varies
        -- widely across round kinds (bit-sliced permutations, LFSR-based
        -- stream ciphers, Feistel halves, ... each use different keys).
        CREATE TABLE IF NOT EXISTS rounds (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            spec_json TEXT NOT NULL,
            round_hash TEXT NOT NULL,
            component_flow_signature TEXT NOT NULL,
            state_model_json TEXT,
            notes TEXT
        );

        -- Families (both tiers, discriminated by "tier") --------------------
        CREATE TABLE IF NOT EXISTS families (
            id TEXT PRIMARY KEY,
            tier TEXT NOT NULL CHECK (tier IN ('primitive', 'mode')),
            name TEXT NOT NULL,
            year INTEGER,
            notes TEXT,
            authors_json TEXT,
            underlying_primitive_ids_json TEXT,
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
            params_json  TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (family_id, component_id, params_json),
            FOREIGN KEY (family_id)    REFERENCES families(id)   ON DELETE CASCADE,
            FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE RESTRICT
        );

        -- Split by tier (mirrors primitive_constructions vs mode_constructions)
        -- so construction_id is FK-checked against the correct catalogue
        -- instead of being resolved against "whichever one matches" at query
        -- time. A primitive-tier family's constructions live here...
        CREATE TABLE IF NOT EXISTS primitive_family_constructions (
            family_id TEXT NOT NULL,
            construction_id TEXT NOT NULL,
            PRIMARY KEY (family_id, construction_id),
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
            FOREIGN KEY (construction_id) REFERENCES primitive_constructions(id) ON DELETE RESTRICT
        );

        -- ...and a mode-tier family's constructions live here.
        CREATE TABLE IF NOT EXISTS mode_family_constructions (
            family_id TEXT NOT NULL,
            construction_id TEXT NOT NULL,
            PRIMARY KEY (family_id, construction_id),
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
            FOREIGN KEY (construction_id) REFERENCES mode_constructions(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS family_rounds (
            family_id TEXT NOT NULL,
            round_id TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'primary',
            PRIMARY KEY (family_id, round_id),
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
            FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE RESTRICT
        );

        -- Holds every reference a family cites, standards included; there is
        -- no separate family_standards table since "is this a standard" is
        -- just references.kind, joinable on demand instead of being forked
        -- into a second, easy-to-forget-to-check junction table.
        CREATE TABLE IF NOT EXISTS family_references (
            family_id TEXT NOT NULL,
            reference_id TEXT NOT NULL,
            PRIMARY KEY (family_id, reference_id),
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
            FOREIGN KEY (reference_id) REFERENCES "references"(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS family_processes (
            family_id  TEXT NOT NULL,
            process_id TEXT NOT NULL,
            status     TEXT,
            stage_ids_json TEXT NOT NULL DEFAULT '[]',
            PRIMARY KEY (family_id, process_id),
            FOREIGN KEY (family_id)  REFERENCES families(id)  ON DELETE CASCADE,
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

        -- Instances (both tiers, discriminated by "tier") -------------------
        -- Derived (not hand-curated) edges: two families tagged with the same
        -- level-2 construction leaf (e.g. both balanced_feistel), chained
        -- chronologically older -> newer. Kept separate from family_influences
        -- since these are computed at build time from construction_ids +
        -- resolved year, not authored facts backed by a citation.
        CREATE TABLE IF NOT EXISTS construction_sharing_edges (
            source_family_id TEXT NOT NULL,
            target_family_id TEXT NOT NULL,
            construction_id TEXT NOT NULL,
            PRIMARY KEY (source_family_id, target_family_id, construction_id),
            FOREIGN KEY (source_family_id) REFERENCES families(id) ON DELETE CASCADE,
            FOREIGN KEY (target_family_id) REFERENCES families(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS instances (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            family_id TEXT NOT NULL,
            tier TEXT NOT NULL CHECK (tier IN ('primitive', 'mode')),
            type_id TEXT NOT NULL,
            block_size_bits INTEGER,
            output_size_bits INTEGER,
            characteristics_json TEXT NOT NULL,
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS instance_references (
            instance_id TEXT NOT NULL,
            reference_id TEXT NOT NULL,
            PRIMARY KEY (instance_id, reference_id),
            FOREIGN KEY (instance_id) REFERENCES instances(id)   ON DELETE CASCADE,
            FOREIGN KEY (reference_id) REFERENCES "references"(id) ON DELETE RESTRICT
        );
        """
    )


def clear_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DELETE FROM instance_references;
        DELETE FROM instances;
        DELETE FROM construction_sharing_edges;
        DELETE FROM family_influences;
        DELETE FROM family_processes;
        DELETE FROM family_references;
        DELETE FROM primitive_family_constructions;
        DELETE FROM mode_family_constructions;
        DELETE FROM family_rounds;
        DELETE FROM family_components;
        DELETE FROM family_targets;
        DELETE FROM families;
        DELETE FROM rounds;
        DELETE FROM primitive_constructions;
        DELETE FROM mode_constructions;
        DELETE FROM primitive_types;
        DELETE FROM mode_types;
        DELETE FROM components;
        DELETE FROM process_stage_participants;
        DELETE FROM process_stages;
        DELETE FROM processes;
        DELETE FROM "references";
        """
    )


def main() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.unlink(missing_ok=True)  # always rebuild from scratch

    data = load_all_data([
        "primitive_families", "mode_families", "components",
        "primitive_constructions", "mode_constructions",
        "rounds", "primitive_types", "mode_types", "references", "processes",
    ])
    components_doc   = data["components"]
    primitive_constructions_doc = data["primitive_constructions"]
    mode_constructions_doc      = data["mode_constructions"]
    rounds_doc       = data["rounds"]
    primitive_types_doc = data["primitive_types"]
    mode_types_doc       = data["mode_types"]
    references_doc = data["references"]
    processes_doc    = data["processes"]

    families = all_families(data)
    instances = all_instances(families)

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
            for stage in process.get("stages", []):
                conn.execute(
                    "INSERT INTO process_stages"
                    " (process_id, stage_id, label, kind, parent_stage_id)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (process["id"], stage["id"], stage["label"],
                     stage.get("kind"), stage.get("parent_stage_id")),
                )
                for participant in stage.get("participants", []):
                    family_id = participant.get("family_id")
                    name = participant.get("name")
                    note = participant.get("note")
                    conn.execute(
                        "INSERT OR IGNORE INTO process_stage_participants"
                        " (process_id, stage_id, family_id, name, note)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (process["id"], stage["id"], family_id, name, note),
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

        for mode_type in mode_types_doc.get("mode_types", []):
            conn.execute(
                "INSERT INTO mode_types (id, name, notes) VALUES (?, ?, ?)",
                (mode_type["id"], mode_type["name"], mode_type.get("notes")),
            )

        for construction in primitive_constructions_doc.get("primitive_constructions", []):
            conn.execute(
                "INSERT INTO primitive_constructions (id, name, special_case_of, notes) VALUES (?, ?, ?, ?)",
                (
                    construction["id"],
                    construction["name"],
                    construction.get("special_case_of"),
                    construction.get("notes"),
                ),
            )

        for construction in mode_constructions_doc.get("mode_constructions", []):
            conn.execute(
                "INSERT INTO mode_constructions (id, name, special_case_of, notes) VALUES (?, ?, ?, ?)",
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
            component_flow_signature = round_component_flow_signature(round_def)
            state_model = spec.get("state_model")
            state_model_json = (
                json.dumps(state_model, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
                if state_model else None
            )
            conn.execute(
                "INSERT INTO rounds"
                " (id, name, kind, spec_json, round_hash, component_flow_signature, state_model_json, notes)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    round_def["id"],
                    round_def["name"],
                    round_def["kind"],
                    spec_json,
                    round_hash,
                    component_flow_signature,
                    state_model_json,
                    round_def.get("notes"),
                ),
            )

        for family in families:
            c = family.get("characteristics", {})
            innovative_ideas = family.get("innovative_ideas", [])
            ref_ids = family.get("reference_ids", [])
            authors = family.get("authors")
            underlying = family.get("underlying_primitive_ids")
            conn.execute(
                "INSERT INTO families"
                " (id, tier, name, year, notes, authors_json, underlying_primitive_ids_json,"
                "  characteristics_json, innovative_ideas_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (family["id"], family["_tier"], family["name"], family_year(family, references_by_id),
                 family.get("notes"),
                 json.dumps(authors, ensure_ascii=True) if authors else None,
                 json.dumps(underlying, ensure_ascii=True) if underlying else None,
                 json.dumps(c, ensure_ascii=True),
                 json.dumps(innovative_ideas, ensure_ascii=True)),
            )
            for target in family.get("target_applications", []):
                conn.execute(
                    "INSERT INTO family_targets (family_id, target) VALUES (?, ?)",
                    (family["id"], target))
            for comp_ref in c.get("components", []):
                params_json = json.dumps(
                    comp_ref.get("params") or {},
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                conn.execute(
                    "INSERT INTO family_components (family_id, component_id, params_json)"
                    " VALUES (?, ?, ?)",
                    (family["id"], comp_ref["id"], params_json))
            construction_table = (
                "primitive_family_constructions" if family["_tier"] == "primitive" else "mode_family_constructions"
            )
            for construction_id in family.get("construction_ids", []):
                conn.execute(
                    f"INSERT INTO {construction_table} (family_id, construction_id) VALUES (?, ?)",
                    (family["id"], construction_id),
                )
            for round_id in family.get("round_ids", []):
                conn.execute(
                    "INSERT INTO family_rounds (family_id, round_id, role) VALUES (?, ?, ?)",
                    (family["id"], round_id, "primary"),
                )
            refs_for_family: set[str] = set(ref_ids)
            for ref_id in ref_ids:
                conn.execute(
                    "INSERT INTO family_references (family_id, reference_id) VALUES (?, ?)",
                    (family["id"], ref_id),
                )
            family_reference_ids[family["id"]] = refs_for_family
            for pp in family.get("process_participations", []):
                proc_id = pp["process_id"]
                stage_ids = pp.get("stage_ids", [])
                status = pp.get("status")
                conn.execute(
                    "INSERT INTO family_processes"
                    " (family_id, process_id, status, stage_ids_json)"
                    " VALUES (?, ?, ?, ?)",
                    (family["id"], proc_id, status,
                     json.dumps(stage_ids, ensure_ascii=True)))
        # Insert influences in a second pass so all families exist before any FK is checked.
        for family in families:
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

        leaf_ids = construction_leaf_ids(data)
        sharing_edges = compute_construction_sharing_edges(families, leaf_ids, references_by_id)
        for source_family_id, target_family_id, construction_id in sharing_edges:
            conn.execute(
                "INSERT INTO construction_sharing_edges"
                " (source_family_id, target_family_id, construction_id)"
                " VALUES (?, ?, ?)",
                (source_family_id, target_family_id, construction_id),
            )

        for instance in instances:
            c = instance.get("characteristics", {})
            instance_ref_ids = set(instance.get("reference_ids", []))
            if not instance_ref_ids:
                instance_ref_ids = set(family_reference_ids.get(instance["family_id"], set()))

            conn.execute(
                "INSERT INTO instances"
                " (id, name, family_id, tier, type_id, block_size_bits, output_size_bits,"
                "  characteristics_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (instance["id"], instance["name"], instance["family_id"], instance["_tier"],
                 instance["type"], c.get("block_size_bits"), c.get("output_size_bits"),
                 json.dumps(c, ensure_ascii=True)),
            )

            for ref_id in sorted(instance_ref_ids):
                conn.execute(
                    "INSERT INTO instance_references (instance_id, reference_id) VALUES (?, ?)",
                    (instance["id"], ref_id),
                )

        conn.commit()
        print(f"Database built: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
