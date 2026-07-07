(function () {
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
    return /^-?\d+(\.\d+)?$/.test(value.trim());
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
      .replace(/"/g, "&quot;");
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
    return /^https?:\/\//i.test(String(text || "").trim());
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
          `<th data-col="${col}">`,
          `<div class="head-cell">`,
          `<button type="button" data-sort="${col}"><span class="codeish">${col}</span> <span>${marker}</span></button>`,
          `<span class="resizer" data-resize="${col}"></span>`,
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
              return `<td title="${escaped}"><a href="${escaped}" target="_blank" rel="noopener noreferrer">${escaped}</a></td>`;
            }
            return `<td title="${escaped}">${escaped}</td>`;
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
    select.innerHTML = names.map((name) => `<option value="${name}">${name} (${data.tables[name].rowCount})</option>`).join("");

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
        return `<label><input type="checkbox" data-value="${esc}" /><span>${esc}</span></label>`;
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
            return `<label class="column-item"><input type="checkbox" data-col="${item.key}" data-group="${group.group}" ${checked} /><span class="codeish">${item.sub}</span></label>`;
          }).join("");
          return `<section class="column-group"><label class="column-item column-group-title"><input type="checkbox" data-group-toggle="${group.group}" /><span>${group.group}</span></label>${items}</section>`;
        })
        .join("");
      ui.columnPicker.innerHTML = html;

      Array.from(ui.columnPicker.querySelectorAll("input[data-group-toggle]")).forEach((toggle) => {
        const group = toggle.getAttribute("data-group-toggle") || "";
        const children = Array.from(ui.columnPicker.querySelectorAll(`input[data-group="${group}"]`));
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
      if (typeValues.size) clauses.push(`"primitive.type_name" IN (${Array.from(typeValues).map((v) => `'${v.replace(/'/g, "''")}'`).join(", ")})`);
      const refKindValues = selectedChecklistValues(ui.referenceKind);
      if (refKindValues.size) clauses.push(`"reference.kind" IN (${Array.from(refKindValues).map((v) => `'${v.replace(/'/g, "''")}'`).join(", ")})`);

      const ryMin = parseOptionalNumber(ui.referenceYearMin.value);
      if (Number.isFinite(ryMin)) clauses.push(`"reference.year" >= ${ryMin}`);
      const ryMax = parseOptionalNumber(ui.referenceYearMax.value);
      if (Number.isFinite(ryMax)) clauses.push(`"reference.year" <= ${ryMax}`);

      const familyName = (ui.familyName.value || "").trim();
      if (familyName) clauses.push(`"family.name" LIKE '%${familyName.replace(/'/g, "''")}%'`);
      const referenceTitle = (ui.referenceTitle.value || "").trim();
      if (referenceTitle) clauses.push(`"reference.title" LIKE '%${referenceTitle.replace(/'/g, "''")}%'`);
      if (ui.hasReferenceLink.checked) clauses.push(`"reference.url" IS NOT NULL AND TRIM("reference.url") <> ''`);

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
      const selectCols = visible.length ? visible.map((c) => `"${c}"`).join(", ") : "*";
      const whereSql = whereClauses.length ? `\nWHERE ${whereClauses.join("\n  AND ")}` : "";
      ui.sqlPreview.textContent = `SELECT ${selectCols}\nFROM (${builder.baseSql})${whereSql};`;
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
    const colMinus = document.getElementById("vizColMinus");
    const colPlus = document.getElementById("vizColPlus");
    const colReset = document.getElementById("vizColReset");
    const colSpacingValue = document.getElementById("vizColSpacingValue");
    const familySearch = document.getElementById("vizFamilySearch");
    const vizFrame = document.getElementById("vizFrame");
    const collapseGroups = document.getElementById("vizCollapseGroups");
    const collapseCount = document.getElementById("vizCollapseCount");
    const yearStart = document.getElementById("vizYearStart");
    const yearEnd = document.getElementById("vizYearEnd");
    const yearReset = document.getElementById("vizYearReset");
    const yearRangeValue = document.getElementById("vizYearRangeValue");
    const relationInfoBox = document.getElementById("vizRelationInfo");
    if (!plotSvg || !xAxisSvg || !yAxisSvg || !plotScroll || !xAxisTrack || !yAxisTrack || !cornerPane || !vizFrame || !groupBy || !showArrows || !hideDots || !nameModeOff || !nameModeClip || !nameModeWrap || !nameModeFull || !colorByProcess || !processLegend || !groupFilters || !filterAll || !filterNone || !fontMinus || !fontPlus || !fontReset || !fontValue || !zoomOut || !zoomIn || !zoomReset || !zoomFit || !zoomValue || !colMinus || !colPlus || !colReset || !colSpacingValue || !familySearch || !collapseGroups || !collapseCount || !yearStart || !yearEnd || !yearReset || !yearRangeValue || !relationInfoBox) return;

    const BASE_FONT = 12;
    const BASE_ZOOM = 1;
    const BASE_COL_BONUS = 0;
    const COL_STEP = 8;
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
    let colSpacingBonus = BASE_COL_BONUS;
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
    const familyStandards = (tables.family_standards && tables.family_standards.rows) || [];
    const primitiveStandards = (tables.primitive_standards && tables.primitive_standards.rows) || [];

    const typeNameById = new Map(primitiveTypes.map((row) => [String(row.id), String(row.name)]));
    const constructionNameById = new Map(constructions.map((row) => [String(row.id), String(row.name)]));
    const familyById = new Map(families.map((row) => [String(row.id), row]));
    const primitiveFamilyById = new Map(primitives.map((row) => [String(row.id), String(row.family_id || "")]));
    const standardFamilyIds = new Set(familyStandards.map((row) => String(row.family_id)));
    primitiveStandards.forEach((row) => {
      const familyId = primitiveFamilyById.get(String(row.primitive_id));
      if (familyId) standardFamilyIds.add(familyId);
    });

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
      const m = name.match(/\(([A-Z][A-Z0-9]*)/);
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
      const _earlyBW = Math.max(840, (_earlySpan + 1) * (32 + colSpacingBonus + fontPx * 0.8));
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
      const _minColW = nameMode === "full" ? POINT_RADIUS + longestNamePx + 16 : 32 + colSpacingBonus + fontPx * 0.8;
      const basePlotWidth = Math.max(840, (span + 1) * Math.max(32 + colSpacingBonus + fontPx * 0.8, _minColW));
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

      const anchorsByFamily = new Map();
      pointPositions.forEach((point) => {
        if (!anchorsByFamily.has(point.familyId)) anchorsByFamily.set(point.familyId, []);
        anchorsByFamily.get(point.familyId).push(point);
      });

      function relationEndpointPairs(sourceId, targetId) {
        const sources = anchorsByFamily.get(sourceId) || [];
        const targets = anchorsByFamily.get(targetId) || [];
        if (!sources.length || !targets.length) return [];

        // A family can appear in several lanes. Connect every visible target dot
        // from an actual source dot, preferring the matching lane when possible.
        return targets.map((target) => {
          let best = null;
          sources.forEach((source) => {
            const sameGroup = source.group === target.group;
            const dx = target.x - source.x;
            const dy = target.y - source.y;
            const candidate = { source, target, sameGroup, distance: dx * dx + dy * dy };
            if (!best
                || (candidate.sameGroup && !best.sameGroup)
                || (candidate.sameGroup === best.sameGroup && candidate.distance < best.distance)) {
              best = candidate;
            }
          });
          return best;
        });
      }

      const hoverLines = [];
      if (showArrows.checked) {
        influences.forEach((edge) => {
          const sourceId = String(edge.source_family_id || "");
          const targetId = String(edge.target_family_id || "");
          const endpointPairs = relationEndpointPairs(sourceId, targetId);
          if (!endpointPairs.length) return;

          const rel = relationInfo(edge);
          const width = 1.15 + (rel.count - 1) * 1.05;
          const hoverText = `${edge.source_family_id} -> ${edge.target_family_id} | Relations: ${rel.label} | ${normalizeValue(edge.note)}`;

          endpointPairs.forEach((endpoints) => {
            const sx = endpoints.source.x;
            const sy = endpoints.source.y;
            const tx = endpoints.target.x;
            const ty = endpoints.target.y;

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
        });
      }

      const useProcessColor = colorByProcess.checked;

      pointPositions.forEach((point) => {
        const famData = familyById.get(point.familyId);
        const famTypes = Array.from(familyToTypes.get(point.familyId) || []).sort((a, b) => a.localeCompare(b)).join(", ") || "—";
        const famConstructions = Array.from(familyToConstructions.get(point.familyId) || []).sort((a, b) => a.localeCompare(b)).join(", ") || "Not classified";
        const famNotes = famData && famData.notes ? String(famData.notes).trim() : "";
        const procName = processNameForFamily(point.familyId);
        const isStandard = standardFamilyIds.has(point.familyId);
        const tipParts = [`${point.name} (${point.year})`, `Type: ${famTypes}`, `Construction: ${famConstructions}`, `Group: ${point.group}`];
        if (isStandard) tipParts.push("Standard: yes (official specification)");
        if (procName) tipParts.push(`Process: ${procName}`);
        if (famNotes) tipParts.push("\n" + famNotes);
        const richTip = tipParts.join("\n");
        const dotColor = isStandard ? "#000000" : (useProcessColor ? processColorForFamily(point.familyId) : null);

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
            ? `font-size:${fontPx}px;font-family:"IBM Plex Mono",monospace;fill:${dotColor};font-weight:${isStandard ? 700 : 400}`
            : `font-size:${fontPx}px;font-family:"IBM Plex Mono",monospace;font-weight:${isStandard ? 700 : 400}`;
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

      // Standards and process legend
      if (standardFamilyIds.size || (useProcessColor && processList.length)) {
        processLegend.hidden = false;
        clearNode(processLegend);
        if (standardFamilyIds.size) {
          const standardItem = document.createElement("span");
          standardItem.className = "viz-process-legend-item";
          const standardDot = document.createElement("span");
          standardDot.className = "viz-process-legend-dot";
          standardDot.style.background = "#000000";
          const standardLabel = document.createElement("span");
          standardLabel.textContent = "Standard (official specification)";
          standardLabel.style.fontWeight = "700";
          standardLabel.style.color = "#000000";
          standardItem.appendChild(standardDot);
          standardItem.appendChild(standardLabel);
          processLegend.appendChild(standardItem);
        }
        if (useProcessColor) {
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
        }
      } else {
        processLegend.hidden = true;
      }

      fontValue.textContent = `${fontPx}px`;
      colSpacingValue.textContent = `${colSpacingBonus >= 0 ? "+" : ""}${colSpacingBonus}px`;
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
    colMinus.addEventListener("click", () => {
      colSpacingBonus = Math.max(-16, colSpacingBonus - COL_STEP);
      render();
    });
    colPlus.addEventListener("click", () => {
      colSpacingBonus = Math.min(200, colSpacingBonus + COL_STEP);
      render();
    });
    colReset.addEventListener("click", () => {
      colSpacingBonus = BASE_COL_BONUS;
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
    const vizDownloadPng = document.getElementById("vizDownloadPng");
    if (vizDownloadPng) vizDownloadPng.addEventListener("click", () => {
      const yW = Number(yAxisSvg.getAttribute("width") || 0);
      const pW = Number(plotSvg.getAttribute("width") || 0);
      const pH = Number(plotSvg.getAttribute("height") || 0);
      const xH = Number(xAxisSvg.getAttribute("height") || 0);
      const scale = 2;
      const canvas = document.createElement("canvas");
      canvas.width = (yW + pW) * scale;
      canvas.height = (pH + xH) * scale;
      const ctx = canvas.getContext("2d");
      ctx.scale(scale, scale);
      ctx.fillStyle = "#fff";
      ctx.fillRect(0, 0, yW + pW, pH + xH);
      function drawEl(el, dx, dy) {
        return new Promise((ok) => {
          const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(el)], { type: "image/svg+xml" }));
          const img = new Image();
          img.onload = () => { ctx.drawImage(img, dx, dy); URL.revokeObjectURL(url); ok(); };
          img.onerror = () => { URL.revokeObjectURL(url); ok(); };
          img.src = url;
        });
      }
      drawEl(yAxisSvg, 0, 0).then(() => drawEl(plotSvg, yW, 0)).then(() => drawEl(xAxisSvg, yW, pH)).then(() => {
        const a = document.createElement("a"); a.download = "timelines.png"; a.href = canvas.toDataURL("image/png"); a.click();
      });
    });
    render();
  }

  function setupGenealogy() {
    const genPlot = document.getElementById("genPlot");
    const genPlotScroll = document.getElementById("genPlotScroll");
    const genFrame = document.getElementById("genFrame");
    const genColorBy = document.getElementById("genColorBy");
    const genConnectedOnly = document.getElementById("genConnectedOnly");
    const genStandardsOnly = document.getElementById("genStandardsOnly");
    const genFamilySearch = document.getElementById("genFamilySearch");
    const genYearStart = document.getElementById("genYearStart");
    const genYearEnd = document.getElementById("genYearEnd");
    const genYearReset = document.getElementById("genYearReset");
    const genYearRangeValue = document.getElementById("genYearRangeValue");
    const genPrimitiveFilters = document.getElementById("genPrimitiveFilters");
    const genPrimitiveAll = document.getElementById("genPrimitiveAll");
    const genPrimitiveNone = document.getElementById("genPrimitiveNone");
    const genConstructionFilters = document.getElementById("genConstructionFilters");
    const genConstructionAll = document.getElementById("genConstructionAll");
    const genConstructionNone = document.getElementById("genConstructionNone");
    const genProcessFilters = document.getElementById("genProcessFilters");
    const genProcessAll = document.getElementById("genProcessAll");
    const genProcessNone = document.getElementById("genProcessNone");
    const genEdgeInfo = document.getElementById("genEdgeInfo");
    const genLegend = document.getElementById("genLegend");
    const genFontMinus = document.getElementById("genFontMinus");
    const genFontPlus = document.getElementById("genFontPlus");
    const genFontReset = document.getElementById("genFontReset");
    const genFontValue = document.getElementById("genFontValue");
    const genLayoutLayered = document.getElementById("genLayoutLayered");
    const genLayoutRadial = document.getElementById("genLayoutRadial");
    const genRadiusMinus = document.getElementById("genRadiusMinus");
    const genRadiusPlus = document.getElementById("genRadiusPlus");
    const genRadiusReset = document.getElementById("genRadiusReset");
    const genRadiusValue = document.getElementById("genRadiusValue");
    const genByGeneration = document.getElementById("genByGeneration");
    const genShowBullets = document.getElementById("genShowBullets");
    const genCollapseEdges = document.getElementById("genCollapseEdges");
    const genNameClip = document.getElementById("genNameClip");
    const genNameFull = document.getElementById("genNameFull");
    if (!genPlot || !genPlotScroll || !genFrame) return;

    const GEN_BASE_FONT = 12;
    let genFontPx = GEN_BASE_FONT;
    let genLayoutMode = "radial";
    let genNumChars = 8;
    let genNameMode = "clip";

    // ── Data ─────────────────────────────────────────────────────────
    const tables = data.tables || {};
    const families = (tables.families && tables.families.rows) || [];
    const primitives = (tables.primitives && tables.primitives.rows) || [];
    const primitiveTypes = (tables.primitive_types && tables.primitive_types.rows) || [];
    const familyConstructions = (tables.family_constructions && tables.family_constructions.rows) || [];
    const constructions = (tables.constructions && tables.constructions.rows) || [];
    const influences = (tables.family_influences && tables.family_influences.rows) || [];
    const familyStandards = (tables.family_standards && tables.family_standards.rows) || [];
    const primitiveStandards = (tables.primitive_standards && tables.primitive_standards.rows) || [];

    const genProcessData = data.processData || {};
    const genProcessList = genProcessData.processes || [];
    const genFamilyProcessMap = genProcessData.familyProcessMap || {};

    const typeNameById = new Map(primitiveTypes.map((r) => [String(r.id), String(r.name)]));
    const constrNameById = new Map(constructions.map((r) => [String(r.id), String(r.name)]));
    const genFamById = new Map(families.map((r) => [String(r.id), r]));
    const primFamById = new Map(primitives.map((r) => [String(r.id), String(r.family_id || "")]));

    const stdFamIds = new Set(familyStandards.map((r) => String(r.family_id)));
    primitiveStandards.forEach((r) => { const f = primFamById.get(String(r.primitive_id)); if (f) stdFamIds.add(f); });

    const famToTypes = new Map();
    primitives.forEach((r) => {
      const fid = String(r.family_id || ""); if (!fid) return;
      if (!famToTypes.has(fid)) famToTypes.set(fid, new Set());
      const tn = typeNameById.get(String(r.primitive_type || "")) || ""; if (tn) famToTypes.get(fid).add(tn);
    });
    const famToConstrs = new Map();
    familyConstructions.forEach((r) => {
      const fid = String(r.family_id || ""); if (!fid) return;
      if (!famToConstrs.has(fid)) famToConstrs.set(fid, new Set());
      const cn = constrNameById.get(String(r.construction_id || "")) || ""; if (cn) famToConstrs.get(fid).add(cn);
    });

    const PROC_COLORS = ["#1a73c9","#d4501a","#1e9c5e","#9b42b8","#c9961a","#c91a4e","#1ab8c9","#5e6e1a","#7a1ac9","#1a4ec9","#a85a1a","#1a9b9b"];
    const TYPE_COLORS = ["#1e6fa8","#b85a28","#1a8e5c","#7b30a0","#a07818","#98183c","#169aa8","#4c6218","#601aa0","#1a40a0","#8a4818","#1a8080"];
    const genProcColorMap = new Map();
    genProcessList.forEach((p, i) => genProcColorMap.set(String(p.id), PROC_COLORS[i % PROC_COLORS.length]));
    genProcColorMap.set("__none__", "#7a8c8f");
    const typeColorMap = new Map();
    const allTypes = Array.from(new Set(Array.from(famToTypes.values()).flatMap((s) => Array.from(s)))).sort();
    allTypes.forEach((t, i) => typeColorMap.set(t, TYPE_COLORS[i % TYPE_COLORS.length]));
    const constrColorMap = new Map();
    const allConstrs = Array.from(new Set(Array.from(famToConstrs.values()).flatMap((s) => Array.from(s)))).sort();
    allConstrs.forEach((c, i) => constrColorMap.set(c, TYPE_COLORS[i % TYPE_COLORS.length]));
    const relationTypes = Array.from(new Set(influences.flatMap((e) => {
      const rs = parseJsonArray(e.relations_json);
      const fb = String(e.relation || "").trim();
      return rs.length ? rs : (fb ? [fb] : ["related"]);
    }))).sort();
    const relationColorMap = new Map(relationTypes.map((r, i) =>
      [r, `hsl(${Math.round((i * 137.508) % 360)} 68% 38%)`]));

    function edgeRelations(edge) {
      const rs = parseJsonArray(edge.relations_json);
      const fb = String(edge.relation || "").trim();
      return rs.length ? rs : (fb ? [fb] : ["related"]);
    }

    // ── Filter state ──────────────────────────────────────────────────
    const primSel = new Map();
    const constrSel = new Map();
    const procSel = new Map();
    let genYrBounds = null;

    function initFilters() {
      allTypes.forEach((t) => { if (!primSel.has(t)) primSel.set(t, true); });
      allConstrs.forEach((c) => { if (!constrSel.has(c)) constrSel.set(c, true); });
      genProcessList.forEach((p) => { if (!procSel.has(String(p.id))) procSel.set(String(p.id), true); });
      procSel.set("__none__", true);

      buildChk(genPrimitiveFilters, primSel, null, genPrimitiveAll, genPrimitiveNone);
      buildChk(genConstructionFilters, constrSel, null, genConstructionAll, genConstructionNone);
      buildChk(genProcessFilters, procSel,
        [...genProcessList.map((p) => ({ key: String(p.id), label: String(p.name) })), { key: "__none__", label: "No process" }],
        genProcessAll, genProcessNone);

      const yrs = families.map((f) => Number(f.year)).filter(isFinite).sort((a, b) => a - b);
      if (yrs.length) {
        genYrBounds = { min: yrs[0], max: yrs[yrs.length - 1] };
        [genYearStart, genYearEnd].forEach((el) => { el.min = String(genYrBounds.min); el.max = String(genYrBounds.max); el.step = "1"; });
        genYearStart.value = String(genYrBounds.min); genYearEnd.value = String(genYrBounds.max);
        updateYrLbl();
      }
    }

    function buildChk(container, selMap, keyed, btnAll, btnNone) {
      if (!container) return;
      const entries = keyed || Array.from(selMap.keys()).map((k) => ({ key: k, label: k }));
      container.innerHTML = entries.map(({ key, label }) => {
        const esc = escapeHtml(label);
        return `<label><input type="checkbox" data-value="${escapeHtml(key)}"${selMap.get(key) !== false ? " checked" : ""}/><span>${esc}</span></label>`;
      }).join("");
      container.addEventListener("change", (ev) => {
        const t = ev.target;
        if (t && t.type === "checkbox" && t.dataset.value !== undefined) { selMap.set(t.dataset.value, t.checked); render(); }
      });
      if (btnAll) btnAll.addEventListener("click", () => {
        entries.forEach(({ key }) => selMap.set(key, true));
        Array.from(container.querySelectorAll("input[type=checkbox]")).forEach((c) => { c.checked = true; }); render();
      });
      if (btnNone) btnNone.addEventListener("click", () => {
        entries.forEach(({ key }) => selMap.set(key, false));
        Array.from(container.querySelectorAll("input[type=checkbox]")).forEach((c) => { c.checked = false; }); render();
      });
    }

    function updateYrLbl() {
      if (!genYrBounds || !genYearRangeValue) return;
      const s = Number(genYearStart.value); const e = Number(genYearEnd.value);
      genYearRangeValue.textContent = s === e ? String(s) : `${s} - ${e}`;
    }

    function getYrRange() {
      if (!genYrBounds) return null;
      let s = Number(genYearStart.value || genYrBounds.min); let e = Number(genYearEnd.value || genYrBounds.max);
      if (s > e) { const tmp = s; s = e; e = tmp; } return { start: s, end: e };
    }

    function nodeColor(fid) {
      const mode = genColorBy.value;
      if (mode === "process") { const pid = genFamilyProcessMap[fid]; return pid ? (genProcColorMap.get(pid) || "#7a8c8f") : "#7a8c8f"; }
      if (mode === "construction") { const cc = Array.from(famToConstrs.get(fid) || []).sort(); return cc.length ? (constrColorMap.get(cc[0]) || "#5a7a8a") : "#7a8c8f"; }
      const tt = Array.from(famToTypes.get(fid) || []).sort(); return tt.length ? (typeColorMap.get(tt[0]) || "#5a7a8a") : "#7a8c8f";
    }

    function isVis(fid, ignoreSearch = false) {
      const fam = genFamById.get(fid); if (!fam) return false;
      const yr = getYrRange(); const year = Number(fam.year);
      if (yr && (year < yr.start || year > yr.end)) return false;
      const needle = ignoreSearch ? "" : genFamilySearch.value.trim().toLowerCase();
      if (needle && !String(fam.name || fid).toLowerCase().includes(needle)) return false;
      if (genStandardsOnly.checked && !stdFamIds.has(fid)) return false;
      const anyType = Array.from(primSel.values()).some((v) => v);
      if (anyType) { const ft = famToTypes.get(fid) || new Set(); if (!ft.size ? primSel.get("") === false : !Array.from(ft).some((t) => primSel.get(t) !== false)) return false; }
      const anyCon = Array.from(constrSel.values()).some((v) => v);
      if (anyCon) { const fc = famToConstrs.get(fid) || new Set(); if (!fc.size ? constrSel.get("") === false : !Array.from(fc).some((c) => constrSel.get(c) !== false)) return false; }
      const anyProc = Array.from(procSel.values()).some((v) => v);
      if (anyProc) { const pid = genFamilyProcessMap[fid] || "__none__"; if (procSel.get(pid) === false) return false; }
      return true;
    }

    // ── Layout constants (some are dynamic on genFontPx) ─────────────
    const COL_GAP = 10;
    const TOP_PAD = 20;
    const SIDE_PAD = 20;
    const NODE_PAD_X = 7;
    const BASE_EDGE_INFO = "Hover an influence arrow to see relation details.";

    function nodeH() { return Math.round(genFontPx * 1.85); }
    function rowGap() { return Math.round(genFontPx * 4.5); }
    function isoW() { return Math.round(genFontPx * 7.5); }
    function nw(name) { const n = genNameMode === "full" ? String(name).length : Math.min(String(name).length, genNumChars); const raw = Math.ceil(n * genFontPx * 0.58) + NODE_PAD_X * 2; return Math.max(Math.round(genFontPx * 4.5), genNameMode === "full" ? raw : Math.min(Math.round(genFontPx * 12.5), raw)); }

    const SVG_NS = "http://www.w3.org/2000/svg";
    function svgEl(tag, attrs) {
      const el = document.createElementNS(SVG_NS, tag);
      Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
      return el;
    }

    // ── Sugiyama DAG layout helpers ───────────────────────────────────
    function assignLayers(nodeSet, inE) {
      const L = new Map(); const vis = new Set();
      function d(id) {
        if (L.has(id)) return L.get(id);
        if (vis.has(id)) { L.set(id, 0); return 0; }
        vis.add(id);
        const preds = (inE.get(id) || []).filter((p) => nodeSet.has(p));
        const l = preds.length ? Math.max(...preds.map(d)) + 1 : 0;
        L.set(id, l); vis.delete(id); return l;
      }
      nodeSet.forEach(d); return L;
    }

    // Exact crossing count between every adjacent pair of layers (small graph, so the
    // naive O(k^2) pairwise check per boundary is cheap and lets us actually verify
    // whether a re-ordering helped, instead of trusting the barycenter heuristic blindly.
    function countCrossings(layers, inE) {
      let total = 0;
      for (let li = 1; li < layers.length; li++) {
        const posPrev = new Map(layers[li - 1].map((id, i) => [id, i]));
        const edges = [];
        layers[li].forEach((id, ci) => {
          (inE.get(id) || []).forEach((p) => { const pi = posPrev.get(p); if (pi !== undefined) edges.push([pi, ci]); });
        });
        for (let a = 0; a < edges.length; a++) {
          for (let b = a + 1; b < edges.length; b++) {
            if ((edges[a][0] - edges[b][0]) * (edges[a][1] - edges[b][1]) < 0) total++;
          }
        }
      }
      return total;
    }

    function minimiseCrossings(layers, inE, outE) {
      const cloneLayers = () => layers.map((lg) => lg.slice());
      let best = cloneLayers();
      let bestCount = countCrossings(layers, inE);

      // One barycenter pass: a single position map is seeded from the current order and
      // threaded through both the forward (parent-driven) and backward (child-driven)
      // sub-sweeps, exactly as a classic Sugiyama median/barycenter pass does.
      function pass() {
        const pm = new Map();
        layers.forEach((lg) => { const n = lg.length; lg.forEach((id, i) => pm.set(id, n <= 1 ? 0.5 : i / (n - 1))); });
        for (let li = 1; li < layers.length; li++) {
          layers[li].sort((a, b) => {
            const pA = inE.get(a) || []; const pB = inE.get(b) || [];
            const bA = pA.length ? pA.reduce((s, p) => s + (pm.has(p) ? pm.get(p) : 0.5), 0) / pA.length : (pm.get(a) ?? 0.5);
            const bB = pB.length ? pB.reduce((s, p) => s + (pm.has(p) ? pm.get(p) : 0.5), 0) / pB.length : (pm.get(b) ?? 0.5);
            return bA - bB;
          });
          const n = layers[li].length; layers[li].forEach((id, i) => pm.set(id, n <= 1 ? 0.5 : i / (n - 1)));
        }
        for (let li = layers.length - 2; li >= 0; li--) {
          layers[li].sort((a, b) => {
            const sA = outE.get(a) || []; const sB = outE.get(b) || [];
            const bA = sA.length ? sA.reduce((s, p) => s + (pm.has(p) ? pm.get(p) : 0.5), 0) / sA.length : (pm.get(a) ?? 0.5);
            const bB = sB.length ? sB.reduce((s, p) => s + (pm.has(p) ? pm.get(p) : 0.5), 0) / sB.length : (pm.get(b) ?? 0.5);
            return bA - bB;
          });
          const n = layers[li].length; layers[li].forEach((id, i) => pm.set(id, n <= 1 ? 0.5 : i / (n - 1)));
        }
      }

      function crossingsAround(li) {
        let c = 0;
        if (li > 0) c += countCrossings([layers[li - 1], layers[li]], inE);
        if (li < layers.length - 1) c += countCrossings([layers[li], layers[li + 1]], inE);
        return c;
      }

      // Adjacent-swap local search ("transpose"): the barycenter sweeps above can settle
      // into a local optimum they can't escape on their own, so after each pass try
      // swapping neighbouring nodes within a layer and keep the swap only if it actually
      // lowers the crossing count around that layer.
      function transpose() {
        let improved = true; let guard = 0;
        while (improved && guard++ < 4) {
          improved = false;
          for (let li = 0; li < layers.length; li++) {
            const lg = layers[li];
            for (let i = 0; i < lg.length - 1; i++) {
              const before = crossingsAround(li);
              [lg[i], lg[i + 1]] = [lg[i + 1], lg[i]];
              const after = crossingsAround(li);
              if (after < before) improved = true;
              else [lg[i], lg[i + 1]] = [lg[i + 1], lg[i]];
            }
          }
        }
      }

      function checkpoint() {
        const count = countCrossings(layers, inE);
        if (count < bestCount) { bestCount = count; best = cloneLayers(); }
        return bestCount === 0;
      }

      // Phase 1: plain barycenter passes, checkpointing the best ordering seen. (The old
      // implementation just ran 8 of these and kept whatever the last one produced, even
      // if an earlier pass had fewer crossings — checkpointing alone is a free improvement.)
      for (let i = 0; i < 8; i++) {
        pass();
        if (checkpoint()) break;
      }

      // Phase 2: restart from the best barycenter ordering and refine with the transpose
      // local search. Every accepted swap strictly lowers the crossing count around its
      // layer (and leaves every other layer's crossings untouched), so this phase can only
      // match or improve on phase 1 — it never regresses relative to sweeping alone.
      if (bestCount > 0) {
        layers.forEach((lg, li) => { lg.length = 0; lg.push(...best[li]); });
        transpose();
        checkpoint();
      }

      layers.forEach((lg, li) => { lg.length = 0; lg.push(...best[li]); });
    }

    // Least-squares fit of a non-decreasing sequence to `y` (pool-adjacent-violators).
    // Used to place a row of nodes as close as possible to their desired x position
    // while keeping the left-to-right order fixed and never violating a minimum gap.
    function isotonicNonDecreasing(y) {
      const pools = [];
      for (let i = 0; i < y.length; i++) {
        let avg = y[i]; let w = 1; let start = i;
        while (pools.length && pools[pools.length - 1].avg > avg + 1e-9) {
          const p = pools.pop();
          avg = (avg * w + p.avg * p.w) / (w + p.w);
          w += p.w; start = p.start;
        }
        pools.push({ avg, w, start, end: i });
      }
      const out = new Array(y.length);
      pools.forEach((p) => { for (let i = p.start; i <= p.end; i++) out[i] = p.avg; });
      return out;
    }

    function resolveRow(ids, desired, widthOf, posX) {
      const n = ids.length; if (!n) return;
      const half = ids.map((id) => widthOf(id) / 2);
      const cum = new Array(n).fill(0);
      for (let i = 1; i < n; i++) cum[i] = cum[i - 1] + half[i - 1] + COL_GAP + half[i];
      const z = desired.map((d, i) => d - cum[i]);
      const w = isotonicNonDecreasing(z);
      ids.forEach((id, i) => posX.set(id, w[i] + cum[i]));
    }

    // Iterative median alignment: repeatedly pulls each node towards the median x of its
    // already-placed neighbours (parents on the down sweep, children on the up sweep), then
    // re-solves each row to keep spacing valid. This is what actually straightens chains of
    // influence edges — crossing-minimisation alone fixes left-to-right order but leaves
    // nodes packed arbitrarily, which is what made the old layout look zig-zaggy.
    function assignXCoordinates(layerGroups, inE, outE, widthOf) {
      const posX = new Map();
      layerGroups.forEach((lg) => {
        let x = 0;
        lg.forEach((id, i) => {
          const w = widthOf(id);
          x += i === 0 ? w / 2 : widthOf(lg[i - 1]) / 2 + COL_GAP + w / 2;
          posX.set(id, x);
        });
      });

      const ITERS = 10;
      for (let it = 0; it < ITERS; it++) {
        const downward = it % 2 === 0;
        const rows = downward ? layerGroups : [...layerGroups].reverse();
        rows.forEach((lg) => {
          if (!lg.length) return;
          const desired = lg.map((id) => {
            const nbrs = ((downward ? inE.get(id) : outE.get(id)) || []).filter((n) => posX.has(n));
            if (!nbrs.length) return posX.get(id);
            const xs = nbrs.map((n) => posX.get(n)).sort((a, b) => a - b);
            const mid = (xs.length - 1) / 2;
            return xs.length % 2 ? xs[mid] : (xs[Math.floor(mid)] + xs[Math.ceil(mid)]) / 2;
          });
          resolveRow(lg, desired, widthOf, posX);
        });
      }
      return posX;
    }

    // ── Legend helper (shared by both layouts) ─────────────────────────
    function drawLegend() {
      if (!genLegend) return;
      while (genLegend.firstChild) genLegend.removeChild(genLegend.firstChild);
      const mode = genColorBy.value;
      const items = mode === "process"
        ? [...genProcessList.map((p) => ({ color: genProcColorMap.get(String(p.id)), label: String(p.name) })), { color: genProcColorMap.get("__none__"), label: "No process" }]
        : mode === "construction"
          ? allConstrs.filter((c) => constrSel.get(c) !== false).map((c) => ({ color: constrColorMap.get(c) || "#7a8c8f", label: c }))
          : allTypes.filter((t) => primSel.get(t) !== false).map((t) => ({ color: typeColorMap.get(t) || "#7a8c8f", label: t }));
      const mkItem = (color, label, bold) => {
        const s = document.createElement("span"); s.className = "viz-process-legend-item";
        const d = document.createElement("span"); d.className = "viz-process-legend-dot"; d.style.cssText = `background:${color};${bold ? "border:2px solid #000;box-sizing:border-box" : ""}`;
        const l = document.createElement("span"); l.textContent = label; if (bold) l.style.fontWeight = "700";
        s.appendChild(d); s.appendChild(l); return s;
      };
      genLegend.appendChild(mkItem("#152021", "Standard", true));
      items.forEach(({ color, label }) => genLegend.appendChild(mkItem(color || "#7a8c8f", label, false)));
      relationTypes.forEach((relation) => {
        const item = mkItem(relationColorMap.get(relation), relation.replace(/_/g, " "), false);
        item.firstChild.style.cssText += ";border-radius:1px;height:3px";
        genLegend.appendChild(item);
      });
      genLegend.hidden = false;
    }

    // ── Sugiyama layered layout ────────────────────────────────────────
    function drawSugiyama(dagNodes, isoNodes, inE, outE, dagSet, visEdges) {
      genPlot.style.display = ""; genPlot.style.margin = "";
      const NH = nodeH(); const RG = rowGap(); const IW = isoW();
      const useGen = !!(genByGeneration && genByGeneration.checked);

      // Layer assignment: by graph depth (generation) or by publication year
      let layerOf; let rowLabel;
      if (useGen) {
        layerOf = assignLayers(new Set(dagNodes), inE);
        rowLabel = (li) => `gen ${li}`;
      } else {
        const yrOf = (n) => { const y = Number((genFamById.get(n) || {}).year); return (y > 1800 && y < 2200) ? y : 9999; };
        const uniqueYears = [...new Set(dagNodes.map(yrOf))].sort((a, b) => a - b);
        const yearToLayer = new Map(uniqueYears.map((y, i) => [y, i]));
        layerOf = new Map(dagNodes.map((n) => [n, yearToLayer.get(yrOf(n)) ?? 0]));
        rowLabel = (li) => String(uniqueYears[li] ?? li);
      }

      const maxLayer = dagNodes.length ? Math.max(...dagNodes.map((n) => layerOf.get(n) || 0)) : -1;
      const numLayers = maxLayer + 1;

      const layerGroups = Array.from({ length: numLayers }, () => []);
      dagNodes.forEach((n) => layerGroups[layerOf.get(n) || 0].push(n));
      layerGroups.forEach((lg) => lg.sort((a, b) => Number((genFamById.get(a) || {}).year || 9999) - Number((genFamById.get(b) || {}).year || 9999)));
      if (numLayers > 1) minimiseCrossings(layerGroups, inE, outE);

      const widthOf = (id) => nw(String((genFamById.get(id) || {}).name || id));
      const posX = numLayers ? assignXCoordinates(layerGroups, inE, outE, widthOf) : new Map();
      const posY = new Map();
      layerGroups.forEach((lg, li) => { const y = TOP_PAD + li * (NH + RG); lg.forEach((n) => posY.set(n, y)); });

      let dagMinX = Infinity; let dagMaxX = -Infinity;
      dagNodes.forEach((n) => {
        const cx = posX.get(n); if (cx === undefined) return;
        const w = widthOf(n);
        dagMinX = Math.min(dagMinX, cx - w / 2); dagMaxX = Math.max(dagMaxX, cx + w / 2);
      });
      const dagW = dagNodes.length ? (dagMaxX - dagMinX) : 0;

      const ISO_COLS = Math.max(1, Math.floor((Math.max(dagW, 400) + COL_GAP) / (IW + COL_GAP)));
      const isoRows = isoNodes.length ? Math.ceil(isoNodes.length / ISO_COLS) : 0;
      const dagH = numLayers ? numLayers * (NH + RG) - RG : 0;
      const isoH = isoRows ? RG * 2 + isoRows * (NH + COL_GAP) : 0;
      const canvasW = Math.max(600, dagW + SIDE_PAD * 2, ISO_COLS * (IW + COL_GAP) - COL_GAP + SIDE_PAD * 2);
      const canvasH = Math.max(260, TOP_PAD + dagH + isoH + 20);

      genPlot.setAttribute("viewBox", `0 0 ${canvasW} ${canvasH}`);
      genPlot.setAttribute("width", String(canvasW));
      genPlot.setAttribute("height", String(canvasH));
      genFrame.style.height = `${Math.max(220, Math.min(Math.round(window.innerHeight * 0.70), canvasH + 8))}px`;

      if (dagNodes.length) {
        const shift = (canvasW - dagW) / 2 - dagMinX;
        dagNodes.forEach((n) => posX.set(n, posX.get(n) + shift));
      }

      const isoBase = TOP_PAD + dagH + (numLayers ? RG * 2 : 0);
      isoNodes.forEach((n, idx) => {
        const col = idx % ISO_COLS; const row = Math.floor(idx / ISO_COLS);
        posX.set(n, SIDE_PAD + col * (IW + COL_GAP) + IW / 2);
        posY.set(n, isoBase + row * (NH + COL_GAP));
      });

      const defs = svgEl("defs", {});
      const marker = svgEl("marker", { id: "genArrow", markerWidth: "10", markerHeight: "7", markerUnits: "userSpaceOnUse", refX: "0", refY: "3.5", orient: "auto" });
      marker.appendChild(svgEl("path", { d: "M0,0 L10,3.5 L0,7 z", fill: "rgba(55,75,80,0.78)" }));
      defs.appendChild(marker); genPlot.appendChild(defs);

      const stripes = ["rgba(231,244,248,0.52)", "rgba(248,244,231,0.52)"];
      layerGroups.forEach((lg, li) => {
        const y = TOP_PAD + li * (NH + RG) - 7;
        genPlot.appendChild(svgEl("rect", { x: "0", y: String(y), width: String(canvasW), height: String(NH + 14), fill: stripes[li % 2] }));
        const genLbl = svgEl("text", { x: String(canvasW - 5), y: String(y + NH * 0.65 + 7), "text-anchor": "end", style: "font-size:9px;fill:#8a9ea2;font-family:sans-serif" });
        genLbl.textContent = rowLabel(li);
        genPlot.appendChild(genLbl);
      });

      if (isoNodes.length && numLayers) {
        const sepY = isoBase - RG;
        genPlot.appendChild(svgEl("line", { x1: String(SIDE_PAD), x2: String(canvasW - SIDE_PAD), y1: String(sepY), y2: String(sepY), stroke: "#c8c6b8", "stroke-width": "1", "stroke-dasharray": "4 3" }));
        const sepLbl = svgEl("text", { x: String(SIDE_PAD), y: String(sepY - 4), class: "viz-label", style: "font-size:9px;fill:#8a9ea2" });
        sepLbl.textContent = "No visible influence links";
        genPlot.appendChild(sepLbl);
      }

      const hoverPaths = [];
      visEdges.forEach((e) => {
        const src = String(e.source_family_id || ""); const tgt = String(e.target_family_id || "");
        if (!posX.has(src) || !posX.has(tgt)) return;
        const sx = posX.get(src); const sy = posY.get(src) + NH;
        const tx = posX.get(tgt); const ty = posY.get(tgt) - 12;
        const vGap = Math.max(RG, ty - sy);
        const cpY = Math.min(vGap * 0.48, RG * 0.85);
        const pd = `M ${sx} ${sy} C ${sx} ${sy + cpY}, ${tx} ${ty - cpY}, ${tx} ${ty}`;
        const rels = edgeRelations(e);
        const relLabel = rels.map((r) => String(r).replace(/_/g, " ")).join(", ");
        const srcName = String((genFamById.get(src) || {}).name || src);
        const tgtName = String((genFamById.get(tgt) || {}).name || tgt);
        const note = String(e.note || "").trim();
        const hoverTxt = `${srcName} → ${tgtName}: ${relLabel}${note ? " | " + note : ""}`;
        if (genCollapseEdges && genCollapseEdges.checked) {
          genPlot.appendChild(svgEl("path", { d: pd, stroke: "rgba(0,0,0,0.32)", "stroke-width": "0.9", fill: "none", "pointer-events": "none", "marker-end": "url(#genArrow)" }));
        } else {
          rels.forEach((relation, i) => {
            const strokeW = 0.8 + (rels.length - i - 1) * 1.3;
            const attrs = { d: pd, stroke: relationColorMap.get(relation), "stroke-width": String(strokeW), fill: "none", "pointer-events": "none", opacity: "0.5" };
            if (i === rels.length - 1) attrs["marker-end"] = "url(#genArrow)";
            genPlot.appendChild(svgEl("path", attrs));
          });
        }
        const hp = svgEl("path", { d: pd, stroke: "rgba(0,0,0,0.001)", "stroke-width": String(Math.max(10, rels.length * 2.2 + 5)), fill: "none", "pointer-events": "all" });
        const hpT = svgEl("title", {}); hpT.textContent = hoverTxt; hp.appendChild(hpT);
        hp.addEventListener("mouseenter", () => { if (genEdgeInfo) genEdgeInfo.textContent = hoverTxt; });
        hp.addEventListener("mouseleave", () => { if (genEdgeInfo) genEdgeInfo.textContent = BASE_EDGE_INFO; });
        hoverPaths.push(hp);
      });

      [...dagNodes, ...isoNodes].forEach((fid) => {
        const fam = genFamById.get(fid); if (!fam) return;
        const cx = posX.get(fid); const cy = posY.get(fid); if (cx === undefined || cy === undefined) return;
        const isIso = !dagSet.has(fid); const isStd = stdFamIds.has(fid);
        const name = String(fam.name || fid);
        const w = isIso ? IW : nw(name);
        const color = nodeColor(fid);
        const famTypes = Array.from(famToTypes.get(fid) || []).sort().join(", ") || "—";
        const famConstrs = Array.from(famToConstrs.get(fid) || []).sort().join(", ") || "—";
        const pid = genFamilyProcessMap[fid]; const proc = pid ? genProcessList.find((p) => String(p.id) === pid) : null;
        const tip = [`${name} (${fam.year})`, `Type: ${famTypes}`, `Construction: ${famConstrs}`, ...(isStd ? ["Standard: yes"] : []), ...(proc ? [`Process: ${proc.name}`] : []), ...(fam.notes ? [fam.notes] : [])].join("\n");
        const rect = svgEl("rect", { x: String(cx - w / 2), y: String(cy), width: String(w), height: String(NH), rx: "4", ry: "4", fill: isStd ? "#152021" : color, stroke: isStd ? "#000" : "rgba(0,0,0,0.22)", "stroke-width": isStd ? "2" : "1", opacity: isIso ? "0.58" : "1" });
        const rt = svgEl("title", {}); rt.textContent = tip; rect.appendChild(rt);
        genPlot.appendChild(rect);
        const maxCh = Math.min(genNumChars, Math.max(4, Math.floor((w - NODE_PAD_X * 2) / (genFontPx * 0.56))));
        const lblStyle = `font-size:${genFontPx}px;font-family:"IBM Plex Mono",monospace;fill:#fff;pointer-events:none;font-weight:${isStd ? 700 : 400};opacity:${isIso ? "0.8" : "1"}`;
        const lbl = svgEl("text", { "text-anchor": "middle", style: lblStyle });
        const disp = genNameMode === "full" ? name : (name.length <= maxCh ? name : name.slice(0, Math.max(1, maxCh - 1)) + "…");
        lbl.setAttribute("x", String(cx));
        lbl.setAttribute("y", String(cy + NH * 0.67));
        lbl.textContent = disp;
        genPlot.appendChild(lbl);
      });

      hoverPaths.forEach((hp) => genPlot.appendChild(hp));
    }

    // ── Radial (Lepage-Bandet style): year → radius, angle from tree ──
    function drawRadial(dagNodes, isoNodes, inE, outE, dagSet, visEdges) {
      const useGen = !!(genByGeneration && genByGeneration.checked);

      // Pre-compute DAG layers when in generation mode
      let layerOf;
      if (useGen) layerOf = assignLayers(new Set(dagNodes), inE);

      // Which recorded relation actually denotes direct lineage vs. a looser design
      // similarity — used below so a node with several DAG parents picks its strongest
      // relationship as the tree parent, instead of just whichever parent is most recent.
      const REL_TIER = { improvement_of: 3, variant_of: 3, standardization_of: 3, generalization_of: 3, inspired_by: 2 };
      const edgeTier = new Map();
      visEdges.forEach((e) => {
        const src = String(e.source_family_id || ""); const tgt = String(e.target_family_id || "");
        const tier = edgeRelations(e).reduce((m, r) => Math.max(m, REL_TIER[r] || 1), 1);
        const key = `${src}|${tgt}`;
        edgeTier.set(key, Math.max(edgeTier.get(key) || 0, tier));
      });
      const parentTier = (parent, node) => edgeTier.get(`${parent}|${node}`) || 1;

      // Build spanning tree for angular placement only. All influence edges are rendered alike.
      const treeChildren = new Map(dagNodes.map((n) => [n, []]));
      const treeParentOf = new Map();
      const roots = [];
      dagNodes.forEach((n) => {
        const parents = (inE.get(n) || []).filter((p) => dagSet.has(p));
        if (!parents.length) { roots.push(n); return; }
        let prim;
        if (useGen) {
          const myL = layerOf.get(n) || 0;
          const prevLayer = parents.filter((p) => (layerOf.get(p) || 0) === myL - 1);
          const candidates = prevLayer.length ? prevLayer : parents;
          prim = [...candidates].sort((a, b) =>
            parentTier(b, n) - parentTier(a, n) ||
            Number((genFamById.get(b) || {}).year || 0) - Number((genFamById.get(a) || {}).year || 0) || a.localeCompare(b))[0];
        } else {
          prim = [...parents].sort((a, b) =>
            parentTier(b, n) - parentTier(a, n) ||
            Number((genFamById.get(b) || {}).year || 0) - Number((genFamById.get(a) || {}).year || 0))[0];
        }
        treeParentOf.set(n, prim);
        treeChildren.get(prim).push(n);
      });
      treeChildren.forEach((kids) => kids.sort((a, b) =>
        Number((genFamById.get(a) || {}).year || 9999) - Number((genFamById.get(b) || {}).year || 9999)));

      // Leaf count (memoised — fixed by tree structure, not affected by child ordering)
      const lcCache = new Map();
      function lc(id) {
        if (lcCache.has(id)) return lcCache.get(id);
        const kids = treeChildren.get(id) || [];
        const v = kids.length ? kids.reduce((s, k) => s + lc(k), 0) : 1;
        lcCache.set(id, v); return v;
      }

      // Angle assignment wrapped to be re-callable as child ordering is refined
      const angleOf = new Map();
      function runAssignAngles() {
        angleOf.clear();
        function rec(id, start, span) {
          const kids = treeChildren.get(id) || [];
          if (!kids.length) { angleOf.set(id, start + span / 2); return; }
          const total = lc(id); let pos = start;
          kids.forEach((k) => { const s = span * lc(k) / total; rec(k, pos, s); pos += s; });
          const ca = kids.map((k) => angleOf.get(k));
          angleOf.set(id, (Math.min(...ca) + Math.max(...ca)) / 2);
        }
        const totalLeaves = roots.reduce((s, r) => s + lc(r), 0) || 1;
        let aPos = 0;
        roots.forEach((r) => { const span = 360 * lc(r) / totalLeaves; rec(r, aPos, span); aPos += span; });
      }
      runAssignAngles();

      // Subtree membership cache (fixed — membership doesn't change, only ordering does)
      const stNodesCache = new Map();
      function stNodes(id) {
        if (stNodesCache.has(id)) return stNodesCache.get(id);
        const s = new Set([id]);
        (treeChildren.get(id) || []).forEach((k) => stNodes(k).forEach((n) => s.add(n)));
        stNodesCache.set(id, s); return s;
      }
      dagNodes.forEach((n) => stNodes(n));

      // Circular mean angle of cross-edges for a subtree (null when there are none)
      function extBary(rootId) {
        const inside = stNodes(rootId);
        let sx = 0, sy = 0, cnt = 0;
        inside.forEach((id) => {
          [...(outE.get(id) || []), ...(inE.get(id) || [])].forEach((nb) => {
            if (!inside.has(nb) && angleOf.has(nb)) {
              const a = (angleOf.get(nb) || 0) * Math.PI / 180;
              sx += Math.cos(a); sy += Math.sin(a); cnt++;
            }
          });
        });
        return cnt === 0 ? null : Math.atan2(sy, sx) * 180 / Math.PI;
      }

      // Total angular "stress": sum over every visible edge of the angular distance
      // between its two endpoints. This is the real objective — low stress means related
      // families sit close together on the circle — and lets us verify a re-ordering
      // actually helped instead of trusting the barycenter heuristic blindly (it isn't
      // monotonic pass-to-pass, so without this a later, worse pass could win).
      function totalStress() {
        let s = 0;
        visEdges.forEach((e) => {
          const src = String(e.source_family_id || ""); const tgt = String(e.target_family_id || "");
          if (!angleOf.has(src) || !angleOf.has(tgt)) return;
          let d = Math.abs(angleOf.get(src) - angleOf.get(tgt)) % 360;
          if (d > 180) d = 360 - d;
          s += d;
        });
        return s;
      }
      function snapshotOrder() { return { children: new Map([...treeChildren].map(([k, v]) => [k, v.slice()])), roots: roots.slice() }; }
      function restoreOrder(snap) {
        snap.children.forEach((arr, k) => { const cur = treeChildren.get(k); cur.length = 0; cur.push(...arr); });
        roots.length = 0; roots.push(...snap.roots);
      }

      let best = snapshotOrder();
      let bestStress = totalStress();

      // Circular Sugiyama barycenter heuristic: iteratively reorder children so that
      // subtrees whose cross-edges point in the same direction are placed adjacent,
      // reducing angular crossings. Angles are normalized relative to the parent arc
      // midpoint to handle the 0°/360° wraparound correctly.
      for (let pass = 0; pass < 8; pass++) {
        let changed = false;
        const baryMap = new Map();
        dagNodes.forEach((id) => { baryMap.set(id, extBary(id)); });

        treeChildren.forEach((kids, _par) => {
          if (kids.length < 2) return;
          const parAngles = kids.map((k) => angleOf.get(k) || 0);
          const parMid = (Math.min(...parAngles) + Math.max(...parAngles)) / 2;
          const prev = [...kids];
          kids.sort((a, b) => {
            const ba = baryMap.get(a); const bb = baryMap.get(b);
            if (ba == null && bb == null) return 0;
            if (ba == null) return 1; if (bb == null) return -1;
            let ra = ba - parMid; while (ra > 180) ra -= 360; while (ra < -180) ra += 360;
            let rb = bb - parMid; while (rb > 180) rb -= 360; while (rb < -180) rb += 360;
            return ra - rb;
          });
          if (kids.some((k, i) => k !== prev[i])) changed = true;
        });

        if (roots.length > 1) {
          const prev = [...roots];
          roots.sort((a, b) => {
            const ba = baryMap.get(a); const bb = baryMap.get(b);
            if (ba == null && bb == null) return 0;
            if (ba == null) return 1; if (bb == null) return -1;
            const ra = ba < 0 ? ba + 360 : ba;
            const rb = bb < 0 ? bb + 360 : bb;
            return ra - rb;
          });
          if (roots.some((r, i) => r !== prev[i])) changed = true;
        }

        runAssignAngles();
        const stress = totalStress();
        if (stress < bestStress) { bestStress = stress; best = snapshotOrder(); }
        if (!changed) break;
      }
      restoreOrder(best); runAssignAngles();

      // Transpose refinement: adjacent-swap local search on top of the best barycenter
      // ordering found above, at every level of the tree (including the root ring).
      // A swap is kept only when it strictly lowers total stress, so this can only match
      // or improve on the barycenter passes — it never regresses relative to sweeping alone.
      function transposeGroup(arr) {
        let improved = true; let guard = 0;
        while (improved && guard++ < 4) {
          improved = false;
          for (let i = 0; i < arr.length - 1; i++) {
            [arr[i], arr[i + 1]] = [arr[i + 1], arr[i]];
            runAssignAngles();
            const s = totalStress();
            if (s < bestStress) { bestStress = s; improved = true; }
            else { [arr[i], arr[i + 1]] = [arr[i + 1], arr[i]]; runAssignAngles(); }
          }
        }
      }
      treeChildren.forEach((kids) => { if (kids.length > 1) transposeGroup(kids); });
      if (roots.length > 1) transposeGroup(roots);

      // Radius mapping: year mode or generation mode
      const charW = genFontPx * 0.62; // use bold advance width (synthesised bold ≈ 0.62 em)
      const R_MIN = 2;
      let nodeR;      // fid → radius (px)
      let maxR;
      let ringLabels; // [{r, label}] for concentric guide rings

      if (useGen) {
        const maxLayer = dagNodes.length ? Math.max(...dagNodes.map((n) => layerOf.get(n) || 0)) : 0;
        nodeR = (fid) => R_MIN + (1 + (layerOf.get(fid) || 0)) * genNumChars * charW;
        maxR = R_MIN + (1 + maxLayer) * genNumChars * charW;
        ringLabels = Array.from({ length: maxLayer + 1 }, (_, g) => ({ r: R_MIN + (1 + g) * genNumChars * charW, label: `G${g}` }));
      } else {
        const allYears = dagNodes.map((n) => Number((genFamById.get(n) || {}).year)).filter((y) => y > 1800 && y < 2200);
        const minY = allYears.length ? Math.min(...allYears) : 1970;
        const maxY = allYears.length ? Math.max(...allYears) : 2025;
        nodeR = (fid) => R_MIN + Math.max(0, Number((genFamById.get(fid) || {}).year || minY) - minY) * genNumChars * charW;
        maxR = R_MIN + (maxY - minY) * genNumChars * charW;
        const d1 = Math.floor(minY / 10) * 10; const d2 = Math.floor(maxY / 10) * 10;
        ringLabels = [];
        for (let yr = d1; yr <= maxY; yr++) {
          const r = Math.max(R_MIN, R_MIN + (yr - minY) * genNumChars * charW);
          const isDecade = yr % 10 === 0;
          ringLabels.push({ r, label: isDecade ? String(yr) : null, minor: !isDecade });
        }
      }

      const diam = Math.max(400, 2 * Math.ceil(maxR + genNumChars * charW + 20));
      const rcx = diam / 2; const rcy = diam / 2;

      // Polar (deg, 0=top clockwise) → cartesian SVG
      function pol(r, deg) {
        const a = (deg - 90) * Math.PI / 180;
        return { x: rcx + r * Math.cos(a), y: rcy + r * Math.sin(a) };
      }

      // Minimum angular gap per node (degrees) → used for label truncation
      const sortedByAngle = [...angleOf.entries()].sort((a, b) => a[1] - b[1]);
      const minGapOf = new Map();
      const nAng = sortedByAngle.length;
      sortedByAngle.forEach(([id, ang], i) => {
        const prev = sortedByAngle[(i - 1 + nAng) % nAng][1] + (i === 0 ? -360 : 0);
        const next = sortedByAngle[(i + 1) % nAng][1] + (i === nAng - 1 ? 360 : 0);
        minGapOf.set(id, Math.min(ang - prev, next - ang));
      });

      genPlot.setAttribute("viewBox", `0 0 ${diam} ${diam}`);
      genPlot.setAttribute("width", String(diam));
      genPlot.setAttribute("height", String(diam));
      genPlot.style.display = "block"; genPlot.style.margin = "0 auto";
      genFrame.style.height = `${Math.max(320, Math.min(Math.round(window.innerHeight * 0.82), diam + 8))}px`;

      // Concentric guide rings (per-year + decade in year mode, per-gen in gen mode)
      ringLabels.forEach(({ r, label, minor }) => {
        genPlot.appendChild(svgEl("circle", { cx: String(rcx), cy: String(rcy), r: String(r.toFixed(1)), fill: "none", stroke: minor ? "#eeece6" : "#d8d5cc", "stroke-width": minor ? "0.4" : "0.8" }));
        if (label) {
          const tp = pol(Math.max(r + 2, genFontPx * 0.8), 0);
          const rl = svgEl("text", { x: String(tp.x.toFixed(1)), y: String(tp.y.toFixed(1)), "text-anchor": "middle", style: "font-size:8px;fill:#b0b0a0;font-family:sans-serif" });
          rl.textContent = label; genPlot.appendChild(rl);
        }
      });

      // Radial S-curve bezier between two polar positions
      function rPath(srcId, tgtId) {
        const sr = nodeR(srcId); const tr = nodeR(tgtId);
        const sd = angleOf.get(srcId) || 0; const td = angleOf.get(tgtId) || 0;
        const mr = (sr + tr) / 2;
        const s = pol(sr, sd); const cp1 = pol(mr, sd); const cp2 = pol(mr, td); const t = pol(tr, td);
        return `M ${s.x.toFixed(1)} ${s.y.toFixed(1)} C ${cp1.x.toFixed(1)} ${cp1.y.toFixed(1)}, ${cp2.x.toFixed(1)} ${cp2.y.toFixed(1)}, ${t.x.toFixed(1)} ${t.y.toFixed(1)}`;
      }

      // Draw every relation as a solid colored band. Wider bands are drawn first so
      // multi-relation edges retain a visible stripe for each relation type.
      const hoverPaths = [];
      visEdges.forEach((e) => {
        const src = String(e.source_family_id || ""); const tgt = String(e.target_family_id || "");
        if (!angleOf.has(src) || !angleOf.has(tgt)) return;
        const pd = rPath(src, tgt);
        const rels = edgeRelations(e);
        const relLabel = rels.map((r) => String(r).replace(/_/g, " ")).join(", ");
        const hoverTxt = `${String((genFamById.get(src) || {}).name || src)} → ${String((genFamById.get(tgt) || {}).name || tgt)}: ${relLabel}${e.note ? " | " + String(e.note) : ""}`;
        if (genCollapseEdges && genCollapseEdges.checked) {
          genPlot.appendChild(svgEl("path", { d: pd, stroke: "rgba(0,0,0,0.28)", "stroke-width": "0.9", fill: "none" }));
        } else {
          rels.forEach((relation, i) => {
            const strokeW = 0.8 + (rels.length - i - 1) * 1.3;
            genPlot.appendChild(svgEl("path", { d: pd, stroke: relationColorMap.get(relation), "stroke-width": String(strokeW), fill: "none", opacity: "0.5" }));
          });
        }
        const hp = svgEl("path", { d: pd, stroke: "rgba(0,0,0,0.001)", "stroke-width": String(Math.max(10, rels.length * 2.1 + 5)), fill: "none", "pointer-events": "all" });
        const hpT = svgEl("title", {}); hpT.textContent = hoverTxt; hp.appendChild(hpT);
        hp.addEventListener("mouseenter", () => { if (genEdgeInfo) genEdgeInfo.textContent = hoverTxt; });
        hp.addEventListener("mouseleave", () => { if (genEdgeInfo) genEdgeInfo.textContent = BASE_EDGE_INFO; });
        hoverPaths.push(hp);
      });

      // Draw nodes and radial labels
      dagNodes.forEach((fid) => {
        if (!angleOf.has(fid)) return;
        const fam = genFamById.get(fid); if (!fam) return;
        const yr = Number(fam.year || 0);
        const rr = nodeR(fid);
        const deg = angleOf.get(fid);
        const { x: nx, y: ny } = pol(rr, deg);
        const isStd = stdFamIds.has(fid);
        const color = nodeColor(fid);
        const famTypes = Array.from(famToTypes.get(fid) || []).sort().join(", ") || "—";
        const famConstrs = Array.from(famToConstrs.get(fid) || []).sort().join(", ") || "—";
        const pid = genFamilyProcessMap[fid]; const proc = pid ? genProcessList.find((p) => String(p.id) === pid) : null;
        const genLabel = useGen ? `Gen ${layerOf.get(fid) || 0}` : String(yr);
        const tip = [`${String(fam.name || fid)} (${genLabel})`, `Type: ${famTypes}`, `Construction: ${famConstrs}`, ...(isStd ? ["Standard: yes"] : []), ...(proc ? [`Process: ${proc.name}`] : [])].join("\n");
        const showBullets = !genShowBullets || genShowBullets.checked;
        const nodeRad = isStd ? 4 : 3;
        if (showBullets) {
          const circ = svgEl("circle", { cx: String(nx.toFixed(1)), cy: String(ny.toFixed(1)), r: String(nodeRad), fill: isStd ? "#152021" : color, stroke: isStd ? "#000" : "rgba(0,0,0,0.25)", "stroke-width": isStd ? "1.5" : "0.8" });
          const ct = svgEl("title", {}); ct.textContent = tip; circ.appendChild(ct); genPlot.appendChild(circ);
        }
        const name = String(fam.name || fid);
        const isRight = deg <= 180;
        const rad = (deg - 90) * Math.PI / 180;
        const off = showBullets ? nodeRad + 5 : 3;
        const lx = nx + off * Math.cos(rad);
        const ly = ny + off * Math.sin(rad);
        const textRot = isRight ? (deg - 90) : (deg + 90);
        const maxLabelCh = genNumChars;
        const labelFill = showBullets ? (isStd ? "#162022" : "#1a2a2e") : color;
        const radStyle = `font-size:${genFontPx}px;font-family:"IBM Plex Mono",monospace;fill:${labelFill};pointer-events:${showBullets ? "none" : "all"};font-weight:${isStd ? 700 : 400}`;
        const anchor = isRight ? "start" : "end";
        const disp = genNameMode === "full" ? name : (name.length <= maxLabelCh ? name : name.slice(0, Math.max(2, maxLabelCh - 1)) + "…");
        const lbl = svgEl("text", { x: String(lx.toFixed(1)), y: String(ly.toFixed(1)), "text-anchor": anchor,
          transform: `rotate(${textRot.toFixed(1)},${lx.toFixed(1)},${ly.toFixed(1)})`, style: radStyle });
        lbl.textContent = disp;
        if (!showBullets) { const lt = svgEl("title", {}); lt.textContent = tip; lbl.appendChild(lt); }
        genPlot.appendChild(lbl);
      });
      hoverPaths.forEach((hp) => genPlot.appendChild(hp));
    }

    // ── Render dispatcher ─────────────────────────────────────────────
    function render() {
      updateYrLbl();
      while (genPlot.firstChild) genPlot.removeChild(genPlot.firstChild);

      const eligibleIds = families.map((f) => String(f.id || "")).filter((fid) => fid && isVis(fid, true));
      const eligibleSet = new Set(eligibleIds);
      const needle = genFamilySearch.value.trim().toLowerCase();
      let visIds = eligibleIds;
      if (needle) {
        const matched = new Set(eligibleIds.filter((fid) =>
          String((genFamById.get(fid) || {}).name || fid).toLowerCase().includes(needle)));
        const expanded = new Set(matched);
        influences.forEach((e) => {
          const src = String(e.source_family_id || ""); const tgt = String(e.target_family_id || "");
          if (matched.has(src) && eligibleSet.has(tgt)) expanded.add(tgt);
          if (matched.has(tgt) && eligibleSet.has(src)) expanded.add(src);
        });
        visIds = eligibleIds.filter((fid) => expanded.has(fid));
      }
      const visSet = new Set(visIds);

      if (!visIds.length) {
        genPlot.setAttribute("viewBox", "0 0 620 160"); genPlot.setAttribute("width", "620"); genPlot.setAttribute("height", "160");
        const msg = svgEl("text", { x: "24", y: "42", class: "viz-label" }); msg.textContent = "No families match the current filters.";
        genPlot.appendChild(msg); genFrame.style.height = "200px"; if (genLegend) genLegend.hidden = true; return;
      }

      const visEdges = influences.filter((e) => visSet.has(String(e.source_family_id || "")) && visSet.has(String(e.target_family_id || "")));

      const inE = new Map(visIds.map((n) => [n, []])); const outE = new Map(visIds.map((n) => [n, []]));
      visEdges.forEach((e) => { const src = String(e.source_family_id); const tgt = String(e.target_family_id); inE.get(tgt).push(src); outE.get(src).push(tgt); });

      const dagSet = new Set(); visEdges.forEach((e) => { dagSet.add(String(e.source_family_id)); dagSet.add(String(e.target_family_id)); });
      const dagNodes = visIds.filter((n) => dagSet.has(n));
      const isoNodes = genConnectedOnly.checked ? [] : visIds.filter((n) => !dagSet.has(n));

      if (genLayoutMode === "radial") {
        drawRadial(dagNodes, isoNodes, inE, outE, dagSet, visEdges);
      } else {
        drawSugiyama(dagNodes, isoNodes, inE, outE, dagSet, visEdges);
      }
      drawLegend();
    }

    genColorBy.addEventListener("change", render);
    genConnectedOnly.addEventListener("change", render);
    genStandardsOnly.addEventListener("change", render);
    if (genByGeneration) genByGeneration.addEventListener("change", render);
    if (genShowBullets) genShowBullets.addEventListener("change", render);
    if (genCollapseEdges) genCollapseEdges.addEventListener("change", render);
    genFamilySearch.addEventListener("input", render);
    genFamilySearch.addEventListener("change", render);
    genYearStart.addEventListener("input", render);
    genYearEnd.addEventListener("input", render);
    genYearReset.addEventListener("click", () => {
      if (!genYrBounds) return;
      genYearStart.value = String(genYrBounds.min); genYearEnd.value = String(genYrBounds.max); render();
    });
    if (genFontMinus) genFontMinus.addEventListener("click", () => {
      genFontPx = Math.max(6, genFontPx - 1);
      if (genFontValue) genFontValue.textContent = `${genFontPx}px`; render();
    });
    if (genFontPlus) genFontPlus.addEventListener("click", () => {
      genFontPx = Math.min(16, genFontPx + 1);
      if (genFontValue) genFontValue.textContent = `${genFontPx}px`; render();
    });
    if (genFontReset) genFontReset.addEventListener("click", () => {
      genFontPx = GEN_BASE_FONT;
      if (genFontValue) genFontValue.textContent = `${genFontPx}px`; render();
    });
    if (genRadiusMinus) genRadiusMinus.addEventListener("click", () => {
      genNumChars = Math.max(3, genNumChars - 1);
      if (genRadiusValue) genRadiusValue.textContent = `${genNumChars}ch`; render();
    });
    if (genRadiusPlus) genRadiusPlus.addEventListener("click", () => {
      genNumChars = Math.min(30, genNumChars + 1);
      if (genRadiusValue) genRadiusValue.textContent = `${genNumChars}ch`; render();
    });
    if (genRadiusReset) genRadiusReset.addEventListener("click", () => {
      genNumChars = 8;
      if (genRadiusValue) genRadiusValue.textContent = "8ch"; render();
    });
    if (genLayoutLayered) genLayoutLayered.addEventListener("click", () => {
      genLayoutMode = "layered";
      if (genLayoutLayered) genLayoutLayered.classList.add("is-active");
      if (genLayoutRadial) genLayoutRadial.classList.remove("is-active");
      render();
    });
    if (genLayoutRadial) genLayoutRadial.addEventListener("click", () => {
      genLayoutMode = "radial";
      if (genLayoutRadial) genLayoutRadial.classList.add("is-active");
      if (genLayoutLayered) genLayoutLayered.classList.remove("is-active");
      render();
    });
    [[genNameClip, "clip"], [genNameFull, "full"]].forEach(([btn, mode]) => {
      if (!btn) return;
      btn.addEventListener("click", () => {
        genNameMode = mode;
        [genNameClip, genNameFull].forEach((b) => { if (b) b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        render();
      });
    });

    const genDownloadPng = document.getElementById("genDownloadPng");
    if (genDownloadPng) genDownloadPng.addEventListener("click", () => {
      const w = Number(genPlot.getAttribute("width") || 800);
      const h = Number(genPlot.getAttribute("height") || 600);
      const scale = 2;
      const canvas = document.createElement("canvas");
      canvas.width = w * scale; canvas.height = h * scale;
      const ctx = canvas.getContext("2d");
      ctx.scale(scale, scale);
      ctx.fillStyle = "#fff";
      ctx.fillRect(0, 0, w, h);
      const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(genPlot)], { type: "image/svg+xml" }));
      const img = new Image();
      img.onload = () => { ctx.drawImage(img, 0, 0); URL.revokeObjectURL(url); const a = document.createElement("a"); a.download = "genealogy.png"; a.href = canvas.toDataURL("image/png"); a.click(); };
      img.onerror = () => URL.revokeObjectURL(url);
      img.src = url;
    });
    initFilters();
    render();

  }

  setupNavigator();
  setupAllTablesBrowser();
  setupBuilder();
  setupFamilyVisualization();
  setupGenealogy();
})();
