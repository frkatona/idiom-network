/* Idiom Phonetics Explorer — static site app logic */
(function () {
  "use strict";

  var PAGE_SIZE = 20;

  var state = {
    records: [],
    filtered: [],
    selectedId: null,
    page: 0,
    sortCol: null,
    sortAsc: true,
    colFilters: {}
  };

  var els = {
    search: document.getElementById("search"),
    rhyme: document.getElementById("rhyme-key"),
    initial: document.getElementById("initial-phone"),
    minSyllables: document.getElementById("min-syllables"),
    maxSyllables: document.getElementById("max-syllables"),
    alliteration: document.getElementById("alliteration"),
    alliterationValue: document.getElementById("alliteration-value"),
    ignoreStopwords: document.getElementById("ignore-stopwords"),
    hideUnknown: document.getElementById("hide-unknown"),
    summary: document.getElementById("results-summary"),
    table: document.getElementById("table-wrap"),
    detail: document.getElementById("detail-panel"),
    rhymeGroups: document.getElementById("rhyme-groups"),
    alliterationGroups: document.getElementById("alliteration-groups"),
    graph: document.getElementById("cluster-graph"),
    helpOpen: document.getElementById("help-open"),
    helpClose: document.getElementById("help-close"),
    helpModal: document.getElementById("help-modal"),
    helpTabs: document.querySelectorAll("[data-help-tab]"),
    helpPanels: document.querySelectorAll("[data-help-panel]"),
    forceLink: document.getElementById("force-link"),
    forceCharge: document.getElementById("force-charge"),
    forceCollide: document.getElementById("force-collide"),
    forceWall: document.getElementById("force-wall"),
    nodeSize: document.getElementById("node-size"),
    showLabels: document.getElementById("show-labels")
  };

  var graphSimulation = null;

  /* ---- Fuzzy search ---- */

  function bigrams(s) {
    var b = [];
    for (var i = 0; i < s.length - 1; i++) b.push(s.charAt(i) + s.charAt(i + 1));
    return b;
  }

  function hasWildcard(s) {
    return s.indexOf('*') !== -1 || s.indexOf('?') !== -1;
  }

  function matchWildcard(query, text) {
    // Escape regex characters except * and ?
    var escaped = query.replace(/[-\/\\^$*+?.()|[\]{}]/g, function (char) {
      if (char === '*') return '__STAR__';
      if (char === '?') return '__QUESTION__';
      return '\\' + char;
    });
    var regexStr = '^' + escaped.replace(/__STAR__/g, '.*').replace(/__QUESTION__/g, '.') + '$';
    try {
      var rx = new RegExp(regexStr, 'i');
      return rx.test(text);
    } catch (e) {
      return false;
    }
  }

  function fuzzyMatch(query, text) {
    if (!query) return true;
    query = query.trim().toLowerCase();
    text = text.toLowerCase();
    if (hasWildcard(query)) {
      return matchWildcard(query, text);
    }
    if (text.indexOf(query) !== -1) return true;
    if (query.length < 3) return false;
    var qb = bigrams(query), tb = bigrams(text);
    if (!qb.length || !tb.length) return false;
    var tset = {};
    for (var i = 0; i < tb.length; i++) tset[tb[i]] = true;
    var hits = 0;
    for (var j = 0; j < qb.length; j++) if (tset[qb[j]]) hits++;
    return (hits / qb.length) >= 0.45;
  }

  /* ---- Helpers ---- */

  function escapeHtml(v) {
    return String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  }

  function countValues(arr) {
    var c = {};
    for (var i = 0; i < arr.length; i++) c[arr[i]] = (c[arr[i]] || 0) + 1;
    return c;
  }

  function initials(r) {
    return els.ignoreStopwords.checked ? r.initial_phonemes : r.initial_phonemes_with_stopwords;
  }

  function dominantInitial(r) {
    return els.ignoreStopwords.checked ? r.dominant_initial : r.dominant_initial_with_stopwords;
  }

  function alliterationScore(r) {
    return els.ignoreStopwords.checked ? r.alliteration_score : r.alliteration_score_with_stopwords;
  }

  /* ---- Init ---- */

  fetch("./data/idioms_phonetic.json")
    .then(function (r) { return r.json(); })
    .then(function (records) {
      state.records = records;
      hydrateOptions(records);
      initRangeSlider();
      update();
    });

  var controls = [els.search, els.rhyme, els.initial, els.minSyllables,
    els.maxSyllables, els.alliteration, els.ignoreStopwords, els.hideUnknown];
  for (var i = 0; i < controls.length; i++) {
    controls[i].addEventListener("input", function () { state.page = 0; update(); });
    controls[i].addEventListener("change", function () { state.page = 0; update(); });
  }

  /* ---- Help modal ---- */

  els.helpOpen.addEventListener("click", openHelp);
  els.helpClose.addEventListener("click", closeHelp);
  els.helpModal.querySelector("[data-close-help]").addEventListener("click", closeHelp);
  els.helpTabs.forEach(function (b) {
    b.addEventListener("click", function () { selectHelpTab(b.dataset.helpTab); });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && els.helpModal.classList.contains("is-open")) closeHelp();
  });

  function openHelp() {
    els.helpModal.classList.add("is-open");
    els.helpOpen.setAttribute("aria-expanded", "true");
    els.helpClose.focus();
  }

  function closeHelp() {
    els.helpModal.classList.remove("is-open");
    els.helpOpen.setAttribute("aria-expanded", "false");
    els.helpOpen.focus();
  }

  function selectHelpTab(name) {
    els.helpTabs.forEach(function (b) {
      var sel = b.dataset.helpTab === name;
      b.classList.toggle("help-tab-selected", sel);
      b.setAttribute("aria-selected", sel ? "true" : "false");
    });
    els.helpPanels.forEach(function (p) {
      var sel = p.dataset.helpPanel === name;
      p.classList.toggle("is-active", sel);
      p.hidden = !sel;
    });
  }

  /* ---- Range slider ---- */

  function initRangeSlider() {
    var mn = parseInt(els.minSyllables.min), mx = parseInt(els.minSyllables.max);
    var ticks = document.getElementById("syllable-range-ticks");
    ticks.innerHTML = "";

    // Create tick marks with labels
    var labeled = new Set();
    labeled.add(mn);
    labeled.add(mx);
    for (var v = mn; v <= mx; v++) {
      if (v % 2 === 1) labeled.add(v);
    }

    for (var val = mn; val <= mx; val++) {
      var pct = ((val - mn) / (mx - mn)) * 100;
      
      var tick = document.createElement("div");
      tick.className = "range-slider-tick";
      if (!labeled.has(val)) {
        tick.classList.add("minor-tick");
      }
      tick.style.left = pct + "%";
      ticks.appendChild(tick);

      if (labeled.has(val)) {
        var lbl = document.createElement("span");
        lbl.className = "range-slider-tick-label";
        lbl.style.left = pct + "%";
        lbl.textContent = val;
        ticks.appendChild(lbl);
      }
    }

    updateRangeTrack();

    // Give the min slider a higher z-index so it stays reachable
    els.minSyllables.style.zIndex = "6";

    els.minSyllables.addEventListener("input", function () {
      var hi = parseInt(els.maxSyllables.value);
      if (parseInt(els.minSyllables.value) > hi) els.minSyllables.value = hi;
      updateRangeTrack();
    });
    els.maxSyllables.addEventListener("input", function () {
      var lo = parseInt(els.minSyllables.value);
      if (parseInt(els.maxSyllables.value) < lo) els.maxSyllables.value = lo;
      updateRangeTrack();
    });
  }

  function updateRangeTrack() {
    var mn = parseInt(els.minSyllables.min), mx = parseInt(els.minSyllables.max);
    var lo = parseInt(els.minSyllables.value), hi = parseInt(els.maxSyllables.value);
    var track = document.getElementById("syllable-range-track");
    track.style.setProperty("--range-start", ((lo - mn) / (mx - mn) * 100) + "%");
    track.style.setProperty("--range-end", ((hi - mn) / (mx - mn) * 100) + "%");

    // When min is past the midpoint, promote max slider so it stays reachable
    var mid = (mn + mx) / 2;
    els.minSyllables.style.zIndex = lo > mid ? "5" : "6";
    els.maxSyllables.style.zIndex = lo > mid ? "6" : "5";
  }

  /* ---- Options hydration ---- */

  function hydrateOptions(records) {
    var rc = countValues(records.map(function (r) { return r.rhyme_key; }).filter(Boolean));
    Object.entries(rc)
      .filter(function (e) { return e[1] > 1; })
      .sort(function (a, b) { return b[1] - a[1] || a[0].localeCompare(b[0]); })
      .forEach(function (e) { els.rhyme.append(new Option(e[0] + " (" + e[1] + ")", e[0])); });

    var inits = new Set();
    records.forEach(function (r) {
      r.initial_phonemes.forEach(function (p) { inits.add(p); });
      r.initial_phonemes_with_stopwords.forEach(function (p) { inits.add(p); });
    });
    Array.from(inits).sort().forEach(function (p) { els.initial.append(new Option(p, p)); });
  }

  /* ---- Filter & sort ---- */

  function update() {
    els.alliterationValue.textContent = Number(els.alliteration.value).toFixed(2);
    var query = els.search.value.trim().toLowerCase();
    var minS = Number(els.minSyllables.value);
    var maxS = Number(els.maxSyllables.value);
    var floor = Number(els.alliteration.value);

    state.filtered = state.records.filter(function (r) {
      var text = r.idiom + " " + r.normalized_idiom + " " + r.raw_entry_head;
      if (!fuzzyMatch(query, text)) return false;
      if (r.syllable_count < minS || r.syllable_count > maxS) return false;
      if (els.rhyme.value && r.rhyme_key !== els.rhyme.value) return false;
      if (els.initial.value && initials(r).indexOf(els.initial.value) === -1) return false;
      if (alliterationScore(r) < floor) return false;
      if (els.hideUnknown.checked && r.unknown_words.length > 0) return false;
      
      // Column filters
      for (var c = 0; c < COLUMNS.length; c++) {
        var colId = COLUMNS[c].id;
        var fval = state.colFilters[colId];
        if (fval) {
          fval = fval.trim().toLowerCase();
          var val = String(sortValue(r, colId)).toLowerCase();
          if (hasWildcard(fval)) {
            if (!matchWildcard(fval, val)) return false;
          } else {
            if (val.indexOf(fval) === -1) return false;
          }
        }
      }
      
      return true;
    });

    applySortToFiltered();

    if (!state.filtered.some(function (r) { return r.id === state.selectedId; })) {
      state.selectedId = state.filtered.length ? state.filtered[0].id : null;
    }
    var maxPage = Math.max(0, Math.ceil(state.filtered.length / PAGE_SIZE) - 1);
    if (state.page > maxPage) state.page = maxPage;
    render();
  }

  function applySortToFiltered() {
    var col = state.sortCol;
    if (!col) {
      state.filtered.sort(function (a, b) {
        return a.syllable_count - b.syllable_count || a.idiom.localeCompare(b.idiom);
      });
      return;
    }
    var dir = state.sortAsc ? 1 : -1;
    state.filtered.sort(function (a, b) {
      var va = sortValue(a, col), vb = sortValue(b, col);
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
      return String(va).localeCompare(String(vb)) * dir;
    });
  }

  function sortValue(r, col) {
    switch (col) {
      case "idiom": return r.idiom;
      case "syllables": return r.syllable_count;
      case "rhyme_key": return r.rhyme_key || "";
      case "initials": return initials(r).join(" ");
      case "stress": return r.stress_pattern.join("");
      case "alliteration": return alliterationScore(r);
      default: return "";
    }
  }

  function handleSort(col) {
    if (state.sortCol === col) {
      state.sortAsc = !state.sortAsc;
    } else {
      state.sortCol = col;
      state.sortAsc = true;
    }
    state.page = 0;
    applySortToFiltered();
    render();
  }

  /* ---- Render ---- */

  function render() {
    var total = state.filtered.length;
    els.summary.innerHTML = "<div><strong>" + total.toLocaleString() + " matches</strong></div>";
    renderTable();
    renderDetail();
    renderGroups(els.rhymeGroups, groupBy(
      state.filtered.filter(function (r) { return r.rhyme_key; }),
      function (r) { return r.rhyme_key; }, 2));
    renderGroups(els.alliterationGroups, groupBy(
      state.filtered.filter(function (r) {
        return alliterationScore(r) >= Math.max(0.5, Number(els.alliteration.value));
      }), dominantInitial, 2));
    renderGraph();
  }

  /* ---- Table ---- */

  var COLUMNS = [
    { id: "idiom", label: "Idiom" },
    { id: "syllables", label: "Syllables" },
    { id: "rhyme_key", label: "Rhyme Key" },
    { id: "initials", label: "Initials" },
    { id: "stress", label: "Stress" },
    { id: "alliteration", label: "Alliteration" }
  ];

  function renderTable() {
    var activeFilter = document.activeElement && document.activeElement.classList.contains('col-filter')
      ? document.activeElement.dataset.col : null;

    var start = state.page * PAGE_SIZE;
    var rows = state.filtered.slice(start, start + PAGE_SIZE);
    if (!rows.length && !Object.keys(state.colFilters).some(function(k){return state.colFilters[k];})) {
      els.table.innerHTML = '<p class="empty-state">No idioms match the current filters.</p>';
      return;
    }
    
    var html = '<table class="static-table"><thead><tr>';
    for (var c = 0; c < COLUMNS.length; c++) {
      var col = COLUMNS[c];
      var active = state.sortCol === col.id;
      var arrow = active ? (state.sortAsc ? "▲" : "▼") : "⇅";
      var cls = active ? "sort-indicator active" : "sort-indicator";
      html += '<th data-sort="' + col.id + '">' + col.label +
        '<span class="' + cls + '">' + arrow + '</span></th>';
    }
    html += '</tr><tr class="filter-row">';
    for (var c = 0; c < COLUMNS.length; c++) {
      var col = COLUMNS[c];
      var fval = state.colFilters[col.id] || "";
      var clearBtn = fval ? '<button class="col-filter-clear" data-col="' + col.id + '" aria-label="Clear filter" title="Clear filter">×</button>' : '';
      html += '<th><div class="col-filter-wrap"><input type="text" class="col-filter" data-col="' + col.id + '" value="' + escapeHtml(fval) + '" placeholder="Filter...">' + clearBtn + '</div></th>';
    }
    html += '</tr></thead><tbody>';

    if (!rows.length) {
      html += '<tr><td colspan="' + COLUMNS.length + '" class="empty-state" style="text-align: center; padding: 20px;">No idioms match the column filters.</td></tr>';
    } else {
      for (var r = 0; r < rows.length; r++) {
        var rec = rows[r];
        var sel = rec.id === state.selectedId ? ' class="row-selected"' : '';
        html += '<tr' + sel + '>' +
          '<td><button data-id="' + rec.id + '">' + escapeHtml(rec.idiom) + '</button></td>' +
          '<td>' + rec.syllable_count + '</td>' +
          '<td>' + escapeHtml(rec.rhyme_key || "") + '</td>' +
          '<td>' + escapeHtml(initials(rec).join(" ")) + '</td>' +
          '<td>' + escapeHtml(rec.stress_pattern.join("") || "") + '</td>' +
          '<td>' + alliterationScore(rec).toFixed(2) + '</td></tr>';
      }
    }
    html += '</tbody></table>';
    html += renderPagination();
    els.table.innerHTML = html;

    els.table.querySelectorAll("button[data-id]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.selectedId = Number(btn.dataset.id);
        renderTable();
        renderDetail();
      });
    });
    els.table.querySelectorAll("th[data-sort]").forEach(function (th) {
      th.addEventListener("click", function () { handleSort(th.dataset.sort); });
    });
    els.table.querySelectorAll(".page-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.page = Number(btn.dataset.page);
        renderTable();
      });
    });
    
    var colFilters = els.table.querySelectorAll(".col-filter");
    colFilters.forEach(function(input) {
      input.addEventListener("input", function(e) {
        state.colFilters[e.target.dataset.col] = e.target.value;
        state.page = 0;
        update();
      });
    });

    var colFiltersClear = els.table.querySelectorAll(".col-filter-clear");
    colFiltersClear.forEach(function(btn) {
      btn.addEventListener("click", function(e) {
        state.colFilters[e.target.dataset.col] = "";
        state.page = 0;
        update();
      });
    });

    if (activeFilter) {
      var input = els.table.querySelector('.col-filter[data-col="' + activeFilter + '"]');
      if (input) {
        input.focus();
        var len = input.value.length;
        input.setSelectionRange(len, len);
      }
    }
  }

  function renderPagination() {
    var total = state.filtered.length;
    var pages = Math.ceil(total / PAGE_SIZE);
    if (pages <= 1) return "";
    var cur = state.page;
    var html = '<div class="pagination">';
    html += '<button class="page-btn" data-page="' + Math.max(0, cur - 1) + '"' +
      (cur === 0 ? " disabled" : "") + '>‹</button>';

    var start = Math.max(0, cur - 3), end = Math.min(pages - 1, cur + 3);
    if (start > 0) {
      html += '<button class="page-btn" data-page="0">1</button>';
      if (start > 1) html += '<span class="page-info">…</span>';
    }
    for (var p = start; p <= end; p++) {
      html += '<button class="page-btn' + (p === cur ? " page-active" : "") +
        '" data-page="' + p + '">' + (p + 1) + '</button>';
    }
    if (end < pages - 1) {
      if (end < pages - 2) html += '<span class="page-info">…</span>';
      html += '<button class="page-btn" data-page="' + (pages - 1) + '">' + pages + '</button>';
    }
    html += '<button class="page-btn" data-page="' + Math.min(pages - 1, cur + 1) + '"' +
      (cur >= pages - 1 ? " disabled" : "") + '>›</button>';
    html += '<span class="page-info">' + (cur * PAGE_SIZE + 1) + '–' +
      Math.min(total, (cur + 1) * PAGE_SIZE) + ' of ' + total + '</span></div>';
    return html;
  }

  /* ---- Detail panel ---- */

  function renderDetail() {
    var rec = state.records.find(function (r) { return r.id === state.selectedId; });
    if (!rec) {
      els.detail.innerHTML = '<p class="empty-state">Select filters that return at least one idiom.</p>';
      return;
    }
    var related = rec.related_idioms || [];
    var relHtml = related.length
      ? '<ul>' + related.map(function (it) {
        return '<li><span>' + escapeHtml(it.idiom) + '</span><small>' +
          it.score.toFixed(2) + ' – ' + escapeHtml(it.reasons.join(", ")) + '</small></li>';
      }).join("") + '</ul>'
      : '<p class="empty-state">No strong related idioms found.</p>';
    els.detail.innerHTML =
      '<div class="detail-content"><h2>' + escapeHtml(rec.idiom) + '</h2>' +
      '<div class="detail-badges"><span>' + rec.syllable_count + ' syllables</span>' +
      '<span>' + escapeHtml(rec.rhyme_key || "no rhyme key") + '</span>' +
      '<span>' + (rec.unknown_words.length ? "unknown words" : "CMUdict covered") + '</span></div>' +
      '<h3>Tokens</h3><code>' + escapeHtml(rec.tokens.join(" | ")) + '</code>' +
      '<h3>Phonemes</h3><code>' + escapeHtml(rec.phonemes.join(" ") || "None") + '</code>' +
      '<h3>Stress</h3><code>' + escapeHtml(rec.stress_pattern.join("") || "None") + '</code>' +
      '<h3>Initial Phonemes</h3><code>' + escapeHtml(rec.initial_phonemes.join(" ") || "None") + '</code>' +
      '<h3>Unknown Words</h3><code>' + escapeHtml(rec.unknown_words.join(", ") || "None") + '</code>' +
      '<h3>Related Idioms</h3>' + relHtml + '</div>';
  }

  /* ---- Groups ---- */

  function groupBy(records, keyFn, minSize) {
    var groups = new Map();
    records.forEach(function (r) {
      var k = keyFn(r);
      if (!k) return;
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(r);
    });
    return Array.from(groups.entries())
      .filter(function (e) { return e[1].length >= minSize; })
      .sort(function (a, b) { return b[1].length - a[1].length || a[0].localeCompare(b[0]); })
      .slice(0, 12);
  }

  function renderGroups(el, groups) {
    if (!groups.length) {
      el.innerHTML = '<p class="empty-state">No matching groups.</p>';
      return;
    }
    el.innerHTML = '<div class="group-list">' + groups.map(function (e) {
      return '<div class="group-block"><h3><span>' + escapeHtml(e[0]) +
        '</span><small>' + e[1].length + ' idioms</small></h3><ul>' +
        e[1].slice(0, 8).map(function (r) {
          return '<li>' + escapeHtml(r.idiom) + '</li>';
        }).join("") + '</ul></div>';
    }).join("") + '</div>';
  }

  /* ---- D3 Force-Directed Network Graph ---- */

  function renderGraph() {
    els.graph.innerHTML = "";
    var points = state.filtered.slice(0, 120);
    if (!points.length) {
      els.graph.innerHTML = '<div class="graph-empty">No idioms match the current filters.</div>';
      return;
    }

    var idSet = new Set(points.map(function (r) { return r.id; }));
    var nodes = points.map(function (r) {
      return {
        id: r.id, idiom: r.idiom, syllables: r.syllable_count,
        rhyme: r.rhyme_key || "none", initials: initials(r).join(" ") || "none",
        allit: alliterationScore(r)
      };
    });
    var nodeIndex = {};
    nodes.forEach(function (n, i) { nodeIndex[n.id] = i; });

    // Build adjacency for hover highlight
    var adjacency = {};
    nodes.forEach(function (n) { adjacency[n.id] = new Set(); });

    var linkSet = new Set();
    var links = [];
    function addLink(src, tgt, type, strength) {
      var key = Math.min(src, tgt) + "-" + Math.max(src, tgt);
      if (linkSet.has(key)) return;
      linkSet.add(key);
      links.push({ source: nodeIndex[src], target: nodeIndex[tgt],
                   srcId: src, tgtId: tgt, type: type, strength: strength || 0.5 });
      adjacency[src].add(tgt);
      adjacency[tgt].add(src);
    }

    // Rhyme edges (stronger, drawn differently)
    var byRhyme = {};
    points.forEach(function (r) {
      if (r.rhyme_key) {
        if (!byRhyme[r.rhyme_key]) byRhyme[r.rhyme_key] = [];
        byRhyme[r.rhyme_key].push(r);
      }
    });
    Object.values(byRhyme).forEach(function (cluster) {
      if (cluster.length < 2) return;
      cluster.sort(function (a, b) { return a.idiom.localeCompare(b.idiom); });
      for (var j = 1; j < Math.min(cluster.length, 8); j++) {
        addLink(cluster[0].id, cluster[j].id, "rhyme", 0.9);
      }
    });

    // Phonetic similarity edges
    points.forEach(function (r) {
      (r.related_idioms || []).forEach(function (rel) {
        var target = points.find(function (p) { return p.idiom === rel.idiom; });
        if (target && idSet.has(target.id) && rel.score >= 0.4) {
          addLink(r.id, target.id, "phonetic", rel.score);
        }
      });
    });

    // Color scale by syllable count
    var syllMin = d3.min(nodes, function (n) { return n.syllables; });
    var syllMax = d3.max(nodes, function (n) { return n.syllables; });
    var color = d3.scaleSequential(d3.interpolateViridis).domain([syllMin, syllMax]);

    var width = els.graph.clientWidth || 600;
    var height = 520;
    var wallStr = parseInt(els.forceWall.value, 10);
    var linkDist = parseInt(els.forceLink.value, 10);
    var chargeStr = parseInt(els.forceCharge.value, 10);
    var collideRad = parseInt(els.forceCollide.value, 10);
    var sizeMult = parseFloat(els.nodeSize.value);
    var showLabels = els.showLabels.checked;

    function getRadius(d) { return (5 + 10 * d.allit) * sizeMult; }

    // Wall repulsion: custom force that pushes nodes away from all four edges
    function forceWall(strength) {
      var str = strength || 60;
      function force() {
        nodes.forEach(function (d) {
          if (d.x !== undefined) {
            var lx = d.x, rx = width - d.x;
            var ty = d.y, by = height - d.y;
            d.vx += (str / (lx * lx + 1)) - (str / (rx * rx + 1));
            d.vy += (str / (ty * ty + 1)) - (str / (by * by + 1));
          }
        });
      }
      force.strength = function(s) { str = s; return force; };
      return force;
    }

    var wallForce = forceWall(wallStr);

    graphSimulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).distance(linkDist).strength(function(l) {
        return l.type === "rhyme" ? 0.7 : 0.3;
      }))
      .force("charge", d3.forceManyBody().strength(chargeStr).distanceMax(300))
      .force("center", d3.forceCenter(width / 2, height / 2).strength(0.05))
      .force("collision", d3.forceCollide().radius(function(d) { return getRadius(d) + collideRad; }))
      .force("wall", wallForce)
      .alphaDecay(0.025)
      .velocityDecay(0.4);

    var svg = d3.select(els.graph).append("svg")
      .attr("class", "network-graph")
      .attr("viewBox", "0 0 " + width + " " + height);

    // Arrowhead / gradient defs (reuse for both link types)
    var defs = svg.append("defs");
    defs.append("filter").attr("id", "glow")
      .html('<feGaussianBlur stdDeviation="2.5" result="coloredBlur"/>' +
            '<feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>');

    // Legend
    var legend = svg.append("g").attr("class", "graph-legend")
      .attr("transform", "translate(12,12)");
    legend.append("line").attr("x1",0).attr("y1",6).attr("x2",22).attr("y2",6)
      .attr("class", "link link-rhyme");
    legend.append("text").attr("x",26).attr("y",10).attr("class","legend-label").text("Rhyme");
    legend.append("line").attr("x1",0).attr("y1",22).attr("x2",22).attr("y2",22)
      .attr("class", "link link-phonetic");
    legend.append("text").attr("x",26).attr("y",26).attr("class","legend-label").text("Phonetic");

    // Links — curved paths
    var linkG = svg.append("g").attr("class", "links");
    var link = linkG.selectAll("path")
      .data(links).join("path")
      .attr("class", function(l) { return "link link-" + l.type; })
      .attr("stroke-opacity", function(l) { return 0.3 + 0.5 * l.strength; })
      .attr("stroke-width", function(l) { return l.type === "rhyme" ? 1.8 : 1; });

    // Nodes
    var nodeG = svg.append("g").attr("class", "nodes");
    var node = nodeG.selectAll("g.node")
      .data(nodes).join("g").attr("class", "node");

    node.append("circle")
      .attr("r", getRadius)
      .attr("fill", function (d) { return color(d.syllables); })
      .attr("stroke-width", 1.5);

    node.append("text")
      .attr("class", "node-label")
      .style("display", showLabels ? "block" : "none")
      .text(function(d) {
        // Truncate long phrases so labels don't dominate
        return d.idiom.length > 22 ? d.idiom.slice(0, 20) + "…" : d.idiom;
      });

    var tooltip = d3.select(els.graph).append("div").attr("class", "graph-tooltip");

    // Hover: highlight neighbourhood
    node
      .on("mouseover", function (event, d) {
        var nbrs = adjacency[d.id];
        var connCount = nbrs.size;
        var rhymeLinks = links.filter(function(l) {
          return (l.srcId === d.id || l.tgtId === d.id) && l.type === "rhyme";
        }).length;
        tooltip.html(
          "<strong>" + escapeHtml(d.idiom) + "</strong>" +
          "<span class='tip-meta'>" + d.syllables + " syl &nbsp;·&nbsp; " +
          escapeHtml(d.rhyme) + "</span>" +
          (connCount ? "<span class='tip-conn'>" + connCount + " connection" +
            (connCount !== 1 ? "s" : "") +
            (rhymeLinks ? " · " + rhymeLinks + " rhyme" : "") + "</span>" : "")
        ).classed("visible", true);

        // Dim everything, then re-highlight neighbours
        node.classed("node-dimmed", true);
        link.classed("link-dimmed", true);

        d3.select(this).classed("node-dimmed", false).classed("node-focus", true);
        link.filter(function(l) {
          return l.srcId === d.id || l.tgtId === d.id;
        }).classed("link-dimmed", false).classed("link-focus", true);
        node.filter(function(n) {
          return nbrs.has(n.id);
        }).classed("node-dimmed", false).classed("node-neighbour", true);
      })
      .on("mousemove", function (event) {
        var rect = els.graph.getBoundingClientRect();
        tooltip.style("left", (event.clientX - rect.left + 14) + "px")
          .style("top", (event.clientY - rect.top - 14) + "px");
      })
      .on("mouseout", function () {
        tooltip.classed("visible", false);
        node.classed("node-dimmed", false).classed("node-focus", false).classed("node-neighbour", false);
        link.classed("link-dimmed", false).classed("link-focus", false);
      })
      .call(d3.drag()
        .on("start", function (event, d) {
          if (!event.active) graphSimulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on("drag", function (event, d) { d.fx = event.x; d.fy = event.y; })
        .on("end", function (event, d) {
          if (!event.active) graphSimulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
      );

    // Curved path generator
    function linkPath(l) {
      var s = l.source, t = l.target;
      if (!s.x) return "";
      var dx = t.x - s.x, dy = t.y - s.y;
      var dr = Math.sqrt(dx * dx + dy * dy);
      // Rhyme edges curve more; phonetic edges are nearly straight
      var curve = l.type === "rhyme" ? dr * 0.35 : dr * 0.12;
      return "M" + s.x + "," + s.y +
             "A" + curve + "," + curve + " 0 0,1 " + t.x + "," + t.y;
    }

    graphSimulation.on("tick", function () {
      link.attr("d", linkPath);
      node.attr("transform", function(d) {
        var r = getRadius(d);
        d.x = Math.max(r + 4, Math.min(width - r - 4, d.x));
        d.y = Math.max(r + 4, Math.min(height - r - 4, d.y));
        return "translate(" + d.x + "," + d.y + ")";
      });
    });
  }

  // --- Graph Controls ---
  els.forceLink.addEventListener("input", function() {
    if (graphSimulation) {
      graphSimulation.force("link").distance(parseInt(this.value, 10));
      graphSimulation.alpha(0.3).restart();
    }
  });
  els.forceCharge.addEventListener("input", function() {
    if (graphSimulation) {
      graphSimulation.force("charge").strength(parseInt(this.value, 10));
      graphSimulation.alpha(0.3).restart();
    }
  });
  els.forceCollide.addEventListener("input", function() {
    if (graphSimulation) {
      var collRad = parseInt(this.value, 10);
      var mult = parseFloat(els.nodeSize.value);
      graphSimulation.force("collision").radius(function(d) {
        return (5 + 10 * d.allit) * mult + collRad;
      });
      graphSimulation.alpha(0.3).restart();
    }
  });
  els.forceWall.addEventListener("input", function() {
    if (graphSimulation) {
      graphSimulation.force("wall").strength(parseInt(this.value, 10));
      graphSimulation.alpha(0.3).restart();
    }
  });
  els.nodeSize.addEventListener("input", function() {
    if (graphSimulation) {
      var mult = parseFloat(this.value);
      d3.selectAll(".network-graph circle").attr("r", function(d) {
        return (5 + 10 * d.allit) * mult;
      });
    }
  });
  els.showLabels.addEventListener("change", function() {
    var display = this.checked ? "block" : "none";
    d3.selectAll(".network-graph .node-label").style("display", display);
  });

})();
