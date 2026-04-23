from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

from phonetics import build_dataset, build_indices, dataset_stats, write_csv, write_json

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "american_idioms_clean_list.csv"
OUTPUT_DIR = ROOT / "output"
DATA_PATH = OUTPUT_DIR / "idioms_phonetic.json"
CSV_OUTPUT_PATH = OUTPUT_DIR / "idioms_phonetic.csv"
INDEX_OUTPUT_PATH = OUTPUT_DIR / "idioms_indices.json"
STATS_OUTPUT_PATH = OUTPUT_DIR / "dataset_stats.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a static GitHub Pages version of the idiom explorer."
    )
    parser.add_argument(
        "--site-dir",
        type=Path,
        default=Path("site"),
        help="Output directory passed to upload-pages-artifact.",
    )
    parser.add_argument(
        "--subpath",
        default="idiom-dictionary-network",
        help="Subdirectory where the app should be published.",
    )
    return parser.parse_args()


def ensure_dataset() -> list[dict]:
    if not DATA_PATH.exists() or not CSV_OUTPUT_PATH.exists():
        records = build_dataset(CSV_PATH)
        write_json(records, DATA_PATH)
        write_csv(records, CSV_OUTPUT_PATH)
        with INDEX_OUTPUT_PATH.open("w", encoding="utf-8") as handle:
            json.dump(build_indices(records), handle, ensure_ascii=False, indent=2)
        with STATS_OUTPUT_PATH.open("w", encoding="utf-8") as handle:
            json.dump(dataset_stats(records), handle, ensure_ascii=False, indent=2)

    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def browser_record(record: dict, index: int) -> dict:
    return {
        "id": index,
        "idiom": record["idiom"],
        "normalized_idiom": record["normalized_idiom"],
        "dict_page": record["dict_page"],
        "pdf_page": record["pdf_page"],
        "raw_entry_head": record["raw_entry_head"],
        "tokens": record["tokens"],
        "phonemes": record["phonemes"],
        "syllable_count": record["syllable_count"],
        "rhyme_key": record["rhyme_key"],
        "initial_phonemes": record["initial_phonemes"],
        "initial_phonemes_with_stopwords": record["initial_phonemes_with_stopwords"],
        "dominant_initial": record["dominant_initial"],
        "dominant_initial_with_stopwords": record["dominant_initial_with_stopwords"],
        "alliteration_score": record["alliteration_score"],
        "alliteration_score_with_stopwords": record["alliteration_score_with_stopwords"],
        "stress_pattern": record["stress_pattern"],
        "unknown_words": record["unknown_words"],
        "related_idioms": record.get("related_idioms", [])[:8],
    }


def write_static_data(records: list[dict], app_dir: Path) -> None:
    data_dir = app_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    browser_records = [browser_record(record, index) for index, record in enumerate(records)]

    with (data_dir / "idioms_phonetic.json").open("w", encoding="utf-8") as handle:
        json.dump(browser_records, handle, ensure_ascii=False, separators=(",", ":"))

    stats = dataset_stats(records)
    with (data_dir / "dataset_stats.json").open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, ensure_ascii=False, indent=2)


def write_static_assets(app_dir: Path) -> None:
    assets_dir = app_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    source_css = ROOT / "assets" / "styles.css"
    if source_css.exists():
        shutil.copy2(source_css, assets_dir / "styles.css")
    (assets_dir / "static.css").write_text(STATIC_CSS, encoding="utf-8")


def write_index(app_dir: Path, records: list[dict]) -> None:
    syllable_counts = [record["syllable_count"] for record in records]
    rhyme_clusters = Counter(record["rhyme_key"] for record in records if record["rhyme_key"])
    html = (
        INDEX_TEMPLATE.replace("__RECORD_COUNT__", f"{len(records):,}")
        .replace("__MIN_SYLLABLES__", str(min(syllable_counts)))
        .replace("__MAX_SYLLABLES__", str(max(syllable_counts)))
        .replace(
            "__RHYME_CLUSTER_COUNT__",
            str(sum(1 for count in rhyme_clusters.values() if count > 1)),
        )
    )
    (app_dir / "index.html").write_text(html, encoding="utf-8")


def write_root_redirect(site_dir: Path, subpath: str) -> None:
    target = subpath.strip("/")
    index = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url=./{target}/">
  <title>Idiom Phonetics Explorer</title>
</head>
<body>
  <p><a href="./{target}/">Open the Idiom Phonetics Explorer</a></p>
</body>
</html>
"""
    (site_dir / "index.html").write_text(index, encoding="utf-8")


def main() -> None:
    args = parse_args()
    site_dir = args.site_dir
    subpath = args.subpath.strip("/")
    app_dir = site_dir / subpath

    records = ensure_dataset()
    if site_dir.exists():
        shutil.rmtree(site_dir)
    app_dir.mkdir(parents=True, exist_ok=True)

    write_static_data(records, app_dir)
    write_static_assets(app_dir)
    write_index(app_dir, records)
    write_root_redirect(site_dir, subpath)
    (site_dir / ".nojekyll").write_text("", encoding="utf-8")

    print(f"Wrote static site to {app_dir}")
    print(f"Subpage path: /{subpath}/")


STATIC_CSS = """
.static-note {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

.static-controls {
  grid-template-columns: repeat(4, minmax(170px, 1fr));
}

.static-controls input[type="number"] {
  width: 100%;
}

.static-controls select {
  width: 100%;
  height: 38px;
  padding: 0 10px;
  border: 1px solid #c8bfb2;
  border-radius: 6px;
  background: var(--panel);
  color: var(--ink);
  font: inherit;
}

.static-controls input[type="range"] {
  width: 100%;
}

.static-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.static-table th,
.static-table td {
  padding: 8px;
  border-bottom: 1px solid #e1d8cb;
  text-align: left;
  vertical-align: top;
}

.static-table th {
  background: #efe8dc;
}

.static-table button {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--accent);
  font: inherit;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
}

.small-muted {
  color: var(--muted);
  font-size: 12px;
}

@media (max-width: 980px) {
  .static-controls {
    grid-template-columns: 1fr;
  }
}
"""


INDEX_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Idiom Phonetics Explorer</title>
  <link rel="stylesheet" href="./assets/styles.css">
  <link rel="stylesheet" href="./assets/static.css">
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body>
  <div class="app-shell">
    <header class="masthead">
      <div class="masthead-copy">
        <h1>Idiom Phonetics Explorer</h1>
        <p>__RECORD_COUNT__ American idioms indexed by syllables, rhyme, initial phonemes, and phonetic similarity.</p>
        <p class="static-note">Static GitHub Pages build. Data is loaded in your browser from this subpage.</p>
      </div>
      <div class="dataset-meta">
        <span>Records</span><strong>__RECORD_COUNT__</strong>
        <span>Syllables</span><strong>__MIN_SYLLABLES__-__MAX_SYLLABLES__</strong>
        <span>Rhyme clusters</span><strong>__RHYME_CLUSTER_COUNT__</strong>
      </div>
    </header>

    <section class="controls static-controls">
      <label><span>Search</span><input id="search" type="text" placeholder="Type an idiom or phrase fragment"></label>
      <label><span>Rhyme Key</span><select id="rhyme-key"><option value="">Any rhyme</option></select></label>
      <label><span>Initial Phoneme</span><select id="initial-phone"><option value="">Any initial</option></select></label>
      <label><span>Min Syllables</span><input id="min-syllables" type="number" min="__MIN_SYLLABLES__" max="__MAX_SYLLABLES__" value="__MIN_SYLLABLES__"></label>
      <label><span>Max Syllables</span><input id="max-syllables" type="number" min="__MIN_SYLLABLES__" max="__MAX_SYLLABLES__" value="__MAX_SYLLABLES__"></label>
      <label><span>Alliteration Floor</span><input id="alliteration" type="range" min="0" max="1" step="0.05" value="0"><strong id="alliteration-value">0.00</strong></label>
      <div class="checklist">
        <label><input id="ignore-stopwords" type="checkbox" checked> Ignore stopwords</label>
        <label><input id="hide-unknown" type="checkbox"> Hide unknown pronunciations</label>
      </div>
    </section>

    <main class="workspace">
      <section class="panel table-panel">
        <div id="results-summary" class="summary-bar"></div>
        <div id="table-wrap"></div>
      </section>
      <aside id="detail-panel" class="panel detail-panel"></aside>
      <section class="panel">
        <h2>Rhyme Groups</h2>
        <div id="rhyme-groups"></div>
      </section>
      <section class="panel">
        <h2>Alliteration Groups</h2>
        <div id="alliteration-groups"></div>
      </section>
      <section class="panel graph-panel">
        <h2>Cluster View</h2>
        <div id="cluster-graph" style="height:520px"></div>
      </section>
    </main>
  </div>

  <script>
    const state = { records: [], filtered: [], selectedId: null };

    const els = {
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
      graph: document.getElementById("cluster-graph")
    };

    fetch("./data/idioms_phonetic.json")
      .then(response => response.json())
      .then(records => {
        state.records = records;
        hydrateOptions(records);
        update();
      });

    for (const control of [els.search, els.rhyme, els.initial, els.minSyllables, els.maxSyllables, els.alliteration, els.ignoreStopwords, els.hideUnknown]) {
      control.addEventListener("input", update);
      control.addEventListener("change", update);
    }

    function hydrateOptions(records) {
      const rhymes = countValues(records.map(record => record.rhyme_key).filter(Boolean));
      Object.entries(rhymes)
        .filter(([, count]) => count > 1)
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .forEach(([key, count]) => els.rhyme.append(new Option(`${key} (${count})`, key)));

      const initials = new Set();
      records.forEach(record => {
        [...record.initial_phonemes, ...record.initial_phonemes_with_stopwords].forEach(phone => initials.add(phone));
      });
      [...initials].sort().forEach(phone => els.initial.append(new Option(phone, phone)));
    }

    function countValues(values) {
      return values.reduce((counts, value) => {
        counts[value] = (counts[value] || 0) + 1;
        return counts;
      }, {});
    }

    function initials(record) {
      return els.ignoreStopwords.checked ? record.initial_phonemes : record.initial_phonemes_with_stopwords;
    }

    function dominantInitial(record) {
      return els.ignoreStopwords.checked ? record.dominant_initial : record.dominant_initial_with_stopwords;
    }

    function alliteration(record) {
      return els.ignoreStopwords.checked ? record.alliteration_score : record.alliteration_score_with_stopwords;
    }

    function update() {
      els.alliterationValue.textContent = Number(els.alliteration.value).toFixed(2);
      const query = els.search.value.trim().toLowerCase();
      const minSyllables = Number(els.minSyllables.value);
      const maxSyllables = Number(els.maxSyllables.value);
      const floor = Number(els.alliteration.value);

      state.filtered = state.records
        .filter(record => !query || `${record.idiom} ${record.normalized_idiom} ${record.raw_entry_head}`.toLowerCase().includes(query))
        .filter(record => record.syllable_count >= minSyllables && record.syllable_count <= maxSyllables)
        .filter(record => !els.rhyme.value || record.rhyme_key === els.rhyme.value)
        .filter(record => !els.initial.value || initials(record).includes(els.initial.value))
        .filter(record => alliteration(record) >= floor)
        .filter(record => !els.hideUnknown.checked || record.unknown_words.length === 0)
        .sort((a, b) => a.syllable_count - b.syllable_count || a.idiom.localeCompare(b.idiom));

      if (!state.filtered.some(record => record.id === state.selectedId)) {
        state.selectedId = state.filtered[0]?.id ?? null;
      }
      render();
    }

    function render() {
      els.summary.innerHTML = `<div><strong>${state.filtered.length.toLocaleString()} matches</strong><span>Table shows the first 500 matches.</span></div>`;
      renderTable();
      renderDetail();
      renderGroups(els.rhymeGroups, groupBy(state.filtered.filter(record => record.rhyme_key), record => record.rhyme_key, 2));
      renderGroups(els.alliterationGroups, groupBy(state.filtered.filter(record => alliteration(record) >= Math.max(0.5, Number(els.alliteration.value))), dominantInitial, 2));
      renderGraph();
    }

    function renderTable() {
      const rows = state.filtered.slice(0, 500);
      if (!rows.length) {
        els.table.innerHTML = `<p class="empty-state">No idioms match the current filters.</p>`;
        return;
      }
      els.table.innerHTML = `
        <table class="static-table">
          <thead><tr><th>Idiom</th><th>Syllables</th><th>Rhyme Key</th><th>Initials</th><th>Alliteration</th><th>Unknown</th></tr></thead>
          <tbody>
            ${rows.map(record => `
              <tr>
                <td><button data-id="${record.id}">${escapeHtml(record.idiom)}</button></td>
                <td>${record.syllable_count}</td>
                <td>${escapeHtml(record.rhyme_key || "")}</td>
                <td>${escapeHtml(initials(record).join(" "))}</td>
                <td>${alliteration(record).toFixed(2)}</td>
                <td>${escapeHtml(record.unknown_words.join(", "))}</td>
              </tr>`).join("")}
          </tbody>
        </table>`;
      els.table.querySelectorAll("button[data-id]").forEach(button => {
        button.addEventListener("click", () => {
          state.selectedId = Number(button.dataset.id);
          renderDetail();
        });
      });
    }

    function renderDetail() {
      const record = state.records.find(item => item.id === state.selectedId);
      if (!record) {
        els.detail.innerHTML = `<p class="empty-state">Select filters that return at least one idiom.</p>`;
        return;
      }
      els.detail.innerHTML = `
        <div class="detail-content">
          <h2>${escapeHtml(record.idiom)}</h2>
          <div class="detail-badges">
            <span>${record.syllable_count} syllables</span>
            <span>${escapeHtml(record.rhyme_key || "no rhyme key")}</span>
            <span>${record.unknown_words.length ? "unknown words" : "CMUdict covered"}</span>
          </div>
          <h3>Tokens</h3><code>${escapeHtml(record.tokens.join(" | "))}</code>
          <h3>Phonemes</h3><code>${escapeHtml(record.phonemes.join(" ") || "None")}</code>
          <h3>Stress</h3><code>${escapeHtml(record.stress_pattern.join("") || "None")}</code>
          <h3>Initial Phonemes</h3><code>${escapeHtml(record.initial_phonemes.join(" ") || "None")}</code>
          <h3>Unknown Words</h3><code>${escapeHtml(record.unknown_words.join(", ") || "None")}</code>
          <h3>Related Idioms</h3>
          ${record.related_idioms.length ? `<ul>${record.related_idioms.map(item => `<li><span>${escapeHtml(item.idiom)}</span><small>${item.score.toFixed(2)} - ${escapeHtml(item.reasons.join(", "))}</small></li>`).join("")}</ul>` : `<p class="empty-state">No strong related idioms found.</p>`}
        </div>`;
    }

    function groupBy(records, keyFn, minimumSize) {
      const groups = new Map();
      records.forEach(record => {
        const key = keyFn(record);
        if (!key) return;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(record);
      });
      return [...groups.entries()]
        .filter(([, items]) => items.length >= minimumSize)
        .sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))
        .slice(0, 12);
    }

    function renderGroups(element, groups) {
      if (!groups.length) {
        element.innerHTML = `<p class="empty-state">No matching groups.</p>`;
        return;
      }
      element.innerHTML = `<div class="group-list">${groups.map(([name, items]) => `
        <div class="group-block">
          <h3><span>${escapeHtml(name)}</span><small>${items.length} idioms</small></h3>
          <ul>${items.slice(0, 8).map(item => `<li>${escapeHtml(item.idiom)}</li>`).join("")}</ul>
        </div>`).join("")}</div>`;
    }

    function renderGraph() {
      const points = state.filtered.slice(0, 180);
      if (!points.length) {
        Plotly.react(els.graph, [], { annotations: [{ text: "No idioms match the current filters.", x: 0.5, y: 0.5, xref: "paper", yref: "paper", showarrow: false }] }, { displayModeBar: false });
        return;
      }
      const rhymeCounts = countValues(points.map(record => record.rhyme_key).filter(Boolean));
      const trace = {
        type: "scatter",
        mode: "markers",
        x: points.map(record => record.syllable_count),
        y: points.map(record => alliteration(record)),
        marker: {
          size: points.map(record => 9 + Math.min(18, (rhymeCounts[record.rhyme_key] || 1) * 2)),
          color: points.map(record => rhymeCounts[record.rhyme_key] || 1),
          colorscale: "Viridis",
          line: { width: 1, color: "#2f3437" },
          colorbar: { title: "Rhyme cluster" }
        },
        text: points.map(record => `<b>${escapeHtml(record.idiom)}</b><br>Syllables: ${record.syllable_count}<br>Rhyme: ${escapeHtml(record.rhyme_key || "none")}<br>Initials: ${escapeHtml(initials(record).join(" ") || "none")}`),
        hovertemplate: "%{text}<extra></extra>"
      };
      Plotly.react(els.graph, [trace], {
        margin: { l: 50, r: 20, t: 10, b: 45 },
        paper_bgcolor: "#f7f4ef",
        plot_bgcolor: "#f7f4ef",
        xaxis: { title: "Syllable count", dtick: 1 },
        yaxis: { title: "Alliteration score", range: [-0.05, 1.05] }
      }, { displayModeBar: false, responsive: true });
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
