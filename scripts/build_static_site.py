#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import sqlite3
import time
from pathlib import Path

from reference_pdfs import REFERENCES_DIR, build_family_pdf_map

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "build" / "symmetric_primitives.db"
SITE_DIR = ROOT / "build" / "site"
TEMPLATE_DIR = ROOT / "scripts" / "site_template"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render_index_html(cache_token: str) -> str:
    template = (TEMPLATE_DIR / "index.html.tmpl").read_text(encoding="utf-8")
    glossary_html = (TEMPLATE_DIR / "glossary_content.html").read_text(encoding="utf-8")
    return (
        template
        .replace("__CACHE_TOKEN__", cache_token)
        .replace("__GLOSSARY_CONTENT__", glossary_html)
    )


def fetch_rows(conn: sqlite3.Connection, query: str) -> list[dict[str, object]]:
    cur = conn.execute(query)
    cols = [desc[0] for desc in cur.description]
    return [{cols[i]: row[i] for i in range(len(cols))} for row in cur.fetchall()]


def get_table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [r[0] for r in rows]


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    quoted = table_name.replace('"', '""')
    rows = conn.execute(f'PRAGMA table_info("{quoted}")').fetchall()
    return [r[1] for r in rows]


def load_all_tables(conn: sqlite3.Connection) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for table_name in get_table_names(conn):
        cols = get_table_columns(conn, table_name)
        quoted = table_name.replace('"', '""')
        rows = fetch_rows(conn, f'SELECT * FROM "{quoted}"')
        out[table_name] = {"columns": cols, "rows": rows, "rowCount": len(rows)}
    return out


def load_join_builder_dataset(conn: sqlite3.Connection) -> dict[str, object]:
    rows = fetch_rows(
        conn,
        """
        SELECT
          i.id AS "instance.id",
          i.name AS "instance.name",
          i.tier AS "instance.tier",
          i.type_id AS "instance.type_id",
          COALESCE(pt.name, mt.name) AS "instance.type_name",
          i.block_size_bits AS "instance.fixed_input_bits",
          i.output_size_bits AS "instance.fixed_output_bits",
          i.characteristics_json AS "instance.characteristics_json",
          f.id AS "family.id",
          f.name AS "family.name",
          f.year AS "family.year",
          f.notes AS "family.notes",
          (SELECT GROUP_CONCAT(pc.name, ', ')
             FROM primitive_family_constructions pfc
             JOIN primitive_constructions pc ON pc.id = pfc.construction_id
            WHERE pfc.family_id = f.id) AS "family.primitive_construction_names",
          (SELECT GROUP_CONCAT(mc.name, ', ')
             FROM mode_family_constructions mfc
             JOIN mode_constructions mc ON mc.id = mfc.construction_id
            WHERE mfc.family_id = f.id) AS "family.mode_construction_names",
          (SELECT GROUP_CONCAT(fcomp.component_id, ', ')
             FROM family_components fcomp
            WHERE fcomp.family_id = f.id) AS "family.component_ids",
          (SELECT GROUP_CONCAT(DISTINCT comp.name)
             FROM family_components fcomp
             JOIN components comp ON comp.id = fcomp.component_id
            WHERE fcomp.family_id = f.id) AS "family.component_names",
          (SELECT GROUP_CONCAT(fr2.round_id, ', ')
             FROM family_rounds fr2
            WHERE fr2.family_id = f.id) AS "family.round_ids",
          (SELECT GROUP_CONCAT(DISTINCT r2.round_hash)
             FROM family_rounds fr2 JOIN rounds r2 ON r2.id = fr2.round_id
            WHERE fr2.family_id = f.id) AS "family.round_hashes",
          (SELECT GROUP_CONCAT(DISTINCT r2.component_flow_signature)
             FROM family_rounds fr2 JOIN rounds r2 ON r2.id = fr2.round_id
            WHERE fr2.family_id = f.id) AS "family.round_component_flow_signatures",
          (SELECT GROUP_CONCAT(DISTINCT r2.state_model_json)
             FROM family_rounds fr2 JOIN rounds r2 ON r2.id = fr2.round_id
            WHERE fr2.family_id = f.id) AS "family.round_state_models",
          ref.id AS "reference.id",
          ref.title AS "reference.title",
          ref.kind AS "reference.kind",
          ref.year AS "reference.year",
          ref.url AS "reference.url",
          ref.venue AS "reference.venue",
          ref.organization AS "reference.organization",
          ref.status AS "reference.status"
        FROM instances i
        JOIN families f ON f.id = i.family_id
        LEFT JOIN primitive_types pt ON pt.id = i.type_id
        LEFT JOIN mode_types mt ON mt.id = i.type_id
        LEFT JOIN instance_references ir ON ir.instance_id = i.id
        LEFT JOIN "references" ref ON ref.id = ir.reference_id
        ORDER BY f.year, i.name, ref.year
        """,
    )

    columns = list(rows[0].keys()) if rows else []

    base_sql = (
        'SELECT i.id AS "instance.id", i.name AS "instance.name", '
        'i.tier AS "instance.tier", i.type_id AS "instance.type_id", '
        'COALESCE(pt.name, mt.name) AS "instance.type_name", '
        'i.block_size_bits AS "instance.fixed_input_bits", '
        'i.output_size_bits AS "instance.fixed_output_bits", '
        'i.characteristics_json AS "instance.characteristics_json", '
        'f.id AS "family.id", f.name AS "family.name", f.year AS "family.year", '
        'f.notes AS "family.notes", '
        '(SELECT GROUP_CONCAT(pc.name, \', \') FROM primitive_family_constructions pfc '
        'JOIN primitive_constructions pc ON pc.id = pfc.construction_id '
        'WHERE pfc.family_id = f.id) AS "family.primitive_construction_names", '
        '(SELECT GROUP_CONCAT(mc.name, \', \') FROM mode_family_constructions mfc '
        'JOIN mode_constructions mc ON mc.id = mfc.construction_id '
        'WHERE mfc.family_id = f.id) AS "family.mode_construction_names", '
        '(SELECT GROUP_CONCAT(fcomp.component_id, \', \') FROM family_components fcomp '
        'WHERE fcomp.family_id = f.id) AS "family.component_ids", '
        '(SELECT GROUP_CONCAT(DISTINCT comp.name) FROM family_components fcomp '
        'JOIN components comp ON comp.id = fcomp.component_id '
        'WHERE fcomp.family_id = f.id) AS "family.component_names", '
        '(SELECT GROUP_CONCAT(fr2.round_id, \', \') FROM family_rounds fr2 '
        'WHERE fr2.family_id = f.id) AS "family.round_ids", '
        '(SELECT GROUP_CONCAT(DISTINCT r2.round_hash) FROM family_rounds fr2 '
        'JOIN rounds r2 ON r2.id = fr2.round_id '
        'WHERE fr2.family_id = f.id) AS "family.round_hashes", '
        '(SELECT GROUP_CONCAT(DISTINCT r2.component_flow_signature) FROM family_rounds fr2 '
        'JOIN rounds r2 ON r2.id = fr2.round_id '
        'WHERE fr2.family_id = f.id) AS "family.round_component_flow_signatures", '
        '(SELECT GROUP_CONCAT(DISTINCT r2.state_model_json) FROM family_rounds fr2 '
        'JOIN rounds r2 ON r2.id = fr2.round_id '
        'WHERE fr2.family_id = f.id) AS "family.round_state_models", '
        'ref.id AS "reference.id", '
        'ref.title AS "reference.title", ref.kind AS "reference.kind", '
        'ref.year AS "reference.year", ref.url AS "reference.url", '
        'ref.venue AS "reference.venue", ref.organization AS "reference.organization", '
        'ref.status AS "reference.status" '
        'FROM instances i '
        'JOIN families f ON f.id = i.family_id '
        'LEFT JOIN primitive_types pt ON pt.id = i.type_id '
        'LEFT JOIN mode_types mt ON mt.id = i.type_id '
        'LEFT JOIN instance_references ir ON ir.instance_id = i.id '
        'LEFT JOIN "references" ref ON ref.id = ir.reference_id'
    )

    return {"columns": columns, "rows": rows, "baseSql": base_sql}


def load_process_data(conn: sqlite3.Connection) -> dict[str, object]:
    """Return process list and a map of family_id → primary process_id."""
    processes = fetch_rows(
        conn,
        "SELECT id, name, organizer, start_year, end_year FROM processes ORDER BY start_year",
    )
    # family_id → primary process_id (winner > finalist > recommended > candidate > submitted)
    STATUS_RANK = {
        "winner": 0, "recommended": 1, "candidate_recommended": 2,
        "finalist": 3, "special_recognition": 4, "portfolio": 5,
        "monitored": 6, "candidate": 7, "submitted": 8,
    }
    participations = fetch_rows(
        conn,
        "SELECT family_id, process_id, status FROM family_process_outcomes ORDER BY family_id",
    )
    family_process_map: dict[str, str] = {}
    family_process_rank: dict[str, int] = {}
    for row in participations:
        fid = row["family_id"]
        pid = row["process_id"]
        rank = STATUS_RANK.get(row["status"] or "", 99)
        if fid not in family_process_rank or rank < family_process_rank[fid]:
            family_process_map[fid] = pid
            family_process_rank[fid] = rank
    return {"processes": processes, "familyProcessMap": family_process_map}


def build_family_pdf_payload() -> dict[str, list[str]]:
    """family_id -> sorted list of "references/<file>" paths, relative to the
    site root, for the "Open PDF" button (Timelines/Genealogy notes). Reuses
    reference_pdfs.build_family_pdf_map() rather than re-deriving the
    filename-matching logic in JS, so both stay in sync automatically.
    """
    fam_map = build_family_pdf_map()
    return {
        fid: [f"references/{p.name}" for p in paths]
        for fid, paths in fam_map.items()
        if paths
    }


def copy_reference_pdfs() -> None:
    """Copy references/*.pdf|*.txt into build/site/references/ so the "Open
    PDF" button has something to link/embed -- the site is otherwise fully
    self-contained (index.html/styles.css/app.js/data.js), but these files
    are the actual documents the family-PDF map above points at.
    """
    dest = SITE_DIR / "references"
    dest.mkdir(parents=True, exist_ok=True)
    for src in REFERENCES_DIR.iterdir():
        if src.is_file() and src.suffix.lower() in {".pdf", ".txt"}:
            shutil.copy2(src, dest / src.name)


def build_site() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Missing {DB_PATH}. Run make build-db first.")

    with sqlite3.connect(DB_PATH) as conn:
        all_tables = load_all_tables(conn)
        builder_dataset = load_join_builder_dataset(conn)
        process_data = load_process_data(conn)

    payload = {
        "summary": {
            "tableCount": len(all_tables),
            "totalRows": sum(t["rowCount"] for t in all_tables.values()),
            "builderRows": len(builder_dataset["rows"]),
        },
        "tables": all_tables,
        "joinBuilder": builder_dataset,
        "processData": process_data,
        "familyPdfMap": build_family_pdf_payload(),
    }

    cache_token = str(int(time.time()))

    index_html = render_index_html(cache_token)
    styles_css = (TEMPLATE_DIR / "styles.css").read_text(encoding="utf-8")
    app_js = (TEMPLATE_DIR / "app.js").read_text(encoding="utf-8")

    data_js = "window.__SPDB_DATA__ = " + json.dumps(payload, ensure_ascii=True) + ";\n"

    write_text(SITE_DIR / "index.html", index_html)
    write_text(SITE_DIR / "styles.css", styles_css)
    write_text(SITE_DIR / "app.js", app_js)
    write_text(SITE_DIR / "data.js", data_js)
    copy_reference_pdfs()

    print(f"Static site generated in: {SITE_DIR}")


if __name__ == "__main__":
    build_site()
