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

  // Shared "Find family" matching, used by both the Timelines and Genealogy
  // search boxes. Plain substring search (the historic behavior) makes a
  // search for "DES" also match "HADES" -- exact mode instead requires the
  // needle to appear as a whole word (bounded by non-word characters), so
  // "DES" matches "DES" or "Triple DES" but not "HADES".
  function familyNameMatches(name, needle, exact) {
    const text = String(name || "");
    if (!needle) return true;
    if (!exact) return text.toLowerCase().includes(needle.toLowerCase());
    try {
      const escaped = needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return new RegExp(`\\b${escaped}\\b`, "i").test(text);
    } catch (error) {
      return text.toLowerCase().includes(needle.toLowerCase());
    }
  }

  // ── "Open PDF" viewer -- shared by every family/relation note across the
  // Timelines and Genealogy tabs. data.familyPdfMap (family_id -> local
  // "references/<file>" paths) is precomputed at build time (see
  // scripts/build_static_site.py, scripts/reference_pdfs.py) by the same
  // filename-matching logic the influence-mining workflow already relies on,
  // rather than re-deriving it here.
  function pdfPathsForFamily(fid) {
    const map = (data && data.familyPdfMap) || {};
    return map[fid] || [];
  }

  // entries: [{fid, name}] for a single family, or [{fid,name},{fid,name}]
  // for a relation between two families. Returns null (no "Open PDF" button)
  // unless at least one entry actually resolves to a local PDF.
  function pdfEntriesForFamilies(entries) {
    const any = entries.some((e) => pdfPathsForFamily(e.fid).length);
    return any ? entries : null;
  }

  function openPdfViewer(entries) {
    const modal = document.getElementById("pdfViewerModal");
    const panesEl = document.getElementById("pdfViewerPanes");
    const titleEl = document.getElementById("pdfViewerTitle");
    const layoutToggle = document.getElementById("pdfViewerLayoutToggle");
    if (!modal || !panesEl) return;

    panesEl.innerHTML = "";
    entries.forEach((entry) => {
      const paths = pdfPathsForFamily(entry.fid);
      const paneEl = document.createElement("div");
      paneEl.className = "pdf-viewer-pane";
      const head = document.createElement("div");
      head.className = "pdf-viewer-pane-head";
      const label = document.createElement("span");
      label.className = "pdf-viewer-pane-family";
      label.textContent = entry.name;
      head.appendChild(label);
      const frame = document.createElement("iframe");
      frame.className = "pdf-viewer-pane-frame";
      frame.title = `${entry.name} reference PDF`;
      if (paths.length > 1) {
        const select = document.createElement("select");
        select.className = "pdf-viewer-pane-select";
        paths.forEach((p) => {
          const opt = document.createElement("option");
          opt.value = p;
          opt.textContent = p.replace(/^references\//, "");
          select.appendChild(opt);
        });
        select.addEventListener("change", () => { frame.src = select.value; });
        head.appendChild(select);
      }
      paneEl.appendChild(head);
      if (paths.length) {
        frame.src = paths[0];
        paneEl.appendChild(frame);
      } else {
        const empty = document.createElement("div");
        empty.className = "pdf-viewer-pane-empty";
        empty.textContent = "No local PDF on file for this family.";
        paneEl.appendChild(empty);
      }
      panesEl.appendChild(paneEl);
    });

    if (titleEl) titleEl.textContent = entries.length > 1 ? `${entries[0].name} ↔ ${entries[1].name}` : entries[0].name;

    if (layoutToggle) {
      if (entries.length > 1) {
        layoutToggle.hidden = false;
        // Default to side-by-side on a landscape screen (room for two panes
        // wide), stacked on portrait -- the button still lets the user
        // switch either way, e.g. to compare two figures that are each
        // wider than they are tall.
        const isLandscape = window.matchMedia("(orientation: landscape)").matches;
        panesEl.classList.toggle("is-stacked", !isLandscape);
        layoutToggle.textContent = panesEl.classList.contains("is-stacked") ? "Side by side" : "Stack";
        layoutToggle.onclick = () => {
          const stacked = panesEl.classList.toggle("is-stacked");
          layoutToggle.textContent = stacked ? "Side by side" : "Stack";
        };
      } else {
        layoutToggle.hidden = true;
        panesEl.classList.remove("is-stacked");
      }
    }

    modal.hidden = false;
    document.body.classList.add("pdf-viewer-open");
  }

  function setupPdfViewer() {
    const modal = document.getElementById("pdfViewerModal");
    if (!modal) return;
    const closeBtn = document.getElementById("pdfViewerClose");
    const backdrop = modal.querySelector(".pdf-viewer-backdrop");
    function close() {
      modal.hidden = true;
      document.body.classList.remove("pdf-viewer-open");
      const panesEl = document.getElementById("pdfViewerPanes");
      // Clearing the panes drops their <iframe>s so a large embedded PDF
      // isn't still rendering/decoded in the background after closing.
      if (panesEl) panesEl.innerHTML = "";
    }
    if (closeBtn) closeBtn.addEventListener("click", close);
    if (backdrop) backdrop.addEventListener("click", close);
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && !modal.hidden) close();
    });
  }

  // Wraps a text display element so hovering a target shows its tip (desktop
  // mouse) and clicking/tapping a target pins that tip in place (needed since
  // touch screens have no hover state at all) until the box itself is
  // clicked/tapped a second time. Shared by every hover-tip display across
  // the Timelines and Genealogy tabs so touch support isn't reimplemented
  // per tab.
  function createPinnableInfoBox(boxEl, baseText) {
    let pinned = false;
    // Pinning a note about a family (or a relation between two families) that
    // has a locally-stored reference PDF adds an "Open PDF" button inside the
    // note -- textContent can't hold an element, so the pinned state renders
    // structured DOM instead of a plain string; the unpinned hover-preview
    // stays plain text like before.
    function show(text, pdfEntries) {
      if (!boxEl) return;
      pinned = true;
      boxEl.textContent = "";
      const span = document.createElement("span");
      span.textContent = `${text}  (tap here to dismiss)`;
      boxEl.appendChild(span);
      if (pdfEntries && pdfEntries.length) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "info-box-pdf-btn";
        btn.textContent = "Open PDF";
        btn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          openPdfViewer(pdfEntries);
        });
        boxEl.appendChild(btn);
      }
      boxEl.classList.add("is-pinned");
    }
    function reset() {
      if (!boxEl) return;
      pinned = false;
      boxEl.textContent = baseText;
      boxEl.classList.remove("is-pinned");
    }
    function attach(el, textOrFn, pdfEntriesOrFn) {
      const getText = typeof textOrFn === "function" ? textOrFn : () => textOrFn;
      const getPdfEntries = typeof pdfEntriesOrFn === "function" ? pdfEntriesOrFn : () => pdfEntriesOrFn;
      el.addEventListener("mouseenter", () => { if (!pinned && boxEl) boxEl.textContent = getText(); });
      el.addEventListener("mouseleave", () => { if (!pinned && boxEl) boxEl.textContent = baseText; });
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        show(getText(), pdfEntriesOrFn ? getPdfEntries() : null);
      });
    }
    if (boxEl) {
      boxEl.addEventListener("click", () => {
        if (pinned) { pinned = false; reset(); }
      });
    }
    return {
      attach,
      reset,
      setBase: (text) => { baseText = text; if (!pinned) reset(); },
      isPinned: () => pinned,
    };
  }

  // Right-click/long-press a family node to filter to it, instead of having
  // to type its name into the search box by hand. Shared by the Timelines
  // dots/labels and both Genealogy layouts. Touch screens have no
  // right-click, so a long-press (default ~550ms, cancelled by scrolling)
  // triggers the same filter; a normal short tap is left alone so it still
  // pins the hover tip via the separate click handler.
  function attachFamilyContextMenu(el, familyName, searchInput, onChange) {
    function trigger() {
      searchInput.value = familyName;
      onChange();
    }
    el.addEventListener("contextmenu", (ev) => {
      ev.preventDefault();
      trigger();
    });

    const LONG_PRESS_MS = 550;
    const MOVE_TOLERANCE_PX = 10;
    let timer = null;
    let longPressed = false;
    let startX = 0;
    let startY = 0;
    el.addEventListener("touchstart", (ev) => {
      if (!ev.touches || ev.touches.length !== 1) return;
      longPressed = false;
      startX = ev.touches[0].clientX;
      startY = ev.touches[0].clientY;
      timer = setTimeout(() => { longPressed = true; trigger(); }, LONG_PRESS_MS);
    }, { passive: true });
    el.addEventListener("touchmove", (ev) => {
      if (!timer || !ev.touches || !ev.touches.length) return;
      const dx = ev.touches[0].clientX - startX;
      const dy = ev.touches[0].clientY - startY;
      if (Math.hypot(dx, dy) > MOVE_TOLERANCE_PX) { clearTimeout(timer); timer = null; }
    }, { passive: true });
    el.addEventListener("touchend", (ev) => {
      if (timer) { clearTimeout(timer); timer = null; }
      // A long-press already triggered the filter above; suppress the
      // synthetic click that would otherwise follow and pin the tooltip too.
      if (longPressed) ev.preventDefault();
    });
  }

  // Shared registry so a view's plot can be asked to re-fit itself to its
  // container. Each view's setup function fills in its own entry (a function
  // taking a `force` boolean) if it has a "fit to container width" concept.
  // Two callers use this:
  //  - the navigator, the first time a view becomes the active tab (force
  //    = false, i.e. only if that view has never successfully fit itself
  //    yet -- a view's very first render happens while its panel is still
  //    display:none, so its container has zero width and any fit attempt
  //    at that point silently no-ops; activating the tab is the first
  //    chance to measure a real width and retry);
  //  - the Fullscreen toggle (force = true, i.e. always re-fit, since the
  //    container size just changed dramatically).
  const viewRefreshHooks = {};
  function triggerViewRefresh(viewName, force) {
    const hook = viewRefreshHooks[viewName];
    if (typeof hook !== "function") return;
    // Wait a couple of frames so the browser has applied the display/layout
    // change before we measure container width/height for re-fitting.
    requestAnimationFrame(() => requestAnimationFrame(() => hook(!!force)));
  }

  function setupNavigator() {
    const tabs = Array.from(document.querySelectorAll(".nav-tab[data-view-target]"));
    const views = Array.from(document.querySelectorAll(".view-panel[data-view]"));
    if (!tabs.length || !views.length) return;

    const burger = document.getElementById("navBurger");
    const navigator_ = document.getElementById("navigator");

    function closeMenu() {
      if (!burger || !navigator_) return;
      navigator_.classList.remove("is-open");
      burger.setAttribute("aria-expanded", "false");
    }

    if (burger && navigator_) {
      burger.addEventListener("click", () => {
        const open = navigator_.classList.toggle("is-open");
        burger.setAttribute("aria-expanded", open ? "true" : "false");
      });
      document.addEventListener("click", (ev) => {
        if (!navigator_.classList.contains("is-open")) return;
        if (navigator_.contains(ev.target) || burger.contains(ev.target)) return;
        closeMenu();
      });
      document.addEventListener("keydown", (ev) => {
        if (ev.key === "Escape") closeMenu();
      });
    }

    function activate(viewName) {
      views.forEach((view) => {
        view.classList.toggle("is-active", view.getAttribute("data-view") === viewName);
      });
      tabs.forEach((tab) => {
        tab.classList.toggle("is-active", tab.getAttribute("data-view-target") === viewName);
      });
      triggerViewRefresh(viewName, false);
    }

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        activate(tab.getAttribute("data-view-target") || "visualizations");
        closeMenu();
      });
    });

    activate("visualizations");
  }

  function setupFullscreenAndFilterToggles() {
    // Entering fullscreen should show only the plot/table -- force the
    // filters closed (if they weren't already) so the user has to
    // deliberately reveal them via the (now floating) Show filters button.
    function forceCollapseFilters(panel) {
      const wrap = panel.querySelector(".view-controls-wrap");
      if (!wrap || wrap.classList.contains("is-collapsed")) return;
      wrap.classList.add("is-collapsed");
      const filtersBtn = panel.querySelector("[data-toggle-filters]");
      if (filtersBtn) filtersBtn.textContent = "Show filters";
    }

    document.querySelectorAll("[data-fullscreen-target]").forEach((btn) => {
      const viewName = btn.getAttribute("data-fullscreen-target");
      const panel = document.querySelector(`.view-panel[data-view="${viewName}"]`);
      if (!panel) return;
      btn.addEventListener("click", () => {
        const isFullscreen = panel.classList.toggle("is-fullscreen");
        document.body.classList.toggle("spdb-fullscreen", isFullscreen);
        btn.textContent = isFullscreen ? "Exit fullscreen" : "Fullscreen";
        if (isFullscreen) forceCollapseFilters(panel);
        triggerViewRefresh(viewName, true);
      });
    });

    document.addEventListener("keydown", (ev) => {
      if (ev.key !== "Escape") return;
      const openPanel = document.querySelector(".view-panel.is-fullscreen");
      if (!openPanel) return;
      const viewName = openPanel.getAttribute("data-view");
      openPanel.classList.remove("is-fullscreen");
      document.body.classList.remove("spdb-fullscreen");
      const btn = document.querySelector(`[data-fullscreen-target="${viewName}"]`);
      if (btn) btn.textContent = "Fullscreen";
      triggerViewRefresh(viewName, true);
    });

    // The fullscreen overlay is sized off window.innerHeight/innerWidth at
    // the moment it's entered (see ensureFit/ensureGenFit); toggling our
    // button never fires a native resize, but the browser's own real
    // fullscreen (F11) or a maximize/monitor change happening *while*
    // already in our overlay does, and nothing was re-fitting the plot to
    // the new size -- the axis/plot stayed stuck at whatever width/height
    // they were last fit to. Re-fit whichever panel is currently fullscreen.
    let fullscreenResizeTimer = null;
    window.addEventListener("resize", () => {
      const openPanel = document.querySelector(".view-panel.is-fullscreen");
      if (!openPanel) return;
      clearTimeout(fullscreenResizeTimer);
      fullscreenResizeTimer = setTimeout(() => {
        triggerViewRefresh(openPanel.getAttribute("data-view"), true);
      }, 120);
    });

    // Dragging the browser window from one monitor to another with a
    // different display scale factor (e.g. a HiDPI laptop panel to a
    // "normal"-DPI wide external monitor) changes window.devicePixelRatio
    // without necessarily changing window.innerWidth/innerHeight -- the OS
    // commonly keeps the window's *logical* (CSS-pixel) size the same
    // across the move, so no `resize` event fires at all, yet the fit-to-
    // width math re-scales against the same numbers while the browser's
    // device-pixel rounding underneath it changed, which is exactly the
    // kind of thing that can knock two independently-set pixel widths out
    // of sync at high zoom multipliers (see the ResizeObserver comment
    // above). There's no native "devicePixelRatio changed" event; the
    // standard workaround is a matchMedia query pinned to the *current*
    // ratio, which stops matching (fires "change") the instant it isn't
    // current anymore -- then re-arm it for whatever the new ratio is.
    function watchDevicePixelRatio(onChange) {
      if (typeof matchMedia !== "function") return;
      function arm() {
        const mql = matchMedia(`(resolution: ${window.devicePixelRatio}dppx)`);
        mql.addEventListener("change", () => { onChange(); arm(); }, { once: true });
      }
      arm();
    }
    watchDevicePixelRatio(() => {
      triggerViewRefresh("visualizations", true);
      triggerViewRefresh("genealogy", true);
    });

    // Declutter toggle: hides every floating button overlaying the plot
    // (zoom controls, Tune Layout, and in fullscreen the Hide filters/
    // Filters on top/Exit fullscreen row) except this toggle itself, since
    // they can cover family labels -- especially Genealogy's layered mode.
    document.querySelectorAll("[data-toggle-frame-controls]").forEach((btn) => {
      const panel = btn.closest(".view-panel");
      if (!panel) return;
      btn.addEventListener("click", () => {
        const hidden = panel.classList.toggle("controls-hidden");
        btn.setAttribute("aria-pressed", String(hidden));
        btn.textContent = hidden ? "Show UI" : "Hide UI";
        btn.title = hidden ? "Show the floating buttons overlaying the plot" : "Hide the floating buttons overlaying the plot";
      });
    });

    document.querySelectorAll("[data-toggle-filters]").forEach((btn) => {
      const key = btn.getAttribute("data-toggle-filters");
      const wrap = document.getElementById(`${key}ControlsWrap`);
      if (!wrap) return;
      btn.addEventListener("click", () => {
        const collapsed = wrap.classList.toggle("is-collapsed");
        btn.textContent = collapsed ? "Show filters" : "Hide filters";
      });
    });

    // "Filters on left" puts the filter sections in a side column next to
    // the plot/graph frame instead of stacked above it -- handy on a
    // landscape screen where width is more available than height. Only
    // wired up for the two tabs that have a plot/graph frame beside their
    // filters (viz, gen); the short key here matches the "{key}ControlsWrap"
    // id convention used above, not the full data-view name.
    const SIDE_LAYOUT_VIEW_NAMES = { viz: "visualizations", gen: "genealogy", qb: "builder" };
    // Default to "Filters on left" on a large landscape screen (e.g. a
    // laptop), where width is more available than height -- narrower or
    // portrait screens (tablet/phone) keep the stacked-on-top default. This
    // only sets the *initial* state; the button below still lets the user
    // override it either way for the rest of the session.
    const isLargeLandscape = !!(window.matchMedia && window.matchMedia("(min-width: 1024px) and (orientation: landscape)").matches);
    document.querySelectorAll("[data-toggle-layout]").forEach((btn) => {
      const key = btn.getAttribute("data-toggle-layout");
      const wrap = document.getElementById(`${key}ControlsWrap`);
      const panel = wrap ? wrap.closest(".view-panel") : null;
      if (!panel) return;
      if (isLargeLandscape) {
        panel.classList.add("is-side-layout");
        btn.textContent = "Filters on top";
        btn.setAttribute("aria-pressed", "true");
      }
      btn.addEventListener("click", () => {
        const isSide = panel.classList.toggle("is-side-layout");
        btn.textContent = isSide ? "Filters on top" : "Filters on left";
        btn.setAttribute("aria-pressed", String(isSide));
        triggerViewRefresh(SIDE_LAYOUT_VIEW_NAMES[key] || key, true);
      });
    });

    // "Collapse all" / "Expand all" toggle every <details class="filter-section">
    // within that tab's own controls wrap at once, on top of each section's
    // own individual <summary> click-to-collapse.
    function wireCollapseAll(selector, open) {
      document.querySelectorAll(selector).forEach((btn) => {
        const key = btn.getAttribute(open ? "data-expand-all" : "data-collapse-all");
        const wrap = document.getElementById(`${key}ControlsWrap`);
        if (!wrap) return;
        btn.addEventListener("click", () => {
          wrap.querySelectorAll(".filter-section").forEach((details) => { details.open = open; });
        });
      });
    }
    wireCollapseAll("[data-collapse-all]", false);
    wireCollapseAll("[data-expand-all]", true);
  }

  // Two-finger pinch support for the plot-scroll containers: maps the
  // change in distance between the two touch points to a multiplicative
  // zoom factor, applied via the same setter each plot's +/- buttons use.
  // preventDefault() on the pinch touchmove stops the browser's own
  // page-zoom gesture from also firing over the plot area.
  function attachPinchZoom(el, getScale, applyScale) {
    if (!el) return;
    let startDist = 0;
    let startScale = 1;
    function touchDist(touches) {
      const [a, b] = touches;
      return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
    }
    // Midpoint between the two fingers, in viewport (client) coordinates --
    // passed through to applyScale as the zoom anchor so pinching zooms
    // into the point between your fingers rather than the corner of the
    // plot.
    function touchMid(touches) {
      const [a, b] = touches;
      return { x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 };
    }
    el.addEventListener("touchstart", (ev) => {
      if (ev.touches.length === 2) {
        startDist = touchDist(ev.touches);
        startScale = getScale();
      }
    }, { passive: true });
    el.addEventListener("touchmove", (ev) => {
      if (ev.touches.length !== 2 || !startDist) return;
      ev.preventDefault();
      const mid = touchMid(ev.touches);
      applyScale(startScale * (touchDist(ev.touches) / startDist), mid.x, mid.y);
    }, { passive: false });
    el.addEventListener("touchend", (ev) => {
      if (ev.touches.length < 2) startDist = 0;
    });
    el.addEventListener("touchcancel", () => { startDist = 0; });
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

  function setupBuilder() {
    const builder = data.joinBuilder;
    const view = createTableView("builderView");

    const ui = {
      referenceKind: document.getElementById("fReferenceKind"),
      referenceYearMin: document.getElementById("fReferenceYearMin"),
      referenceYearMax: document.getElementById("fReferenceYearMax"),
      referenceYearReset: document.getElementById("fReferenceYearReset"),
      referenceYearValue: document.getElementById("fReferenceYearValue"),
      familyName: document.getElementById("fFamilyName"),
      referenceTitle: document.getElementById("fReferenceTitle"),
      componentSearch: document.getElementById("fComponentSearch"),
      roundFlowSearch: document.getElementById("fRoundFlowSearch"),
      hasReferenceLink: document.getElementById("fHasReferenceLink"),
      resetFilters: document.getElementById("resetFilters"),
      columnPicker: document.getElementById("columnPicker"),
      sqlPreview: document.getElementById("sqlPreview"),
    };

    const defaultColumns = [
      "instance.id", "instance.name", "instance.tier", "instance.type_name", "family.name", "reference.title", "reference.year", "reference.url",
    ].filter((c) => builder.columns.includes(c));
    const visibleColumns = new Set(defaultColumns.length ? defaultColumns : builder.columns);

    // Same Fixed-length primitives / Variable-length modes filtering as the
    // Timelines and Genealogy tabs — reused rather than reimplemented so all
    // three tabs share one definition of "type / construction / target /
    // process" filtering and can't drift out of sync.
    const dims = buildDimensionMaps(data.tables);
    const processData = data.processData || {};
    const processList = processData.processes || [];
    const familyProcessMap = processData.familyProcessMap || {};
    const qbFilterPanel = createTierFilterPanel("qb", dims, familyProcessMap, processList, () => refresh());

    // Reference year filter -- a "From year"/"To year" range-slider pair,
    // same control as the Timelines/Genealogy tabs' year filter (see
    // normalizeYearControls() in setupFamilyVisualization), instead of two
    // free-typed number inputs.
    let qbYearsBounds = null;
    function initializeQbYearBounds() {
      if (qbYearsBounds) return qbYearsBounds;
      const validYears = builder.rows
        .map((r) => Number(r["reference.year"]))
        .filter((year) => Number.isFinite(year))
        .sort((a, b) => a - b);
      if (!validYears.length) return null;
      qbYearsBounds = { min: validYears[0], max: validYears[validYears.length - 1] };
      [ui.referenceYearMin, ui.referenceYearMax].forEach((input) => {
        input.min = String(qbYearsBounds.min);
        input.max = String(qbYearsBounds.max);
        input.step = "1";
      });
      ui.referenceYearMin.value = String(qbYearsBounds.min);
      ui.referenceYearMax.value = String(qbYearsBounds.max);
      return qbYearsBounds;
    }
    function normalizeQbYearControls() {
      const bounds = initializeQbYearBounds();
      if (!bounds) {
        if (ui.referenceYearValue) ui.referenceYearValue.textContent = "No years available";
        return null;
      }
      let start = Number(ui.referenceYearMin.value || bounds.min);
      let end = Number(ui.referenceYearMax.value || bounds.max);
      if (start > end) {
        if (document.activeElement === ui.referenceYearMin) { end = start; ui.referenceYearMax.value = String(end); }
        else { start = end; ui.referenceYearMin.value = String(start); }
      }
      if (ui.referenceYearValue) ui.referenceYearValue.textContent = start === end ? `${start}` : `${start} - ${end}`;
      return { start, end };
    }

    function fillFilterOptions() {
      const referenceKinds = Array.from(new Set(builder.rows.map((r) => normalizeValue(r["reference.kind"]).trim()).filter(Boolean))).sort((a, b) => a.localeCompare(b));
      renderFilterChecklist(ui.referenceKind, referenceKinds);
      initializeQbYearBounds();
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

    // How many checkboxes in the reused tier filter panel currently exclude
    // something (tier off, or a dimension with at least one box unchecked).
    // The panel's own state doesn't translate cleanly into flat SQL text (it
    // spans instances, family_targets and family_process_outcomes as well as the two
    // construction tables), so the SQL preview notes how many such filters
    // are active rather than re-deriving them as WHERE clauses.
    function activeTierPanelFilterCount() {
      let count = 0;
      [qbFilterPanel.primitive, qbFilterPanel.mode].forEach((section) => {
        if (section.tierCheckbox && !section.tierCheckbox.checked) count += 1;
        [section.typeSel, section.constructionSel, section.targetSel, section.processSel].forEach((selMap) => {
          if (Array.from(selMap.values()).some((v) => !v)) count += 1;
        });
      });
      return count;
    }

    function buildWhereClauses() {
      const clauses = [];
      const refKindValues = selectedChecklistValues(ui.referenceKind);
      if (refKindValues.size) clauses.push(`"reference.kind" IN (${Array.from(refKindValues).map((v) => `'${v.replace(/'/g, "''")}'`).join(", ")})`);

      const qbYearRange = initializeQbYearBounds() ? { start: Number(ui.referenceYearMin.value), end: Number(ui.referenceYearMax.value) } : null;
      if (qbYearRange && qbYearRange.start !== qbYearsBounds.min) clauses.push(`"reference.year" >= ${qbYearRange.start}`);
      if (qbYearRange && qbYearRange.end !== qbYearsBounds.max) clauses.push(`"reference.year" <= ${qbYearRange.end}`);

      const familyName = (ui.familyName.value || "").trim();
      if (familyName) clauses.push(`"family.name" LIKE '%${familyName.replace(/'/g, "''")}%'`);
      const referenceTitle = (ui.referenceTitle.value || "").trim();
      if (referenceTitle) clauses.push(`"reference.title" LIKE '%${referenceTitle.replace(/'/g, "''")}%'`);
      const componentSearch = (ui.componentSearch.value || "").trim();
      if (componentSearch) {
        const esc = componentSearch.replace(/'/g, "''");
        clauses.push(`("family.component_ids" LIKE '%${esc}%' OR "family.component_names" LIKE '%${esc}%')`);
      }
      const roundFlowSearch = (ui.roundFlowSearch.value || "").trim();
      if (roundFlowSearch) clauses.push(`"family.round_component_flow_signatures" LIKE '%${roundFlowSearch.replace(/'/g, "''")}%'`);
      if (ui.hasReferenceLink.checked) clauses.push(`"reference.url" IS NOT NULL AND TRIM("reference.url") <> ''`);

      return clauses;
    }

    function filterRows(rows) {
      const refKindValues = selectedChecklistValues(ui.referenceKind);
      const ryMin = Number(ui.referenceYearMin.value);
      const ryMax = Number(ui.referenceYearMax.value);
      const familyName = (ui.familyName.value || "").trim().toLowerCase();
      const referenceTitle = (ui.referenceTitle.value || "").trim().toLowerCase();
      const componentSearch = (ui.componentSearch.value || "").trim().toLowerCase();
      const roundFlowSearch = (ui.roundFlowSearch.value || "").trim().toLowerCase();

      return rows.filter((row) => {
        if (!qbFilterPanel.isFamilyVisible(String(row["family.id"] || ""))) return false;
        const refKind = normalizeValue(row["reference.kind"]);
        if (refKindValues.size && !refKindValues.has(refKind)) return false;

        const referenceYear = Number(row["reference.year"]);
        if (Number.isFinite(ryMin) && referenceYear < ryMin) return false;
        if (Number.isFinite(ryMax) && referenceYear > ryMax) return false;

        if (familyName && !normalizeValue(row["family.name"]).toLowerCase().includes(familyName)) return false;
        if (referenceTitle && !normalizeValue(row["reference.title"]).toLowerCase().includes(referenceTitle)) return false;
        if (componentSearch &&
            !normalizeValue(row["family.component_ids"]).toLowerCase().includes(componentSearch) &&
            !normalizeValue(row["family.component_names"]).toLowerCase().includes(componentSearch)) return false;
        if (roundFlowSearch && !normalizeValue(row["family.round_component_flow_signatures"]).toLowerCase().includes(roundFlowSearch)) return false;
        if (ui.hasReferenceLink.checked && !normalizeValue(row["reference.url"]).trim()) return false;
        return true;
      });
    }

    function refresh() {
      normalizeQbYearControls();
      const visible = builder.columns.filter((c) => visibleColumns.has(c));
      const filtered = filterRows(builder.rows);
      renderGrid(view, visible, filtered);
      const whereClauses = buildWhereClauses();
      const selectCols = visible.length ? visible.map((c) => `"${c}"`).join(", ") : "*";
      const whereSql = whereClauses.length ? `\nWHERE ${whereClauses.join("\n  AND ")}` : "";
      const panelFilterCount = activeTierPanelFilterCount();
      const panelNote = panelFilterCount
        ? `\n-- + ${panelFilterCount} Fixed-length/Variable-length filter(s) from the panel above (applied to the table below, not restated as SQL here)`
        : "";
      ui.sqlPreview.textContent = `SELECT ${selectCols}\nFROM (${builder.baseSql})${whereSql};${panelNote}`;
    }

    [ui.referenceYearMin, ui.referenceYearMax, ui.familyName, ui.referenceTitle, ui.componentSearch, ui.roundFlowSearch, ui.hasReferenceLink].forEach((node) => {
      node.addEventListener("change", refresh);
      node.addEventListener("input", refresh);
    });

    ui.referenceKind.addEventListener("change", (event) => {
      const target = event.target;
      if (target && target.matches('input[type="checkbox"][data-value]')) refresh();
    });

    if (ui.referenceYearReset) ui.referenceYearReset.addEventListener("click", () => {
      const bounds = initializeQbYearBounds();
      if (!bounds) return;
      ui.referenceYearMin.value = String(bounds.min);
      ui.referenceYearMax.value = String(bounds.max);
      refresh();
    });

    ui.resetFilters.addEventListener("click", () => {
      Array.from(ui.referenceKind.querySelectorAll('input[type="checkbox"][data-value]')).forEach((box) => {
        box.checked = false;
      });
      const bounds = initializeQbYearBounds();
      if (bounds) {
        ui.referenceYearMin.value = String(bounds.min);
        ui.referenceYearMax.value = String(bounds.max);
      }
      [ui.familyName, ui.referenceTitle, ui.componentSearch, ui.roundFlowSearch].forEach((node) => { node.value = ""; });
      ui.hasReferenceLink.checked = false;
      refresh();
    });

    fillFilterOptions();
    renderColumnPicker();
    refresh();
  }

  // ── Shared primitive/mode dimension model ──────────────────────────────
  // Used identically by the Timelines and Genealogy tabs so both offer the
  // same filtering: a tier toggle (fixed-length primitives / variable-length
  // modes) plus Types / Constructions / Target applications / Processes
  // checklists. "Type" and "Construction" resolve against whichever of the
  // two catalogues (primitive_* or mode_*) matches each family's own tier,
  // merged into one lookup since the id spaces never collide.
  function buildDimensionMaps(tables) {
    const families = (tables.families && tables.families.rows) || [];
    const instances = (tables.instances && tables.instances.rows) || [];
    const primitiveTypes = (tables.primitive_types && tables.primitive_types.rows) || [];
    const modeTypes = (tables.mode_types && tables.mode_types.rows) || [];
    const primitiveFamilyConstructions = (tables.primitive_family_constructions && tables.primitive_family_constructions.rows) || [];
    const modeFamilyConstructions = (tables.mode_family_constructions && tables.mode_family_constructions.rows) || [];
    const familyConstructions = [...primitiveFamilyConstructions, ...modeFamilyConstructions];
    const primitiveConstructions = (tables.primitive_constructions && tables.primitive_constructions.rows) || [];
    const modeConstructions = (tables.mode_constructions && tables.mode_constructions.rows) || [];
    const familyTargets = (tables.family_targets && tables.family_targets.rows) || [];

    const typeNameById = new Map(
      [...primitiveTypes, ...modeTypes].map((r) => [String(r.id), String(r.name)])
    );
    const allConstructionRows = [...primitiveConstructions, ...modeConstructions];
    const constructionNameById = new Map(
      allConstructionRows.map((r) => [String(r.id), String(r.name)])
    );
    // Two-level construction taxonomy: a construction with no special_case_of
    // is a level-1 root (e.g. "feistel"); one with special_case_of set is a
    // level-2 leaf directly under that root (e.g. "balanced_feistel" under
    // "feistel"). The taxonomy is exactly two levels deep (enforced by
    // scripts/validate.py), so this is a flat id -> parent-id lookup, not a
    // general tree.
    const constructionParentById = new Map(
      allConstructionRows
        .filter((r) => r.special_case_of)
        .map((r) => [String(r.id), String(r.special_case_of)])
    );
    const familyTierById = new Map(families.map((r) => [String(r.id), String(r.tier || "")]));

    const familyToTypes = new Map();
    const instanceFamilyById = new Map();
    instances.forEach((row) => {
      const familyId = String(row.family_id || "");
      instanceFamilyById.set(String(row.id), familyId);
      if (!familyId) return;
      if (!familyToTypes.has(familyId)) familyToTypes.set(familyId, new Set());
      const typeId = String(row.type_id || "");
      const typeName = typeNameById.get(typeId) || typeId;
      if (typeName) familyToTypes.get(familyId).add(typeName);
    });

    const familyToConstructions = new Map();
    const familyToConstructionIds = new Map();
    familyConstructions.forEach((row) => {
      const familyId = String(row.family_id || "");
      if (!familyId) return;
      const cid = String(row.construction_id || "");
      if (!cid) return;
      if (!familyToConstructions.has(familyId)) familyToConstructions.set(familyId, new Set());
      const cname = constructionNameById.get(cid) || cid;
      if (cname) familyToConstructions.get(familyId).add(cname);
      if (!familyToConstructionIds.has(familyId)) familyToConstructionIds.set(familyId, new Set());
      familyToConstructionIds.get(familyId).add(cid);
    });

    const familyToTargets = new Map();
    familyTargets.forEach((row) => {
      const familyId = String(row.family_id || "");
      if (!familyId) return;
      if (!familyToTargets.has(familyId)) familyToTargets.set(familyId, new Set());
      const target = String(row.target || "").trim();
      if (target) familyToTargets.get(familyId).add(target);
    });

    return {
      families, instances, typeNameById, constructionNameById, constructionParentById, familyTierById,
      familyToTypes, familyToConstructions, familyToConstructionIds, familyToTargets, instanceFamilyById,
    };
  }

  // Family ids tied to a standard-kind reference, either directly or through
  // one of their instances. There is no dedicated family_standards/
  // instance_standards table (see build_db.py): "standard" is just
  // references.kind, joined against family_references/instance_references
  // here instead of being pre-split into a second table per level.
  function computeStandardFamilyIds(tables, instanceFamilyById) {
    const familyRefs = (tables.family_references && tables.family_references.rows) || [];
    const instanceRefs = (tables.instance_references && tables.instance_references.rows) || [];
    const referenceKindById = new Map(
      ((tables.references && tables.references.rows) || []).map((r) => [String(r.id), String(r.kind || "").toLowerCase()])
    );
    const isStandardRef = (refId) => (referenceKindById.get(String(refId)) || "").includes("standard");

    const standardFamilyIds = new Set();
    familyRefs.forEach((row) => {
      if (isStandardRef(row.reference_id)) standardFamilyIds.add(String(row.family_id));
    });
    instanceRefs.forEach((row) => {
      if (!isStandardRef(row.reference_id)) return;
      const familyId = instanceFamilyById.get(String(row.instance_id));
      if (familyId) standardFamilyIds.add(familyId);
    });
    return standardFamilyIds;
  }

  // Generic checklist-with-All/None-buttons wiring, shared by every filter
  // panel (Types / Constructions / Target applications / Processes) in both
  // the Timelines and Genealogy tabs.
  function buildChecklistFilter(container, selMap, entries, btnAll, btnNone, onChange) {
    if (!container) return;
    const items = entries || Array.from(selMap.keys()).map((k) => ({ key: k, label: k }));
    container.innerHTML = items.map(({ key, label }) => {
      const esc = escapeHtml(label);
      const checked = selMap.get(key) !== false ? " checked" : "";
      return `<label><input type="checkbox" data-value="${escapeHtml(key)}"${checked}/><span>${esc}</span></label>`;
    }).join("");
    container.addEventListener("change", (ev) => {
      const t = ev.target;
      if (t && t.type === "checkbox" && t.dataset.value !== undefined) {
        selMap.set(t.dataset.value, t.checked);
        onChange();
      }
    });
    if (btnAll) btnAll.addEventListener("click", () => {
      items.forEach(({ key }) => selMap.set(key, true));
      Array.from(container.querySelectorAll("input[type=checkbox]")).forEach((c) => { c.checked = true; });
      onChange();
    });
    if (btnNone) btnNone.addEventListener("click", () => {
      items.forEach(({ key }) => selMap.set(key, false));
      Array.from(container.querySelectorAll("input[type=checkbox]")).forEach((c) => { c.checked = false; });
      onChange();
    });
  }

  // True if a family's value-set for one dimension clears that dimension's
  // filter. If nothing at all is checked, the dimension is treated as
  // disabled (shows everything) rather than hiding everything, matching the
  // existing genealogy filter behavior this generalizes from. A family with
  // no tagged value in this dimension always passes (untagged values aren't
  // forced through a checkbox).
  function passesDimensionFilter(selMap, valueSet) {
    const anyChecked = Array.from(selMap.values()).some((v) => v);
    if (!anyChecked) return true;
    if (!valueSet || !valueSet.size) return true;
    return Array.from(valueSet).some((v) => selMap.get(v) !== false);
  }

  // Generates the markup for one two-section (Primitives/Modes) filter panel,
  // parameterized by prefix so the same HTML (and the same element ids that
  // createTierSection/createTierFilterPanel expect) can be produced for every
  // tab that offers this filtering, instead of hand-duplicating the block in
  // index.html.tmpl once per tab.
  function renderTierFilterPanelMarkup(prefix) {
    function dimensionPanel(idPrefix, label) {
      return `
            <details class="collapsible gen-filter-panel">
              <summary>${label}</summary>
              <div class="collapsible-body">
                <div class="viz-filter-actions">
                  <button id="${idPrefix}All" type="button">All</button>
                  <button id="${idPrefix}None" type="button">None</button>
                </div>
                <div id="${idPrefix}Filters" class="filter-checklist viz-filter-checklist"></div>
              </div>
            </details>`;
    }

    // Constructions get a two-level panel (level-1 root header, level-2 leaf
    // checkboxes underneath, mirroring the Genealogy tab's relation-group
    // filter) instead of the flat single-list markup every other dimension
    // uses -- the group sections themselves are generated by JS
    // (createTierSection's refreshConstructionGroups), so this only needs an
    // empty mount point.
    function constructionDimensionPanel(idPrefix, label) {
      return `
            <details class="collapsible gen-filter-panel">
              <summary>${label}</summary>
              <div class="collapsible-body">
                <div class="viz-filter-actions">
                  <button id="${idPrefix}All" type="button">All</button>
                  <button id="${idPrefix}None" type="button">None</button>
                </div>
                <div id="${idPrefix}Groups"></div>
              </div>
            </details>`;
    }

    function tierSection(tierKey, label) {
      const p = `${prefix}${tierKey}`;
      return `
        <div class="tier-section">
          <label class="inline-check tier-section-toggle"><input id="${prefix}Filter${tierKey}s" type="checkbox" checked /> <strong>${label}</strong></label>
          <div class="gen-filters-row">${dimensionPanel(`${p}Type`, "Types")}${constructionDimensionPanel(`${p}Construction`, "Constructions")}${dimensionPanel(`${p}Target`, "Target applications")}${dimensionPanel(`${p}Process`, "Processes")}
          </div>
        </div>`;
    }

    // Top-level All/None spanning every dimension in both tiers at once,
    // wired up in createTierFilterPanel (mirrors the per-panel and per-group
    // All/None buttons, but at the whole-"Family filters"-section level).
    const familyActions = `
      <div class="viz-filter-actions">
        <button id="${prefix}FamilyAll" type="button">All</button>
        <button id="${prefix}FamilyNone" type="button">None</button>
      </div>`;

    return familyActions + tierSection("Primitive", "Fixed-length primitives") + tierSection("Mode", "Variable-length modes");
  }

  // Builds the tier + 4-dimension filter panel for one tab (prefix "viz" or
  // "gen"). Both tabs call this with their own DOM ids but identical
  // semantics, per-dimension state, and All/None wiring.
  // One tier's worth of filtering: its own "include this tier" checkbox plus
  // Types / Constructions / Target applications / Processes checklists, each
  // scoped to families of that tier only (e.g. the primitives section never
  // shows a mode's AEAD/hash type or its sponge/duplex construction).
  function createTierSection(prefix, tierKey, dims, familyProcessMap, processList, onChange) {
    const el = (suffix) => document.getElementById(`${prefix}${tierKey}${suffix}`);
    const tierCheckbox = document.getElementById(`${prefix}Filter${tierKey}s`);
    const typeSel = new Map();
    const constructionSel = new Map();
    const targetSel = new Map();
    const processSel = new Map();
    const tierValue = tierKey === "Primitive" ? "primitive" : "mode";

    function familyIdsOfTier() {
      const out = [];
      dims.familyTierById.forEach((tier, fid) => { if (tier === tierValue) out.push(fid); });
      return out;
    }

    function collectValues(dimMap) {
      const values = new Set();
      familyIdsOfTier().forEach((fid) => {
        (dimMap.get(fid) || new Set()).forEach((v) => values.add(v));
      });
      return Array.from(values).sort((a, b) => a.localeCompare(b));
    }

    // Groups the construction ids actually used by this tier's families into
    // a two-level structure: one group per level-1 root that has at least
    // one used leaf or is itself directly used, each group listing its used
    // leaves (plus the root itself, labeled "general/unspecified", if any
    // family is tagged with just the root and no more specific leaf).
    function buildConstructionGroups() {
      const usedIds = collectValues(dims.familyToConstructionIds);
      const usedSet = new Set(usedIds);
      const rootToLeaves = new Map();
      usedIds.forEach((cid) => {
        const parent = dims.constructionParentById.get(cid);
        const rootId = parent || cid;
        if (!rootToLeaves.has(rootId)) rootToLeaves.set(rootId, new Set());
        if (parent) rootToLeaves.get(rootId).add(cid);
      });
      const nameOf = (cid) => dims.constructionNameById.get(cid) || cid;
      return Array.from(rootToLeaves.keys())
        .sort((a, b) => nameOf(a).localeCompare(nameOf(b)))
        .map((rootId) => {
          const members = [];
          if (usedSet.has(rootId)) members.push({ key: rootId, label: `${nameOf(rootId)} (general/unspecified)` });
          Array.from(rootToLeaves.get(rootId))
            .sort((a, b) => nameOf(a).localeCompare(nameOf(b)))
            .forEach((leafId) => members.push({ key: leafId, label: nameOf(leafId) }));
          return { id: rootId, label: nameOf(rootId), members };
        })
        .filter((g) => g.members.length);
    }

    // Each level-1 root gets its own nested collapsible (matching the outer
    // "Types"/"Constructions"/... panels' own collapse-triangle style)
    // instead of a checkbox: an include/exclude master toggle would just
    // duplicate what "None" (clear every member below) and "All" (check
    // every member) already do to the same per-member constructionSel map,
    // so there's no separate on/off state to track here.
    function refreshConstructionGroups() {
      const groups = buildConstructionGroups();
      const container = el("ConstructionGroups");
      if (container) {
        container.innerHTML = groups.map((g, i) => `
          <details class="collapsible filter-group" open>
            <summary>${escapeHtml(g.label)}</summary>
            <div class="collapsible-body">
              <div class="viz-filter-actions">
                <button id="${prefix}${tierKey}ConstrGroup${i}All" type="button">All</button>
                <button id="${prefix}${tierKey}ConstrGroup${i}None" type="button">None</button>
                <button id="${prefix}${tierKey}ConstrGroup${i}Only" type="button">Only</button>
              </div>
              <div id="${prefix}${tierKey}ConstrGroup${i}Filters" class="filter-checklist viz-filter-checklist"></div>
            </div>
          </details>`).join("");
      }
      groups.forEach((g, i) => {
        g.members.forEach((m) => { if (!constructionSel.has(m.key)) constructionSel.set(m.key, true); });
        buildChecklistFilter(
          document.getElementById(`${prefix}${tierKey}ConstrGroup${i}Filters`), constructionSel,
          g.members,
          document.getElementById(`${prefix}${tierKey}ConstrGroup${i}All`),
          document.getElementById(`${prefix}${tierKey}ConstrGroup${i}None`),
          onChange,
        );
        // "Only": select every member of this group and clear every member
        // of every other group in one click, e.g. isolate ARX-PN alone.
        const onlyBtn = document.getElementById(`${prefix}${tierKey}ConstrGroup${i}Only`);
        if (onlyBtn) onlyBtn.addEventListener("click", () => {
          groups.forEach((g2) => {
            g2.members.forEach((m2) => constructionSel.set(m2.key, g2.id === g.id));
          });
          if (container) {
            container.querySelectorAll("input[type=checkbox]").forEach((c) => {
              c.checked = constructionSel.get(c.dataset.value) !== false;
            });
          }
          onChange();
        });
      });

      // Top-level All/None spanning every group, mirroring the Types/Target
      // applications/Processes panels' own top-level buttons -- the per-group
      // All/None/Only buttons above only ever touch one group's members.
      const allBtn = el("ConstructionAll");
      const noneBtn = el("ConstructionNone");
      if (allBtn) allBtn.addEventListener("click", () => {
        groups.forEach((g) => g.members.forEach((m) => constructionSel.set(m.key, true)));
        if (container) container.querySelectorAll("input[type=checkbox]").forEach((c) => { c.checked = true; });
        onChange();
      });
      if (noneBtn) noneBtn.addEventListener("click", () => {
        groups.forEach((g) => g.members.forEach((m) => constructionSel.set(m.key, false)));
        if (container) container.querySelectorAll("input[type=checkbox]").forEach((c) => { c.checked = false; });
        onChange();
      });
    }

    function passesConstructionFilter(fid) {
      const idSet = dims.familyToConstructionIds.get(fid);
      if (!idSet || !idSet.size) return true;
      const anyChecked = Array.from(constructionSel.values()).some((v) => v);
      if (!anyChecked) return true;
      return Array.from(idSet).some((cid) => constructionSel.get(cid) !== false);
    }

    function refreshChecklist() {
      const typeValues = collectValues(dims.familyToTypes);
      const targetValues = collectValues(dims.familyToTargets);
      typeValues.forEach((v) => { if (!typeSel.has(v)) typeSel.set(v, true); });
      targetValues.forEach((v) => { if (!targetSel.has(v)) targetSel.set(v, true); });
      refreshConstructionGroups();

      const relevantProcessIds = new Set();
      familyIdsOfTier().forEach((fid) => {
        const pid = familyProcessMap[fid];
        if (pid) relevantProcessIds.add(pid);
      });
      const processEntries = [
        ...processList.filter((p) => relevantProcessIds.has(String(p.id))).map((p) => ({ key: String(p.id), label: String(p.name) })),
        { key: "__none__", label: "No process" },
      ];
      processEntries.forEach(({ key }) => { if (!processSel.has(key)) processSel.set(key, true); });

      buildChecklistFilter(el("TypeFilters"), typeSel,
        typeValues.map((v) => ({ key: v, label: v })), el("TypeAll"), el("TypeNone"), onChange);
      buildChecklistFilter(el("TargetFilters"), targetSel,
        targetValues.map((v) => ({ key: v, label: v })), el("TargetAll"), el("TargetNone"), onChange);
      buildChecklistFilter(el("ProcessFilters"), processSel, processEntries, el("ProcessAll"), el("ProcessNone"), onChange);
    }

    function isVisible(fid) {
      if (tierCheckbox && !tierCheckbox.checked) return false;
      if (!passesDimensionFilter(typeSel, dims.familyToTypes.get(fid))) return false;
      if (!passesConstructionFilter(fid)) return false;
      if (!passesDimensionFilter(targetSel, dims.familyToTargets.get(fid))) return false;
      const anyProc = Array.from(processSel.values()).some((v) => v);
      if (anyProc) {
        const pid = familyProcessMap[fid] || "__none__";
        if (processSel.get(pid) === false) return false;
      }
      return true;
    }

    refreshChecklist();
    return { isVisible, refreshChecklist, typeSel, constructionSel, targetSel, processSel, tierCheckbox };
  }

  // Builds the full two-section (Primitives / Modes) filter panel for one tab
  // (prefix "viz", "gen", or "qb"). Every tab that wants this filtering calls
  // this with its own prefix but identical semantics and markup, so they
  // can't drift out of sync and the HTML never needs hand-duplicating: this
  // renders into "<prefix>TierFilterPanel" itself before wiring it up.
  function createTierFilterPanel(prefix, dims, familyProcessMap, processList, onChange) {
    const container = document.getElementById(`${prefix}TierFilterPanel`);
    if (container) container.innerHTML = renderTierFilterPanelMarkup(prefix);

    const primitiveSection = createTierSection(prefix, "Primitive", dims, familyProcessMap, processList, onChange);
    const modeSection = createTierSection(prefix, "Mode", dims, familyProcessMap, processList, onChange);

    if (primitiveSection.tierCheckbox) primitiveSection.tierCheckbox.addEventListener("change", onChange);
    if (modeSection.tierCheckbox) modeSection.tierCheckbox.addEventListener("change", onChange);

    // Top-level All/None: every Type/Construction/Target/Process checkbox in
    // both tiers, plus the "Fixed-length primitives"/"Variable-length modes"
    // tier toggles themselves, so All/None puts every family filter back to
    // a single known state in one click.
    function setEveryDimension(value) {
      [primitiveSection, modeSection].forEach((section) => {
        [section.typeSel, section.constructionSel, section.targetSel, section.processSel].forEach((selMap) => {
          Array.from(selMap.keys()).forEach((k) => selMap.set(k, value));
        });
        if (section.tierCheckbox) section.tierCheckbox.checked = value;
      });
      if (container) {
        container.querySelectorAll("input[type=checkbox][data-value]").forEach((c) => { c.checked = value; });
      }
      onChange();
    }
    const familyAllBtn = document.getElementById(`${prefix}FamilyAll`);
    const familyNoneBtn = document.getElementById(`${prefix}FamilyNone`);
    if (familyAllBtn) familyAllBtn.addEventListener("click", () => setEveryDimension(true));
    if (familyNoneBtn) familyNoneBtn.addEventListener("click", () => setEveryDimension(false));

    function isFamilyVisible(fid) {
      const tier = dims.familyTierById.get(fid) || "";
      if (tier === "primitive") return primitiveSection.isVisible(fid);
      if (tier === "mode") return modeSection.isVisible(fid);
      return true;
    }

    // A legend/coloring value (a type name, construction name, or process id)
    // only ever lives in one tier's own catalogue, so check whichever
    // section's map actually has that key rather than assuming a tier.
    function isValueChecked(dimension, key) {
      const sectionMap = { type: "typeSel", construction: "constructionSel", target: "targetSel", process: "processSel" }[dimension];
      if (primitiveSection[sectionMap].has(key)) return primitiveSection[sectionMap].get(key) !== false;
      if (modeSection[sectionMap].has(key)) return modeSection[sectionMap].get(key) !== false;
      return true;
    }

    return {
      isFamilyVisible,
      isValueChecked,
      primitive: primitiveSection,
      mode: modeSection,
    };
  }

  // Builds the "Relations shown in genealogy" filter panel: one nested
  // collapsible per relation group (design/usage/process, see RELATION_GROUPS
  // in setupGenealogy) with All/None/Only buttons and a checklist of the
  // individual relation tags inside it, mirroring the filter-group
  // pattern used for Types/Constructions/Targets/Processes -- no separate
  // group-level toggle, since "None" already clears every member the toggle
  // would have gated.
  // groups: [{ id, label, members: [relationKey, ...], synthetic? }]
  // edgeRelationKeys(edge): Set of relation keys (raw tags plus any synthetic
  // ones such as "__usage_core__") that apply to that influence edge.
  function createRelationFilterPanel(groups, edgeRelationKeys, onChange) {
    const container = document.getElementById("genRelationFilterPanel");
    const RELATION_LABELS = { __usage_core__: "(implied: mode/primitive built directly on the other)" };
    const relLabel = (key) => RELATION_LABELS[key] || key.replace(/_/g, " ");

    if (container) {
      const topActions = `
        <div class="viz-filter-actions">
          <button id="genRelationAll" type="button">All</button>
          <button id="genRelationNone" type="button">None</button>
        </div>`;
      container.innerHTML = topActions + groups.map((g, i) => `
        <details class="collapsible filter-group" open>
          <summary>${escapeHtml(g.label)}</summary>
          <div class="collapsible-body">
            <div class="viz-filter-actions">
              <button id="genRelGroup${i}All" type="button">All</button>
              <button id="genRelGroup${i}None" type="button">None</button>
              <button id="genRelGroup${i}Only" type="button">Only</button>
            </div>
            <div id="genRelGroup${i}Filters" class="filter-checklist viz-filter-checklist"></div>
          </div>
        </details>`).join("");
    }

    const relSel = new Map();
    groups.forEach((g, i) => {
      g.members.forEach((m) => { if (!relSel.has(m)) relSel.set(m, true); });
      buildChecklistFilter(
        document.getElementById(`genRelGroup${i}Filters`), relSel,
        g.members.map((m) => ({ key: m, label: relLabel(m) })),
        document.getElementById(`genRelGroup${i}All`), document.getElementById(`genRelGroup${i}None`),
        onChange,
      );
      // "Only": select every member of this group and clear every member of
      // every other group in one click.
      const onlyBtn = document.getElementById(`genRelGroup${i}Only`);
      if (onlyBtn) onlyBtn.addEventListener("click", () => {
        groups.forEach((g2) => {
          g2.members.forEach((m2) => relSel.set(m2, g2.id === g.id));
        });
        if (container) {
          container.querySelectorAll("input[type=checkbox]").forEach((c) => {
            c.checked = relSel.get(c.dataset.value) !== false;
          });
        }
        onChange();
      });
    });

    // Top-level All/None spanning every group at once, mirroring the same
    // pattern added to the Constructions and Family filters panels.
    const relAllBtn = document.getElementById("genRelationAll");
    const relNoneBtn = document.getElementById("genRelationNone");
    if (relAllBtn) relAllBtn.addEventListener("click", () => {
      groups.forEach((g) => g.members.forEach((m) => relSel.set(m, true)));
      if (container) container.querySelectorAll("input[type=checkbox]").forEach((c) => { c.checked = true; });
      onChange();
    });
    if (relNoneBtn) relNoneBtn.addEventListener("click", () => {
      groups.forEach((g) => g.members.forEach((m) => relSel.set(m, false)));
      if (container) container.querySelectorAll("input[type=checkbox]").forEach((c) => { c.checked = false; });
      onChange();
    });

    function isEdgeVisible(edge) {
      const keys = Array.from(edgeRelationKeys(edge));
      if (!keys.length) return true;
      const anyChecked = Array.from(relSel.values()).some((v) => v);
      if (!anyChecked) return true;
      return keys.some((k) => relSel.get(k) !== false);
    }

    return { isEdgeVisible };
  }

  function setupFamilyVisualization() {
    const plotSvg = document.getElementById("familyVizPlot");
    const xAxisSvg = document.getElementById("familyVizXAxis");
    const yAxisSvg = document.getElementById("familyVizYAxis");
    const plotScroll = document.getElementById("vizPlotScroll");
    const xAxisTrack = document.getElementById("vizXAxisTrack");
    const xAxisPane = xAxisTrack ? xAxisTrack.parentElement : null;
    const yAxisTrack = document.getElementById("vizYAxisTrack");
    const cornerPane = document.getElementById("vizCornerPane");
    const processLegend = document.getElementById("vizProcessLegend");
    const groupBy = document.getElementById("vizGroupBy");
    const hideDots = document.getElementById("vizHideDots");
    const nameModeOff = document.getElementById("vizNameOff");
    const nameModeClip = document.getElementById("vizNameClip");
    const nameModeWrap = document.getElementById("vizNameWrap");
    const nameModeFull = document.getElementById("vizNameFull");
    const familyCountBadge = document.getElementById("vizFamilyCount");
    let nameMode = "clip";
    const colorByProcess = document.getElementById("vizColorByProcess");
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
    const familySearchExact = document.getElementById("vizFamilySearchExact");
    const vizFrame = document.getElementById("vizFrame");
    const collapseGroups = document.getElementById("vizCollapseGroups");
    const collapseCount = document.getElementById("vizCollapseCount");
    const yearStart = document.getElementById("vizYearStart");
    const yearEnd = document.getElementById("vizYearEnd");
    const yearReset = document.getElementById("vizYearReset");
    const yearRangeValue = document.getElementById("vizYearRangeValue");
    const relationInfoBox = document.getElementById("vizRelationInfo");
    if (!plotSvg || !xAxisSvg || !yAxisSvg || !plotScroll || !xAxisTrack || !xAxisPane || !yAxisTrack || !cornerPane || !vizFrame || !groupBy || !hideDots || !nameModeOff || !nameModeClip || !nameModeWrap || !nameModeFull || !colorByProcess || !processLegend || !fontMinus || !fontPlus || !fontReset || !fontValue || !zoomOut || !zoomIn || !zoomReset || !zoomFit || !zoomValue || !colMinus || !colPlus || !colReset || !colSpacingValue || !familySearch || !collapseGroups || !collapseCount || !yearStart || !yearEnd || !yearReset || !yearRangeValue || !relationInfoBox) return;

    // *** The actual root cause of the axis-misalignment bug ***
    // xAxisSvg's height (AXIS_HEIGHT) never scales with zoom while its width
    // does, and yAxisSvg's width (LEFT_AXIS_WIDTH) never scales while its
    // height does -- so at any zoom level other than 1x, each one's CSS box
    // has a *different aspect ratio than its own viewBox*. SVG's default
    // preserveAspectRatio ("xMidYMid meet") reacts to that by uniformly
    // scaling to whichever axis needs the *smaller* scale factor (to avoid
    // cropping) and letterboxing/centering the rest -- confirmed directly
    // via getScreenCTM(): at a large fit-to-width zoom multiplier (reachable
    // on a very wide monitor, matched here with a 3200px-wide viewport),
    // xAxisSvg's actual on-screen scale came out to exactly 1.0 (its height
    // constraint, since AXIS_HEIGHT never changes) while plotSvg's was the
    // intended ~1.34x -- the ticks were being rendered at a *different,
    // smaller scale* than the gridlines, compressed and centered inside the
    // wider box instead of stretched to fill it. plotSvg itself doesn't
    // show this (both its dimensions scale together, so its aspect ratio
    // matches its viewBox at any zoom), which is why only the axes drifted.
    // "none" instead stretches non-uniformly to exactly fill the CSS box on
    // both axes, which is what every other part of this code already
    // assumes happens.
    [plotSvg, xAxisSvg, yAxisSvg].forEach((svg) => svg.setAttribute("preserveAspectRatio", "none"));

    // Safety net on top of applyZoom() setting both SVGs' width from the same
    // expression: whatever the actual cause of a divergence turns out to be
    // (a container-specific scrollbar reducing one pane's available width
    // but not the other's, a layout recalculation neither resize listener
    // nor fit-to-container call happens to run for, ...), mirroring
    // xAxisSvg's width directly off of plotSvg guarantees they can never
    // visibly disagree, without having to keep chasing every possible root
    // cause individually. Deliberately copies plotSvg.style.width (the exact
    // CSS text applyZoom() already set) rather than re-measuring via
    // getBoundingClientRect(): the latter returns layout-precision
    // (sub-pixel) floats that can differ by a fraction of a CSS pixel from
    // what was actually *set*, once ancestor grid-track distribution and
    // device-pixel-ratio rounding are involved -- copying the two elements
    // to a *different* value than each other, which at extreme zoom (a very
    // wide monitor's fit-to-width can be a large multiplier) gets visibly
    // amplified toward the right edge. Copying the exact string sidesteps
    // that arithmetic entirely.
    if (typeof ResizeObserver !== "undefined") {
      const axisWidthSync = new ResizeObserver(() => {
        if (plotSvg.style.width) xAxisSvg.style.width = plotSvg.style.width;
      });
      axisWidthSync.observe(plotSvg);
    }

    const BASE_FONT = 12;
    const BASE_ZOOM = 1;
    const BASE_COL_BONUS = 0;
    const COL_STEP = 8;
    // Low enough that "Fit" can always shrink the plot to the container width
    // on a narrow/mobile screen, even at the cost of unreadable labels -- the
    // user can always zoom back in afterwards.
    const MIN_ZOOM = 0.05;
    const MAX_ZOOM = 4;
    const ZOOM_FACTOR = 1.2;
    const LEFT_AXIS_WIDTH = 100;
    const AXIS_HEIGHT = 48;

    // ── Layout tuning parameters (user-adjustable, persisted) ───────────
    // Mirrors the Genealogy tab's floating "Tune layout" panel: row/group
    // spacing that used to be hardcoded is exposed as sliders so a crowded
    // or overly sparse plot can be retuned live instead of filing a request.
    const VIZ_LAYOUT_PARAMS_KEY = "spdb_viz_layout_params_v1";
    const DEFAULT_VIZ_LAYOUT_PARAMS = {
      stackStep: 0.34,     // vertical spacing between stacked points within a row (lane-step units)
      groupGapUnits: 0.42, // extra vertical gap inserted between groups/rows (lane-step units)
    };
    function loadVizLayoutParams() {
      const out = { ...DEFAULT_VIZ_LAYOUT_PARAMS };
      try {
        const raw = JSON.parse(localStorage.getItem(VIZ_LAYOUT_PARAMS_KEY) || "{}");
        Object.keys(DEFAULT_VIZ_LAYOUT_PARAMS).forEach((k) => {
          const v = Number(raw[k]);
          if (Number.isFinite(v)) out[k] = v;
        });
      } catch { /* corrupt/unavailable storage falls back to defaults */ }
      return out;
    }
    let vizLayoutParams = loadVizLayoutParams();
    function saveVizLayoutParams() {
      try { localStorage.setItem(VIZ_LAYOUT_PARAMS_KEY, JSON.stringify(vizLayoutParams)); } catch { /* storage unavailable (e.g. private mode) -- tuning still works, just doesn't persist */ }
    }
    const POINT_RADIUS = 4.25;
    const BASE_RELATION_TEXT = "Hover or tap a family dot/label or a relation arrow to see details. Use the zoom controls or Cmd/Ctrl + wheel inside the plot to adjust scale.";
    const relationTip = createPinnableInfoBox(relationInfoBox, BASE_RELATION_TEXT);
    let fontPx = BASE_FONT;
    let zoomScale = BASE_ZOOM;
    let colSpacingBonus = BASE_COL_BONUS;
    let hasAutoFit = false;
    let lastRenderSize = { plotWidth: 920, plotHeight: 640 };
    let yearsBounds = null;
    let suppressYearRender = false;

    const tables = data.tables || {};

    const dims = buildDimensionMaps(tables);
    const families = dims.families;
    const familyById = new Map(families.map((row) => [String(row.id), row]));
    const standardFamilyIds = computeStandardFamilyIds(tables, dims.instanceFamilyById);
    const familyToTypes = dims.familyToTypes;
    const familyToConstructions = dims.familyToConstructions;
    const familyToTargets = dims.familyToTargets;

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

    const filterPanel = createTierFilterPanel("viz", dims, familyProcessMap, processList, () => render());

    function clearNode(node) {
      while (node.firstChild) node.removeChild(node.firstChild);
    }

    function groupsForFamily(familyId, mode) {
      if (mode === "none") return ["All families"];
      if (mode === "type") {
        const values = Array.from(familyToTypes.get(familyId) || []);
        return values.length ? values.sort((a, b) => a.localeCompare(b)) : ["No type tagged"];
      }
      if (mode === "construction") {
        const values = Array.from(familyToConstructions.get(familyId) || []);
        return values.length ? values.sort((a, b) => a.localeCompare(b)) : ["No construction tagged"];
      }
      if (mode === "process") {
        const name = processNameForFamily(familyId);
        return [name || "No process"];
      }
      const values = Array.from(familyToTargets.get(familyId) || []);
      return values.length ? values.sort((a, b) => a.localeCompare(b)) : ["Unspecified target"];
    }

    function modePalette(mode) {
      if (mode === "construction") return ["rgba(248, 240, 224, 0.92)", "rgba(252, 247, 238, 0.98)"];
      if (mode === "target") return ["rgba(232, 243, 234, 0.92)", "rgba(246, 251, 247, 0.98)"];
      if (mode === "process") return ["rgba(240, 232, 248, 0.92)", "rgba(249, 246, 252, 0.98)"];
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

    function syncAxisTracks() {
      yAxisTrack.style.transform = `translateY(${-plotScroll.scrollTop}px)`;
      // Deliberately native scrollLeft, not a CSS transform: plotSvg's own
      // horizontal position moves via the browser's native scrolling, and a
      // separate translateX() applied to the axis track is a *different*
      // code path that isn't guaranteed to round sub-pixel/device-pixel
      // positions identically to native scrolling on every browser/display
      // combination -- exactly the kind of thing that could drift out of
      // sync at high zoom on a high- or mixed-DPI display without ever
      // showing up in a same-DPI, low-zoom test. Setting scrollLeft on the
      // (overflow:hidden, so no visible scrollbar or user-drag) axis pane
      // itself keeps both elements on the *same* native scroll-positioning
      // pipeline, which can't disagree with itself.
      xAxisPane.scrollLeft = plotScroll.scrollLeft;
    }

    function clampZoom(nextZoom) {
      return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, nextZoom));
    }

    function applyZoom() {
      const scaledH = Math.round(lastRenderSize.plotHeight * zoomScale);
      const isFullscreen = document.body.classList.contains("spdb-fullscreen");
      const maxFrameH = Math.round(window.innerHeight * (isFullscreen ? 0.97 : 0.68));
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

    // Zooms while keeping a chosen anchor point visually fixed on screen
    // (defaults to the center of the currently visible scroll viewport, so
    // the +/- buttons zoom "into the middle of what you're looking at"
    // rather than growing from the top-left corner; pinch and Cmd/Ctrl+wheel
    // pass their own anchor -- the pinch midpoint / cursor position).
    function setZoom(nextZoom, anchorClientX, anchorClientY) {
      const rect = plotScroll.getBoundingClientRect();
      const ax = anchorClientX ?? (rect.left + rect.width / 2);
      const ay = anchorClientY ?? (rect.top + rect.height / 2);
      const oldScale = zoomScale;
      const contentX = (plotScroll.scrollLeft + (ax - rect.left)) / oldScale;
      const contentY = (plotScroll.scrollTop + (ay - rect.top)) / oldScale;
      zoomScale = clampZoom(nextZoom);
      applyZoom();
      plotScroll.scrollLeft = contentX * zoomScale - (ax - rect.left);
      plotScroll.scrollTop = contentY * zoomScale - (ay - rect.top);
      syncAxisTracks();
    }

    function fitZoom() {
      // Zero-width container means the panel is currently hidden (e.g. the
      // very first render happens before the user has switched to this
      // tab) -- there's nothing sensible to fit to yet, so report failure
      // rather than zooming to (near) zero.
      // Deliberately uses offsetWidth, not clientWidth: plotScroll is the
      // only one of the two synced panes that scrolls vertically, so on a
      // browser with classic (space-reserving, not overlay) scrollbars, a
      // tall plot gives it a vertical scrollbar that shrinks clientWidth
      // below the x-axis pane's -- fitting to that narrower width left the
      // axis visibly short of the plot's actual right edge. offsetWidth
      // (the grid column's full width, not reduced by this element's own
      // scrollbar) is shared by both panes, so plot and axis always agree.
      if (!plotScroll.offsetWidth || !lastRenderSize.plotWidth) return false;
      const fitWidth = Math.max(240, plotScroll.offsetWidth - 8);
      // Deliberately bypasses clampZoom()/MIN_ZOOM: "Fit" must always be
      // able to shrink all the way down to the container's actual width,
      // even for a very wide plot on a narrow screen, so the user can see
      // the whole thing at once -- labels becoming unreadably small is an
      // acceptable trade-off they can undo with the +/- buttons.
      zoomScale = fitWidth / lastRenderSize.plotWidth;
      applyZoom();
      return true;
    }

    // Fits the plot to its container the first time that's actually
    // possible (container visible with a real width), then leaves the
    // user's zoom alone on subsequent calls unless force is set (used when
    // the container just changed size dramatically, e.g. entering/exiting
    // fullscreen).
    function ensureFit(force) {
      if (force || !hasAutoFit) {
        if (fitZoom()) { hasAutoFit = true; return; }
      }
      applyZoom();
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

    function renderEmptyState(message) {
      clearNode(plotSvg);
      clearNode(xAxisSvg);
      clearNode(yAxisSvg);
      relationInfoBox.hidden = false;
      relationTip.reset();
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
      relationInfoBox.hidden = false;
      relationTip.reset();
      const mode = groupBy.value;
      cornerPane.innerHTML = `<b>${escapeHtml(modeLabel(mode))}</b><span style="font-weight:400;opacity:0.75">Publication year</span>`;
      const rawPoints = [];
      const yearRange = normalizeYearControls();
      const searchNeedle = familySearch.value.trim();

      families.forEach((family) => {
        const year = Number(family.year);
        if (!Number.isFinite(year)) return;
        if (yearRange && (year < yearRange.start || year > yearRange.end)) return;
        const familyId = String(family.id || "");
        if (!familyId) return;
        if (!filterPanel.isFamilyVisible(familyId)) return;
        const familyName = String(family.name || familyId);
        if (!familyNameMatches(familyName, searchNeedle, !!(familySearchExact && familySearchExact.checked))) return;
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
        if (familyCountBadge) familyCountBadge.textContent = "0 families shown";
        if (searchNeedle) {
          renderEmptyState("No families match the current name search, filters, and year range.");
        } else {
          renderEmptyState("No families match the current filters. Enable more tiers/types/constructions to see data.");
        }
        return;
      }

      const points = rawPoints;
      points.sort((a, b) => a.group.localeCompare(b.group) || a.year - b.year || a.name.localeCompare(b.name));
      const groupLabels = Array.from(new Set(points.map((point) => point.group))).sort((a, b) => a.localeCompare(b));
      if (familyCountBadge) {
        const shownCount = new Set(points.map((p) => p.familyId)).size;
        familyCountBadge.textContent = `${shownCount} famil${shownCount === 1 ? "y" : "ies"} shown`;
      }

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
        ? Math.max(vizLayoutParams.stackStep, _maxLinesNeeded * (fontPx * 1.4) / _earlyLaneStep + 0.04)
        : vizLayoutParams.stackStep;

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
        nextBaseUnit = endUnit + vizLayoutParams.groupGapUnits;
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
          relationTip.attach(circle, richTip, () => pdfEntriesForFamilies([{ fid: point.familyId, name: point.name }]));
          attachFamilyContextMenu(circle, point.name, familySearch, render);
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
          relationTip.attach(label, richTip, () => pdfEntriesForFamilies([{ fid: point.familyId, name: point.name }]));
          attachFamilyContextMenu(label, point.name, familySearch, render);
          plotSvg.appendChild(label);
        }
      });

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

      // Standards and process legend -- "Standard" only appears if at least
      // one currently-visible (post-filter/year-range/search) family is
      // actually a standard, so the legend never advertises a category that
      // isn't represented anywhere in the current view.
      const visibleFamilyIdSet = new Set(points.map((p) => p.familyId));
      const anyVisibleStandard = Array.from(visibleFamilyIdSet).some((fid) => standardFamilyIds.has(fid));
      if (anyVisibleStandard || (useProcessColor && processList.length)) {
        processLegend.hidden = false;
        clearNode(processLegend);
        if (anyVisibleStandard) {
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
          // Only legend entries an actually-visible family has -- computed
          // from the same points list the plot itself just drew from, so a
          // disabled tier (e.g. unchecking "Variable-length modes" entirely)
          // or a year-range/search filter correctly empties the legend too,
          // not just an individually-unchecked Processes checkbox.
          const presentProcessIds = new Set(Array.from(visibleFamilyIdSet).map((fid) => familyProcessMap[fid] || "__none__"));
          processList.filter((proc) => presentProcessIds.has(String(proc.id))).forEach((proc) => {
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
          if (presentProcessIds.has("__none__")) {
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
        }
      } else {
        processLegend.hidden = true;
      }

      fontValue.textContent = `${fontPx}px`;
      colSpacingValue.textContent = `${colSpacingBonus >= 0 ? "+" : ""}${colSpacingBonus}px`;
      ensureFit(false);
    }

    groupBy.addEventListener("change", render);
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
    if (familySearchExact) familySearchExact.addEventListener("change", render);
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
    // Floating fullscreen-only zoom controls -- same underlying zoom state
    // and setters as the toolbar buttons above, just reachable when the
    // toolbar itself is hidden in fullscreen mode.
    const vizFsZoomOut = document.getElementById("vizFsZoomOut");
    const vizFsZoomIn = document.getElementById("vizFsZoomIn");
    const vizFsZoomFit = document.getElementById("vizFsZoomFit");
    if (vizFsZoomOut) vizFsZoomOut.addEventListener("click", () => setZoom(zoomScale / ZOOM_FACTOR));
    if (vizFsZoomIn) vizFsZoomIn.addEventListener("click", () => setZoom(zoomScale * ZOOM_FACTOR));
    if (vizFsZoomFit) vizFsZoomFit.addEventListener("click", () => fitZoom());
    attachPinchZoom(plotScroll, () => zoomScale, (s, ax, ay) => setZoom(s, ax, ay));

    // ── "Tune layout" floating panel -- mirrors the Genealogy tab's panel
    // (same toggle/close/reset interaction), exposing the row/group spacing
    // that used to be hardcoded.
    const vizParamsToggle = document.getElementById("vizParamsToggle");
    const vizParamsPanel = document.getElementById("vizParamsPanel");
    const vizParamsClose = document.getElementById("vizParamsClose");
    const vizParamsReset = document.getElementById("vizParamsReset");
    const vizParamStackStep = document.getElementById("vizParamStackStep");
    const vizParamStackStepValue = document.getElementById("vizParamStackStepValue");
    const vizParamGroupGap = document.getElementById("vizParamGroupGap");
    const vizParamGroupGapValue = document.getElementById("vizParamGroupGapValue");
    if (vizParamsToggle && vizParamsPanel) {
      vizParamsToggle.addEventListener("click", () => {
        const open = vizParamsPanel.hidden;
        vizParamsPanel.hidden = !open;
        vizParamsToggle.setAttribute("aria-expanded", String(open));
      });
    }
    if (vizParamsClose && vizParamsPanel && vizParamsToggle) {
      vizParamsClose.addEventListener("click", () => {
        vizParamsPanel.hidden = true;
        vizParamsToggle.setAttribute("aria-expanded", "false");
      });
    }
    const VIZ_LAYOUT_PARAM_SLIDERS = [
      { key: "stackStep", input: vizParamStackStep, out: vizParamStackStepValue },
      { key: "groupGapUnits", input: vizParamGroupGap, out: vizParamGroupGapValue },
    ];
    function syncVizLayoutParamSliders() {
      VIZ_LAYOUT_PARAM_SLIDERS.forEach(({ key, input, out }) => {
        if (input) input.value = String(Math.round(vizLayoutParams[key] * 100));
        if (out) out.textContent = `${Math.round(vizLayoutParams[key] * 100)}%`;
      });
    }
    syncVizLayoutParamSliders();
    VIZ_LAYOUT_PARAM_SLIDERS.forEach(({ key, input, out }) => {
      if (!input) return;
      input.addEventListener("input", () => {
        vizLayoutParams[key] = Number(input.value) / 100;
        if (out) out.textContent = `${Math.round(vizLayoutParams[key] * 100)}%`;
        saveVizLayoutParams();
        render();
      });
    });
    if (vizParamsReset) vizParamsReset.addEventListener("click", () => {
      vizLayoutParams = { ...DEFAULT_VIZ_LAYOUT_PARAMS };
      syncVizLayoutParamSliders();
      saveVizLayoutParams();
      render();
    });
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
      setZoom(zoomScale * factor, event.clientX, event.clientY);
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
    viewRefreshHooks.visualizations = ensureFit;
  }

  function setupGenealogy() {
    const genPlot = document.getElementById("genPlot");
    const genPlotScroll = document.getElementById("genPlotScroll");
    const genFrame = document.getElementById("genFrame");
    const genColorBy = document.getElementById("genColorBy");
    const genHighlightBy = document.getElementById("genHighlightBy");
    const genHighlightValues = document.getElementById("genHighlightValues");
    const genConnectedOnly = document.getElementById("genConnectedOnly");
    const genStandardsOnly = document.getElementById("genStandardsOnly");
    const genFamilySearch = document.getElementById("genFamilySearch");
    const genFamilySearchExact = document.getElementById("genFamilySearchExact");
    const genFamilyCountBadge = document.getElementById("genFamilyCount");
    const genFamilySearchDegree = document.getElementById("genFamilySearchDegree");
    const genDegreeMinus = document.getElementById("genDegreeMinus");
    const genDegreePlus = document.getElementById("genDegreePlus");
    const genYearStart = document.getElementById("genYearStart");
    const genYearEnd = document.getElementById("genYearEnd");
    const genYearReset = document.getElementById("genYearReset");
    const genYearRangeValue = document.getElementById("genYearRangeValue");
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
    const genDebugHitAreas = document.getElementById("genDebugHitAreas");
    const genDebugNodeHitAreas = document.getElementById("genDebugNodeHitAreas");
    const genDebugPointerArea = document.getElementById("genDebugPointerArea");
    const genDebugPointerMarker = document.getElementById("genDebugPointerMarker");
    const genDebugReadout = document.getElementById("genDebugReadout");
    const genPinnedBanner = document.getElementById("genPinnedBanner");
    const genNameClip = document.getElementById("genNameClip");
    const genNameFull = document.getElementById("genNameFull");
    const genZoomOut = document.getElementById("genZoomOut");
    const genZoomIn = document.getElementById("genZoomIn");
    const genZoomReset = document.getElementById("genZoomReset");
    const genZoomFit = document.getElementById("genZoomFit");
    const genZoomValue = document.getElementById("genZoomValue");
    const genParamsToggle = document.getElementById("genParamsToggle");
    const genParamsPanel = document.getElementById("genParamsPanel");
    const genParamsClose = document.getElementById("genParamsClose");
    const genParamsRadialGroup = document.getElementById("genParamsRadial");
    const genParamsLayeredGroup = document.getElementById("genParamsLayered");
    const genParamLabelPitch = document.getElementById("genParamLabelPitch");
    const genParamLabelPitchValue = document.getElementById("genParamLabelPitchValue");
    const genParamAlphaMax = document.getElementById("genParamAlphaMax");
    const genParamAlphaMaxValue = document.getElementById("genParamAlphaMaxValue");
    const genParamRowGap = document.getElementById("genParamRowGap");
    const genParamRowGapValue = document.getElementById("genParamRowGapValue");
    const genParamNodeH = document.getElementById("genParamNodeH");
    const genParamNodeHValue = document.getElementById("genParamNodeHValue");
    const genParamColGap = document.getElementById("genParamColGap");
    const genParamColGapValue = document.getElementById("genParamColGapValue");
    const genParamIsoW = document.getElementById("genParamIsoW");
    const genParamIsoWValue = document.getElementById("genParamIsoWValue");
    const genParamEdgeOpacity = document.getElementById("genParamEdgeOpacity");
    const genParamEdgeOpacityValue = document.getElementById("genParamEdgeOpacityValue");
    const genParamsReset = document.getElementById("genParamsReset");
    const genParamsExport = document.getElementById("genParamsExport");
    const genParamsImportBtn = document.getElementById("genParamsImportBtn");
    const genParamsImportFile = document.getElementById("genParamsImportFile");
    const genParamsStatus = document.getElementById("genParamsStatus");
    if (!genPlot || !genPlotScroll || !genFrame) return;

    const GEN_BASE_FONT = 12;
    let genFontPx = GEN_BASE_FONT;
    let genLayoutMode = "radial";
    let genNumChars = 8;
    let genNameMode = "clip";

    // ── Layout tuning parameters (user-adjustable, persisted) ───────────
    // Exposed via the floating "Tune layout" panel so a user hitting
    // crowding/empty-space problems (radial: labels overlapping on one ring
    // while another ring's arc sits empty; layered: rows/columns too tight or
    // too loose) can retune the layout live, have it stick across reloads,
    // and export the result as JSON to hand to a developer as new defaults.
    const GEN_LAYOUT_PARAMS_KEY = "spdb_genealogy_layout_params_v1";
    const DEFAULT_LAYOUT_PARAMS = {
      radialLabelPitchMult: 1.25, // radial: min arc (× font size) reserved per label
      radialAlphaMax: 0.8,        // radial: max strength of the even-spacing relaxation (0-1)
      layeredRowGapMult: 4.5,     // layered: vertical gap between generations (× font size)
      layeredNodeHMult: 1.85,     // layered: node box height (× font size)
      layeredColGap: 10,          // layered: horizontal gap between sibling nodes (px)
      layeredIsoWMult: 7.5,       // layered: width of isolated-node columns (× font size)
      edgeOpacity: 0.1,           // relation edges: low by default -- large plots have hundreds of overlapping edges that would otherwise bury family labels
    };
    function loadLayoutParams() {
      const out = { ...DEFAULT_LAYOUT_PARAMS };
      try {
        const raw = JSON.parse(localStorage.getItem(GEN_LAYOUT_PARAMS_KEY) || "{}");
        Object.keys(DEFAULT_LAYOUT_PARAMS).forEach((k) => {
          const v = Number(raw[k]);
          if (Number.isFinite(v)) out[k] = v;
        });
      } catch { /* corrupt/unavailable storage falls back to defaults */ }
      return out;
    }
    let layoutParams = loadLayoutParams();
    function saveLayoutParams() {
      try { localStorage.setItem(GEN_LAYOUT_PARAMS_KEY, JSON.stringify(layoutParams)); } catch { /* storage unavailable (e.g. private mode) -- tuning still works, just doesn't persist */ }
    }

    // Plot zoom (mirrors the Timelines "Plot zoom" control): the SVG's
    // width/height attributes are always set to its natural (100%) size by
    // the layout functions below, and genZoomScale scales that down/up via
    // inline style, which the browser stretches uniformly against the fixed
    // viewBox -- so labels shrink along with everything else, letting the
    // plot fit a narrow screen even if the text becomes unreadable.
    const GEN_BASE_ZOOM = 1;
    const GEN_MIN_ZOOM = 0.05;
    const GEN_MAX_ZOOM = 4;
    const GEN_ZOOM_FACTOR = 1.2;
    let genZoomScale = GEN_BASE_ZOOM;
    let genHasAutoFit = false;
    // genFrame's own height (as opposed to genPlot's zoom-scaled height) is
    // fit to window.innerHeight with a fullscreen-vs-normal ratio, set by
    // whichever layout last ran (drawSugiyama/drawRadial -- see
    // recomputeGenFrameHeight()'s callers). Toggling fullscreen doesn't
    // re-run either of those (only ensureGenFit's zoom-refit), so without
    // re-deriving it here too, genFrame stayed stuck at its pre-fullscreen
    // height -- the plot itself would resize but the frame around it
    // wouldn't grow to fill the newly-available viewport height, leaving a
    // gap below it.
    let lastGenFrameSizing = null;
    function recomputeGenFrameHeight() {
      if (!lastGenFrameSizing) return;
      const { naturalH, minH, ratioNormal } = lastGenFrameSizing;
      const isFullscreen = document.body.classList.contains("spdb-fullscreen");
      const ratio = isFullscreen ? 0.97 : ratioNormal;
      genFrame.style.height = `${Math.max(minH, Math.min(Math.round(window.innerHeight * ratio), naturalH + 8))}px`;
    }

    function clampGenZoom(next) {
      return Math.min(GEN_MAX_ZOOM, Math.max(GEN_MIN_ZOOM, next));
    }

    function applyGenZoom() {
      const naturalW = Number(genPlot.getAttribute("width")) || 0;
      const naturalH = Number(genPlot.getAttribute("height")) || 0;
      if (!naturalW || !naturalH) return;
      genPlot.style.width = `${Math.round(naturalW * genZoomScale)}px`;
      genPlot.style.height = `${Math.round(naturalH * genZoomScale)}px`;
      recomputeGenFrameHeight();
      if (genZoomValue) genZoomValue.textContent = `${Math.round(genZoomScale * 100)}%`;
      // Re-scaling moves plot content underneath a cursor that never fired
      // its own mousemove -- see the comment by lastPointerClientPos further
      // down for why this matters (defined later in the file, but hoisted:
      // this function is itself only ever called after user interaction).
      if (typeof refreshHoverAtPointer === "function") refreshHoverAtPointer();
    }

    // Zooms while keeping a chosen anchor point visually fixed on screen --
    // see setZoom() in setupFamilyVisualization for the full rationale.
    // Defaults to the center of the visible scroll viewport for the +/-
    // buttons; pinch and Cmd/Ctrl+wheel pass their own anchor.
    function setGenZoom(next, anchorClientX, anchorClientY) {
      const rect = genPlotScroll.getBoundingClientRect();
      const ax = anchorClientX ?? (rect.left + rect.width / 2);
      const ay = anchorClientY ?? (rect.top + rect.height / 2);
      const oldScale = genZoomScale;
      const contentX = (genPlotScroll.scrollLeft + (ax - rect.left)) / oldScale;
      const contentY = (genPlotScroll.scrollTop + (ay - rect.top)) / oldScale;
      genZoomScale = clampGenZoom(next);
      applyGenZoom();
      genPlotScroll.scrollLeft = contentX * genZoomScale - (ax - rect.left);
      genPlotScroll.scrollTop = contentY * genZoomScale - (ay - rect.top);
    }

    function fitGenZoom() {
      const naturalW = Number(genPlot.getAttribute("width")) || 0;
      // Zero-width container means the panel is currently hidden (its very
      // first render happens before the user has switched to this tab) --
      // report failure so the caller retries once the tab is actually shown.
      if (!genPlotScroll.clientWidth || !naturalW) return false;
      const fitWidth = Math.max(160, genPlotScroll.clientWidth - 8);
      // Deliberately bypasses clampGenZoom()/GEN_MIN_ZOOM, same reasoning as
      // fitZoom() in setupFamilyVisualization: "Fit" must always be able to
      // shrink all the way down to the container's actual width.
      genZoomScale = fitWidth / naturalW;
      applyGenZoom();
      return true;
    }

    // Mirrors ensureFit() in setupFamilyVisualization: fit once a real
    // width is measurable, then leave the user's zoom alone unless forced
    // (entering/exiting fullscreen).
    function ensureGenFit(force) {
      if (force || !genHasAutoFit) {
        if (fitGenZoom()) { genHasAutoFit = true; return; }
      }
      applyGenZoom();
    }

    // ── Data ─────────────────────────────────────────────────────────
    const tables = data.tables || {};
    const rawInfluences = (tables.family_influences && tables.family_influences.rows) || [];

    const genProcessData = data.processData || {};
    const genProcessList = genProcessData.processes || [];
    const genFamilyProcessMap = genProcessData.familyProcessMap || {};

    const genDims = buildDimensionMaps(tables);
    const families = genDims.families;
    const genFamById = new Map(families.map((r) => [String(r.id), r]));

    // construction_sharing_edges is computed at build time (scripts/common.py:
    // compute_construction_sharing_edges), not hand-curated -- for every
    // construction id a family carries (root or leaf), the earliest-year
    // family tagged with it is the star's origin, with every later family
    // sharing that id linked directly to it, older -> newer. Folded into the
    // same edge list as family_influences so it flows through the existing
    // edgeRelations()/render() machinery, tagged with a synthetic
    // "shares_construction" relation kept independently toggleable via
    // RELATION_GROUPS below.
    const constructionSharingRows = (tables.construction_sharing_edges && tables.construction_sharing_edges.rows) || [];
    const derivedConstructionEdges = constructionSharingRows.map((row) => {
      const label = genDims.constructionNameById.get(row.construction_id) || row.construction_id;
      return {
        source_family_id: row.source_family_id,
        target_family_id: row.target_family_id,
        relation: "shares_construction",
        relations_json: JSON.stringify(["shares_construction"]),
        note: `Both tagged as ${label} (derived from a shared construction id, not hand-curated).`,
      };
    });
    const influences = rawInfluences.concat(derivedConstructionEdges);

    const stdFamIds = computeStandardFamilyIds(tables, genDims.instanceFamilyById);

    const famToTypes = genDims.familyToTypes;
    // Keyed by construction ID (not name) so it lines up with the tier
    // filter panel's per-leaf checkboxes; genDims.constructionNameById maps
    // back to a display name wherever these ids are shown to the user.
    const famToConstrs = genDims.familyToConstructionIds;
    const famToTargets = genDims.familyToTargets;

    const PROC_COLORS = ["#1a73c9","#d4501a","#1e9c5e","#9b42b8","#c9961a","#c91a4e","#1ab8c9","#5e6e1a","#7a1ac9","#1a4ec9","#a85a1a","#1a9b9b"];
    const TYPE_COLORS = ["#1e6fa8","#b85a28","#1a8e5c","#7b30a0","#a07818","#98183c","#169aa8","#4c6218","#601aa0","#1a40a0","#8a4818","#1a8080"];
    const genProcColorMap = new Map();
    genProcessList.forEach((p, i) => genProcColorMap.set(String(p.id), PROC_COLORS[i % PROC_COLORS.length]));
    genProcColorMap.set("__none__", "#7a8c8f");
    const typeColorMap = new Map();
    const allTypes = Array.from(new Set(Array.from(famToTypes.values()).flatMap((s) => Array.from(s)))).sort();
    allTypes.forEach((t, i) => typeColorMap.set(t, TYPE_COLORS[i % TYPE_COLORS.length]));
    // Construction/target application are deliberately not coloring
    // dimensions (see nodeColor()) -- these two lists only feed the
    // "Highlight" checklist below, picking out a chosen subset instead.
    const allConstrs = Array.from(new Set(Array.from(famToConstrs.values()).flatMap((s) => Array.from(s)))).sort();
    const allTargets = Array.from(new Set(Array.from(famToTargets.values()).flatMap((s) => Array.from(s)))).sort();
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

    // ── Relation-type groups ────────────────────────────────────────────
    // Groups the curated relation tags into the kinds of relationship this
    // database hand-curates from primary sources -- literal component/round/
    // state sharing is deliberately NOT one of these (it's derivable by
    // querying characteristics.components/round definitions directly rather
    // than hand-tagged; see the Custom Query Builder). What remains:
    //   - design relations: an inherited or related design idea, with no
    //     claim about which specific component was reused.
    //   - usage relations: one family is a functional building block of
    //     another (the "usage_core" group -- either an explicit used_by tag,
    //     or computed from primitive/mode tier crossing).
    // "process" covers administrative facts (standardization) that are
    // neither a design nor a usage relation.
    const RELATION_GROUPS = [
      { id: "design_idea", label: "Design: inherited architecture or idea", members: [
        "inspired_by", "related_to", "variant_of", "improvement_of",
        "generalization_of", "specializes",
      ] },
      { id: "usage_core", label: "Usage: built on (part of the definition)", members: ["__usage_core__", "used_by"], synthetic: true },
      { id: "process", label: "Process: standardization", members: [
        "standardization_of",
      ] },
      { id: "derived_construction", label: "Derived: shares a specific construction type (computed, not hand-curated)", members: [
        "shares_construction",
      ], synthetic: true },
    ];
    (function addCatchAllGroup() {
      const grouped = new Set(RELATION_GROUPS.flatMap((g) => g.members));
      const leftover = relationTypes.filter((r) => !grouped.has(r));
      if (leftover.length) RELATION_GROUPS.push({ id: "other", label: "Other", members: leftover });
    })();

    // A mode/primitive built directly on another (crossing tiers) is always
    // a usage relation.
    function edgeRelationKeys(edge) {
      const rels = edgeRelations(edge);
      const keys = new Set(rels);
      const srcTier = genDims.familyTierById.get(String(edge.source_family_id || ""));
      const tgtTier = genDims.familyTierById.get(String(edge.target_family_id || ""));
      if (srcTier && tgtTier && srcTier !== tgtTier) {
        keys.add("__usage_core__");
      }
      return keys;
    }

    // ── Filter state ──────────────────────────────────────────────────
    let genYrBounds = null;

    const genFilterPanel = createTierFilterPanel("gen", genDims, genFamilyProcessMap, genProcessList, () => render());
    const genRelationFilterPanel = createRelationFilterPanel(RELATION_GROUPS, edgeRelationKeys, () => render());

    function initFilters() {
      const yrs = families.map((f) => Number(f.year)).filter(isFinite).sort((a, b) => a - b);
      if (yrs.length) {
        genYrBounds = { min: yrs[0], max: yrs[yrs.length - 1] };
        [genYearStart, genYearEnd].forEach((el) => { el.min = String(genYrBounds.min); el.max = String(genYrBounds.max); el.step = "1"; });
        genYearStart.value = String(genYrBounds.min); genYearEnd.value = String(genYrBounds.max);
        updateYrLbl();
      }
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

    // Coloring only covers Type and Process -- both are close to
    // single-valued per family in practice. Construction and Target
    // application are not: most families carry several of each, so coloring
    // by either would just show the alphabetically-first value and imply a
    // precision the data doesn't have. Those two are offered as a
    // "Highlight" pick-a-subset control instead (see isHighlighted() below),
    // which fades everything else out without pretending each family has
    // exactly one construction/target.
    function nodeColor(fid) {
      const mode = genColorBy.value;
      if (mode === "process") { const pid = genFamilyProcessMap[fid]; return pid ? (genProcColorMap.get(pid) || "#7a8c8f") : "#7a8c8f"; }
      const tt = Array.from(famToTypes.get(fid) || []).sort(); return tt.length ? (typeColorMap.get(tt[0]) || "#5a7a8a") : "#7a8c8f";
    }

    // ── Highlight: pick a subset of Constructions/Target applications and
    // fade every non-matching node, instead of trying to color by a
    // multi-valued dimension (see nodeColor() above).
    let genHighlightDim = "none";
    const genHighlightSelected = new Set();
    function isHighlightActive() { return genHighlightDim !== "none" && genHighlightSelected.size > 0; }
    function isHighlighted(fid) {
      if (!isHighlightActive()) return true;
      const map = genHighlightDim === "construction" ? famToConstrs : famToTargets;
      const values = map.get(fid);
      if (!values) return false;
      return Array.from(values).some((v) => genHighlightSelected.has(v));
    }
    function highlightOpacity(fid) { return isHighlighted(fid) ? 1 : 0.15; }

    // ── Edge/node hover-click highlight ──────────────────────────────
    // Hovering (or clicking, which pins it -- click the same thing again to
    // unpin) a relation edge or a family node bolds it and whatever it's
    // connected to (an edge's two endpoints; a node's own box/label plus
    // every edge touching it and *their* other endpoints).
    //
    // This is driven by a single delegated mousemove/click pair on genPlot
    // (registered once, further below) using elementsFromPoint() instead of
    // per-element listeners, for two reasons:
    //  1. With 1000+ overlapping edge hit-areas, a plain per-element
    //     mouseenter only ever reaches whichever one happens to be topmost
    //     in paint order at a given pixel -- anything underneath it was
    //     silently, permanently unreachable. elementsFromPoint() collects
    //     every hit-area actually under the cursor, so overlapping edges
    //     highlight (and pin) together instead of only the top one ever
    //     responding.
    //  2. It lets node hover reuse the exact same code path as edge hover:
    //     nodes register into the same edgeHitData map (see the node-drawing
    //     loops in drawSugiyama/drawRadial), so hitsAtPoint() doesn't care
    //     which kind of element it found.
    //
    // edgeHitData values may hold either a plain array or a zero-arg
    // function returning one, because an edge's node endpoints aren't known
    // yet at the point the edge itself is drawn (nodes are drawn after
    // edges) -- a function defers that lookup until it's actually read,
    // which only happens later on user interaction, by which point the
    // node-drawing loop has long since finished.
    const edgeHitData = new WeakMap(); // hit element -> { edgeEls, nodeEls } (each may be an array or a () => array)
    function resolveHitList(value) { return typeof value === "function" ? value() : value; }
    // Mouse/touch imprecision tolerance lives here, on the *pointer's* side,
    // rather than in each edge's own hit-area width (see the comment by the
    // hp path elements in drawSugiyama/drawRadial for why). A small ring of
    // sample points around the actual cursor position -- checked with
    // elementsFromPoint() same as the center point -- gives a tolerance zone
    // that's centered on the cursor and a fixed size in *screen* pixels at
    // any zoom level, instead of one that balloons at high zoom and shrinks
    // at low zoom the way a viewBox-unit-based line fattening would.
    const POINTER_HIT_RADIUS_PX = 3;
    const POINTER_HIT_SAMPLES = 6;
    function hitsAtPoint(clientX, clientY) {
      const edgeEls = []; const nodeEls = [];
      // The elements actually found by elementsFromPoint() (an edge's hp
      // path, or a node's own rect/circle/text) -- as opposed to edgeEls/
      // nodeEls above, which are what those hits *expand to* (an edge's
      // visible colored line(s); a node's connected edges and their other
      // endpoints). Kept separately because only the raw hit carries its
      // own <title>/label text for the debug readout -- the expanded
      // elements don't (a colored edge line has no title of its own, only
      // its hp sibling does).
      const rawHits = [];
      const seen = new Set();
      function checkPoint(x, y) {
        document.elementsFromPoint(x, y).forEach((el) => {
          if (seen.has(el)) return;
          const data = edgeHitData.get(el);
          if (!data) return;
          seen.add(el);
          rawHits.push(el);
          edgeEls.push(...resolveHitList(data.edgeEls));
          nodeEls.push(...resolveHitList(data.nodeEls));
        });
      }
      checkPoint(clientX, clientY);
      for (let i = 0; i < POINTER_HIT_SAMPLES; i++) {
        const angle = (i / POINTER_HIT_SAMPLES) * 2 * Math.PI;
        checkPoint(clientX + POINTER_HIT_RADIUS_PX * Math.cos(angle), clientY + POINTER_HIT_RADIUS_PX * Math.sin(angle));
      }
      return { edgeEls, nodeEls, rawHits };
    }
    function sameEls(a, b) {
      if (a.length !== b.length) return false;
      const set = new Set(a);
      return b.every((el) => set.has(el));
    }
    function uniqueEls(list) { return [...new Set(list)]; }

    // A bold font-weight alone didn't read well against the plot's busy
    // background, so a highlighted label instead gets a small opaque
    // backdrop rect (fixed, high-contrast colors -- see .gen-label-backdrop
    // in styles.css) inserted directly behind it. One reusable rect per
    // label (tracked here rather than recreated every time) since the same
    // label can enter/leave the highlighted set repeatedly as the mouse
    // moves. svgEl() is defined further down but this only ever *runs* on
    // user interaction, long after it's hoisted and available.
    const labelBackdrops = new WeakMap(); // text element -> its backdrop rect
    function showLabelBackdrop(textEl) {
      let rect = labelBackdrops.get(textEl);
      if (!rect) {
        rect = svgEl("rect", { class: "gen-label-backdrop" });
        labelBackdrops.set(textEl, rect);
      }
      let bbox;
      try { bbox = textEl.getBBox(); } catch { return; }
      const pad = 1.5;
      rect.setAttribute("x", String(bbox.x - pad));
      rect.setAttribute("y", String(bbox.y - pad));
      rect.setAttribute("width", String(bbox.width + pad * 2));
      rect.setAttribute("height", String(bbox.height + pad * 2));
      // Radial labels carry their own rotate() transform; mirror it so the
      // backdrop stays aligned with the (possibly rotated) text.
      const t = textEl.getAttribute("transform");
      if (t) rect.setAttribute("transform", t); else rect.removeAttribute("transform");
      if (rect.parentNode !== textEl.parentNode || rect.nextSibling !== textEl) {
        textEl.parentNode.insertBefore(rect, textEl);
      }
    }
    function hideLabelBackdrop(textEl) {
      const rect = labelBackdrops.get(textEl);
      if (rect && rect.parentNode) rect.parentNode.removeChild(rect);
    }

    // Debug aid (same "Show hit-areas" checkbox as the red edge hit-area
    // lines): outlines a *node's* actual hit-testable geometry -- its own
    // rect/circle, but also its label text, which is registered into
    // edgeHitData too (radial labels are always pointer-events:all now, not
    // just when there's no bullet -- see the node-drawing loops) and can be
    // significantly wider than the visible glyphs suggest once its own
    // rotate() transform is applied, especially for long family names. The
    // edge hit-area lines alone don't explain "the cursor isn't touching
    // anything but a relation still lit up" if what it's actually near is a
    // node's hit box instead of an edge's line.
    function debugOutlineNodeHitArea(el) {
      let box;
      try { box = el.getBBox(); } catch { return; }
      const pad = 0.5;
      const outline = svgEl("rect", {
        x: String(box.x - pad),
        y: String(box.y - pad),
        width: String(box.width + pad * 2),
        height: String(box.height + pad * 2),
        fill: "rgba(30, 100, 255, 0.18)",
        stroke: "rgba(20, 60, 200, 0.9)",
        "stroke-width": "0.6",
        "pointer-events": "none",
      });
      const t = el.getAttribute("transform");
      if (t) outline.setAttribute("transform", t);
      genPlot.appendChild(outline);
    }

    let hotShown = null;   // { edgeEls, nodeEls } currently CSS-classed/backdropped
    function clearHotClasses() {
      if (!hotShown) return;
      hotShown.edgeEls.forEach((el) => {
        el.classList.remove("gen-edge-hot");
        el.setAttribute("opacity", String(layoutParams.edgeOpacity));
      });
      hotShown.nodeEls.forEach((el) => {
        el.classList.remove("gen-node-hot");
        if (el.tagName === "text") hideLabelBackdrop(el);
      });
      hotShown = null;
    }
    function applyHotClasses(edgeEls, nodeEls) {
      const dedupedEdges = uniqueEls(edgeEls);
      const dedupedNodes = uniqueEls(nodeEls);
      if (hotShown && sameEls(hotShown.edgeEls, dedupedEdges) && sameEls(hotShown.nodeEls, dedupedNodes)) return;
      clearHotClasses();
      // A highlighted edge forced to full opacity buried the labels under a
      // wall of opaque lines on dense graphs -- bump the *current* opacity
      // by 10 points (capped at 100%) instead, so it's clearly more visible
      // than an unhighlighted edge without overpowering everything else.
      // The extra stroke-width (see .gen-edge-hot) still does most of the
      // "this one's highlighted" work.
      const hotOpacity = Math.min(1, layoutParams.edgeOpacity + 0.1);
      dedupedEdges.forEach((el) => {
        el.classList.add("gen-edge-hot");
        el.setAttribute("opacity", String(hotOpacity));
      });
      dedupedNodes.forEach((el) => {
        el.classList.add("gen-node-hot");
        if (el.tagName === "text") showLabelBackdrop(el);
      });
      hotShown = { edgeEls: dedupedEdges, nodeEls: dedupedNodes };
    }

    // hotPinned is set by a click and, unlike a hover, is *not* cleared by
    // moving the mouse elsewhere -- only by clicking the same edge/node
    // again. Whatever's live-hovered is shown *in addition to* the pin
    // (their union), so hovering around while something is pinned keeps
    // previewing other relations without losing the pinned one; mouseleave
    // (or hovering empty space) just drops back to showing the pin alone.
    // A pin looks *identical* to a fresh hover otherwise (same classes),
    // which reads as "stuck"/buggy if it's not obvious something was
    // deliberately pinned earlier -- genPinnedBanner makes that state
    // visible regardless of where the cursor currently is.
    let hotPinned = null; // { edgeEls, nodeEls }
    function setHotPinned(value) {
      hotPinned = value;
      if (genPinnedBanner) genPinnedBanner.hidden = !value;
    }
    function unionWithPin(liveEdgeEls, liveNodeEls) {
      if (!hotPinned) return { edgeEls: liveEdgeEls, nodeEls: liveNodeEls };
      return {
        edgeEls: [...hotPinned.edgeEls, ...liveEdgeEls],
        nodeEls: [...hotPinned.nodeEls, ...liveNodeEls],
      };
    }
    // Debug aid: a short, unambiguous label for one matched element, read
    // from the same <title> text (or, for a label with no title of its
    // own, its displayed name) already used for the hover tooltip --
    // avoids having to eyeball a screenshot to guess whether a given pixel
    // is really inside a thin edge's hit-area or a label's hit box.
    function describeHitEl(el) {
      const titleEl = el.querySelector && el.querySelector("title");
      if (titleEl && titleEl.textContent) return titleEl.textContent.split("\n")[0];
      if (el.tagName === "text") return el.textContent;
      return el.tagName;
    }
    function updateDebugReadout(hover) {
      if (!genDebugReadout) return;
      if (!(genDebugPointerArea && genDebugPointerArea.checked)) {
        genDebugReadout.hidden = true;
        return;
      }
      genDebugReadout.hidden = false;
      // rawHits, not edgeEls/nodeEls: those are what a hit *expands to*
      // (an edge's visible colored line(s); a node's connected edges/other
      // endpoints), which don't carry their own title/label text -- only
      // the actually-matched element (an edge's hp path, or a node's own
      // rect/circle/text) does. Edges are always <path>; nodes are
      // rect/circle/text -- reliable since that's exactly how the two are
      // told apart when registering them into edgeHitData in the first
      // place.
      const edgeHits = hover.rawHits.filter((el) => el.tagName === "path");
      const nodeHits = hover.rawHits.filter((el) => el.tagName !== "path");
      const MAX_LISTED = 8;
      const lines = [`Live hit-test at cursor: ${edgeHits.length} edge(s), ${nodeHits.length} node element(s)`];
      edgeHits.slice(0, MAX_LISTED).forEach((el) => lines.push(`  edge: ${describeHitEl(el)}`));
      if (edgeHits.length > MAX_LISTED) lines.push(`  ...+${edgeHits.length - MAX_LISTED} more edges`);
      nodeHits.slice(0, MAX_LISTED).forEach((el) => lines.push(`  node: ${describeHitEl(el)}`));
      if (nodeHits.length > MAX_LISTED) lines.push(`  ...+${nodeHits.length - MAX_LISTED} more nodes`);
      if (!edgeHits.length && !nodeHits.length) lines.push("  (nothing under the pointer or its tolerance ring)");
      genDebugReadout.textContent = lines.join("\n");
    }
    // The mouse staying physically still is not the same thing as nothing
    // under it changing: scrolling/panning genPlotScroll, or zooming (which
    // re-scales genPlot's content around some anchor other than the
    // cursor -- the toolbar +/-/Fit/Reset buttons, in particular), both
    // move plot content underneath a cursor that never fired a mousemove
    // of its own. Without re-checking, whatever was hot before stayed
    // classed as hot -- confirmed directly: hovering a dense hub, then
    // panning the container by a few hundred px with the mouse held still,
    // left the *same* ~50 edges classed hot while a fresh hit-test at that
    // same screen position found a completely different, much smaller set
    // actually there. lastPointerClientPos plus refreshHoverAtPointer()
    // lets scroll/zoom handlers re-run the same check the mouse itself
    // would have triggered, using wherever the pointer last actually was.
    let lastPointerClientPos = null;
    function refreshHoverAtPointer() {
      if (!lastPointerClientPos) return;
      const hover = hitsAtPoint(lastPointerClientPos.x, lastPointerClientPos.y);
      updateDebugReadout(hover);
      const { edgeEls, nodeEls } = unionWithPin(hover.edgeEls, hover.nodeEls);
      if (edgeEls.length || nodeEls.length) applyHotClasses(edgeEls, nodeEls);
      else clearHotClasses();
    }
    // Registered once (not per-render): genPlot itself is never replaced,
    // only its children, so a listener here keeps working across every
    // re-render via normal DOM event delegation.
    genPlot.addEventListener("mousemove", (ev) => {
      lastPointerClientPos = { x: ev.clientX, y: ev.clientY };
      if (genDebugPointerMarker && genDebugPointerArea && genDebugPointerArea.checked) {
        genDebugPointerMarker.hidden = false;
        genDebugPointerMarker.style.left = `${ev.clientX}px`;
        genDebugPointerMarker.style.top = `${ev.clientY}px`;
      }
      refreshHoverAtPointer();
    });
    genPlot.addEventListener("mouseleave", () => {
      lastPointerClientPos = null;
      if (genDebugPointerMarker) genDebugPointerMarker.hidden = true;
      if (genDebugReadout) genDebugReadout.hidden = true;
      if (hotPinned) applyHotClasses(hotPinned.edgeEls, hotPinned.nodeEls);
      else clearHotClasses();
    });
    // Panning (scrolling genPlotScroll without necessarily moving the
    // mouse -- a trackpad two-finger swipe held under a still cursor is the
    // easy way to do this) moves content underneath the pointer exactly
    // like the zoom handlers below do; same fix.
    genPlotScroll.addEventListener("scroll", refreshHoverAtPointer);
    // Capture phase: attach()'s own click listener (below, per edge/node
    // element, for the text info box) calls stopPropagation(), which would
    // otherwise stop this delegated listener from ever seeing the click.
    genPlot.addEventListener("click", (ev) => {
      const hits = hitsAtPoint(ev.clientX, ev.clientY);
      if (!hits.edgeEls.length && !hits.nodeEls.length) {
        // A pin can only otherwise be cleared by clicking the exact same
        // edge/node again -- easy to lose track of once pinned, especially
        // since a dense hub can pin dozens of edges/nodes at once from a
        // single, easy-to-trigger-by-accident click (a trackpad tap while
        // passing through a crowded spot, say). Clicking anywhere empty
        // is a common "dismiss" gesture elsewhere in this UI already (see
        // createPinnableInfoBox's own pinned-text dismissal) and gives an
        // obvious way out without having to relocate the original spot.
        if (hotPinned) { setHotPinned(null); clearHotClasses(); }
        return;
      }
      if (hotPinned && sameEls(hotPinned.edgeEls, hits.edgeEls) && sameEls(hotPinned.nodeEls, hits.nodeEls)) {
        setHotPinned(null);
      } else {
        setHotPinned(hits);
      }
      applyHotClasses(hits.edgeEls, hits.nodeEls);
    }, true);
    // The empty-space case above only fires for clicks that land somewhere
    // inside genPlot's own SVG canvas -- a click on the page background, a
    // filter panel, or any other element outside genPlot never reaches a
    // listener registered on genPlot at all (it's not an ancestor of the
    // click target, so it's never in that event's capture/bubble path).
    // Without this, a pin from an easy-to-trigger-by-accident click (a
    // trackpad tap while passing through a crowded hub, say) would have no
    // way to be dismissed by clicking elsewhere on the page.
    document.addEventListener("click", (ev) => {
      if (!hotPinned || genPlot.contains(ev.target)) return;
      setHotPinned(null);
      clearHotClasses();
    });
    function renderHighlightChecklist() {
      if (!genHighlightValues) return;
      if (genHighlightDim === "none") { genHighlightValues.hidden = true; genHighlightValues.innerHTML = ""; return; }
      const entries = genHighlightDim === "construction"
        ? allConstrs.map((c) => ({ key: c, label: genDims.constructionNameById.get(c) || c }))
        : allTargets.map((t) => ({ key: t, label: t }));
      genHighlightValues.hidden = false;
      genHighlightValues.innerHTML = entries.map(({ key, label }) => {
        const esc = escapeHtml(label);
        const checked = genHighlightSelected.has(key) ? " checked" : "";
        return `<label><input type="checkbox" data-value="${escapeHtml(key)}"${checked}/><span>${esc}</span></label>`;
      }).join("");
    }

    function isVis(fid, ignoreSearch = false) {
      const fam = genFamById.get(fid); if (!fam) return false;
      const yr = getYrRange(); const year = Number(fam.year);
      if (yr && (year < yr.start || year > yr.end)) return false;
      const needle = ignoreSearch ? "" : genFamilySearch.value.trim();
      if (needle && !familyNameMatches(fam.name || fid, needle, !!(genFamilySearchExact && genFamilySearchExact.checked))) return false;
      if (genStandardsOnly.checked && !stdFamIds.has(fid)) return false;
      if (!genFilterPanel.isFamilyVisible(fid)) return false;
      return true;
    }

    // ── Layout constants (some are dynamic on genFontPx) ─────────────
    let COL_GAP = 10; // reassigned from layoutParams.layeredColGap at the top of drawSugiyama
    const TOP_PAD = 20;
    const SIDE_PAD = 20;
    const NODE_PAD_X = 7;
    const BASE_EDGE_INFO = "Hover or tap a family node or an influence arrow to see details. Right-click/long-press a node to filter the graph to it.";
    const edgeTip = createPinnableInfoBox(genEdgeInfo, BASE_EDGE_INFO);

    function nodeH() { return Math.round(genFontPx * layoutParams.layeredNodeHMult); }
    function rowGap() { return Math.round(genFontPx * layoutParams.layeredRowGapMult); }
    function isoW() { return Math.round(genFontPx * layoutParams.layeredIsoWMult); }
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
    // drawnFamilyIds is exactly the set of nodes actually on screen this
    // render (post tier-enable/type/construction/target/process/year/search
    // filters, and post "Only connected families"). The legend is built
    // from what's actually present among those nodes rather than from
    // per-value checkbox state, so e.g. disabling the whole "Variable-length
    // modes" tier empties AEAD/XOF/Hash/... from the Type legend too --
    // checking only each value's own checkbox missed that case, since the
    // checkboxes inside a disabled tier stay individually checked.
    function drawLegend(drawnFamilyIds) {
      if (!genLegend) return;
      while (genLegend.firstChild) genLegend.removeChild(genLegend.firstChild);
      const mode = genColorBy.value;
      const ids = drawnFamilyIds || [];
      const anyVisibleStandard = ids.some((fid) => stdFamIds.has(fid));
      const present = new Set();
      if (mode === "process") {
        ids.forEach((fid) => present.add(genFamilyProcessMap[fid] || "__none__"));
      } else {
        ids.forEach((fid) => (famToTypes.get(fid) || new Set()).forEach((t) => present.add(t)));
      }
      const items = mode === "process"
        ? [...genProcessList.filter((p) => present.has(String(p.id))).map((p) => ({ color: genProcColorMap.get(String(p.id)), label: String(p.name) })),
           ...(present.has("__none__") ? [{ color: genProcColorMap.get("__none__"), label: "No process" }] : [])]
        : allTypes.filter((t) => present.has(t)).map((t) => ({ color: typeColorMap.get(t) || "#7a8c8f", label: t }));
      const mkItem = (color, label, bold) => {
        const s = document.createElement("span"); s.className = "viz-process-legend-item";
        const d = document.createElement("span"); d.className = "viz-process-legend-dot"; d.style.cssText = `background:${color};${bold ? "border:2px solid #000;box-sizing:border-box" : ""}`;
        const l = document.createElement("span"); l.textContent = label; if (bold) l.style.fontWeight = "700";
        s.appendChild(d); s.appendChild(l); return s;
      };
      if (anyVisibleStandard) genLegend.appendChild(mkItem("#152021", "Standard", true));
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
      COL_GAP = layoutParams.layeredColGap;
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
      lastGenFrameSizing = { naturalH: canvasH, minH: 220, ratioNormal: 0.70 };
      recomputeGenFrameHeight();

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
      const nodeElsByFamily = new Map();
      const edgesByFamily = new Map(); // fid -> [{ edgeEls, otherFid }]
      function addEdgeFamily(fid, entry) {
        if (!edgesByFamily.has(fid)) edgesByFamily.set(fid, []);
        edgesByFamily.get(fid).push(entry);
      }
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
        const edgeEls = [];
        if (genCollapseEdges && genCollapseEdges.checked) {
          edgeEls.push(genPlot.appendChild(svgEl("path", { d: pd, stroke: "rgba(0,0,0,0.7)", "stroke-width": "0.9", fill: "none", "pointer-events": "none", opacity: String(layoutParams.edgeOpacity), "marker-end": "url(#genArrow)" })));
        } else {
          rels.forEach((relation, i) => {
            const strokeW = 0.8 + (rels.length - i - 1) * 1.3;
            const attrs = { d: pd, stroke: relationColorMap.get(relation), "stroke-width": String(strokeW), fill: "none", "pointer-events": "none", opacity: String(layoutParams.edgeOpacity) };
            if (i === rels.length - 1) attrs["marker-end"] = "url(#genArrow)";
            edgeEls.push(genPlot.appendChild(svgEl("path", attrs)));
          });
        }
        // Hit-area matches the edge's own thickest visible stroke exactly --
        // no added tolerance here. A wide (or even slightly padded) fixed
        // hit-width let hitsAtPoint() would happily find (a real fix,
        // elsewhere) drown out *precision* instead: in a crowded spot with
        // several close but distinct lines, a fat hit-area made nearly any
        // point among them match several unrelated edges at once, and
        // adjacent lines' fattened areas could overlap even where the
        // visible lines themselves don't. Mouse/touch imprecision tolerance
        // instead comes from the *pointer's* side -- hitsAtPoint() samples a
        // small, constant-screen-pixel radius around the actual cursor
        // position (see hitsAtPoint()) rather than from fattening the line,
        // which keeps the tolerance zone centered on the cursor and a fixed
        // size on screen regardless of zoom, instead of a per-edge zone that
        // balloons at high zoom and shrinks at low zoom.
        const maxStrokeW = 0.8 + Math.max(0, rels.length - 1) * 1.3;
        const hitAreaStroke = (genDebugHitAreas && genDebugHitAreas.checked) ? "rgba(255,0,0,0.35)" : "rgba(0,0,0,0.001)";
        // pointer-events MUST be "visibleStroke", not "all": "all" hit-tests
        // the path's fill/interior *regardless of the fill property's
        // actual value* -- for an open (unclosed) curve, the browser
        // computes that interior by implicitly closing the path with a
        // straight line back to the start, so a curve that bulges away from
        // a straight line between its endpoints (a wide S-curve, e.g.) had
        // its entire enclosed area hit-testable, not just the stroked
        // line -- confirmed directly: a point sitting on the straight
        // chord between an edge's two endpoints, hundreds of viewBox units
        // from the actual visible curve, registered as a hit. "fill: none"
        // alone does not opt out of this -- pointer-events has to.
        const hp = svgEl("path", { d: pd, stroke: hitAreaStroke, "stroke-width": String(maxStrokeW), fill: "none", "pointer-events": "visibleStroke" });
        const hpT = svgEl("title", {}); hpT.textContent = hoverTxt; hp.appendChild(hpT);
        edgeTip.attach(hp, hoverTxt, () => pdfEntriesForFamilies([{ fid: src, name: srcName }, { fid: tgt, name: tgtName }]));
        // nodeElsByFamily is only fully populated once the node loop below
        // runs, but this getter is only called later (on user interaction),
        // by which point the whole render() call has long since completed.
        edgeHitData.set(hp, { edgeEls, nodeEls: () => [...(nodeElsByFamily.get(src) || []), ...(nodeElsByFamily.get(tgt) || [])] });
        addEdgeFamily(src, { edgeEls, otherFid: tgt });
        addEdgeFamily(tgt, { edgeEls, otherFid: src });
        hoverPaths.push(hp);
      });
      // Append edge hit-areas before nodes/labels so nodes/labels paint (and
      // hit-test) on top -- otherwise a fat invisible edge hover-path lying
      // under a label intercepts clicks meant for that label.
      hoverPaths.forEach((hp) => genPlot.appendChild(hp));

      [...dagNodes, ...isoNodes].forEach((fid) => {
        const fam = genFamById.get(fid); if (!fam) return;
        const cx = posX.get(fid); const cy = posY.get(fid); if (cx === undefined || cy === undefined) return;
        const isIso = !dagSet.has(fid); const isStd = stdFamIds.has(fid);
        const name = String(fam.name || fid);
        const w = isIso ? IW : nw(name);
        const color = nodeColor(fid);
        const famTypes = Array.from(famToTypes.get(fid) || []).sort().join(", ") || "—";
        const famConstrs = Array.from(famToConstrs.get(fid) || []).map((c) => genDims.constructionNameById.get(c) || c).sort().join(", ") || "—";
        const pid = genFamilyProcessMap[fid]; const proc = pid ? genProcessList.find((p) => String(p.id) === pid) : null;
        const tip = [`${name} (${fam.year})`, `Type: ${famTypes}`, `Construction: ${famConstrs}`, ...(isStd ? ["Standard: yes"] : []), ...(proc ? [`Process: ${proc.name}`] : []), ...(fam.notes ? [fam.notes] : [])].join("\n");
        const hlOpacity = highlightOpacity(fid);
        const rect = svgEl("rect", { x: String(cx - w / 2), y: String(cy), width: String(w), height: String(NH), rx: "4", ry: "4", fill: isStd ? "#152021" : color, stroke: isStd ? "#000" : "rgba(0,0,0,0.22)", "stroke-width": isStd ? "2" : "1", opacity: String((isIso ? 0.58 : 1) * hlOpacity) });
        const rt = svgEl("title", {}); rt.textContent = tip; rect.appendChild(rt);
        edgeTip.attach(rect, tip, () => pdfEntriesForFamilies([{ fid, name }]));
        attachFamilyContextMenu(rect, name, genFamilySearch, render);
        genPlot.appendChild(rect);
        const maxCh = Math.min(genNumChars, Math.max(4, Math.floor((w - NODE_PAD_X * 2) / (genFontPx * 0.56))));
        const lblStyle = `font-size:${genFontPx}px;font-family:"IBM Plex Mono",monospace;fill:#fff;pointer-events:none;font-weight:${isStd ? 700 : 400};opacity:${(isIso ? 0.8 : 1) * hlOpacity}`;
        const lbl = svgEl("text", { "text-anchor": "middle", style: lblStyle });
        const disp = genNameMode === "full" ? name : (name.length <= maxCh ? name : name.slice(0, Math.max(1, maxCh - 1)) + "…");
        lbl.setAttribute("x", String(cx));
        lbl.setAttribute("y", String(cy + NH * 0.67));
        lbl.textContent = disp;
        genPlot.appendChild(lbl);
        nodeElsByFamily.set(fid, [rect, lbl]);
      });

      // Third pass: now that every node's elements are known, register each
      // node's own rect as an edgeHitData hit target too, so hovering/
      // clicking a node highlights itself plus every edge touching it and
      // those edges' other endpoints -- the same interaction edges already
      // get, just triggered from the node side. (The label itself doesn't
      // need its own entry: it has pointer-events:none, so it's invisible
      // to elementsFromPoint() anyway, and its rect already covers the same
      // area.)
      [...dagNodes, ...isoNodes].forEach((fid) => {
        const ownEls = nodeElsByFamily.get(fid);
        if (!ownEls) return;
        const related = edgesByFamily.get(fid) || [];
        const edgeEls = related.flatMap((r) => r.edgeEls);
        const nodeEls = [...ownEls, ...related.flatMap((r) => nodeElsByFamily.get(r.otherFid) || [])];
        edgeHitData.set(ownEls[0], { edgeEls, nodeEls });
        if (genDebugNodeHitAreas && genDebugNodeHitAreas.checked) debugOutlineNodeHitArea(ownEls[0]);
      });
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

      // ── Even label spacing: relax angular crowding ring by ring ─────────
      // The barycenter/transpose passes above only minimise edge stress, so nodes
      // stay packed at their subtree barycenters: inner rings (especially gen 0)
      // collide while big subtrees leave whole arcs empty. Here each ring's nodes
      // are nudged toward an even comb, but only as far as that ring is actually
      // crowded — strength α = (nodes × label pitch) ÷ ring circumference, which is
      // ~1 for tight inner rings and ~0 for roomy outer ones, so well-separated
      // outer nodes keep their clean near-radial edges. Circular order is preserved
      // (the comb is aligned to the ring's mean angle), so edges never re-cross.
      const LABEL_PITCH = genFontPx * layoutParams.radialLabelPitchMult; // px of arc each label needs clear of its neighbour
      const ALPHA_MAX = layoutParams.radialAlphaMax;                    // never fully abandon the barycenter placement
      const ringGroups = new Map();
      angleOf.forEach((deg, id) => {
        const key = useGen ? String(layerOf.get(id) || 0) : String(Math.round(nodeR(id)));
        if (!ringGroups.has(key)) ringGroups.set(key, []);
        ringGroups.get(key).push(id);
      });
      ringGroups.forEach((ids) => {
        const m = ids.length;
        if (m < 2) return;
        const circ = 2 * Math.PI * Math.max(nodeR(ids[0]), 1);
        const alpha = Math.min(ALPHA_MAX, (m * LABEL_PITCH) / circ);
        if (alpha <= 0.02) return;
        ids.sort((a, b) => angleOf.get(a) - angleOf.get(b));
        const step = 360 / m;
        // Rotation of the even comb that best matches the ring's current angles,
        // so nodes move as little as possible (circular mean of angle − i·step).
        let sx = 0, sy = 0;
        ids.forEach((id, i) => {
          const d = (angleOf.get(id) - i * step) * Math.PI / 180;
          sx += Math.cos(d); sy += Math.sin(d);
        });
        const phi = Math.atan2(sy, sx) * 180 / Math.PI;
        ids.forEach((id, i) => {
          const target = phi + i * step;
          const delta = ((target - angleOf.get(id)) % 360 + 540) % 360 - 180;
          angleOf.set(id, angleOf.get(id) + alpha * delta);
        });
      });

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
      lastGenFrameSizing = { naturalH: diam, minH: 320, ratioNormal: 0.82 };
      recomputeGenFrameHeight();

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
      const nodeElsByFamily = new Map();
      const edgesByFamily = new Map(); // fid -> [{ edgeEls, otherFid }]
      function addEdgeFamily(fid, entry) {
        if (!edgesByFamily.has(fid)) edgesByFamily.set(fid, []);
        edgesByFamily.get(fid).push(entry);
      }
      visEdges.forEach((e) => {
        const src = String(e.source_family_id || ""); const tgt = String(e.target_family_id || "");
        if (!angleOf.has(src) || !angleOf.has(tgt)) return;
        const pd = rPath(src, tgt);
        const rels = edgeRelations(e);
        const relLabel = rels.map((r) => String(r).replace(/_/g, " ")).join(", ");
        const hoverTxt = `${String((genFamById.get(src) || {}).name || src)} → ${String((genFamById.get(tgt) || {}).name || tgt)}: ${relLabel}${e.note ? " | " + String(e.note) : ""}`;
        const edgeEls = [];
        if (genCollapseEdges && genCollapseEdges.checked) {
          edgeEls.push(genPlot.appendChild(svgEl("path", { d: pd, stroke: "rgba(0,0,0,0.7)", "stroke-width": "0.9", fill: "none", opacity: String(layoutParams.edgeOpacity) })));
        } else {
          rels.forEach((relation, i) => {
            const strokeW = 0.8 + (rels.length - i - 1) * 1.3;
            edgeEls.push(genPlot.appendChild(svgEl("path", { d: pd, stroke: relationColorMap.get(relation), "stroke-width": String(strokeW), fill: "none", opacity: String(layoutParams.edgeOpacity) })));
          });
        }
        // See the matching comment in drawSugiyama: hit-area matches the
        // edge's own visible thickness exactly; pointer tolerance instead
        // comes from hitsAtPoint()'s own small screen-pixel sampling radius.
        const maxStrokeW = 0.8 + Math.max(0, rels.length - 1) * 1.3;
        const hitAreaStroke = (genDebugHitAreas && genDebugHitAreas.checked) ? "rgba(255,0,0,0.35)" : "rgba(0,0,0,0.001)";
        // pointer-events MUST be "visibleStroke", not "all": "all" hit-tests
        // the path's fill/interior *regardless of the fill property's
        // actual value* -- for an open (unclosed) curve, the browser
        // computes that interior by implicitly closing the path with a
        // straight line back to the start, so a curve that bulges away from
        // a straight line between its endpoints (a wide S-curve, e.g.) had
        // its entire enclosed area hit-testable, not just the stroked
        // line -- confirmed directly: a point sitting on the straight
        // chord between an edge's two endpoints, hundreds of viewBox units
        // from the actual visible curve, registered as a hit. "fill: none"
        // alone does not opt out of this -- pointer-events has to.
        const hp = svgEl("path", { d: pd, stroke: hitAreaStroke, "stroke-width": String(maxStrokeW), fill: "none", "pointer-events": "visibleStroke" });
        const hpT = svgEl("title", {}); hpT.textContent = hoverTxt; hp.appendChild(hpT);
        edgeTip.attach(hp, hoverTxt, () => pdfEntriesForFamilies([
          { fid: src, name: String((genFamById.get(src) || {}).name || src) },
          { fid: tgt, name: String((genFamById.get(tgt) || {}).name || tgt) },
        ]));
        // See the matching comment in drawSugiyama: nodeElsByFamily is
        // populated by the node loop below, but this getter is only called
        // later, on user interaction.
        edgeHitData.set(hp, { edgeEls, nodeEls: () => [...(nodeElsByFamily.get(src) || []), ...(nodeElsByFamily.get(tgt) || [])] });
        addEdgeFamily(src, { edgeEls, otherFid: tgt });
        addEdgeFamily(tgt, { edgeEls, otherFid: src });
        hoverPaths.push(hp);
      });
      // Append edge hit-areas before nodes/labels so nodes/labels paint (and
      // hit-test) on top -- otherwise a fat invisible edge hover-path lying
      // under a label intercepts clicks meant for that label.
      hoverPaths.forEach((hp) => genPlot.appendChild(hp));

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
        const famConstrs = Array.from(famToConstrs.get(fid) || []).map((c) => genDims.constructionNameById.get(c) || c).sort().join(", ") || "—";
        const pid = genFamilyProcessMap[fid]; const proc = pid ? genProcessList.find((p) => String(p.id) === pid) : null;
        const genLabel = useGen ? `Gen ${layerOf.get(fid) || 0}` : String(yr);
        const tip = [`${String(fam.name || fid)} (${genLabel})`, `Type: ${famTypes}`, `Construction: ${famConstrs}`, ...(isStd ? ["Standard: yes"] : []), ...(proc ? [`Process: ${proc.name}`] : [])].join("\n");
        const showBullets = !genShowBullets || genShowBullets.checked;
        const nodeRad = isStd ? 4 : 3;
        const name = String(fam.name || fid);
        const hlOpacity = highlightOpacity(fid);
        let circEl = null;
        if (showBullets) {
          const circ = svgEl("circle", { cx: String(nx.toFixed(1)), cy: String(ny.toFixed(1)), r: String(nodeRad), fill: isStd ? "#152021" : color, stroke: isStd ? "#000" : "rgba(0,0,0,0.25)", "stroke-width": isStd ? "1.5" : "0.8", opacity: String(hlOpacity), "pointer-events": "all" });
          const ct = svgEl("title", {}); ct.textContent = tip; circ.appendChild(ct);
          edgeTip.attach(circ, tip, () => pdfEntriesForFamilies([{ fid, name }]));
          attachFamilyContextMenu(circ, name, genFamilySearch, render);
          genPlot.appendChild(circ);
          circEl = circ;
        }
        const isRight = deg <= 180;
        const rad = (deg - 90) * Math.PI / 180;
        const off = showBullets ? nodeRad + 5 : 3;
        const lx = nx + off * Math.cos(rad);
        const ly = ny + off * Math.sin(rad);
        const textRot = isRight ? (deg - 90) : (deg + 90);
        const maxLabelCh = genNumChars;
        const labelFill = showBullets ? (isStd ? "#162022" : "#1a2a2e") : color;
        // Always hit-testable (not just when there's no bullet): the label
        // text is often the larger, easier-to-hit target of the two, and
        // hovering/clicking it should highlight the node like hovering the
        // bullet already does.
        const radStyle = `font-size:${genFontPx}px;font-family:"IBM Plex Mono",monospace;fill:${labelFill};pointer-events:all;font-weight:${isStd ? 700 : 400};opacity:${hlOpacity}`;
        const anchor = isRight ? "start" : "end";
        const disp = genNameMode === "full" ? name : (name.length <= maxLabelCh ? name : name.slice(0, Math.max(2, maxLabelCh - 1)) + "…");
        const lbl = svgEl("text", { x: String(lx.toFixed(1)), y: String(ly.toFixed(1)), "text-anchor": anchor,
          transform: `rotate(${textRot.toFixed(1)},${lx.toFixed(1)},${ly.toFixed(1)})`, style: radStyle });
        lbl.textContent = disp;
        const lt = svgEl("title", {}); lt.textContent = tip; lbl.appendChild(lt);
        edgeTip.attach(lbl, tip, () => pdfEntriesForFamilies([{ fid, name }]));
        attachFamilyContextMenu(lbl, name, genFamilySearch, render);
        genPlot.appendChild(lbl);
        nodeElsByFamily.set(fid, circEl ? [circEl, lbl] : [lbl]);
      });

      // Third pass: register each node's own elements (bullet and/or label)
      // as edgeHitData hit targets -- see the matching comment at the end
      // of drawSugiyama. (Radial doesn't render isoNodes at all -- only
      // dagNodes get drawn above -- so there's nothing to register for them.)
      dagNodes.forEach((fid) => {
        const ownEls = nodeElsByFamily.get(fid);
        if (!ownEls) return;
        const related = edgesByFamily.get(fid) || [];
        const edgeEls = related.flatMap((r) => r.edgeEls);
        const nodeEls = [...ownEls, ...related.flatMap((r) => nodeElsByFamily.get(r.otherFid) || [])];
        ownEls.forEach((el) => {
          edgeHitData.set(el, { edgeEls, nodeEls });
          if (genDebugNodeHitAreas && genDebugNodeHitAreas.checked) debugOutlineNodeHitArea(el);
        });
      });
    }

    // ── Render dispatcher ─────────────────────────────────────────────
    function render() {
      updateYrLbl();
      // The DOM elements these referenced are about to be discarded; a pin
      // can't meaningfully survive a full re-render (different filters can
      // remove the pinned edge/node entirely), so it resets too.
      hotShown = null;
      setHotPinned(null);
      while (genPlot.firstChild) genPlot.removeChild(genPlot.firstChild);

      const eligibleIds = families.map((f) => String(f.id || "")).filter((fid) => fid && isVis(fid, true));
      const eligibleSet = new Set(eligibleIds);
      // A relation the user has unchecked is treated as absent for every
      // purpose below, including the search's relation-degree hop -- hidden
      // relations shouldn't let the BFS reach through them either.
      const relVisibleInfluences = influences.filter((e) => genRelationFilterPanel.isEdgeVisible(e));
      const needle = genFamilySearch.value.trim();
      const exactWord = !!(genFamilySearchExact && genFamilySearchExact.checked);
      let visIds = eligibleIds;
      if (needle) {
        const matched = new Set(eligibleIds.filter((fid) =>
          familyNameMatches((genFamById.get(fid) || {}).name || fid, needle, exactWord)));
        const rawDegree = genFamilySearchDegree ? parseInt(genFamilySearchDegree.value, 10) : 1;
        const degree = Number.isFinite(rawDegree) ? Math.max(0, rawDegree) : 1;
        // BFS outward from the matched set, one relation "hop" per round, so a
        // degree of 1 (the default) keeps the original direct-neighbors-only
        // behavior and a higher degree pulls in more distant relations.
        let frontier = matched;
        const expanded = new Set(matched);
        for (let hop = 0; hop < degree && frontier.size; hop++) {
          const next = new Set();
          relVisibleInfluences.forEach((e) => {
            const src = String(e.source_family_id || ""); const tgt = String(e.target_family_id || "");
            if (frontier.has(src) && eligibleSet.has(tgt) && !expanded.has(tgt)) next.add(tgt);
            if (frontier.has(tgt) && eligibleSet.has(src) && !expanded.has(src)) next.add(src);
          });
          next.forEach((fid) => expanded.add(fid));
          frontier = next;
        }
        visIds = eligibleIds.filter((fid) => expanded.has(fid));
      }
      const visSet = new Set(visIds);

      if (!visIds.length) {
        if (genFamilyCountBadge) genFamilyCountBadge.textContent = "0 families shown";
        genPlot.setAttribute("viewBox", "0 0 620 160"); genPlot.setAttribute("width", "620"); genPlot.setAttribute("height", "160");
        const msg = svgEl("text", { x: "24", y: "42", class: "viz-label" }); msg.textContent = "No families match the current filters.";
        genPlot.appendChild(msg); genFrame.style.height = "200px"; if (genLegend) genLegend.hidden = true;
        genPlot.style.width = ""; genPlot.style.height = "";
        return;
      }

      const visEdges = relVisibleInfluences.filter((e) => visSet.has(String(e.source_family_id || "")) && visSet.has(String(e.target_family_id || "")));

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
      const shownNodes = dagNodes.concat(isoNodes);
      if (genFamilyCountBadge) {
        genFamilyCountBadge.textContent = `${shownNodes.length} famil${shownNodes.length === 1 ? "y" : "ies"} shown`;
      }
      drawLegend(shownNodes);
      ensureGenFit(false);
    }

    genColorBy.addEventListener("change", render);
    renderHighlightChecklist();
    if (genHighlightBy) genHighlightBy.addEventListener("change", () => {
      genHighlightDim = genHighlightBy.value;
      genHighlightSelected.clear();
      renderHighlightChecklist();
      render();
    });
    if (genHighlightValues) genHighlightValues.addEventListener("change", (ev) => {
      const t = ev.target;
      if (t && t.type === "checkbox" && t.dataset.value !== undefined) {
        if (t.checked) genHighlightSelected.add(t.dataset.value);
        else genHighlightSelected.delete(t.dataset.value);
        render();
      }
    });
    genConnectedOnly.addEventListener("change", render);
    genStandardsOnly.addEventListener("change", render);
    if (genByGeneration) genByGeneration.addEventListener("change", render);
    if (genShowBullets) genShowBullets.addEventListener("change", render);
    if (genCollapseEdges) genCollapseEdges.addEventListener("change", render);
    if (genDebugHitAreas) genDebugHitAreas.addEventListener("change", render);
    if (genDebugNodeHitAreas) genDebugNodeHitAreas.addEventListener("change", render);
    if (genDebugPointerArea) genDebugPointerArea.addEventListener("change", () => {
      if (!genDebugPointerArea.checked && genDebugPointerMarker) genDebugPointerMarker.hidden = true;
    });
    genFamilySearch.addEventListener("input", render);
    genFamilySearch.addEventListener("change", render);
    if (genFamilySearchExact) genFamilySearchExact.addEventListener("change", render);
    if (genFamilySearchDegree) {
      genFamilySearchDegree.addEventListener("input", render);
      genFamilySearchDegree.addEventListener("change", render);
    }
    if (genDegreeMinus) genDegreeMinus.addEventListener("click", () => {
      const cur = parseInt(genFamilySearchDegree.value, 10);
      genFamilySearchDegree.value = String(Math.max(0, (Number.isFinite(cur) ? cur : 1) - 1));
      render();
    });
    if (genDegreePlus) genDegreePlus.addEventListener("click", () => {
      const cur = parseInt(genFamilySearchDegree.value, 10);
      genFamilySearchDegree.value = String((Number.isFinite(cur) ? cur : 1) + 1);
      render();
    });
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
    // Shows only the tuning-panel group relevant to the active layout, so the
    // radial and layered sliders never appear (or get confused for one
    // another) at the same time.
    function syncParamsGroupVisibility() {
      if (genParamsRadialGroup) genParamsRadialGroup.hidden = genLayoutMode !== "radial";
      if (genParamsLayeredGroup) genParamsLayeredGroup.hidden = genLayoutMode !== "layered";
    }
    if (genLayoutLayered) genLayoutLayered.addEventListener("click", () => {
      genLayoutMode = "layered";
      if (genLayoutLayered) genLayoutLayered.classList.add("is-active");
      if (genLayoutRadial) genLayoutRadial.classList.remove("is-active");
      syncParamsGroupVisibility();
      render();
      fitGenZoom();
    });
    if (genLayoutRadial) genLayoutRadial.addEventListener("click", () => {
      genLayoutMode = "radial";
      if (genLayoutRadial) genLayoutRadial.classList.add("is-active");
      if (genLayoutLayered) genLayoutLayered.classList.remove("is-active");
      syncParamsGroupVisibility();
      render();
      fitGenZoom();
    });
    syncParamsGroupVisibility();

    // ── Layout tuning panel: floats over the plot, toggled on demand ────
    if (genParamsToggle && genParamsPanel) {
      genParamsToggle.addEventListener("click", () => {
        const open = genParamsPanel.hidden;
        genParamsPanel.hidden = !open;
        genParamsToggle.setAttribute("aria-expanded", String(open));
      });
    }
    if (genParamsClose && genParamsPanel && genParamsToggle) {
      genParamsClose.addEventListener("click", () => {
        genParamsPanel.hidden = true;
        genParamsToggle.setAttribute("aria-expanded", "false");
      });
    }
    const LAYOUT_PARAM_SLIDERS = [
      { key: "radialLabelPitchMult", input: genParamLabelPitch, out: genParamLabelPitchValue, scale: 100, fmt: (v) => `${Math.round(v * 100)}%` },
      { key: "radialAlphaMax", input: genParamAlphaMax, out: genParamAlphaMaxValue, scale: 100, fmt: (v) => `${Math.round(v * 100)}%` },
      { key: "layeredRowGapMult", input: genParamRowGap, out: genParamRowGapValue, scale: 100, fmt: (v) => `${Math.round(v * 100)}%` },
      { key: "layeredNodeHMult", input: genParamNodeH, out: genParamNodeHValue, scale: 100, fmt: (v) => `${Math.round(v * 100)}%` },
      { key: "layeredColGap", input: genParamColGap, out: genParamColGapValue, scale: 1, fmt: (v) => `${Math.round(v)}px` },
      { key: "layeredIsoWMult", input: genParamIsoW, out: genParamIsoWValue, scale: 100, fmt: (v) => `${Math.round(v * 100)}%` },
      { key: "edgeOpacity", input: genParamEdgeOpacity, out: genParamEdgeOpacityValue, scale: 100, fmt: (v) => `${Math.round(v * 100)}%` },
    ];
    function syncLayoutParamSliders() {
      LAYOUT_PARAM_SLIDERS.forEach(({ key, input, out, scale, fmt }) => {
        if (input) input.value = String(Math.round(layoutParams[key] * scale));
        if (out) out.textContent = fmt(layoutParams[key]);
      });
    }
    syncLayoutParamSliders();
    LAYOUT_PARAM_SLIDERS.forEach(({ key, input, out, scale, fmt }) => {
      if (!input) return;
      input.addEventListener("input", () => {
        layoutParams[key] = Number(input.value) / scale;
        if (out) out.textContent = fmt(layoutParams[key]);
        saveLayoutParams();
        render();
      });
    });
    if (genParamsReset) genParamsReset.addEventListener("click", () => {
      layoutParams = { ...DEFAULT_LAYOUT_PARAMS };
      syncLayoutParamSliders();
      saveLayoutParams();
      if (genParamsStatus) genParamsStatus.textContent = "Spacing reset to defaults.";
      render();
    });
    if (genParamsExport) genParamsExport.addEventListener("click", () => {
      const blob = new Blob([JSON.stringify(layoutParams, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "genealogy-layout-params.json";
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      if (genParamsStatus) genParamsStatus.textContent = "Exported genealogy-layout-params.json";
    });
    if (genParamsImportBtn && genParamsImportFile) {
      genParamsImportBtn.addEventListener("click", () => genParamsImportFile.click());
      genParamsImportFile.addEventListener("change", () => {
        const file = genParamsImportFile.files && genParamsImportFile.files[0];
        genParamsImportFile.value = "";
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
          try {
            const raw = JSON.parse(String(reader.result || "{}"));
            const next = { ...DEFAULT_LAYOUT_PARAMS };
            let count = 0;
            Object.keys(DEFAULT_LAYOUT_PARAMS).forEach((k) => {
              const v = Number(raw[k]);
              if (Number.isFinite(v)) { next[k] = v; count++; }
            });
            layoutParams = next;
            syncLayoutParamSliders();
            saveLayoutParams();
            if (genParamsStatus) genParamsStatus.textContent = `Imported ${count} parameter(s) from ${file.name}.`;
            render();
          } catch (err) {
            if (genParamsStatus) genParamsStatus.textContent = `Import failed: ${err.message}`;
          }
        };
        reader.readAsText(file);
      });
    }
    [[genNameClip, "clip"], [genNameFull, "full"]].forEach(([btn, mode]) => {
      if (!btn) return;
      btn.addEventListener("click", () => {
        genNameMode = mode;
        [genNameClip, genNameFull].forEach((b) => { if (b) b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        render();
      });
    });

    if (genZoomOut) genZoomOut.addEventListener("click", () => setGenZoom(genZoomScale / GEN_ZOOM_FACTOR));
    if (genZoomIn) genZoomIn.addEventListener("click", () => setGenZoom(genZoomScale * GEN_ZOOM_FACTOR));
    if (genZoomReset) genZoomReset.addEventListener("click", () => setGenZoom(GEN_BASE_ZOOM));
    if (genZoomFit) genZoomFit.addEventListener("click", () => fitGenZoom());
    // Floating fullscreen-only zoom controls, mirroring the Timelines tab.
    const genFsZoomOut = document.getElementById("genFsZoomOut");
    const genFsZoomIn = document.getElementById("genFsZoomIn");
    const genFsZoomFit = document.getElementById("genFsZoomFit");
    if (genFsZoomOut) genFsZoomOut.addEventListener("click", () => setGenZoom(genZoomScale / GEN_ZOOM_FACTOR));
    if (genFsZoomIn) genFsZoomIn.addEventListener("click", () => setGenZoom(genZoomScale * GEN_ZOOM_FACTOR));
    if (genFsZoomFit) genFsZoomFit.addEventListener("click", () => fitGenZoom());
    attachPinchZoom(genPlotScroll, () => genZoomScale, (s, ax, ay) => setGenZoom(s, ax, ay));
    genPlotScroll.addEventListener("wheel", (event) => {
      if (!(event.ctrlKey || event.metaKey)) return;
      event.preventDefault();
      const factor = event.deltaY < 0 ? GEN_ZOOM_FACTOR : 1 / GEN_ZOOM_FACTOR;
      setGenZoom(genZoomScale * factor, event.clientX, event.clientY);
    }, { passive: false });

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
    viewRefreshHooks.genealogy = ensureGenFit;

  }

  setupNavigator();
  setupAllTablesBrowser();
  setupBuilder();
  setupFamilyVisualization();
  setupGenealogy();
  setupFullscreenAndFilterToggles();
  setupPdfViewer();
})();
