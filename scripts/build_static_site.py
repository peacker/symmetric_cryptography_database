#!/usr/bin/env python3

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "build" / "symmetric_primitives.db"
SITE_DIR = ROOT / "build" / "site"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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
          p.id AS "primitive.id",
          p.name AS "primitive.name",
          p.primitive_type AS "primitive.type_id",
          pt.name AS "primitive.type_name",
          p.block_size_bits AS "primitive.fixed_input_bits",
          p.output_size_bits AS "primitive.fixed_output_bits",
          p.characteristics_json AS "primitive.characteristics_json",
          f.id AS "family.id",
          f.name AS "family.name",
          f.year AS "family.year",
          f.notes AS "family.notes",
          ref.id AS "reference.id",
          ref.title AS "reference.title",
          ref.kind AS "reference.kind",
          ref.year AS "reference.year",
          ref.url AS "reference.url",
          ref.venue AS "reference.venue",
          ref.organization AS "reference.organization",
          ref.status AS "reference.status"
        FROM primitives p
        JOIN families f ON f.id = p.family_id
        LEFT JOIN primitive_types pt ON pt.id = p.primitive_type
        LEFT JOIN primitive_references pr ON pr.primitive_id = p.id
        LEFT JOIN "references" ref ON ref.id = pr.reference_id
        ORDER BY f.year, p.name, ref.year
        """,
    )

    columns = list(rows[0].keys()) if rows else []

    base_sql = (
        'SELECT p.id AS "primitive.id", p.name AS "primitive.name", '
        'p.primitive_type AS "primitive.type_id", pt.name AS "primitive.type_name", '
        'p.block_size_bits AS "primitive.fixed_input_bits", '
        'p.output_size_bits AS "primitive.fixed_output_bits", '
        'p.characteristics_json AS "primitive.characteristics_json", '
        'f.id AS "family.id", f.name AS "family.name", f.year AS "family.year", '
        'f.notes AS "family.notes", ref.id AS "reference.id", '
        'ref.title AS "reference.title", ref.kind AS "reference.kind", '
        'ref.year AS "reference.year", ref.url AS "reference.url", '
        'ref.venue AS "reference.venue", ref.organization AS "reference.organization", '
        'ref.status AS "reference.status" '
        'FROM primitives p '
        'JOIN families f ON f.id = p.family_id '
        'LEFT JOIN primitive_types pt ON pt.id = p.primitive_type '
        'LEFT JOIN primitive_references pr ON pr.primitive_id = p.id '
        'LEFT JOIN "references" ref ON ref.id = pr.reference_id'
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
        "SELECT family_id, process_id, status FROM family_processes ORDER BY family_id",
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
    }

    cache_token = str(int(time.time()))

    index_html = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Symmetric Cryptography Database</title>
    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\" />
    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin />
    <link href=\"https://fonts.googleapis.com/css2?family=Archivo+SemiCondensed:wght@400;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap\" rel=\"stylesheet\" />
    <link rel=\"stylesheet\" href=\"styles.css?v={cache_token}\" />
    <script src=\"data.js?v={cache_token}\" defer></script>
    <script src=\"app.js?v={cache_token}\" defer></script>
  </head>
  <body>
    <main class=\"page\">
      <header class=\"top-header panel\">
        <section class=\"hero\">
          <h1>Symmetric Cryptography Database</h1>
        </section>
        <nav class=\"navigator\" aria-label=\"Section navigation\">
          <button type=\"button\" class=\"nav-tab is-active\" data-view-target=\"visualizations\">Family Visualizations</button>
          <button type=\"button\" class=\"nav-tab\" data-view-target=\"tables\">All SQLite Tables</button>
          <button type=\"button\" class=\"nav-tab\" data-view-target=\"builder\">Custom Query Builder</button>
        </nav>
      </header>

      <section class=\"panel meta\" id=\"summary\"></section>

      <section class=\"panel view-panel is-active\" data-view=\"visualizations\">
        <h2>Family Visualizations</h2>
        <p class=\"small-note\">X axis = publication year. Y axis grouping is selectable.</p>
        <div class=\"toolbar viz-toolbar\">
          <label class=\"toolbar-field\">Group families by
            <select id=\"vizGroupBy\">
              <option value=\"primitive\">Primitive type</option>
              <option value=\"construction\">Construction type</option>
              <option value=\"target\">Target application</option>
            </select>
          </label>
          <div class=\"viz-display-group\">
            <div class=\"viz-name-section\">
              <span class=\"viz-name-section-label\">Names</span>
              <div class=\"viz-name-mode\" role=\"group\"><button id=\"vizNameOff\" type=\"button\" class=\"name-mode-btn\">Off</button><button id=\"vizNameClip\" type=\"button\" class=\"name-mode-btn is-active\">Clip</button><button id=\"vizNameWrap\" type=\"button\" class=\"name-mode-btn\">Wrap</button><button id=\"vizNameFull\" type=\"button\" class=\"name-mode-btn\">Full</button></div>
            </div>
            <label class=\"inline-check\"><input id=\"vizCollapseGroups\" type=\"checkbox\" checked /> Collapse to <input id=\"vizCollapseCount\" type=\"number\" min=\"1\" value=\"3\" class=\"viz-collapse-count\" /></label>
            <label class=\"inline-check\"><input id=\"vizHideDots\" type=\"checkbox\" /> Bullet points</label>
            <label class=\"inline-check\"><input id=\"vizShowArrows\" type=\"checkbox\" /> Show relation arrows</label>
            <label class=\"inline-check\"><input id=\"vizColorByProcess\" type=\"checkbox\" checked /> Color by process</label>
          </div>
          <div class=\"viz-font-controls\" aria-label=\"Timeline font size\">
            <button id=\"vizFontMinus\" type=\"button\">A-</button>
            <button id=\"vizFontPlus\" type=\"button\">A+</button>
            <button id=\"vizFontReset\" type=\"button\">Reset</button>
            <span id=\"vizFontValue\" class=\"small-note\">12px</span>
          </div>
          <div class=\"viz-scale-controls\" aria-label=\"Timeline zoom\">
            <button id=\"vizZoomOut\" type=\"button\">-</button>
            <button id=\"vizZoomIn\" type=\"button\">+</button>
            <button id=\"vizZoomReset\" type=\"button\">100%</button>
            <button id=\"vizZoomFit\" type=\"button\">Fit</button>
            <span id=\"vizZoomValue\" class=\"small-note\">100%</span>
          </div>
        </div>
        <div class=\"viz-secondary-controls\">
          <label class=\"toolbar-field viz-search-field\">Find family
            <input id=\"vizFamilySearch\" type=\"search\" placeholder=\"Type a family name\" autocomplete=\"off\" />
          </label>
          <div class=\"viz-year-controls\">
            <label class=\"toolbar-field\">From year
              <input id=\"vizYearStart\" type=\"range\" />
            </label>
            <label class=\"toolbar-field\">To year
              <input id=\"vizYearEnd\" type=\"range\" />
            </label>
            <button id=\"vizYearReset\" type=\"button\">Reset years</button>
            <span id=\"vizYearRangeValue\" class=\"small-note\">All years</span>
          </div>
        </div>
        <details class=\"collapsible viz-filter-panel\" open>
          <summary>Visible groups</summary>
          <div class=\"collapsible-body\">
            <div class=\"viz-filter-actions\">
              <button id=\"vizFilterAll\" type=\"button\">All</button>
              <button id=\"vizFilterNone\" type=\"button\">None</button>
            </div>
            <div id=\"vizGroupFilters\" class=\"filter-checklist viz-filter-checklist\"></div>
          </div>
        </details>
        <div class=\"viz-frame\" id=\"vizFrame\">
          <div id=\"vizYAxisPane\" class=\"viz-yaxis-pane\">
            <div id=\"vizYAxisTrack\" class=\"viz-axis-track\">
              <svg id=\"familyVizYAxis\" role=\"presentation\" aria-hidden=\"true\"></svg>
            </div>
          </div>
          <div class=\"viz-plot-pane\">
            <div id=\"vizPlotScroll\" class=\"viz-plot-scroll\">
              <svg id=\"familyVizPlot\" role=\"img\" aria-label=\"Family timeline visualization\"></svg>
            </div>
            <div class=\"viz-xaxis-pane\">
              <div id=\"vizXAxisTrack\" class=\"viz-axis-track\">
                <svg id=\"familyVizXAxis\" role=\"presentation\" aria-hidden=\"true\"></svg>
              </div>
            </div>
          </div>
          <div id=\"vizCornerPane\" class=\"viz-corner-pane\"></div>
        </div>
        <p id=\"vizRelationInfo\" class=\"small-note viz-relation-info\">Hover a relation arrow to see relation details. Use the zoom controls or Cmd/Ctrl + wheel inside the plot to adjust scale.</p>
        <div id=\"vizProcessLegend\" class=\"viz-process-legend\" hidden></div>
      </section>

      <section class=\"panel view-panel\" data-view=\"tables\">
        <h2>All SQLite Tables</h2>
        <div class=\"toolbar\">
          <label class=\"toolbar-field\">Table
            <select id=\"tableSelect\"></select>
          </label>
          <label class=\"toolbar-field\">Search selected table
            <input id=\"tableSearch\" type=\"search\" placeholder=\"Search all cells\" autocomplete=\"off\" />
          </label>
        </div>
        <div class=\"table-wrap\"><table id=\"allTablesView\"><thead></thead><tbody></tbody></table></div>
      </section>

      <section class=\"panel view-panel\" data-view=\"builder\">
        <h2>Custom Query Builder</h2>
        <p class=\"small-note\">Base join: primitives + families + instance references</p>
        <div class=\"builder-grid\">
          <details class=\"collapsible\" open>
            <summary>Filters</summary>
            <div class=\"collapsible-body filters\">
              <label>Primitive type
                <div id=\"fPrimitiveType\" class=\"filter-checklist\"></div>
              </label>
              <label>Reference kind
                <div id=\"fReferenceKind\" class=\"filter-checklist\"></div>
              </label>
              <label>Reference year min
                <input id=\"fReferenceYearMin\" type=\"number\" />
              </label>
              <label>Reference year max
                <input id=\"fReferenceYearMax\" type=\"number\" />
              </label>
              <label>Family name contains
                <input id=\"fFamilyName\" type=\"search\" autocomplete=\"off\" />
              </label>
              <label>Reference title contains
                <input id=\"fReferenceTitle\" type=\"search\" autocomplete=\"off\" />
              </label>
              <label class=\"inline-check\"><input id=\"fHasReferenceLink\" type=\"checkbox\" /> Only rows with reference URL</label>
              <button id=\"resetFilters\" type=\"button\">Reset filters</button>
            </div>
          </details>
          <details class=\"collapsible\" open>
            <summary>Columns</summary>
            <div class=\"collapsible-body\">
              <div id=\"columnPicker\" class=\"column-picker\"></div>
            </div>
          </details>
        </div>

        <details class=\"collapsible\" open>
          <summary>SQL Preview</summary>
          <div class=\"collapsible-body\">
            <div class=\"sql-box\">
              <div class=\"sql-title\">SQL preview</div>
              <pre id=\"sqlPreview\"></pre>
            </div>
          </div>
        </details>
        <p class=\"small-note\">Tip: drag the divider at the right edge of each header to resize columns.</p>

        <div class=\"table-wrap\"><table id=\"builderView\"><thead></thead><tbody></tbody></table></div>
      </section>
    </main>
  </body>
</html>
"""

    styles_css = """:root {
  --bg: #f2efe5;
  --bg-shade: #e5e0d0;
  --panel: #fffef8;
  --ink: #152021;
  --muted: #4f6062;
  --line: #cfcec0;
  --accent: #0f4c5c;
  --accent-soft: #d7eef2;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: "Archivo SemiCondensed", sans-serif;
  color: var(--ink);
  background:
    radial-gradient(1000px 520px at 10% -10%, #e2d9be 0%, transparent 55%),
    radial-gradient(920px 420px at 110% -30%, #bddde2 0%, transparent 60%),
    linear-gradient(175deg, var(--bg) 0%, var(--bg-shade) 100%);
}

.page {
  width: min(97vw, 1900px);
  margin: 0 auto;
  padding: 1.2rem 0.7rem 2rem;
}

.top-header {
  position: sticky;
  top: 0.4rem;
  z-index: 6;
  display: grid;
  gap: 0.55rem;
  background: color-mix(in srgb, var(--panel) 88%, #ffffff 12%);
  backdrop-filter: blur(7px);
}

.hero h1 {
  margin: 0;
  font-size: clamp(1.8rem, 3.4vw, 2.8rem);
}

.navigator {
  display: flex;
  gap: 0.55rem;
  align-items: center;
  flex-wrap: wrap;
}

.nav-tab {
  width: auto;
  margin: 0;
  border: 1px solid #b8d8de;
  background: #eaf6f8;
  color: #08323d;
  border-radius: 999px;
  padding: 0.32rem 0.72rem;
  font-size: 0.9rem;
  font-weight: 700;
}

.nav-tab:hover { background: #d7eef2; }

.nav-tab.is-active {
  border-color: #2c7d8f;
  background: #c2e8ef;
  color: #062a33;
}

.view-panel { display: none; }
.view-panel.is-active { display: block; }

.panel {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: color-mix(in srgb, var(--panel) 94%, #ffffff 6%);
  margin-top: 0.85rem;
  padding: 0.9rem;
}

.panel h2, .panel h3 { margin: 0.2rem 0 0.6rem; }

.meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 0.55rem;
}

.meta-item {
  border: 1px dashed var(--line);
  border-radius: 10px;
  padding: 0.55rem;
}

.meta-item .label { color: var(--muted); font-size: 0.82rem; }
.meta-item .value { font-size: 1.35rem; font-weight: 700; }

.toolbar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 0.6rem;
}

.toolbar-field { display: block; color: var(--muted); font-size: 0.85rem; }

input, select, button {
  width: 100%;
  font: inherit;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.45rem 0.55rem;
  background: #fff;
  color: var(--ink);
  margin-top: 0.25rem;
}

button { cursor: pointer; width: auto; background: var(--accent-soft); }

.small-note { color: var(--muted); margin: 0 0 0.7rem; }

.builder-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.8rem;
}

.collapsible {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
}

.collapsible summary {
  cursor: pointer;
  list-style: none;
  padding: 0.5rem 0.65rem;
  font-weight: 700;
  color: #11333d;
  background: #eef6f7;
  border-bottom: 1px solid #d6e4e6;
}

.collapsible summary::-webkit-details-marker {
  display: none;
}

.collapsible summary::before {
  content: "▸";
  display: inline-block;
  margin-right: 0.45rem;
}

.collapsible[open] summary::before {
  content: "▾";
}

.collapsible-body {
  padding: 0.55rem;
}

.filters {
  display: grid;
  grid-template-columns: repeat(2, minmax(160px, 1fr));
  gap: 0.45rem 0.7rem;
}

.inline-check { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.2rem; }
.inline-check input { width: auto; margin: 0; }

.filter-checklist {
  max-height: 160px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.35rem 0.45rem;
  background: #fff;
  display: grid;
  gap: 0.28rem;
}

.filter-checklist label {
  display: flex;
  align-items: center;
  gap: 0.42rem;
  margin: 0;
  color: var(--ink);
  font-size: 0.92rem;
}

.filter-checklist input { width: auto; margin: 0; }

.column-picker {
  max-height: 240px;
  overflow: auto;
  display: grid;
  gap: 0.45rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.45rem;
  background: #fff;
}

.column-group {
  border: 1px solid #e4e1d2;
  border-radius: 8px;
  padding: 0.35rem;
}

.column-group-title { font-weight: 700; font-size: 0.88rem; }
.column-item { display: flex; align-items: center; gap: 0.42rem; }
.column-item input { width: auto; margin: 0; }

.sql-box {
  margin-top: 0.7rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
}

.sql-title {
  background: #12313b;
  color: #f2fcfe;
  padding: 0.35rem 0.55rem;
  font-size: 0.82rem;
}

pre {
  margin: 0;
  padding: 0.6rem;
  max-height: 220px;
  overflow: auto;
  background: #fafbf9;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.81rem;
  white-space: pre-wrap;
}

.table-wrap {
  margin-top: 0.7rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: auto;
  max-height: 62vh;
}

.viz-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem 0.85rem;
  align-items: end;
}

.viz-toolbar .toolbar-field {
  min-width: 200px;
}

.viz-font-controls,
.viz-scale-controls {
  display: flex;
  align-items: center;
  gap: 0.42rem;
}

.viz-font-controls button,
.viz-scale-controls button {
  width: auto;
  margin-top: 0;
}

#vizFontValue,
#vizZoomValue {
  margin: 0;
  min-width: 3.2rem;
  text-align: right;
}

.viz-filter-panel {
  margin-top: 0.7rem;
}

.viz-secondary-controls {
  margin-top: 0.55rem;
  display: grid;
  grid-template-columns: minmax(230px, 330px) minmax(320px, 1fr);
  gap: 0.55rem 0.75rem;
  align-items: end;
}

.viz-search-field {
  margin: 0;
}

.viz-display-group {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem 0.85rem;
  flex-wrap: wrap;
  padding: 0.3rem 0.6rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #f4f8f9;
}

.viz-name-section {
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
}

.viz-name-section-label {
  font-size: 0.85rem;
  color: var(--muted);
}

.viz-name-mode {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.name-mode-btn {
  all: unset;
  cursor: pointer;
  padding: 0.22rem 0.55rem;
  font-size: 0.82rem;
  color: var(--muted);
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 5px;
  line-height: 1.2;
  white-space: nowrap;
}

.name-mode-btn:hover { background: var(--accent-soft); }

.name-mode-btn.is-active {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 700;
  border-color: var(--accent);
}

.viz-collapse-count {
  width: 3.2rem;
  padding: 0.2rem 0.3rem;
  margin: 0 0 0 0.35rem;
  display: inline;
}

.viz-year-controls {
  display: grid;
  grid-template-columns: minmax(130px, 1fr) minmax(130px, 1fr) auto auto;
  gap: 0.45rem 0.6rem;
  align-items: end;
}

.viz-year-controls .toolbar-field {
  margin: 0;
}

#vizYearRangeValue {
  margin: 0;
  min-width: 9rem;
  text-align: right;
}

.viz-filter-actions {
  display: flex;
  gap: 0.45rem;
  margin-bottom: 0.55rem;
}

.viz-filter-actions button {
  width: auto;
  margin-top: 0;
}

.viz-filter-checklist {
  max-height: 170px;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
}

.viz-frame {
  margin-top: 0.7rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
  display: grid;
  grid-template-columns: 100px minmax(0, 1fr);
  grid-template-rows: 1fr 48px;
}

.viz-yaxis-pane {
  grid-column: 1;
  grid-row: 1;
  overflow: hidden;
  border-right: 1px solid var(--line);
  background: color-mix(in srgb, #ffffff 92%, #eef5f6 8%);
}

.viz-plot-pane {
  grid-column: 2;
  grid-row: 1 / span 2;
  min-width: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) 48px;
}

.viz-plot-scroll {
  grid-row: 1;
  overflow: auto;
  background: #fff;
}

.viz-xaxis-pane {
  grid-row: 2;
  overflow: hidden;
  border-top: 1px solid var(--line);
  background: color-mix(in srgb, #ffffff 92%, #eef5f6 8%);
}

.viz-corner-pane {
  grid-column: 1;
  grid-row: 2;
  overflow: hidden;
  border-top: 1px solid var(--line);
  border-right: 1px solid var(--line);
  background: color-mix(in srgb, #ffffff 88%, #e4eef0 12%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0.25rem 0.35rem;
  gap: 0.05rem;
  font-size: 0.6rem;
  font-weight: 700;
  color: #294248;
  text-align: center;
}

.viz-axis-track {
  will-change: transform;
}

.viz-relation-info {
  margin: 0.55rem 0 0;
  min-height: 1.4rem;
}

.viz-process-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.1rem;
  margin: 0.6rem 0 0;
  padding: 0.55rem 0.75rem;
  background: rgba(0,0,0,0.025);
  border-radius: 4px;
  font-size: 0.82rem;
}

.viz-process-legend-item {
  display: flex;
  align-items: center;
  gap: 0.38rem;
  white-space: nowrap;
}

.viz-process-legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

#familyVizPlot,
#familyVizYAxis,
#familyVizXAxis {
  display: block;
}

.viz-axis {
  stroke: #5d6d70;
  stroke-width: 1.2;
}

.viz-grid {
  stroke: #d7d8cf;
  stroke-width: 1;
  stroke-dasharray: 4 4;
}

.viz-label {
  fill: #2d4248;
  font-size: 12px;
}

.viz-point {
  fill: #1f77b4;
  stroke: #ffffff;
  stroke-width: 1.1;
}

.viz-text {
  fill: #1f2b2e;
  font-size: 12px;
}

.viz-edge {
  stroke: rgba(76, 91, 95, 0.75);
  fill: none;
}

table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
  min-width: 960px;
}

thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #0f2e37;
  color: #f4fdff;
  text-align: left;
  border-bottom: 1px solid #0a2027;
  padding: 0.45rem 0.5rem;
  white-space: nowrap;
}

th .head-cell {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-width: 0;
  padding-right: 8px;
}

th button {
  all: unset;
  cursor: pointer;
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

th .resizer {
  position: absolute;
  top: 0;
  right: 0;
  width: 12px;
  min-width: 12px;
  height: 100%;
  cursor: col-resize;
  z-index: 3;
  border-left: 1px solid rgba(203, 232, 238, 0.3);
  background: linear-gradient(to right, rgba(203, 232, 238, 0.15), rgba(203, 232, 238, 0.45));
}

th .resizer:hover {
  background: linear-gradient(to right, rgba(203, 232, 238, 0.28), rgba(203, 232, 238, 0.7));
}

tbody td {
  border-bottom: 1px solid #ece9dc;
  padding: 0.4rem 0.5rem;
  white-space: pre-wrap;
  word-break: break-word;
  overflow: visible;
  vertical-align: top;
}

tbody tr:nth-child(even) td { background: #fbfaf5; }

.codeish { font-family: "IBM Plex Mono", monospace; font-size: 0.84rem; }

@media (max-width: 980px) {
  .builder-grid { grid-template-columns: 1fr; }
  .filters { grid-template-columns: 1fr; }
  .navigator { gap: 0.4rem; }
  .nav-tab { flex: 1 1 auto; text-align: center; justify-content: center; }
  .viz-toolbar { grid-template-columns: 1fr; }
  .viz-secondary-controls { grid-template-columns: 1fr; }
  .viz-year-controls {
    grid-template-columns: 1fr;
    align-items: stretch;
  }
  #vizYearRangeValue {
    text-align: left;
  }
  .viz-frame { grid-template-columns: 80px minmax(0, 1fr); }
  .viz-filter-checklist { grid-template-columns: 1fr; }
}
"""

    app_js = """(function () {
  const data = window.__SPDB_DATA__;
  if (!data) return;

  function normalizeValue(value) {
    if (value === null || value === undefined) return "";
    if (Array.isArray(value)) return value.join(", ");
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  function isNumericLike(value) {
    if (typeof value === "number" && Number.isFinite(value)) return true;
    if (typeof value !== "string") return false;
    return /^-?\\d+(\\.\\d+)?$/.test(value.trim());
  }

  function compareValues(a, b) {
    const aa = normalizeValue(a);
    const bb = normalizeValue(b);
    if (isNumericLike(aa) && isNumericLike(bb)) return Number(aa) - Number(bb);
    return aa.localeCompare(bb, undefined, { sensitivity: "base" });
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;");
  }

  function parseJsonArray(value) {
    if (value === null || value === undefined || value === "") return [];
    if (Array.isArray(value)) return value;
    try {
      const parsed = JSON.parse(String(value));
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function isHttpUrl(text) {
    return /^https?:\\/\\//i.test(String(text || "").trim());
  }

  function renderSummary() {
    const host = document.getElementById("summary");
    const rows = [
      ["SQLite tables", data.summary.tableCount],
      ["Rows across all tables", data.summary.totalRows],
      ["Rows in builder join", data.summary.builderRows],
    ];
    host.innerHTML = rows
      .map(([label, value]) => `<article class=\"meta-item\"><div class=\"label\">${label}</div><div class=\"value\">${value}</div></article>`)
      .join("");
  }

  function setupNavigator() {
    const tabs = Array.from(document.querySelectorAll(".nav-tab[data-view-target]"));
    const views = Array.from(document.querySelectorAll(".view-panel[data-view]"));
    if (!tabs.length || !views.length) return;

    function activate(viewName) {
      views.forEach((view) => {
        view.classList.toggle("is-active", view.getAttribute("data-view") === viewName);
      });
      tabs.forEach((tab) => {
        tab.classList.toggle("is-active", tab.getAttribute("data-view-target") === viewName);
      });
    }

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        activate(tab.getAttribute("data-view-target") || "visualizations");
      });
    });

    activate("visualizations");
  }

  function createTableView(tableId) {
    const table = document.getElementById(tableId);
    return {
      table,
      head: table.querySelector("thead"),
      body: table.querySelector("tbody"),
      sortKey: "",
      sortDirection: "asc",
      widths: {},
    };
  }

  function renderGrid(view, columns, rows) {
    if (!columns.length) {
      view.head.innerHTML = "";
      view.body.innerHTML = "";
      return;
    }

    const sorted = [...rows];
    if (view.sortKey) {
      sorted.sort((a, b) => {
        const cmp = compareValues(a[view.sortKey], b[view.sortKey]);
        return view.sortDirection === "asc" ? cmp : -cmp;
      });
    }

    const headHtml = columns
      .map((col) => {
        const marker = view.sortKey === col ? (view.sortDirection === "asc" ? "▲" : "▼") : "↕";
        return [
          `<th data-col=\"${col}\">`,
          `<div class=\"head-cell\">`,
          `<button type=\"button\" data-sort=\"${col}\"><span class=\"codeish\">${col}</span> <span>${marker}</span></button>`,
          `<span class=\"resizer\" data-resize=\"${col}\"></span>`,
          `</div>`,
          `</th>`,
        ].join("");
      })
      .join("");
    view.head.innerHTML = `<tr>${headHtml}</tr>`;

    const bodyHtml = sorted
      .map((row) => {
        const tds = columns
          .map((col) => {
            const text = normalizeValue(row[col]);
            const escaped = escapeHtml(text);
            if (String(col).toLowerCase().endsWith(".url") && isHttpUrl(text)) {
              return `<td title=\"${escaped}\"><a href=\"${escaped}\" target=\"_blank\" rel=\"noopener noreferrer\">${escaped}</a></td>`;
            }
            return `<td title=\"${escaped}\">${escaped}</td>`;
          })
          .join("");
        return `<tr>${tds}</tr>`;
      })
      .join("");
    view.body.innerHTML = bodyHtml;

    const ths = Array.from(view.head.querySelectorAll("th"));
    ths.forEach((th, idx) => {
      const col = th.getAttribute("data-col") || "";
      if (!col) return;
      if (!(col in view.widths)) {
        let maxLen = 0;
        sorted.slice(0, 120).forEach((row) => {
          maxLen = Math.max(maxLen, normalizeValue(row[col]).length);
        });
        view.widths[col] = Math.max(90, Math.min(520, 24 + maxLen * 7.2));
      }
      const w = view.widths[col];
      th.style.width = `${w}px`;
      th.style.minWidth = `${w}px`;
      th.style.maxWidth = `${w}px`;
      Array.from(view.body.querySelectorAll("tr")).forEach((tr) => {
        const td = tr.children[idx];
        if (!td) return;
        td.style.width = `${w}px`;
        td.style.minWidth = `${w}px`;
        td.style.maxWidth = `${w}px`;
      });
    });

    Array.from(view.head.querySelectorAll("button[data-sort]")).forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.getAttribute("data-sort") || "";
        if (!key) return;
        if (view.sortKey === key) view.sortDirection = view.sortDirection === "asc" ? "desc" : "asc";
        else {
          view.sortKey = key;
          view.sortDirection = "asc";
        }
        renderGrid(view, columns, rows);
      });
    });

    Array.from(view.head.querySelectorAll(".resizer[data-resize]")).forEach((handle) => {
      handle.addEventListener("mousedown", (event) => {
        event.preventDefault();
        const key = handle.getAttribute("data-resize") || "";
        if (!key) return;
        const th = handle.closest("th");
        if (!th) return;
        const startX = event.clientX;
        const startW = th.getBoundingClientRect().width;

        function onMove(moveEvent) {
          view.widths[key] = Math.max(70, Math.round(startW + (moveEvent.clientX - startX)));
          renderGrid(view, columns, rows);
        }

        function onUp() {
          window.removeEventListener("mousemove", onMove);
          window.removeEventListener("mouseup", onUp);
        }

        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
      });
    });
  }

  function setupAllTablesBrowser() {
    const select = document.getElementById("tableSelect");
    const search = document.getElementById("tableSearch");
    const view = createTableView("allTablesView");
    const names = Object.keys(data.tables).sort((a, b) => a.localeCompare(b));
    select.innerHTML = names.map((name) => `<option value=\"${name}\">${name} (${data.tables[name].rowCount})</option>`).join("");

    function refresh() {
      const tableData = data.tables[select.value] || { columns: [], rows: [] };
      const needle = (search.value || "").trim().toLowerCase();
      const rows = !needle
        ? tableData.rows
        : tableData.rows.filter((row) => tableData.columns.some((col) => normalizeValue(row[col]).toLowerCase().includes(needle)));
      renderGrid(view, tableData.columns, rows);
    }

    select.addEventListener("change", refresh);
    search.addEventListener("input", refresh);
    refresh();
  }

  function groupedColumns(columns) {
    const by = new Map();
    const out = [];
    columns.forEach((col) => {
      const i = col.indexOf(".");
      const group = i < 0 ? "other" : col.slice(0, i);
      const sub = i < 0 ? col : col.slice(i + 1);
      if (!by.has(group)) {
        const rec = { group, items: [] };
        by.set(group, rec);
        out.push(rec);
      }
      by.get(group).items.push({ key: col, sub });
    });
    return out;
  }

  function selectedChecklistValues(containerEl) {
    if (!containerEl) return new Set();
    const checked = Array.from(containerEl.querySelectorAll('input[type="checkbox"][data-value]:checked'));
    return new Set(checked.map((n) => n.getAttribute("data-value") || "").filter(Boolean));
  }

  function renderFilterChecklist(containerEl, values) {
    containerEl.innerHTML = values
      .map((value) => {
        const esc = escapeHtml(value);
        return `<label><input type=\"checkbox\" data-value=\"${esc}\" /><span>${esc}</span></label>`;
      })
      .join("");
  }

  function parseOptionalNumber(value) {
    const t = String(value || "").trim();
    if (!t) return NaN;
    const n = Number(t);
    return Number.isFinite(n) ? n : NaN;
  }

  function setupBuilder() {
    const builder = data.joinBuilder;
    const view = createTableView("builderView");

    const ui = {
      primitiveType: document.getElementById("fPrimitiveType"),
      referenceKind: document.getElementById("fReferenceKind"),
      referenceYearMin: document.getElementById("fReferenceYearMin"),
      referenceYearMax: document.getElementById("fReferenceYearMax"),
      familyName: document.getElementById("fFamilyName"),
      referenceTitle: document.getElementById("fReferenceTitle"),
      hasReferenceLink: document.getElementById("fHasReferenceLink"),
      resetFilters: document.getElementById("resetFilters"),
      columnPicker: document.getElementById("columnPicker"),
      sqlPreview: document.getElementById("sqlPreview"),
    };

    const defaultColumns = [
      "primitive.id", "primitive.name", "primitive.type_name", "family.name", "reference.title", "reference.year", "reference.url",
    ].filter((c) => builder.columns.includes(c));
    const visibleColumns = new Set(defaultColumns.length ? defaultColumns : builder.columns);

    function fillFilterOptions() {
      const primitiveTypes = Array.from(new Set(builder.rows.map((r) => normalizeValue(r["primitive.type_name"]).trim()).filter(Boolean))).sort((a, b) => a.localeCompare(b));
      const referenceKinds = Array.from(new Set(builder.rows.map((r) => normalizeValue(r["reference.kind"]).trim()).filter(Boolean))).sort((a, b) => a.localeCompare(b));
      renderFilterChecklist(ui.primitiveType, primitiveTypes);
      renderFilterChecklist(ui.referenceKind, referenceKinds);
    }

    function renderColumnPicker() {
      const html = groupedColumns(builder.columns)
        .map((group) => {
          const items = group.items.map((item) => {
            const checked = visibleColumns.has(item.key) ? "checked" : "";
            return `<label class=\"column-item\"><input type=\"checkbox\" data-col=\"${item.key}\" data-group=\"${group.group}\" ${checked} /><span class=\"codeish\">${item.sub}</span></label>`;
          }).join("");
          return `<section class=\"column-group\"><label class=\"column-item column-group-title\"><input type=\"checkbox\" data-group-toggle=\"${group.group}\" /><span>${group.group}</span></label>${items}</section>`;
        })
        .join("");
      ui.columnPicker.innerHTML = html;

      Array.from(ui.columnPicker.querySelectorAll("input[data-group-toggle]")).forEach((toggle) => {
        const group = toggle.getAttribute("data-group-toggle") || "";
        const children = Array.from(ui.columnPicker.querySelectorAll(`input[data-group=\"${group}\"]`));
        const selected = children.filter((c) => c.checked).length;
        toggle.checked = selected === children.length && children.length > 0;
        toggle.indeterminate = selected > 0 && selected < children.length;
        toggle.addEventListener("change", () => {
          children.forEach((child) => {
            child.checked = toggle.checked;
            const col = child.getAttribute("data-col") || "";
            if (!col) return;
            if (toggle.checked) visibleColumns.add(col);
            else visibleColumns.delete(col);
          });
          if (!visibleColumns.size && builder.columns.length) visibleColumns.add(builder.columns[0]);
          renderColumnPicker();
          refresh();
        });
      });

      Array.from(ui.columnPicker.querySelectorAll("input[data-col]")).forEach((input) => {
        input.addEventListener("change", () => {
          const col = input.getAttribute("data-col") || "";
          if (!col) return;
          if (input.checked) visibleColumns.add(col);
          else {
            visibleColumns.delete(col);
            if (!visibleColumns.size && builder.columns.length) visibleColumns.add(builder.columns[0]);
          }
          renderColumnPicker();
          refresh();
        });
      });
    }

    function buildWhereClauses() {
      const clauses = [];
      const typeValues = selectedChecklistValues(ui.primitiveType);
      if (typeValues.size) clauses.push(`\"primitive.type_name\" IN (${Array.from(typeValues).map((v) => `'${v.replace(/'/g, "''")}'`).join(", ")})`);
      const refKindValues = selectedChecklistValues(ui.referenceKind);
      if (refKindValues.size) clauses.push(`\"reference.kind\" IN (${Array.from(refKindValues).map((v) => `'${v.replace(/'/g, "''")}'`).join(", ")})`);

      const ryMin = parseOptionalNumber(ui.referenceYearMin.value);
      if (Number.isFinite(ryMin)) clauses.push(`\"reference.year\" >= ${ryMin}`);
      const ryMax = parseOptionalNumber(ui.referenceYearMax.value);
      if (Number.isFinite(ryMax)) clauses.push(`\"reference.year\" <= ${ryMax}`);

      const familyName = (ui.familyName.value || "").trim();
      if (familyName) clauses.push(`\"family.name\" LIKE '%${familyName.replace(/'/g, "''")}%'`);
      const referenceTitle = (ui.referenceTitle.value || "").trim();
      if (referenceTitle) clauses.push(`\"reference.title\" LIKE '%${referenceTitle.replace(/'/g, "''")}%'`);
      if (ui.hasReferenceLink.checked) clauses.push(`\"reference.url\" IS NOT NULL AND TRIM(\"reference.url\") <> ''`);

      return clauses;
    }

    function filterRows(rows) {
      const typeValues = selectedChecklistValues(ui.primitiveType);
      const refKindValues = selectedChecklistValues(ui.referenceKind);
      const ryMin = parseOptionalNumber(ui.referenceYearMin.value);
      const ryMax = parseOptionalNumber(ui.referenceYearMax.value);
      const familyName = (ui.familyName.value || "").trim().toLowerCase();
      const referenceTitle = (ui.referenceTitle.value || "").trim().toLowerCase();

      return rows.filter((row) => {
        const typeName = normalizeValue(row["primitive.type_name"]);
        if (typeValues.size && !typeValues.has(typeName)) return false;
        const refKind = normalizeValue(row["reference.kind"]);
        if (refKindValues.size && !refKindValues.has(refKind)) return false;

        const referenceYear = Number(row["reference.year"]);
        if (Number.isFinite(ryMin) && referenceYear < ryMin) return false;
        if (Number.isFinite(ryMax) && referenceYear > ryMax) return false;

        if (familyName && !normalizeValue(row["family.name"]).toLowerCase().includes(familyName)) return false;
        if (referenceTitle && !normalizeValue(row["reference.title"]).toLowerCase().includes(referenceTitle)) return false;
        if (ui.hasReferenceLink.checked && !normalizeValue(row["reference.url"]).trim()) return false;
        return true;
      });
    }

    function refresh() {
      const visible = builder.columns.filter((c) => visibleColumns.has(c));
      const filtered = filterRows(builder.rows);
      renderGrid(view, visible, filtered);
      const whereClauses = buildWhereClauses();
      const selectCols = visible.length ? visible.map((c) => `\"${c}\"`).join(", ") : "*";
      const whereSql = whereClauses.length ? `\\nWHERE ${whereClauses.join("\\n  AND ")}` : "";
      ui.sqlPreview.textContent = `SELECT ${selectCols}\\nFROM (${builder.baseSql})${whereSql};`;
    }

    [ui.referenceYearMin, ui.referenceYearMax, ui.familyName, ui.referenceTitle, ui.hasReferenceLink].forEach((node) => {
      node.addEventListener("change", refresh);
      node.addEventListener("input", refresh);
    });

    [ui.primitiveType, ui.referenceKind].forEach((container) => {
      container.addEventListener("change", (event) => {
        const target = event.target;
        if (target && target.matches('input[type="checkbox"][data-value]')) refresh();
      });
    });

    ui.resetFilters.addEventListener("click", () => {
      [ui.primitiveType, ui.referenceKind].forEach((container) => {
        Array.from(container.querySelectorAll('input[type="checkbox"][data-value]')).forEach((box) => {
          box.checked = false;
        });
      });
      [ui.referenceYearMin, ui.referenceYearMax, ui.familyName, ui.referenceTitle].forEach((node) => { node.value = ""; });
      ui.hasReferenceLink.checked = false;
      refresh();
    });

    fillFilterOptions();
    renderColumnPicker();
    refresh();
  }

  function setupFamilyVisualization() {
    const plotSvg = document.getElementById("familyVizPlot");
    const xAxisSvg = document.getElementById("familyVizXAxis");
    const yAxisSvg = document.getElementById("familyVizYAxis");
    const plotScroll = document.getElementById("vizPlotScroll");
    const xAxisTrack = document.getElementById("vizXAxisTrack");
    const yAxisTrack = document.getElementById("vizYAxisTrack");
    const cornerPane = document.getElementById("vizCornerPane");
    const processLegend = document.getElementById("vizProcessLegend");
    const groupBy = document.getElementById("vizGroupBy");
    const showArrows = document.getElementById("vizShowArrows");
    const hideDots = document.getElementById("vizHideDots");
    const nameModeOff = document.getElementById("vizNameOff");
    const nameModeClip = document.getElementById("vizNameClip");
    const nameModeWrap = document.getElementById("vizNameWrap");
    const nameModeFull = document.getElementById("vizNameFull");
    let nameMode = "clip";
    const colorByProcess = document.getElementById("vizColorByProcess");
    const groupFilters = document.getElementById("vizGroupFilters");
    const filterAll = document.getElementById("vizFilterAll");
    const filterNone = document.getElementById("vizFilterNone");
    const fontMinus = document.getElementById("vizFontMinus");
    const fontPlus = document.getElementById("vizFontPlus");
    const fontReset = document.getElementById("vizFontReset");
    const fontValue = document.getElementById("vizFontValue");
    const zoomOut = document.getElementById("vizZoomOut");
    const zoomIn = document.getElementById("vizZoomIn");
    const zoomReset = document.getElementById("vizZoomReset");
    const zoomFit = document.getElementById("vizZoomFit");
    const zoomValue = document.getElementById("vizZoomValue");
    const familySearch = document.getElementById("vizFamilySearch");
    const vizFrame = document.getElementById("vizFrame");
    const collapseGroups = document.getElementById("vizCollapseGroups");
    const collapseCount = document.getElementById("vizCollapseCount");
    const yearStart = document.getElementById("vizYearStart");
    const yearEnd = document.getElementById("vizYearEnd");
    const yearReset = document.getElementById("vizYearReset");
    const yearRangeValue = document.getElementById("vizYearRangeValue");
    const relationInfoBox = document.getElementById("vizRelationInfo");
    if (!plotSvg || !xAxisSvg || !yAxisSvg || !plotScroll || !xAxisTrack || !yAxisTrack || !cornerPane || !vizFrame || !groupBy || !showArrows || !hideDots || !nameModeOff || !nameModeClip || !nameModeWrap || !nameModeFull || !colorByProcess || !processLegend || !groupFilters || !filterAll || !filterNone || !fontMinus || !fontPlus || !fontReset || !fontValue || !zoomOut || !zoomIn || !zoomReset || !zoomFit || !zoomValue || !familySearch || !collapseGroups || !collapseCount || !yearStart || !yearEnd || !yearReset || !yearRangeValue || !relationInfoBox) return;

    const BASE_FONT = 12;
    const BASE_ZOOM = 1;
    const MIN_ZOOM = 0.35;
    const MAX_ZOOM = 4;
    const ZOOM_FACTOR = 1.2;
    const LEFT_AXIS_WIDTH = 100;
    const AXIS_HEIGHT = 48;
    const STACK_STEP = 0.34;
    const GROUP_GAP_UNITS = 0.42;
    const POINT_RADIUS = 4.25;
    const BASE_RELATION_TEXT = "Hover a relation arrow to see relation details. Use the zoom controls or Cmd/Ctrl + wheel inside the plot to adjust scale.";
    const modeSelections = {
      primitive: new Map(),
      construction: new Map(),
      target: new Map(),
    };
    let fontPx = BASE_FONT;
    let zoomScale = BASE_ZOOM;
    let hasAutoFit = false;
    let lastRenderSize = { plotWidth: 920, plotHeight: 640 };
    let yearsBounds = null;
    let suppressYearRender = false;

    const tables = data.tables || {};
    const families = (tables.families && tables.families.rows) || [];
    const primitives = (tables.primitives && tables.primitives.rows) || [];
    const primitiveTypes = (tables.primitive_types && tables.primitive_types.rows) || [];
    const familyConstructions = (tables.family_constructions && tables.family_constructions.rows) || [];
    const constructions = (tables.constructions && tables.constructions.rows) || [];
    const familyTargets = (tables.family_targets && tables.family_targets.rows) || [];
    const influences = (tables.family_influences && tables.family_influences.rows) || [];

    const typeNameById = new Map(primitiveTypes.map((row) => [String(row.id), String(row.name)]));
    const constructionNameById = new Map(constructions.map((row) => [String(row.id), String(row.name)]));
    const familyById = new Map(families.map((row) => [String(row.id), row]));

    const familyToTypes = new Map();
    primitives.forEach((row) => {
      const familyId = String(row.family_id || "");
      if (!familyId) return;
      if (!familyToTypes.has(familyId)) familyToTypes.set(familyId, new Set());
      const typeId = String(row.primitive_type || "");
      const typeName = typeNameById.get(typeId) || typeId;
      if (typeName) familyToTypes.get(familyId).add(typeName);
    });

    const familyToConstructions = new Map();
    familyConstructions.forEach((row) => {
      const familyId = String(row.family_id || "");
      if (!familyId) return;
      if (!familyToConstructions.has(familyId)) familyToConstructions.set(familyId, new Set());
      const cid = String(row.construction_id || "");
      const cname = constructionNameById.get(cid) || cid;
      if (cname) familyToConstructions.get(familyId).add(cname);
    });

    const familyToTargets = new Map();
    familyTargets.forEach((row) => {
      const familyId = String(row.family_id || "");
      if (!familyId) return;
      if (!familyToTargets.has(familyId)) familyToTargets.set(familyId, new Set());
      const target = String(row.target || "").trim();
      if (target) familyToTargets.get(familyId).add(target);
    });

    // Process color palette — saturated, accessible hues
    const processData = (data.processData || {});
    const processList = (processData.processes || []);
    const familyProcessMap = (processData.familyProcessMap || {});
    const PROCESS_COLORS = [
      "#1a73c9", "#d4501a", "#1e9c5e", "#9b42b8", "#c9961a",
      "#c91a4e", "#1ab8c9", "#5e6e1a", "#7a1ac9", "#1a4ec9",
      "#a85a1a", "#1a9b9b",
    ];
    const processColorMap = new Map();
    processList.forEach((proc, idx) => {
      processColorMap.set(String(proc.id), PROCESS_COLORS[idx % PROCESS_COLORS.length]);
    });
    processColorMap.set("__none__", "#7a8c8f");

    function processColorForFamily(familyId) {
      const pid = familyProcessMap[familyId];
      if (!pid) return processColorMap.get("__none__");
      return processColorMap.get(pid) || processColorMap.get("__none__");
    }

    function processNameForFamily(familyId) {
      const pid = familyProcessMap[familyId];
      if (!pid) return "";
      const proc = processList.find((p) => String(p.id) === pid);
      return proc ? String(proc.name) : pid;
    }

    function clearNode(node) {
      while (node.firstChild) node.removeChild(node.firstChild);
    }

    function groupsForFamily(familyId, mode) {
      if (mode === "primitive") {
        const values = Array.from(familyToTypes.get(familyId) || []);
        return values.length ? values.sort((a, b) => a.localeCompare(b)) : ["No primitive instances tagged"];
      }
      if (mode === "construction") {
        const values = Array.from(familyToConstructions.get(familyId) || []);
        return values.length ? values.sort((a, b) => a.localeCompare(b)) : ["No construction tagged"];
      }
      const values = Array.from(familyToTargets.get(familyId) || []);
      return values.length ? values.sort((a, b) => a.localeCompare(b)) : ["Unspecified target"];
    }

    function relationInfo(edge) {
      const relations = parseJsonArray(edge.relations_json);
      const fallback = String(edge.relation || "").trim();
      const effective = relations.length ? relations : (fallback ? [fallback] : []);
      const label = effective.map((item) => String(item).replace(/_/g, " ")).join(", ");
      return { count: Math.max(1, effective.length || 1), label: label || "related" };
    }

    function modePalette(mode) {
      if (mode === "construction") return ["rgba(248, 240, 224, 0.92)", "rgba(252, 247, 238, 0.98)"];
      if (mode === "target") return ["rgba(232, 243, 234, 0.92)", "rgba(246, 251, 247, 0.98)"];
      return ["rgba(231, 244, 248, 0.92)", "rgba(246, 251, 252, 0.98)"];
    }

    function modeLabel(mode) {
      const option = groupBy.options[groupBy.selectedIndex];
      return option ? option.textContent : mode;
    }

    function truncateLabel(text, maxChars) {
      const normalized = String(text || "");
      if (normalized.length <= maxChars) return normalized;
      return `${normalized.slice(0, Math.max(1, maxChars - 1))}…`;
    }

    function shortGroupLabel(name) {
      const m = name.match(/\\(([A-Z][A-Z0-9]*)/);
      return m ? m[1] : name;
    }

    function charsForWidth(widthPx) {
      return Math.max(7, Math.min(28, Math.floor(widthPx / (Math.max(fontPx, 8) * 0.62))));
    }

    function selectionMap(mode) {
      return modeSelections[mode] || modeSelections.primitive;
    }

    function syncAxisTracks() {
      yAxisTrack.style.transform = `translateY(${-plotScroll.scrollTop}px)`;
      xAxisTrack.style.transform = `translateX(${-plotScroll.scrollLeft}px)`;
    }

    function clampZoom(nextZoom) {
      return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, nextZoom));
    }

    function applyZoom() {
      const scaledH = Math.round(lastRenderSize.plotHeight * zoomScale);
      const maxFrameH = Math.round(window.innerHeight * 0.68);
      vizFrame.style.height = `${Math.max(160, Math.min(scaledH, maxFrameH)) + AXIS_HEIGHT}px`;
      plotSvg.style.width = `${Math.round(lastRenderSize.plotWidth * zoomScale)}px`;
      plotSvg.style.height = `${scaledH}px`;
      xAxisSvg.style.width = `${Math.round(lastRenderSize.plotWidth * zoomScale)}px`;
      xAxisSvg.style.height = `${AXIS_HEIGHT}px`;
      yAxisSvg.style.width = `${LEFT_AXIS_WIDTH}px`;
      yAxisSvg.style.height = `${scaledH}px`;
      zoomValue.textContent = `${Math.round(zoomScale * 100)}%`;
      syncAxisTracks();
    }

    function setZoom(nextZoom) {
      zoomScale = clampZoom(nextZoom);
      applyZoom();
    }

    function fitZoom() {
      if (!plotScroll.clientWidth || !lastRenderSize.plotWidth) return;
      const fitWidth = Math.max(240, plotScroll.clientWidth - 8);
      setZoom(fitWidth / lastRenderSize.plotWidth);
    }

    function ensureSelection(mode, labels) {
      const active = selectionMap(mode);
      labels.forEach((label) => {
        if (!active.has(label)) active.set(label, true);
      });
      Array.from(active.keys()).forEach((label) => {
        if (!labels.includes(label)) active.delete(label);
      });
      return active;
    }

    function initializeYearBounds() {
      if (yearsBounds) return yearsBounds;
      const validYears = families
        .map((family) => Number(family.year))
        .filter((year) => Number.isFinite(year))
        .sort((a, b) => a - b);
      if (!validYears.length) return null;
      yearsBounds = { min: validYears[0], max: validYears[validYears.length - 1] };
      yearStart.min = String(yearsBounds.min);
      yearStart.max = String(yearsBounds.max);
      yearEnd.min = String(yearsBounds.min);
      yearEnd.max = String(yearsBounds.max);
      yearStart.step = "1";
      yearEnd.step = "1";
      yearStart.value = String(yearsBounds.min);
      yearEnd.value = String(yearsBounds.max);
      return yearsBounds;
    }

    function getYearRange() {
      const bounds = initializeYearBounds();
      if (!bounds) return null;
      const start = Number(yearStart.value || bounds.min);
      const end = Number(yearEnd.value || bounds.max);
      return {
        start: Number.isFinite(start) ? start : bounds.min,
        end: Number.isFinite(end) ? end : bounds.max,
        min: bounds.min,
        max: bounds.max,
      };
    }

    function normalizeYearControls() {
      const yearRange = getYearRange();
      if (!yearRange) {
        yearRangeValue.textContent = "No years available";
        return null;
      }
      let start = yearRange.start;
      let end = yearRange.end;
      if (start > end) {
        if (document.activeElement === yearStart) {
          end = start;
          yearEnd.value = String(end);
        } else {
          start = end;
          yearStart.value = String(start);
        }
      }
      yearRangeValue.textContent = start === end ? `${start}` : `${start} - ${end}`;
      return { start, end };
    }

    function renderGroupFilterList(mode, labels) {
      const active = ensureSelection(mode, labels);
      clearNode(groupFilters);
      labels.forEach((label) => {
        const row = document.createElement("label");
        const box = document.createElement("input");
        box.type = "checkbox";
        box.checked = active.get(label) !== false;
        box.setAttribute("data-group-label", label);
        const text = document.createElement("span");
        const shortLabel = shortGroupLabel(label);
        text.textContent = shortLabel;
        if (shortLabel !== label) row.title = label;
        row.appendChild(box);
        row.appendChild(text);
        groupFilters.appendChild(row);
      });
    }

    function renderEmptyState(message) {
      clearNode(plotSvg);
      clearNode(xAxisSvg);
      clearNode(yAxisSvg);
      relationInfoBox.hidden = !showArrows.checked;
      if (showArrows.checked) relationInfoBox.textContent = BASE_RELATION_TEXT;
      cornerPane.innerHTML = `<b>${escapeHtml(modeLabel(groupBy.value))}</b><span style="font-weight:400;opacity:0.75">Publication year</span>`;
      plotSvg.setAttribute("viewBox", "0 0 920 260");
      plotSvg.setAttribute("width", "920");
      plotSvg.setAttribute("height", "260");
      xAxisSvg.setAttribute("viewBox", `0 0 920 ${AXIS_HEIGHT}`);
      xAxisSvg.setAttribute("width", "920");
      xAxisSvg.setAttribute("height", String(AXIS_HEIGHT));
      yAxisSvg.setAttribute("viewBox", `0 0 ${LEFT_AXIS_WIDTH} 260`);
      yAxisSvg.setAttribute("width", String(LEFT_AXIS_WIDTH));
      yAxisSvg.setAttribute("height", "260");
      lastRenderSize = { plotWidth: 920, plotHeight: 260 };
      const msg = document.createElementNS("http://www.w3.org/2000/svg", "text");
      msg.setAttribute("x", "24");
      msg.setAttribute("y", "42");
      msg.setAttribute("class", "viz-label");
      msg.textContent = message;
      plotSvg.appendChild(msg);
      applyZoom();
    }

    function render() {
      clearNode(plotSvg);
      clearNode(xAxisSvg);
      clearNode(yAxisSvg);
      relationInfoBox.hidden = !showArrows.checked;
      if (showArrows.checked) relationInfoBox.textContent = BASE_RELATION_TEXT;
      const mode = groupBy.value;
      cornerPane.innerHTML = `<b>${escapeHtml(modeLabel(mode))}</b><span style="font-weight:400;opacity:0.75">Publication year</span>`;
      const rawPoints = [];
      const yearRange = normalizeYearControls();
      const searchNeedle = familySearch.value.trim().toLowerCase();

      families.forEach((family) => {
        const year = Number(family.year);
        if (!Number.isFinite(year)) return;
        if (yearRange && (year < yearRange.start || year > yearRange.end)) return;
        const familyId = String(family.id || "");
        if (!familyId) return;
        const familyName = String(family.name || familyId);
        if (searchNeedle && !familyName.toLowerCase().includes(searchNeedle)) return;
        groupsForFamily(familyId, mode).forEach((group) => {
          rawPoints.push({
            familyId,
            name: familyName,
            year,
            group,
          });
        });
      });

      if (!rawPoints.length) {
        if (searchNeedle) {
          renderEmptyState("No families match the current name search and year range.");
        } else {
          renderEmptyState("No family data available for visualization.");
        }
        return;
      }

      const allGroupLabels = Array.from(new Set(rawPoints.map((point) => point.group))).sort((a, b) => a.localeCompare(b));
      renderGroupFilterList(mode, allGroupLabels);
      const activeGroups = ensureSelection(mode, allGroupLabels);
      const points = rawPoints.filter((point) => activeGroups.get(point.group) !== false);

      if (!points.length) {
        renderEmptyState("No groups are currently enabled. Re-enable at least one group to render the chart.");
        return;
      }

      points.sort((a, b) => a.group.localeCompare(b.group) || a.year - b.year || a.name.localeCompare(b.name));
      const groupLabels = Array.from(new Set(points.map((point) => point.group))).sort((a, b) => a.localeCompare(b));

      const collapseOn = collapseGroups.checked;
      const collapseN = Math.max(1, parseInt(collapseCount.value || "3", 10) || 3);

      // Pre-compute year/spacing estimates needed for wrap-mode line-count calculation
      const _earlyMinY = Math.min(...points.map((p) => p.year));
      const _earlyMaxY = Math.max(...points.map((p) => p.year));
      const _earlySpan = Math.max(1, _earlyMaxY - _earlyMinY);
      const _earlyLaneStep = Math.max(36, fontPx * 2.85);
      const _earlyBW = Math.max(840, (_earlySpan + 1) * (32 + fontPx * 0.8));
      const _earlySpacing = _earlySpan ? _earlyBW / _earlySpan : _earlyBW;
      const _earlyDotOff = hideDots.checked ? (POINT_RADIUS + 2) : 0;
      const _earlyMaxNamePx = Math.max(0, _earlySpacing - _earlyDotOff);
      const wrapLineChars = Math.max(2, Math.floor(_earlyMaxNamePx / (Math.max(fontPx, 8) * 0.58)));
      function wrapIntoLines(name, cpl) {
        const out = [];
        let cur = "";
        name.split(" ").forEach((word) => {
          const joined = cur ? `${cur} ${word}` : word;
          if (joined.length <= cpl) {
            cur = joined;
          } else if (cur) {
            out.push(cur);
            let w = word;
            while (w.length > cpl) { out.push(w.slice(0, cpl)); w = w.slice(cpl); }
            cur = w;
          } else {
            let w = word;
            while (w.length > cpl) { out.push(w.slice(0, cpl)); w = w.slice(cpl); }
            cur = w;
          }
        });
        if (cur) out.push(cur);
        return out;
      }
      function _countLines(name) { return Math.min(wrapIntoLines(name, wrapLineChars).length, 2); }
      let _maxLinesNeeded = 1;
      if (nameMode === "wrap") {
        points.forEach((p) => { _maxLinesNeeded = Math.max(_maxLinesNeeded, _countLines(p.name)); });
      }
      const effectiveStackStep = nameMode === "wrap"
        ? Math.max(STACK_STEP, _maxLinesNeeded * (fontPx * 1.4) / _earlyLaneStep + 0.04)
        : STACK_STEP;

      const familyCountByGroup = new Map();
      points.forEach((p) => {
        if (!familyCountByGroup.has(p.group)) familyCountByGroup.set(p.group, new Set());
        familyCountByGroup.get(p.group).add(p.familyId);
      });

      const counters = new Map();
      const maxStackByGroup = new Map();
      const ellipsisCells = [];

      points.forEach((point) => {
        const key = `${point.group}|||${point.year}`;
        const stack = counters.get(key) || 0;
        counters.set(key, stack + 1);
        if (collapseOn && stack >= collapseN) {
          point.stackIndex = -1;
          if (stack === collapseN) {
            ellipsisCells.push({ group: point.group, year: point.year, stackIndex: collapseN });
            maxStackByGroup.set(point.group, Math.max(maxStackByGroup.get(point.group) || 0, collapseN + 1));
          }
        } else {
          point.stackIndex = stack;
          maxStackByGroup.set(point.group, Math.max(maxStackByGroup.get(point.group) || 0, stack + 1));
        }
      });

      const visiblePoints = points.filter((point) => point.stackIndex !== -1);

      const groupLayout = new Map();
      let nextBaseUnit = 0;
      groupLabels.forEach((label) => {
        const maxStack = maxStackByGroup.get(label) || 1;
        const spanUnits = 1 + Math.max(0, maxStack - 1) * effectiveStackStep;
        const endUnit = nextBaseUnit + spanUnits;
        groupLayout.set(label, { startUnit: nextBaseUnit, endUnit });
        nextBaseUnit = endUnit + GROUP_GAP_UNITS;
      });

      visiblePoints.forEach((point) => {
        const layout = groupLayout.get(point.group);
        point.yUnit = (layout ? layout.startUnit : 0) + point.stackIndex * effectiveStackStep;
      });

      const minYear = Math.min(...points.map((point) => point.year));
      const maxYear = Math.max(...points.map((point) => point.year));
      const span = Math.max(1, maxYear - minYear);
      const laneStep = Math.max(36, fontPx * 2.85);
      const topPad = 12;
      let longestNamePx = 0;
      if (nameMode === "full") {
        visiblePoints.forEach((p) => { longestNamePx = Math.max(longestNamePx, p.name.length * Math.max(fontPx, 8) * 0.62); });
      }
      const _minColW = nameMode === "full" ? POINT_RADIUS + longestNamePx + 16 : 32 + fontPx * 0.8;
      const basePlotWidth = Math.max(840, (span + 1) * Math.max(32 + fontPx * 0.8, _minColW));
      const maxYUnit = Math.max(
        ...visiblePoints.map((point) => point.yUnit || 0),
        ...Array.from(groupLayout.values()).map((layout) => layout.endUnit)
      );
      const plotHeight = Math.max(240, topPad + (maxYUnit + 1) * laneStep + 10);

      const roughYearSpacing = span ? basePlotWidth / span : basePlotWidth;
      const dotOff = hideDots.checked ? (POINT_RADIUS + 2) : 0;
      const maxNamePx = Math.max(0, roughYearSpacing - dotOff);
      const familyLabelChars = (nameMode === "off" || nameMode === "wrap") ? 0 : Math.max(0, Math.floor(maxNamePx / (Math.max(fontPx, 8) * 0.58)));
      const plotLeftPad = POINT_RADIUS + 3;
      const estimatedLabelWidth = nameMode === "off" ? 0
        : nameMode === "full" ? longestNamePx + POINT_RADIUS + 10
        : nameMode === "wrap" ? maxNamePx + POINT_RADIUS + 10
        : familyLabelChars * Math.max(fontPx, 8) * 0.62 + POINT_RADIUS + 10;
      const plotRightPad = Math.max(POINT_RADIUS + 4, estimatedLabelWidth);
      const plotWidth = basePlotWidth + plotLeftPad + plotRightPad;
      const innerPlotWidth = Math.max(1, plotWidth - plotLeftPad - plotRightPad);
      lastRenderSize = { plotWidth, plotHeight };

      plotSvg.setAttribute("viewBox", `0 0 ${plotWidth} ${plotHeight}`);
      plotSvg.setAttribute("width", String(plotWidth));
      plotSvg.setAttribute("height", String(plotHeight));
      xAxisSvg.setAttribute("viewBox", `0 0 ${plotWidth} ${AXIS_HEIGHT}`);
      xAxisSvg.setAttribute("width", String(plotWidth));
      xAxisSvg.setAttribute("height", String(AXIS_HEIGHT));
      yAxisSvg.setAttribute("viewBox", `0 0 ${LEFT_AXIS_WIDTH} ${plotHeight}`);
      yAxisSvg.setAttribute("width", String(LEFT_AXIS_WIDTH));
      yAxisSvg.setAttribute("height", String(plotHeight));

      function xFor(year) {
        if (minYear === maxYear) return plotLeftPad + innerPlotWidth / 2;
        return plotLeftPad + ((year - minYear) / (maxYear - minYear)) * innerPlotWidth;
      }

      function yFor(yUnit) {
        return topPad + yUnit * laneStep;
      }

      const palette = modePalette(mode);

      const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
      const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
      marker.setAttribute("id", "vizArrowHead");
      marker.setAttribute("markerWidth", "10");
      marker.setAttribute("markerHeight", "7");
      marker.setAttribute("markerUnits", "userSpaceOnUse");
      marker.setAttribute("refX", "9");
      marker.setAttribute("refY", "3.5");
      marker.setAttribute("orient", "auto");
      const markerPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
      markerPath.setAttribute("d", "M0,0 L10,3.5 L0,7 z");
      markerPath.setAttribute("fill", "rgba(76, 91, 95, 0.72)");
      marker.appendChild(markerPath);
      defs.appendChild(marker);
      plotSvg.appendChild(defs);

      groupLabels.forEach((label, index) => {
        const layout = groupLayout.get(label);
        if (!layout) return;
        const y = yFor(layout.startUnit);
        const bandTop = Math.max(0, y - laneStep * 0.54);
        const bandBottom = Math.min(plotHeight, yFor(layout.endUnit) + laneStep * 0.28);
        const fill = palette[index % palette.length];

        const plotBand = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        plotBand.setAttribute("x", "0");
        plotBand.setAttribute("y", String(bandTop));
        plotBand.setAttribute("width", String(plotWidth));
        plotBand.setAttribute("height", String(Math.max(1, bandBottom - bandTop)));
        plotBand.setAttribute("fill", fill);
        plotSvg.appendChild(plotBand);

        const yBand = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        yBand.setAttribute("x", "0");
        yBand.setAttribute("y", String(bandTop));
        yBand.setAttribute("width", String(LEFT_AXIS_WIDTH));
        yBand.setAttribute("height", String(Math.max(1, bandBottom - bandTop)));
        yBand.setAttribute("fill", fill);
        yAxisSvg.appendChild(yBand);

        const guide = document.createElementNS("http://www.w3.org/2000/svg", "line");
        guide.setAttribute("x1", "0");
        guide.setAttribute("x2", String(plotWidth));
        guide.setAttribute("y1", String(bandTop));
        guide.setAttribute("y2", String(bandTop));
        guide.setAttribute("class", "viz-grid");
        plotSvg.appendChild(guide);

        const yCenter = bandTop + (bandBottom - bandTop) / 2;
        const xPos = LEFT_AXIS_WIDTH - 5;
        const groupCount = (familyCountByGroup.get(label) || new Set()).size;
        const shortLabel = shortGroupLabel(label);
        const labelWithCount = `${shortLabel} (${groupCount})`;
        const fullLabelWithCount = `${label} (${groupCount})`;
        const yText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        yText.setAttribute("x", String(xPos));
        yText.setAttribute("text-anchor", "end");
        yText.setAttribute("class", "viz-label");
        yText.setAttribute("style", `font-size:${fontPx}px`);
        const maxCharsPerLine = Math.max(4, Math.floor((LEFT_AXIS_WIDTH - 10) / (Math.max(fontPx, 8) * 0.6)));
        const yWords = labelWithCount.split(" ");
        const yLines = [];
        let yCurLine = "";
        yWords.forEach((word) => {
          const test = yCurLine ? `${yCurLine} ${word}` : word;
          if (test.length > maxCharsPerLine && yCurLine) { yLines.push(yCurLine); yCurLine = word; }
          else yCurLine = test;
        });
        if (yCurLine) yLines.push(yCurLine);
        const lineH = Math.round(fontPx * 1.35);
        const totalTextH = (yLines.length - 1) * lineH;
        yLines.forEach((line, i) => {
          const tspan = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
          tspan.setAttribute("x", String(xPos));
          tspan.setAttribute("y", String(yCenter - totalTextH / 2 + i * lineH + fontPx * 0.35));
          tspan.textContent = line;
          yText.appendChild(tspan);
        });
        const yTitle = document.createElementNS("http://www.w3.org/2000/svg", "title");
        yTitle.textContent = fullLabelWithCount;
        yText.appendChild(yTitle);
        yAxisSvg.appendChild(yText);
      });

      const yAxisLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
      yAxisLine.setAttribute("x1", String(LEFT_AXIS_WIDTH - 0.5));
      yAxisLine.setAttribute("x2", String(LEFT_AXIS_WIDTH - 0.5));
      yAxisLine.setAttribute("y1", "0");
      yAxisLine.setAttribute("y2", String(plotHeight));
      yAxisLine.setAttribute("class", "viz-axis");
      yAxisSvg.appendChild(yAxisLine);

      const xAxisLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
      xAxisLine.setAttribute("x1", "0");
      xAxisLine.setAttribute("x2", String(plotWidth));
      xAxisLine.setAttribute("y1", "0.5");
      xAxisLine.setAttribute("y2", "0.5");
      xAxisLine.setAttribute("class", "viz-axis");
      xAxisSvg.appendChild(xAxisLine);

      const pixelsPerYear = span ? innerPlotWidth / span : innerPlotWidth;
      const minLabelPx = Math.max(fontPx, 8) * 4.5;
      const labelStepRaw = minLabelPx / Math.max(pixelsPerYear, 0.1);
      const labelStep = labelStepRaw <= 1 ? 1 : labelStepRaw <= 2 ? 2 : labelStepRaw <= 5 ? 5 : 10;

      for (let year = minYear; year <= maxYear; year++) {
        const x = xFor(year);
        const grid = document.createElementNS("http://www.w3.org/2000/svg", "line");
        grid.setAttribute("x1", String(x));
        grid.setAttribute("x2", String(x));
        grid.setAttribute("y1", "0");
        grid.setAttribute("y2", String(plotHeight));
        grid.setAttribute("class", "viz-grid");
        plotSvg.appendChild(grid);

        if ((year - minYear) % labelStep === 0) {
          const tickMark = document.createElementNS("http://www.w3.org/2000/svg", "line");
          tickMark.setAttribute("x1", String(x));
          tickMark.setAttribute("x2", String(x));
          tickMark.setAttribute("y1", "0");
          tickMark.setAttribute("y2", "9");
          tickMark.setAttribute("class", "viz-axis");
          xAxisSvg.appendChild(tickMark);

          const tick = document.createElementNS("http://www.w3.org/2000/svg", "text");
          tick.setAttribute("x", String(x));
          tick.setAttribute("y", "24");
          tick.setAttribute("text-anchor", "middle");
          tick.setAttribute("class", "viz-label");
          tick.setAttribute("style", `font-size:${Math.max(10, fontPx - 1)}px`);
          tick.textContent = String(year);
          xAxisSvg.appendChild(tick);
        }
      }

      const pointPositions = visiblePoints.map((point) => ({
        ...point,
        x: xFor(point.year),
        y: yFor(point.yUnit || 0),
      }));

      const anchorByFamily = new Map();
      pointPositions.forEach((point) => {
        if (!anchorByFamily.has(point.familyId)) {
          anchorByFamily.set(point.familyId, { sx: 0, sy: 0, count: 0 });
        }
        const anchor = anchorByFamily.get(point.familyId);
        anchor.sx += point.x;
        anchor.sy += point.y;
        anchor.count += 1;
      });

      const hoverLines = [];
      if (showArrows.checked) {
        influences.forEach((edge) => {
          const sourceId = String(edge.source_family_id || "");
          const targetId = String(edge.target_family_id || "");
          const source = anchorByFamily.get(sourceId);
          const target = anchorByFamily.get(targetId);
          if (!source || !target) return;

          const sx = source.sx / source.count;
          const sy = source.sy / source.count;
          const tx = target.sx / target.count;
          const ty = target.sy / target.count;
          const rel = relationInfo(edge);
          const width = 1.15 + (rel.count - 1) * 1.05;

          const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
          line.setAttribute("x1", String(sx));
          line.setAttribute("y1", String(sy));
          line.setAttribute("x2", String(tx));
          line.setAttribute("y2", String(ty));
          line.setAttribute("stroke-width", String(width));
          line.setAttribute("marker-end", "url(#vizArrowHead)");
          line.setAttribute("class", "viz-edge");
          line.setAttribute("pointer-events", "none");
          plotSvg.appendChild(line);

          const hoverLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
          hoverLine.setAttribute("x1", String(sx));
          hoverLine.setAttribute("y1", String(sy));
          hoverLine.setAttribute("x2", String(tx));
          hoverLine.setAttribute("y2", String(ty));
          hoverLine.setAttribute("stroke", "rgba(0,0,0,0.001)");
          hoverLine.setAttribute("stroke-width", String(Math.max(10, width + 8)));
          hoverLine.setAttribute("pointer-events", "all");
          const hoverText = `${edge.source_family_id} -> ${edge.target_family_id} | Relations: ${rel.label} | ${normalizeValue(edge.note)}`;
          const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
          title.textContent = hoverText;
          hoverLine.appendChild(title);
          hoverLine.addEventListener("mouseenter", () => {
            relationInfoBox.textContent = hoverText;
          });
          hoverLine.addEventListener("mouseleave", () => {
            relationInfoBox.textContent = BASE_RELATION_TEXT;
          });
          hoverLines.push(hoverLine);
        });
      }

      const useProcessColor = colorByProcess.checked;

      pointPositions.forEach((point) => {
        const famData = familyById.get(point.familyId);
        const famTypes = Array.from(familyToTypes.get(point.familyId) || []).sort((a, b) => a.localeCompare(b)).join(", ") || "—";
        const famNotes = famData && famData.notes ? String(famData.notes).trim() : "";
        const procName = processNameForFamily(point.familyId);
        const tipParts = [`${point.name} (${point.year})`, `Type: ${famTypes}`, `Group: ${point.group}`];
        if (procName) tipParts.push(`Process: ${procName}`);
        if (famNotes) tipParts.push("\\n" + famNotes);
        const richTip = tipParts.join("\\n");
        const dotColor = useProcessColor ? processColorForFamily(point.familyId) : null;

        if (hideDots.checked) {
          const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
          circle.setAttribute("cx", String(point.x));
          circle.setAttribute("cy", String(point.y));
          circle.setAttribute("r", String(POINT_RADIUS));
          circle.setAttribute("class", "viz-point");
          if (dotColor) circle.setAttribute("fill", dotColor);
          const pointTitle = document.createElementNS("http://www.w3.org/2000/svg", "title");
          pointTitle.textContent = richTip;
          circle.appendChild(pointTitle);
          plotSvg.appendChild(circle);
        }

        if (nameMode !== "off") {
          const labelX = hideDots.checked ? point.x + POINT_RADIUS + 2 : point.x;
          const labelStyle = dotColor
            ? `font-size:${fontPx}px;font-family:"IBM Plex Mono",monospace;fill:${dotColor}`
            : `font-size:${fontPx}px;font-family:"IBM Plex Mono",monospace`;
          const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
          label.setAttribute("text-anchor", "start");
          label.setAttribute("class", "viz-text");
          label.setAttribute("style", labelStyle);
          if (nameMode === "wrap") {
            const dispLines = wrapIntoLines(point.name, wrapLineChars).slice(0, 2);
            const lineH = Math.round(fontPx * 1.3);
            dispLines.forEach((line, i) => {
              const tspan = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
              tspan.setAttribute("x", String(i > 0 ? labelX + 4 : labelX));
              tspan.setAttribute("y", String(point.y + 3.5 + i * lineH));
              tspan.textContent = line;
              label.appendChild(tspan);
            });
          } else {
            label.setAttribute("x", String(labelX));
            label.setAttribute("y", String(point.y + 3.5));
            label.textContent = nameMode === "full" ? point.name : truncateLabel(point.name, familyLabelChars);
          }
          const fullTitle = document.createElementNS("http://www.w3.org/2000/svg", "title");
          fullTitle.textContent = richTip;
          label.appendChild(fullTitle);
          plotSvg.appendChild(label);
        }
      });

      hoverLines.forEach((hoverLine) => plotSvg.appendChild(hoverLine));

      if (collapseOn) {
        ellipsisCells.forEach((cell) => {
          const layout = groupLayout.get(cell.group);
          if (!layout) return;
          const x = xFor(cell.year);
          const y = yFor(layout.startUnit + cell.stackIndex * effectiveStackStep);
          const cellKey = `${cell.group}|||${cell.year}`;
          const hiddenCount = (counters.get(cellKey) || 0) - collapseN;

          if (hideDots.checked) {
            const ellDot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            ellDot.setAttribute("cx", String(x));
            ellDot.setAttribute("cy", String(y));
            ellDot.setAttribute("r", String(POINT_RADIUS));
            ellDot.setAttribute("fill", "#b0babf");
            ellDot.setAttribute("stroke", "#ffffff");
            ellDot.setAttribute("stroke-width", "1.1");
            ellDot.setAttribute("stroke-dasharray", "2 2");
            const ellTitle = document.createElementNS("http://www.w3.org/2000/svg", "title");
            ellTitle.textContent = `+${hiddenCount} more in ${cell.group} (${cell.year})`;
            ellDot.appendChild(ellTitle);
            plotSvg.appendChild(ellDot);
          }

          if (nameMode !== "off") {
            const ellLabelX = hideDots.checked ? x + POINT_RADIUS + 2 : x;
            const ellText = document.createElementNS("http://www.w3.org/2000/svg", "text");
            ellText.setAttribute("x", String(ellLabelX));
            ellText.setAttribute("y", String(y + 3.5));
            ellText.setAttribute("text-anchor", "start");
            ellText.setAttribute("class", "viz-text");
            ellText.setAttribute("style", `font-size:${fontPx}px;font-family:"IBM Plex Mono",monospace;fill:#7a8c8f`);
            ellText.textContent = `+${hiddenCount}`;
            plotSvg.appendChild(ellText);
          }
        });
      }

      // Process legend
      if (useProcessColor && processList.length) {
        processLegend.hidden = false;
        clearNode(processLegend);
        processList.forEach((proc) => {
          const color = processColorMap.get(String(proc.id)) || "#7a8c8f";
          const item = document.createElement("span");
          item.className = "viz-process-legend-item";
          const dot = document.createElement("span");
          dot.className = "viz-process-legend-dot";
          dot.style.background = color;
          const lbl = document.createElement("span");
          lbl.textContent = String(proc.name);
          item.appendChild(dot);
          item.appendChild(lbl);
          processLegend.appendChild(item);
        });
        const noneItem = document.createElement("span");
        noneItem.className = "viz-process-legend-item";
        const noneDot = document.createElement("span");
        noneDot.className = "viz-process-legend-dot";
        noneDot.style.background = processColorMap.get("__none__");
        const noneLbl = document.createElement("span");
        noneLbl.textContent = "No process";
        noneItem.appendChild(noneDot);
        noneItem.appendChild(noneLbl);
        processLegend.appendChild(noneItem);
      } else {
        processLegend.hidden = true;
      }

      fontValue.textContent = `${fontPx}px`;
      if (!hasAutoFit) {
        hasAutoFit = true;
        fitZoom();
      } else {
        applyZoom();
      }
    }

    groupBy.addEventListener("change", render);
    showArrows.addEventListener("change", render);
    hideDots.addEventListener("change", render);
    [["off", nameModeOff], ["clip", nameModeClip], ["wrap", nameModeWrap], ["full", nameModeFull]].forEach(([mode, btn]) => {
      btn.addEventListener("click", () => {
        nameMode = mode;
        [nameModeOff, nameModeClip, nameModeWrap, nameModeFull].forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        render();
      });
    });
    colorByProcess.addEventListener("change", render);
    collapseGroups.addEventListener("change", render);
    collapseCount.addEventListener("change", render);
    collapseCount.addEventListener("input", render);
    familySearch.addEventListener("input", render);
    familySearch.addEventListener("change", render);
    groupFilters.addEventListener("change", (event) => {
      const target = event.target;
      if (!target || target.type !== "checkbox") return;
      selectionMap(groupBy.value).set(target.getAttribute("data-group-label") || "", target.checked);
      render();
    });
    filterAll.addEventListener("click", () => {
      const active = selectionMap(groupBy.value);
      Array.from(active.keys()).forEach((label) => active.set(label, true));
      render();
    });
    filterNone.addEventListener("click", () => {
      const active = selectionMap(groupBy.value);
      Array.from(active.keys()).forEach((label) => active.set(label, false));
      render();
    });
    fontMinus.addEventListener("click", () => {
      fontPx = Math.max(8, fontPx - 1);
      render();
    });
    fontPlus.addEventListener("click", () => {
      fontPx = Math.min(16, fontPx + 1);
      render();
    });
    fontReset.addEventListener("click", () => {
      fontPx = BASE_FONT;
      render();
    });
    zoomOut.addEventListener("click", () => setZoom(zoomScale / ZOOM_FACTOR));
    zoomIn.addEventListener("click", () => setZoom(zoomScale * ZOOM_FACTOR));
    zoomReset.addEventListener("click", () => setZoom(BASE_ZOOM));
    zoomFit.addEventListener("click", () => fitZoom());
    yearStart.addEventListener("input", () => {
      if (suppressYearRender) return;
      render();
    });
    yearEnd.addEventListener("input", () => {
      if (suppressYearRender) return;
      render();
    });
    yearReset.addEventListener("click", () => {
      const bounds = initializeYearBounds();
      if (!bounds) return;
      suppressYearRender = true;
      yearStart.value = String(bounds.min);
      yearEnd.value = String(bounds.max);
      suppressYearRender = false;
      render();
    });
    plotScroll.addEventListener("scroll", syncAxisTracks);
    plotScroll.addEventListener("wheel", (event) => {
      if (!(event.ctrlKey || event.metaKey)) return;
      event.preventDefault();
      const factor = event.deltaY < 0 ? ZOOM_FACTOR : 1 / ZOOM_FACTOR;
      setZoom(zoomScale * factor);
    }, { passive: false });
    render();
  }

  renderSummary();
  setupNavigator();
  setupAllTablesBrowser();
  setupBuilder();
  setupFamilyVisualization();
})();
"""

    data_js = "window.__SPDB_DATA__ = " + json.dumps(payload, ensure_ascii=True) + ";\n"

    write_text(SITE_DIR / "index.html", index_html)
    write_text(SITE_DIR / "styles.css", styles_css)
    write_text(SITE_DIR / "app.js", app_js)
    write_text(SITE_DIR / "data.js", data_js)

    print(f"Static site generated in: {SITE_DIR}")


if __name__ == "__main__":
    build_site()
