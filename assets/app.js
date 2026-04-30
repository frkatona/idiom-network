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
    sortAsc: true
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
    helpPanels: document.querySelectorAll("[data-help-panel]")
  };

  /* ---- Fuzzy search ---- */

  function bigrams(s) {
    var b = [];
    for (var i = 0; i < s.length - 1; i++) b.push(s.charAt(i) + s.charAt(i + 1));
    return b;
  }

  function fuzzyMatch(query, text) {
    if (!query) return true;
    query = query.trim().toLowerCase();
    text = text.toLowerCase();
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
    var start = state.page * PAGE_SIZE;
    var rows = state.filtered.slice(start, start + PAGE_SIZE);
    if (!rows.length) {
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
    html += '</tr></thead><tbody>';
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

    var linkSet = new Set();
    var links = [];
    function addLink(src, tgt) {
      var key = Math.min(src, tgt) + "-" + Math.max(src, tgt);
      if (linkSet.has(key)) return;
      linkSet.add(key);
      links.push({ source: nodeIndex[src], target: nodeIndex[tgt] });
    }

    // Rhyme edges
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
      for (var j = 1; j < Math.min(cluster.length, 10); j++) {
        addLink(cluster[0].id, cluster[j].id);
      }
    });

    // Related idiom edges
    points.forEach(function (r) {
      (r.related_idioms || []).forEach(function (rel) {
        var target = points.find(function (p) { return p.idiom === rel.idiom; });
        if (target && idSet.has(target.id) && rel.score >= 0.4) {
          addLink(r.id, target.id);
        }
      });
    });

    // Color scale
    var syllMin = d3.min(nodes, function (n) { return n.syllables; });
    var syllMax = d3.max(nodes, function (n) { return n.syllables; });
    var color = d3.scaleSequential(d3.interpolateViridis).domain([syllMin, syllMax]);

    var width = els.graph.clientWidth || 600;
    var height = 520;

    var svg = d3.select(els.graph).append("svg")
      .attr("class", "network-graph")
      .attr("viewBox", "0 0 " + width + " " + height);

    var tooltip = d3.select(els.graph).append("div").attr("class", "graph-tooltip");

    var simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).distance(60))
      .force("charge", d3.forceManyBody().strength(-80))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(12));

    var link = svg.append("g").selectAll("line")
      .data(links).join("line").attr("class", "link");

    var node = svg.append("g").selectAll("circle")
      .data(nodes).join("circle").attr("class", "node")
      .attr("r", function (d) { return 6 + 12 * d.allit; })
      .attr("fill", function (d) { return color(d.syllables); })
      .on("mouseover", function (event, d) {
        tooltip.html("<strong>" + escapeHtml(d.idiom) + "</strong>" +
          "Syllables: " + d.syllables + "<br>" +
          "Rhyme: " + escapeHtml(d.rhyme) + "<br>" +
          "Initials: " + escapeHtml(d.initials))
          .classed("visible", true);
      })
      .on("mousemove", function (event) {
        var rect = els.graph.getBoundingClientRect();
        tooltip.style("left", (event.clientX - rect.left + 12) + "px")
          .style("top", (event.clientY - rect.top - 10) + "px");
      })
      .on("mouseout", function () { tooltip.classed("visible", false); })
      .call(d3.drag()
        .on("start", function (event, d) {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on("drag", function (event, d) { d.fx = event.x; d.fy = event.y; })
        .on("end", function (event, d) {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
      );

    simulation.on("tick", function () {
      link.attr("x1", function (d) { return d.source.x; })
        .attr("y1", function (d) { return d.source.y; })
        .attr("x2", function (d) { return d.target.x; })
        .attr("y2", function (d) { return d.target.y; });
      node.attr("cx", function (d) { return d.x = Math.max(10, Math.min(width - 10, d.x)); })
        .attr("cy", function (d) { return d.y = Math.max(10, Math.min(height - 10, d.y)); });
    });
  }
})();
