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

.cluster-legend text {
  fill: #333;
  font-family: inherit;
}

.nodes text {
  font-family: inherit;
  pointer-events: none;
  fill: #222;
}

.links line {
  stroke: #999;
  stroke-opacity: 0.6;
}

.graph-legend {
  font-size: 13px;
  color: #333;
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
  <script src="https://d3js.org/d3.v7.min.js"></script>
</head>
<body>
  <div class="app-shell">
    <header class="masthead">
      <div class="masthead-copy">
        <h1>Idiom Phonetics Explorer</h1>
        <p>__RECORD_COUNT__ American idioms indexed by syllables, rhyme, initial phonemes, and phonetic similarity.</p>
        <p class="static-note">Static GitHub Pages build. Data is loaded in your browser from this subpage.</p>
      </div>
      <div class="masthead-tools">
        <button id="help-open" class="help-button" type="button" title="Open phonetics guide" aria-label="Open phonetics guide" aria-haspopup="dialog" aria-expanded="false">?</button>
        <div class="dataset-meta">
          <span>Records</span><strong>__RECORD_COUNT__</strong>
          <span>Syllables</span><strong>__MIN_SYLLABLES__-__MAX_SYLLABLES__</strong>
          <span>Rhyme clusters</span><strong>__RHYME_CLUSTER_COUNT__</strong>
        </div>
      </div>
    </header>

    <div id="help-modal" class="help-modal" role="dialog" aria-modal="true" aria-labelledby="help-title">
      <div class="help-backdrop" data-close-help></div>
      <div class="help-dialog" role="document">
        <div class="help-modal-header">
          <div>
            <p class="help-kicker">Phonetic Guide</p>
            <h2 id="help-title">How the sound filters work</h2>
          </div>
          <button id="help-close" class="help-close-button" type="button" title="Close help" aria-label="Close help">&times;</button>
        </div>
        <p class="help-intro">These labels are sound-based. Read the phoneme codes as compact pronunciation hints, then use the filters to compare idioms by how they sound.</p>
        <div class="help-tabs-shell">
          <div class="help-tabs" role="tablist" aria-label="Phonetics lessons">
            <button id="help-tab-rhyme" class="help-tab help-tab-selected" type="button" role="tab" aria-selected="true" aria-controls="help-panel-rhyme" data-help-tab="rhyme">Rhyme Key</button>
            <button id="help-tab-initials" class="help-tab" type="button" role="tab" aria-selected="false" aria-controls="help-panel-initials" data-help-tab="initials">Initials</button>
            <button id="help-tab-alliteration" class="help-tab" type="button" role="tab" aria-selected="false" aria-controls="help-panel-alliteration" data-help-tab="alliteration">Alliteration Floor</button>
            <button id="help-tab-stress" class="help-tab" type="button" role="tab" aria-selected="false" aria-controls="help-panel-stress" data-help-tab="stress">Stress</button>
            <button id="help-tab-phonemes" class="help-tab" type="button" role="tab" aria-selected="false" aria-controls="help-panel-phonemes" data-help-tab="phonemes">Phonemes</button>
          </div>
          <section id="help-panel-rhyme" class="help-tab-panel is-active" role="tabpanel" aria-labelledby="help-tab-rhyme" data-help-panel="rhyme">
            <h3>Rhyme key</h3>
            <p>A rhyme key is the ending sound signature for the whole idiom. The app starts at the last stressed vowel and keeps every phoneme to the end.</p>
            <div class="help-example"><span>Example</span><code>EH1 F ER0 T</code><span>Phrase</span><strong>an A for effort</strong></div>
            <ul>
              <li>Use it to find idioms whose endings sound alike.</li>
              <li>Spelling does not matter; the ARPABET sound codes do.</li>
              <li>Blank keys mean the app could not find enough pronunciation data.</li>
            </ul>
          </section>
          <section id="help-panel-initials" class="help-tab-panel" role="tabpanel" aria-labelledby="help-tab-initials" data-help-panel="initials" hidden>
            <h3>Initials</h3>
            <p>Initials are first consonant sounds from counted words, not first letters. Sound is what matters: cat and kite share K, and phone and fun share F even though they do not share the same first letter.</p>
            <div class="help-example"><span>Example</span><code>L K B</code><span>Phrase</span><strong>let the cat out of the bag (stopwords ignored)</strong></div>
            <ul>
              <li>Words that begin with a vowel may not add an initial consonant.</li>
              <li>The stopword option can skip small words such as a, the, of, and to.</li>
              <li>Use the Initial Phoneme filter to gather idioms that start with a chosen sound.</li>
            </ul>
          </section>
          <section id="help-panel-alliteration" class="help-tab-panel" role="tabpanel" aria-labelledby="help-tab-alliteration" data-help-panel="alliteration" hidden>
            <h3>Alliteration floor</h3>
            <p>The floor is the minimum repeated-initial score an idiom must reach. The score is the share of counted words using the most common initial sound.</p>
            <div class="help-example"><span>Example</span><code>0.67 (D F F)</code><span>Phrase</span><strong>add fuel to the fire</strong></div>
            <ul>
              <li>0.00 lets every idiom through.</li>
              <li>0.50 keeps idioms where at least half of the counted initials match.</li>
              <li>1.00 keeps only phrases where every counted initial matches.</li>
            </ul>
          </section>
          <section id="help-panel-stress" class="help-tab-panel" role="tabpanel" aria-labelledby="help-tab-stress" data-help-panel="stress" hidden>
            <h3>Stress</h3>
            <p>Stress marks show which syllables are emphasized in pronunciation. Here, 1 means stressed and 0 means unstressed.</p>
            <div class="help-example"><span>Example</span><code>1 0 1</code><span>Phrase</span><strong>by and by</strong></div>
            <ul>
              <li>ARPABET vowels carry stress numbers: AH0 is unstressed, EH1 is stressed.</li>
              <li>The app treats primary and secondary stress as stressed.</li>
              <li>Stress matters for rhyme because the rhyme key begins near the final stressed vowel.</li>
            </ul>
          </section>
          <section id="help-panel-phonemes" class="help-tab-panel" role="tabpanel" aria-labelledby="help-tab-phonemes" data-help-panel="phonemes" hidden>
            <h3>Phoneme pronunciation guide</h3>
            <p>Phonemes are the speech sounds behind each idiom. This app uses ARPABET codes: consonants are plain letters, and vowels usually end with a stress number.</p>
            <div class="help-example"><span>Example</span><code>K AE1 T = cat</code><span>Phrase</span><strong>let the cat out of the bag</strong></div>
            <div class="phoneme-guide">
              <div class="phoneme-card"><code>AA</code><span>father</span></div>
              <div class="phoneme-card"><code>AE</code><span>cat</span></div>
              <div class="phoneme-card"><code>AH</code><span>strut or sofa</span></div>
              <div class="phoneme-card"><code>AO</code><span>thought</span></div>
              <div class="phoneme-card"><code>AW</code><span>cow</span></div>
              <div class="phoneme-card"><code>AY</code><span>my</span></div>
              <div class="phoneme-card"><code>EH</code><span>bed</span></div>
              <div class="phoneme-card"><code>ER</code><span>bird</span></div>
              <div class="phoneme-card"><code>EY</code><span>day</span></div>
              <div class="phoneme-card"><code>IH</code><span>sit</span></div>
              <div class="phoneme-card"><code>IY</code><span>see</span></div>
              <div class="phoneme-card"><code>OW</code><span>go</span></div>
              <div class="phoneme-card"><code>OY</code><span>boy</span></div>
              <div class="phoneme-card"><code>UH</code><span>book</span></div>
              <div class="phoneme-card"><code>UW</code><span>too</span></div>
              <div class="phoneme-card"><code>CH</code><span>chair</span></div>
              <div class="phoneme-card"><code>DH</code><span>this</span></div>
              <div class="phoneme-card"><code>HH</code><span>hat</span></div>
              <div class="phoneme-card"><code>JH</code><span>judge</span></div>
              <div class="phoneme-card"><code>NG</code><span>sing</span></div>
              <div class="phoneme-card"><code>SH</code><span>shoe</span></div>
              <div class="phoneme-card"><code>TH</code><span>thin</span></div>
              <div class="phoneme-card"><code>ZH</code><span>measure</span></div>
            </div>
            <ul>
              <li>Stress numbers attach to vowels: 0 is unstressed, 1 is primary stress, and 2 is secondary stress.</li>
              <li>Consonant codes such as B, K, L, M, P, S, T, and Z are read much like their letters.</li>
              <li>Read a phrase left to right as sounds, not spelling: F OW1 N is phone.</li>
            </ul>
          </section>
        </div>
      </div>
    </div>

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
      graph: document.getElementById("cluster-graph"),
      helpOpen: document.getElementById("help-open"),
      helpClose: document.getElementById("help-close"),
      helpModal: document.getElementById("help-modal"),
      helpTabs: document.querySelectorAll("[data-help-tab]"),
      helpPanels: document.querySelectorAll("[data-help-panel]")
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

    els.helpOpen.addEventListener("click", openHelp);
    els.helpClose.addEventListener("click", closeHelp);
    els.helpModal.querySelector("[data-close-help]").addEventListener("click", closeHelp);
    els.helpTabs.forEach(button => {
      button.addEventListener("click", () => selectHelpTab(button.dataset.helpTab));
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && els.helpModal.classList.contains("is-open")) {
        closeHelp();
      }
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
      els.helpTabs.forEach(button => {
        const selected = button.dataset.helpTab === name;
        button.classList.toggle("help-tab-selected", selected);
        button.setAttribute("aria-selected", selected ? "true" : "false");
      });
      els.helpPanels.forEach(panel => {
        const selected = panel.dataset.helpPanel === name;
        panel.classList.toggle("is-active", selected);
        panel.hidden = !selected;
      });
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
          <thead><tr><th>Idiom</th><th>Syllables</th><th>Rhyme Key</th><th>Initials</th><th>Stress</th><th>Alliteration</th></tr></thead>
          <tbody>
            ${rows.map(record => `
              <tr>
                <td><button data-id="${record.id}">${escapeHtml(record.idiom)}</button></td>
                <td>${record.syllable_count}</td>
                <td>${escapeHtml(record.rhyme_key || "")}</td>
                <td>${escapeHtml(initials(record).join(" "))}</td>
                <td>${escapeHtml(record.stress_pattern.join("") || "")}</td>
                <td>${alliteration(record).toFixed(2)}</td>
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
      // D3 cluster-force network that links idioms by related scores and groups by rhyme key
      const points = state.filtered.slice(0, 300);
      els.graph.innerHTML = ""; // clear previous contents
      if (!points.length) {
        const p = document.createElement('p');
        p.className = 'empty-state';
        p.textContent = 'No idioms match the current filters.';
        els.graph.appendChild(p);
        return;
      }

      const width = els.graph.clientWidth || 900;
      const height = Math.max(300, els.graph.clientHeight || 520);

      // map idiom text to record id for related links
      const idiomToId = new Map(state.records.map(r => [r.idiom, r.id]));
      const rhymeCounts = countValues(points.map(record => record.rhyme_key).filter(Boolean));

      // build rhyme cluster keys (only those with more than one member)
      const clusterKeys = [...new Set(points.map(p => p.rhyme_key).filter(k => k && (rhymeCounts[k] > 1)))];

      // nodes: idioms + cluster nodes
      const nodes = [];
      const clusterNodes = clusterKeys.map((k, i) => ({ id: `cluster:${k}`, label: k, type: 'cluster', index: i }));
      const idSet = new Set();
      points.forEach(record => {
        nodes.push({
          id: record.id,
          label: record.idiom,
          type: 'idiom',
          group: record.rhyme_key || 'none',
          size: 6 + Math.min(18, (rhymeCounts[record.rhyme_key] || 1) * 2),
          recordId: record.id
        });
        idSet.add(record.id);
      });
      clusterNodes.forEach(c => nodes.push(c));

      // links: idiom -> cluster, and idiom -> related idiom (if present in current points)
      const links = [];
      points.forEach(record => {
        const k = record.rhyme_key;
        if (k && rhymeCounts[k] > 1) {
          links.push({ source: record.id, target: `cluster:${k}`, value: 1 });
        }
        (record.related_idioms || []).forEach(rel => {
          const targetId = idiomToId.get(rel.idiom);
          if (typeof targetId !== 'undefined' && idSet.has(targetId) && targetId !== record.id) {
            links.push({ source: record.id, target: targetId, value: rel.score || 0.3 });
          }
        });
      });

      const svg = d3.select(els.graph).append('svg')
        .attr('width', '100%')
        .attr('height', height)
        .attr('viewBox', `0 0 ${width} ${height}`)
        .style('background', '#f7f4ef');

      const g = svg.append('g');

      const color = d3.scaleOrdinal(d3.schemeTableau10).domain(clusterKeys);

      const link = g.append('g')
          .attr('class', 'links')
        .selectAll('line')
        .data(links)
        .enter().append('line')
          .attr('stroke-width', d => Math.max(1, d.value * 2))
          .attr('stroke', '#9aa5a8')
          .attr('opacity', 0.6);

      const node = g.append('g')
          .attr('class', 'nodes')
        .selectAll('g')
        .data(nodes)
        .enter().append('g')
          .attr('data-id', d => d.id)
          .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

      node.append('circle')
        .attr('r', d => d.type === 'cluster' ? 18 : d.size)
        .attr('fill', d => d.type === 'cluster' ? '#ffffff' : (d.group && color(d.group) ? color(d.group) : '#7a7f83'))
        .attr('stroke', d => d.type === 'cluster' ? '#2f3437' : '#2f3437')
        .attr('stroke-width', d => d.type === 'cluster' ? 2 : 1);

      node.append('text')
        .attr('x', d => d.type === 'cluster' ? 22 : 10)
        .attr('y', 4)
        .text(d => d.type === 'cluster' ? (d.label.length > 18 ? d.label.slice(0, 15) + '…' : d.label) : (d.label.length > 28 ? d.label.slice(0, 25) + '…' : d.label))
        .style('font-size', d => d.type === 'cluster' ? '12px' : '10px')
        .style('fill', '#222');

      const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(d => d.target && String(d.target).startsWith('cluster:') ? 40 : 60).strength(0.6))
        .force('charge', d3.forceManyBody().strength(d => d.type === 'cluster' ? -400 : -60))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => (d.type === 'cluster' ? 24 : (d.size + 6))))
        .on('tick', ticked);

      if (clusterKeys.length) {
        const centers = new Map();
        clusterKeys.forEach((k, i) => {
          const x = (i + 1) * (width / (clusterKeys.length + 1));
          centers.set(k, { x, y: height / 2 });
        });
        simulation.force('x', d3.forceX(d => (d.type === 'idiom' && centers.has(d.group)) ? centers.get(d.group).x : width / 2).strength(0.12));
        simulation.force('y', d3.forceY(d => (d.type === 'idiom' && centers.has(d.group)) ? centers.get(d.group).y : height / 2).strength(0.12));
      }

      svg.call(d3.zoom().on('zoom', (event) => g.attr('transform', event.transform)));

      node.on('click', (event, d) => {
        if (d.type === 'idiom') {
          state.selectedId = d.recordId;
          renderDetail();
        }
      }).on('mouseover', function(event, d) {
        d3.select(this).select('circle').attr('stroke-width', 3);
      }).on('mouseout', function(event, d) {
        d3.select(this).select('circle').attr('stroke-width', d.type === 'cluster' ? 2 : 1);
      });

      function ticked() {
        link
          .attr('x1', d => findNodePos(d.source).x)
          .attr('y1', d => findNodePos(d.source).y)
          .attr('x2', d => findNodePos(d.target).x)
          .attr('y2', d => findNodePos(d.target).y);

        node.attr('transform', d => `translate(${d.x},${d.y})`);
      }

      function findNodePos(ref) {
        return (typeof ref === 'object') ? { x: ref.x, y: ref.y } : (nodes.find(n => n.id === ref) || { x: width/2, y: height/2 });
      }

      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }
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
