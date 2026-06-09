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
          p.fixed_input_bits AS "primitive.fixed_input_bits",
          p.fixed_output_bits AS "primitive.fixed_output_bits",
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
        'p.fixed_input_bits AS "primitive.fixed_input_bits", '
        'p.fixed_output_bits AS "primitive.fixed_output_bits", '
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


def build_site() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Missing {DB_PATH}. Run make build-db first.")

    with sqlite3.connect(DB_PATH) as conn:
        all_tables = load_all_tables(conn)
        builder_dataset = load_join_builder_dataset(conn)

    payload = {
        "summary": {
            "tableCount": len(all_tables),
            "totalRows": sum(t["rowCount"] for t in all_tables.values()),
            "builderRows": len(builder_dataset["rows"]),
        },
        "tables": all_tables,
        "joinBuilder": builder_dataset,
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
          <button type=\"button\" class=\"nav-tab\" data-view-target=\"visualizations\">Family Visualizations</button>
          <button type=\"button\" class=\"nav-tab is-active\" data-view-target=\"tables\">All SQLite Tables</button>
          <button type=\"button\" class=\"nav-tab\" data-view-target=\"builder\">Custom Query Builder</button>
        </nav>
      </header>

      <section class=\"panel meta\" id=\"summary\"></section>

      <section class=\"panel view-panel\" data-view=\"visualizations\">
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
          <label class=\"inline-check\"><input id=\"vizShowArrows\" type=\"checkbox\" /> Show relation arrows</label>
          <div class=\"viz-font-controls\" aria-label=\"Timeline font size\">
            <button id=\"vizFontMinus\" type=\"button\">A-</button>
            <button id=\"vizFontPlus\" type=\"button\">A+</button>
            <button id=\"vizFontReset\" type=\"button\">Reset</button>
            <span id=\"vizFontValue\" class=\"small-note\">12px</span>
          </div>
        </div>
        <div class=\"viz-wrap\">
          <svg id=\"familyViz\" role=\"img\" aria-label=\"Family timeline visualization\"></svg>
        </div>
        <p id=\"vizRelationInfo\" class=\"small-note viz-relation-info\">Hover a relation arrow to see relation details.</p>
      </section>

      <section class=\"panel view-panel is-active\" data-view=\"tables\">
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
  grid-template-columns: minmax(220px, 360px) auto auto;
  align-items: end;
}

.viz-font-controls {
  display: flex;
  align-items: center;
  gap: 0.42rem;
}

.viz-font-controls button {
  width: auto;
  margin-top: 0;
}

#vizFontValue {
  margin: 0;
  min-width: 3.2rem;
  text-align: right;
}

.viz-wrap {
  margin-top: 0.7rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  overflow: auto;
}

.viz-relation-info {
  margin: 0.55rem 0 0;
  min-height: 1.4rem;
}

#familyViz {
  width: auto;
  min-width: 920px;
  height: 640px;
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
  stroke-width: 1.2;
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
        activate(tab.getAttribute("data-view-target") || "tables");
      });
    });

    activate("tables");
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
    const svg = document.getElementById("familyViz");
    const groupBy = document.getElementById("vizGroupBy");
    const showArrows = document.getElementById("vizShowArrows");
    const fontMinus = document.getElementById("vizFontMinus");
    const fontPlus = document.getElementById("vizFontPlus");
    const fontReset = document.getElementById("vizFontReset");
    const fontValue = document.getElementById("vizFontValue");
    const relationInfoBox = document.getElementById("vizRelationInfo");
    if (!svg || !groupBy || !showArrows || !fontMinus || !fontPlus || !fontReset || !fontValue || !relationInfoBox) return;

    const BASE_FONT = 12;
    let fontPx = BASE_FONT;

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

    function groupsForFamily(familyId, mode) {
      if (mode === "primitive") {
        const values = Array.from(familyToTypes.get(familyId) || []);
        return values.length ? values.sort((a, b) => a.localeCompare(b)) : ["Unknown type"];
      }
      if (mode === "construction") {
        const values = Array.from(familyToConstructions.get(familyId) || []);
        return values.length ? values.sort((a, b) => a.localeCompare(b)) : ["Unspecified construction"];
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

    function clearSvg() {
      while (svg.firstChild) svg.removeChild(svg.firstChild);
    }

    function render() {
      clearSvg();
      relationInfoBox.textContent = "Hover a relation arrow to see relation details.";
      const mode = groupBy.value;
      const points = [];

      families.forEach((family) => {
        const year = Number(family.year);
        if (!Number.isFinite(year)) return;
        const familyId = String(family.id || "");
        if (!familyId) return;
        const groups = groupsForFamily(familyId, mode);
        groups.forEach((group) => {
          points.push({
            familyId,
            name: String(family.name || familyId),
            year,
            group,
          });
        });
      });

      if (!points.length) {
        const msg = document.createElementNS("http://www.w3.org/2000/svg", "text");
        msg.setAttribute("x", "24");
        msg.setAttribute("y", "40");
        msg.setAttribute("class", "viz-label");
        msg.textContent = "No family data available for visualization.";
        svg.appendChild(msg);
        return;
      }

      const groupLabels = Array.from(new Set(points.map((p) => p.group))).sort((a, b) => a.localeCompare(b));
      const groupBase = new Map(groupLabels.map((label, idx) => [label, idx]));
      points.sort((a, b) => a.group.localeCompare(b.group) || a.year - b.year || a.name.localeCompare(b.name));

      const counters = new Map();
      points.forEach((point) => {
        const key = `${point.group}|${point.year}`;
        const stack = counters.get(key) || 0;
        point.yUnit = (groupBase.get(point.group) || 0) + stack * 0.46;
        counters.set(key, stack + 1);
      });

      const minYear = Math.min(...points.map((p) => p.year));
      const maxYear = Math.max(...points.map((p) => p.year));
      const span = Math.max(1, maxYear - minYear);
      const laneStep = Math.max(64, fontPx * 4.9);
      const top = 26;
      const bottom = 54;
      const left = 220;
      const right = 32;
      const plotWidth = Math.max(980, (span + 1) * (42 + fontPx * 1.1));
      const maxYUnit = Math.max(...points.map((p) => p.yUnit || 0));
      const plotHeight = Math.max(320, (maxYUnit + 1) * laneStep + 10);
      const width = left + plotWidth + right;
      const height = top + plotHeight + bottom;

      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
      svg.setAttribute("width", String(width));
      svg.setAttribute("height", String(height));

      function xFor(year) {
        if (minYear === maxYear) return left + plotWidth / 2;
        return left + ((year - minYear) / (maxYear - minYear)) * plotWidth;
      }

      function yFor(yUnit) {
        return top + yUnit * laneStep;
      }

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
      markerPath.setAttribute("fill", "rgba(76, 91, 95, 0.75)");
      marker.appendChild(markerPath);
      defs.appendChild(marker);
      svg.appendChild(defs);

      const yAxis = document.createElementNS("http://www.w3.org/2000/svg", "line");
      yAxis.setAttribute("x1", String(left));
      yAxis.setAttribute("x2", String(left));
      yAxis.setAttribute("y1", String(top));
      yAxis.setAttribute("y2", String(top + plotHeight));
      yAxis.setAttribute("class", "viz-axis");
      svg.appendChild(yAxis);

      const xAxis = document.createElementNS("http://www.w3.org/2000/svg", "line");
      xAxis.setAttribute("x1", String(left));
      xAxis.setAttribute("x2", String(left + plotWidth));
      xAxis.setAttribute("y1", String(top + plotHeight));
      xAxis.setAttribute("y2", String(top + plotHeight));
      xAxis.setAttribute("class", "viz-axis");
      svg.appendChild(xAxis);

      groupLabels.forEach((label) => {
        const base = groupBase.get(label) || 0;
        const y = yFor(base);
        const guide = document.createElementNS("http://www.w3.org/2000/svg", "line");
        guide.setAttribute("x1", String(left));
        guide.setAttribute("x2", String(left + plotWidth));
        guide.setAttribute("y1", String(y));
        guide.setAttribute("y2", String(y));
        guide.setAttribute("class", "viz-grid");
        svg.appendChild(guide);

        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", String(left - 8));
        text.setAttribute("y", String(y + 4));
        text.setAttribute("text-anchor", "end");
        text.setAttribute("class", "viz-label");
        text.setAttribute("style", `font-size:${fontPx}px`);
        text.textContent = label;
        svg.appendChild(text);
      });

      const tickStep = span > 40 ? 5 : span > 20 ? 2 : 1;
      for (let year = minYear; year <= maxYear; year += tickStep) {
        const x = xFor(year);
        const grid = document.createElementNS("http://www.w3.org/2000/svg", "line");
        grid.setAttribute("x1", String(x));
        grid.setAttribute("x2", String(x));
        grid.setAttribute("y1", String(top));
        grid.setAttribute("y2", String(top + plotHeight));
        grid.setAttribute("class", "viz-grid");
        svg.appendChild(grid);

        const tick = document.createElementNS("http://www.w3.org/2000/svg", "text");
        tick.setAttribute("x", String(x));
        tick.setAttribute("y", String(top + plotHeight + 18));
        tick.setAttribute("text-anchor", "middle");
        tick.setAttribute("class", "viz-label");
        tick.setAttribute("style", `font-size:${Math.max(10, fontPx - 1)}px`);
        tick.textContent = String(year);
        svg.appendChild(tick);
      }

      const pointPositions = points.map((point) => ({
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
          const width = 1.4 + (rel.count - 1) * 1.3;
          const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
          line.setAttribute("x1", String(sx));
          line.setAttribute("y1", String(sy));
          line.setAttribute("x2", String(tx));
          line.setAttribute("y2", String(ty));
          line.setAttribute("stroke-width", String(width));
          line.setAttribute("marker-end", "url(#vizArrowHead)");
          line.setAttribute("class", "viz-edge");
          line.setAttribute("pointer-events", "none");

          const hoverLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
          hoverLine.setAttribute("x1", String(sx));
          hoverLine.setAttribute("y1", String(sy));
          hoverLine.setAttribute("x2", String(tx));
          hoverLine.setAttribute("y2", String(ty));
          hoverLine.setAttribute("stroke", "rgba(0,0,0,0.001)");
          hoverLine.setAttribute("stroke-width", String(Math.max(12, width + 10)));
          hoverLine.setAttribute("pointer-events", "all");

          const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
          const hoverText = `${edge.source_family_id} -> ${edge.target_family_id} | Relations: ${rel.label} | ${normalizeValue(edge.note)}`;
          title.textContent = hoverText;
          hoverLine.appendChild(title);
          hoverLine.addEventListener("mouseenter", () => {
            relationInfoBox.textContent = hoverText;
          });
          hoverLine.addEventListener("mouseleave", () => {
            relationInfoBox.textContent = "Hover a relation arrow to see relation details.";
          });
          svg.appendChild(line);
          hoverLines.push(hoverLine);
        });
      }

      pointPositions.forEach((point) => {
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", String(point.x));
        circle.setAttribute("cy", String(point.y));
        circle.setAttribute("r", "5.5");
        circle.setAttribute("class", "viz-point");
        const pointTitle = document.createElementNS("http://www.w3.org/2000/svg", "title");
        pointTitle.textContent = `${point.name} (${point.year})\nGroup: ${point.group}`;
        circle.appendChild(pointTitle);
        svg.appendChild(circle);

        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", String(point.x + 8));
        label.setAttribute("y", String(point.y + 4));
        label.setAttribute("text-anchor", "start");
        label.setAttribute("class", "viz-text");
        label.setAttribute("style", `font-size:${fontPx}px`);
        label.textContent = point.name;
        svg.appendChild(label);
      });

      hoverLines.forEach((hoverLine) => svg.appendChild(hoverLine));

      fontValue.textContent = `${fontPx}px`;
    }

    groupBy.addEventListener("change", render);
    showArrows.addEventListener("change", render);
    fontMinus.addEventListener("click", () => {
      fontPx = Math.max(8, fontPx - 1);
      render();
    });
    fontPlus.addEventListener("click", () => {
      fontPx = Math.min(18, fontPx + 1);
      render();
    });
    fontReset.addEventListener("click", () => {
      fontPx = BASE_FONT;
      render();
    });
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
