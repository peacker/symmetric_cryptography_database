#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
VIZ_DIR = ROOT / "build" / "viz"
TIMELINE_PATH = ROOT / "data" / "timeline.yaml"
SITE_DIR = ROOT / "build" / "site"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def require_viz_file(name: str) -> Path:
    path = VIZ_DIR / name
    if not path.exists():
        raise SystemExit(f"Missing {path}. Run make build-db export-viz first.")
    return path


def load_timeline_doc() -> dict[str, object]:
    if not TIMELINE_PATH.exists():
        return {}
    with TIMELINE_PATH.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    return doc if isinstance(doc, dict) else {}


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_site() -> None:
    timeline_rows = read_csv(require_viz_file("timeline_primitives.csv"))
    edges_rows = read_csv(require_viz_file("influence_edges.csv"))
    families_rows = read_csv(require_viz_file("families.csv"))

    timeline_doc = load_timeline_doc()
    timeline_events = timeline_doc.get("events", [])
    timeline_eras = timeline_doc.get("eras", [])

    if not isinstance(timeline_events, list):
        timeline_events = []
    if not isinstance(timeline_eras, list):
        timeline_eras = []

    primitive_types = sorted({row.get("primitive_type", "") for row in timeline_rows if row.get("primitive_type")})
    summary = {
        "primitives": len(timeline_rows),
        "families": len({row.get("family_id", "") for row in families_rows if row.get("family_id")}),
        "influences": len(edges_rows),
        "types": len(primitive_types),
    }

    payload = {
        "summary": summary,
        "primitives": timeline_rows,
        "families": families_rows,
        "influences": edges_rows,
        "timelineEvents": [e for e in timeline_events if isinstance(e, dict)],
        "timelineEras": [e for e in timeline_eras if isinstance(e, dict)],
    }

    index_html = """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Symmetric Primitives Database</title>
    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\" />
    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin />
    <link href=\"https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap\" rel=\"stylesheet\" />
    <link rel=\"stylesheet\" href=\"styles.css\" />
    <script src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\" defer></script>
    <script src=\"data.js\" defer></script>
    <script src=\"app.js\" defer></script>
  </head>
  <body>
    <main class=\"shell\">
      <section class=\"hero\">
        <p class=\"eyebrow\">Cryptography knowledge base</p>
        <h1>Symmetric Primitives Database</h1>
        <p class=\"subtitle\">Static public dashboard built from curated YAML datasets.</p>
      </section>

      <section class=\"stats\" id=\"stats\"></section>

      <section class=\"panel\">
        <h2>Timeline Explorer</h2>
        <div class=\"controls\">
          <label>Family type
            <select id=\"typeFilter\" multiple size=\"5\" autocomplete=\"off\"></select>
          </label>
          <label>Family
            <select id=\"familyFilter\" multiple size=\"6\" autocomplete=\"off\"></select>
          </label>
          <label>Construction
            <select id=\"constructionFilter\" multiple size=\"6\" autocomplete=\"off\"></select>
          </label>
          <label>Year range
            <div class=\"inline-range\">
              <input id=\"yearMin\" type=\"number\" placeholder=\"min\" />
              <input id=\"yearMax\" type=\"number\" placeholder=\"max\" />
            </div>
          </label>
          <label>Input bits range
            <div class=\"inline-range\">
              <input id=\"inputBitsMin\" type=\"number\" placeholder=\"min\" />
              <input id=\"inputBitsMax\" type=\"number\" placeholder=\"max\" />
            </div>
          </label>
          <label>Output bits range
            <div class=\"inline-range\">
              <input id=\"outputBitsMin\" type=\"number\" placeholder=\"min\" />
              <input id=\"outputBitsMax\" type=\"number\" placeholder=\"max\" />
            </div>
          </label>
          <label class=\"toggle\"><input id=\"showLabels\" type=\"checkbox\" checked /> Show cipher labels</label>
          <label class=\"toggle\"><input id=\"showEvents\" type=\"checkbox\" checked /> Show timeline events</label>
          <label class=\"toggle\"><input id=\"showEras\" type=\"checkbox\" checked /> Show eras</label>
          <label>Timeline zoom
            <div class=\"zoom-controls\">
              <button id=\"zoomOut\" type=\"button\">-</button>
              <input id=\"timelineZoom\" type=\"range\" min=\"60\" max=\"180\" value=\"100\" step=\"5\" />
              <button id=\"zoomIn\" type=\"button\">+</button>
            </div>
          </label>
          <button id=\"resetFilters\" type=\"button\">Reset filters</button>
        </div>
        <div id=\"timelineChart\" class=\"chart\"></div>
      </section>

      <section class=\"panel\">
        <h2>Influence Graph</h2>
        <div id=\"influenceChart\" class=\"chart\"></div>
      </section>

      <section class=\"panel\">
        <h2>Research Timeline Events</h2>
        <div id=\"events\" class=\"events\"></div>
      </section>
    </main>
  </body>
</html>
"""

    styles_css = """:root {
  --bg: #f7f8f2;
  --card: #ffffff;
  --ink: #16231a;
  --muted: #5f6f64;
  --accent: #0f766e;
  --line: #d8ded8;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  color: var(--ink);
  font-family: "Outfit", sans-serif;
  background:
    radial-gradient(circle at 20% 15%, #d8f0ea 0%, transparent 30%),
    radial-gradient(circle at 90% 5%, #f4e8cb 0%, transparent 28%),
    var(--bg);
}

.shell {
  width: min(98vw, 2200px);
  margin: 0 auto;
  padding: 2rem 1rem 3rem;
}

.hero h1 {
  margin: 0.2rem 0;
  font-family: "Space Grotesk", sans-serif;
  font-size: clamp(2rem, 3.8vw, 3.2rem);
}

.eyebrow {
  margin: 0;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent);
}

.subtitle {
  margin: 0;
  color: var(--muted);
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
  margin: 1.2rem 0;
}

.stat {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 0.9rem;
}

.stat .label {
  color: var(--muted);
  font-size: 0.82rem;
}

.stat .value {
  font-size: 1.6rem;
  font-family: "Space Grotesk", sans-serif;
}

.panel {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1rem;
  margin-top: 1rem;
}

.panel h2 {
  margin: 0.3rem 0 1rem;
  font-size: 1.2rem;
}

.controls {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.55rem 0.8rem;
  margin-bottom: 0.9rem;
}

.controls label {
  display: block;
  font-size: 0.82rem;
  color: var(--muted);
}

.controls select,
.controls input,
.controls button {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.42rem 0.5rem;
  font: inherit;
  color: var(--ink);
  background: #fff;
  margin-top: 0.25rem;
}

.controls select {
  min-height: 6.2rem;
}

.inline-range {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
}

.toggle {
  display: flex !important;
  align-items: center;
  gap: 0.5rem;
}

.toggle input {
  width: auto;
  margin-top: 0;
}

.zoom-controls {
  display: grid;
  grid-template-columns: 42px 1fr 42px;
  gap: 0.45rem;
  align-items: center;
}

.zoom-controls button {
  padding: 0.35rem 0;
  font-size: 1.1rem;
  line-height: 1;
}

.chart {
  min-height: 380px;
}

.events {
  display: grid;
  gap: 0.65rem;
}

.event {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.75rem;
}

.event .year {
  font-family: "Space Grotesk", sans-serif;
  color: var(--accent);
}

@media (max-width: 700px) {
  .shell {
    padding: 1rem 0.8rem 2rem;
  }
}
"""

    app_js = """(function () {
  const data = window.__SPDB_DATA__;
  if (!data) {
    return;
  }

  function parseYear(value) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    const text = String(value || "");
    const match = text.match(/(\\d{4})/);
    return match ? Number(match[1]) : NaN;
  }

  function asNumber(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : NaN;
  }

  function selectedValues(selectEl) {
    if (selectEl.dataset.touched !== "1") {
      return new Set();
    }
    return new Set(Array.from(selectEl.selectedOptions).map((opt) => opt.value));
  }

  function toOptionList(values) {
    return Array.from(new Set(values.filter(Boolean))).sort((a, b) => a.localeCompare(b));
  }

  function populateSelect(selectEl, values) {
    selectEl.innerHTML = values.map((value) => `<option value=\"${value}\">${value}</option>`).join("");
    selectEl.selectedIndex = -1;
    selectEl.dataset.touched = "0";
  }

  function clearMultiSelect(selectEl) {
    Array.from(selectEl.options).forEach((opt) => {
      opt.selected = false;
    });
  }

  const statsHost = document.getElementById("stats");
  const statRows = [
    ["Primitive Instances", data.summary.primitives],
    ["Families", data.summary.families],
    ["Influence Links", data.summary.influences],
    ["Primitive Types", data.summary.types],
  ];
  statsHost.innerHTML = statRows
    .map(
      ([label, value]) =>
        `<article class=\"stat\"><div class=\"label\">${label}</div><div class=\"value\">${value}</div></article>`,
    )
    .join("");

  const primitivesByFamily = new Map();
  for (const p of data.primitives || []) {
    const rec = {
      input: asNumber(p.fixed_input_bits),
      output: asNumber(p.fixed_output_bits),
    };
    if (!primitivesByFamily.has(p.family_id)) {
      primitivesByFamily.set(p.family_id, []);
    }
    primitivesByFamily.get(p.family_id).push(rec);
  }

  const familyRows = (data.families || [])
    .map((f) => {
      const sizes = primitivesByFamily.get(f.family_id) || [];
      const inputs = sizes.map((s) => s.input).filter(Number.isFinite);
      const outputs = sizes.map((s) => s.output).filter(Number.isFinite);

      return {
        ...f,
        yearNum: parseYear(f.year),
        inputMin: inputs.length ? Math.min(...inputs) : NaN,
        inputMax: inputs.length ? Math.max(...inputs) : NaN,
        outputMin: outputs.length ? Math.min(...outputs) : NaN,
        outputMax: outputs.length ? Math.max(...outputs) : NaN,
      };
    })
    .filter((f) => Number.isFinite(f.yearNum));

  const allFamilyTypes = toOptionList(familyRows.map((f) => f.primitive_type));
  const allFamilies = toOptionList(familyRows.map((f) => f.family_name));
  const allConstructions = toOptionList(familyRows.map((f) => f.constructions));

  const controls = {
    typeFilter: document.getElementById("typeFilter"),
    familyFilter: document.getElementById("familyFilter"),
    constructionFilter: document.getElementById("constructionFilter"),
    yearMin: document.getElementById("yearMin"),
    yearMax: document.getElementById("yearMax"),
    inputBitsMin: document.getElementById("inputBitsMin"),
    inputBitsMax: document.getElementById("inputBitsMax"),
    outputBitsMin: document.getElementById("outputBitsMin"),
    outputBitsMax: document.getElementById("outputBitsMax"),
    showLabels: document.getElementById("showLabels"),
    showEvents: document.getElementById("showEvents"),
    showEras: document.getElementById("showEras"),
    timelineZoom: document.getElementById("timelineZoom"),
    zoomOut: document.getElementById("zoomOut"),
    zoomIn: document.getElementById("zoomIn"),
    resetFilters: document.getElementById("resetFilters"),
  };

  populateSelect(controls.typeFilter, allFamilyTypes);
  populateSelect(controls.familyFilter, allFamilies);
  populateSelect(controls.constructionFilter, allConstructions);
  clearMultiSelect(controls.typeFilter);
  clearMultiSelect(controls.familyFilter);
  clearMultiSelect(controls.constructionFilter);

  const minYear = Math.min(...familyRows.map((f) => f.yearNum));
  const maxYear = Math.max(...familyRows.map((f) => f.yearNum));
  controls.yearMin.value = String(minYear);
  controls.yearMax.value = String(maxYear);

  const symbolPool = ["circle", "square", "diamond", "cross", "triangle-up", "triangle-down", "pentagon", "hexagon", "star"];
  const familySymbols = new Map();
  allFamilies.forEach((name, idx) => {
    familySymbols.set(name, symbolPool[idx % symbolPool.length]);
  });

  const labelPositions = [
    "top center",
    "bottom center",
    "middle left",
    "middle right",
  ];

  function getZoomFactor() {
    const pct = asNumber(controls.timelineZoom.value);
    if (!Number.isFinite(pct) || pct <= 0) {
      return 1;
    }
    return pct / 100;
  }

  function buildTimeline() {
    const selectedTypes = selectedValues(controls.typeFilter);
    const selectedFamilies = selectedValues(controls.familyFilter);
    const selectedConstructions = selectedValues(controls.constructionFilter);

    const yearMinFilter = asNumber(controls.yearMin.value);
    const yearMaxFilter = asNumber(controls.yearMax.value);
    const inMin = asNumber(controls.inputBitsMin.value);
    const inMax = asNumber(controls.inputBitsMax.value);
    const outMin = asNumber(controls.outputBitsMin.value);
    const outMax = asNumber(controls.outputBitsMax.value);

    const filtered = familyRows.filter((row) => {
      if (selectedTypes.size && !selectedTypes.has(row.primitive_type)) return false;
      if (selectedFamilies.size && !selectedFamilies.has(row.family_name)) return false;
      if (selectedConstructions.size && !selectedConstructions.has(row.constructions || "")) return false;
      if (Number.isFinite(yearMinFilter) && row.yearNum < yearMinFilter) return false;
      if (Number.isFinite(yearMaxFilter) && row.yearNum > yearMaxFilter) return false;

      if (Number.isFinite(inMin) && Number.isFinite(row.inputMax) && row.inputMax < inMin) return false;
      if (Number.isFinite(inMax) && Number.isFinite(row.inputMin) && row.inputMin > inMax) return false;
      if (Number.isFinite(outMin) && Number.isFinite(row.outputMax) && row.outputMax < outMin) return false;
      if (Number.isFinite(outMax) && Number.isFinite(row.outputMin) && row.outputMin > outMax) return false;
      return true;
    });

    const sorted = [...filtered].sort((a, b) => a.yearNum - b.yearNum || a.family_name.localeCompare(b.family_name));
    const yearCounter = new Map();
    const colorByType = new Map();
    const palette = ["#0f766e", "#0ea5e9", "#b45309", "#4f46e5", "#7f1d1d", "#166534", "#9333ea"];
    allFamilyTypes.forEach((type, idx) => colorByType.set(type, palette[idx % palette.length]));

    const x = [];
    const y = [];
    const symbols = [];
    const colors = [];
    const text = [];
    const textposition = [];
    const customdata = [];
    const zoom = getZoomFactor();
    const markerSize = Math.max(5, 12 * zoom);
    const textSize = Math.max(7, 11 * zoom);
    const eventTextSize = Math.max(7, 10 * zoom);

    for (const row of sorted) {
      const inYearCount = yearCounter.get(row.yearNum) || 0;
      yearCounter.set(row.yearNum, inYearCount + 1);
      const yPos = inYearCount * 0.55;

      x.push(row.yearNum);
      y.push(yPos);
      symbols.push(familySymbols.get(row.family_name) || "circle");
      colors.push(colorByType.get(row.primitive_type) || "#334155");
      text.push(row.family_name);
      textposition.push(labelPositions[inYearCount % labelPositions.length]);
      customdata.push([
        row.primitive_type,
        row.constructions || "-",
        row.instance_count || "0",
        Number.isFinite(row.inputMin) ? `${row.inputMin}-${row.inputMax}` : "-",
        Number.isFinite(row.outputMin) ? `${row.outputMin}-${row.outputMax}` : "-",
      ]);
    }

    const traces = [
      {
        type: "scatter",
        mode: controls.showLabels.checked ? "markers+text" : "markers",
        x,
        y,
        text,
        textposition,
        textfont: { size: textSize },
        marker: {
          size: markerSize,
          symbol: symbols,
          color: colors,
          line: { color: "#0f172a", width: 0.4 },
        },
        customdata,
        hovertemplate:
          "<b>%{text}</b><br>Year: %{x}<br>Family type: %{customdata[0]}<br>Construction: %{customdata[1]}<br>Instances: %{customdata[2]}<br>Input bits range: %{customdata[3]}<br>Output bits range: %{customdata[4]}<extra></extra>",
        showlegend: false,
      },
    ];

    const shapes = [];
    const annotations = [];

    if (controls.showEvents.checked) {
      const events = (data.timelineEvents || [])
        .map((e) => ({ ...e, yearNum: parseYear(e.date || e.year) }))
        .filter((e) => Number.isFinite(e.yearNum));

      events.forEach((event, idx) => {
        shapes.push({
          type: "line",
          xref: "x",
          yref: "paper",
          x0: event.yearNum,
          x1: event.yearNum,
          y0: 0,
          y1: 1,
          line: {
            color: "rgba(100,116,139,0.28)",
            width: 1,
          },
          layer: "below",
        });

        annotations.push({
          x: event.yearNum,
          y: 1.02 + (idx % 2) * 0.03,
          yref: "paper",
          xref: "x",
          text: event.short_name || event.title || "event",
          textangle: -45,
          showarrow: false,
          xanchor: "left",
          yanchor: "bottom",
          font: { size: eventTextSize, color: "#475569" },
        });
      });
    }

    if (controls.showEras.checked) {
      const eras = (data.timelineEras || [])
        .map((era) => ({
          ...era,
          start: parseYear(era.start_year),
          end: parseYear(era.end_year),
        }))
        .filter((era) => Number.isFinite(era.start) && Number.isFinite(era.end));

      eras.forEach((era, idx) => {
        const yBase = 1.10 + (idx % 4) * 0.065;
        const cap = 0.012;

        shapes.push({
          type: "line",
          xref: "x",
          yref: "paper",
          x0: era.start,
          x1: era.end,
          y0: yBase,
          y1: yBase,
          line: { color: "rgba(15,23,42,0.55)", width: 1.3 },
          layer: "above",
        });
        shapes.push({
          type: "line",
          xref: "x",
          yref: "paper",
          x0: era.start,
          x1: era.start,
          y0: yBase - cap,
          y1: yBase + cap,
          line: { color: "rgba(15,23,42,0.55)", width: 1.3 },
          layer: "above",
        });
        shapes.push({
          type: "line",
          xref: "x",
          yref: "paper",
          x0: era.end,
          x1: era.end,
          y0: yBase - cap,
          y1: yBase + cap,
          line: { color: "rgba(15,23,42,0.55)", width: 1.3 },
          layer: "above",
        });

        annotations.push({
          x: (era.start + era.end) / 2,
          y: yBase + 0.018,
          yref: "paper",
          xref: "x",
          text: era.name || "Era",
          showarrow: false,
          font: { size: eventTextSize, color: "#1f2937" },
        });
      });
    }

    const rangeMin = Number.isFinite(yearMinFilter) ? yearMinFilter : minYear;
    const rangeMax = Number.isFinite(yearMaxFilter) ? yearMaxFilter : maxYear;
    const center = (rangeMin + rangeMax) / 2;
    const span = Math.max(1, (rangeMax - rangeMin) / zoom);
    const xMin = center - span / 2;
    const xMax = center + span / 2;

    Plotly.newPlot(
      "timelineChart",
      traces,
      {
        margin: { l: 50, r: 20, t: 220, b: 55 },
        xaxis: { title: "Year", zeroline: false, range: [xMin, xMax] },
        yaxis: {
          title: "",
          showticklabels: false,
          gridcolor: "rgba(148,163,184,0.18)",
          zeroline: false,
        },
        shapes,
        annotations,
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
      },
      { responsive: true },
    );
  }

  [controls.typeFilter, controls.familyFilter, controls.constructionFilter].forEach((selectEl) => {
    selectEl.addEventListener("change", () => {
      selectEl.dataset.touched = "1";
    });
  });

  [
    controls.typeFilter,
    controls.familyFilter,
    controls.constructionFilter,
    controls.yearMin,
    controls.yearMax,
    controls.inputBitsMin,
    controls.inputBitsMax,
    controls.outputBitsMin,
    controls.outputBitsMax,
    controls.showLabels,
    controls.showEvents,
    controls.showEras,
    controls.timelineZoom,
  ].forEach((el) => {
    el.addEventListener("change", buildTimeline);
    el.addEventListener("input", buildTimeline);
  });

  controls.zoomOut.addEventListener("click", () => {
    const current = asNumber(controls.timelineZoom.value) || 100;
    controls.timelineZoom.value = String(Math.max(60, current - 10));
    buildTimeline();
  });

  controls.zoomIn.addEventListener("click", () => {
    const current = asNumber(controls.timelineZoom.value) || 100;
    controls.timelineZoom.value = String(Math.min(180, current + 10));
    buildTimeline();
  });

  controls.resetFilters.addEventListener("click", () => {
    [controls.typeFilter, controls.familyFilter, controls.constructionFilter].forEach((selectEl) => {
      clearMultiSelect(selectEl);
      selectEl.selectedIndex = -1;
      selectEl.dataset.touched = "0";
    });
    controls.yearMin.value = String(minYear);
    controls.yearMax.value = String(maxYear);
    controls.inputBitsMin.value = "";
    controls.inputBitsMax.value = "";
    controls.outputBitsMin.value = "";
    controls.outputBitsMax.value = "";
    controls.showLabels.checked = true;
    controls.showEvents.checked = true;
    controls.showEras.checked = true;
    controls.timelineZoom.value = "100";
    buildTimeline();
  });

  buildTimeline();

  const nodes = new Set();
  for (const edge of data.influences) {
    if (edge.source_name) nodes.add(edge.source_name);
    if (edge.target_name) nodes.add(edge.target_name);
  }
  const orderedNodes = Array.from(nodes);
  const nodeIndex = new Map(orderedNodes.map((name, idx) => [name, idx]));

  const source = [];
  const target = [];
  const value = [];
  const label = [];
  for (const edge of data.influences) {
    const s = nodeIndex.get(edge.source_name);
    const t = nodeIndex.get(edge.target_name);
    if (s === undefined || t === undefined) continue;
    source.push(s);
    target.push(t);
    value.push(1);
    label.push(edge.relation || "influence");
  }

  Plotly.newPlot(
    "influenceChart",
    [
      {
        type: "sankey",
        arrangement: "snap",
        node: { label: orderedNodes, pad: 15, thickness: 16 },
        link: { source, target, value, label },
      },
    ],
    {
      margin: { l: 10, r: 10, t: 5, b: 10 },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
    },
    { responsive: true },
  );

  const eventsHost = document.getElementById("events");
  const sortedEvents = [...(data.timelineEvents || [])].sort(
    (a, b) => parseYear(a.date || a.year) - parseYear(b.date || b.year),
  );
  eventsHost.innerHTML = sortedEvents
    .map((event) => {
      const title = event.title || event.label || "Untitled event";
      const year = event.date || event.year || "n/a";
      const note = event.note || event.description || "";
      return `<article class=\"event\"><div class=\"year\">${year}</div><strong>${title}</strong><div>${note}</div></article>`;
    })
    .join("");
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
