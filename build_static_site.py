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
        default=Path("docs"),
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
    source_dir = ROOT / "assets"
    for filename in ("styles.css", "static.css", "app.js"):
        source = source_dir / filename
        if source.exists():
            shutil.copy2(source, assets_dir / filename)


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


INDEX_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Idiom Phonetics Explorer</title>
  <meta name="description" content="Explore __RECORD_COUNT__ American idioms by syllable count, rhyme, alliteration, stress patterns, and phonetic similarity.">
  <link rel="stylesheet" href="./assets/styles.css">
  <link rel="stylesheet" href="./assets/static.css">
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
            <button id="help-tab-phonemes" class="help-tab help-tab-selected" type="button" role="tab" aria-selected="true" aria-controls="help-panel-phonemes" data-help-tab="phonemes">Phonemes</button>
            <button id="help-tab-rhyme" class="help-tab" type="button" role="tab" aria-selected="false" aria-controls="help-panel-rhyme" data-help-tab="rhyme">Rhyme Key</button>
            <button id="help-tab-initials" class="help-tab" type="button" role="tab" aria-selected="false" aria-controls="help-panel-initials" data-help-tab="initials">Initials</button>
            <button id="help-tab-alliteration" class="help-tab" type="button" role="tab" aria-selected="false" aria-controls="help-panel-alliteration" data-help-tab="alliteration">Alliteration Floor</button>
            <button id="help-tab-stress" class="help-tab" type="button" role="tab" aria-selected="false" aria-controls="help-panel-stress" data-help-tab="stress">Stress</button>
            <button id="help-tab-cleaning" class="help-tab" type="button" role="tab" aria-selected="false" aria-controls="help-panel-cleaning" data-help-tab="cleaning">Data Cleaning</button>
          </div>
          <section id="help-panel-phonemes" class="help-tab-panel is-active" role="tabpanel" aria-labelledby="help-tab-phonemes" data-help-panel="phonemes">
            <h3>Phoneme pronunciation guide</h3>
            <p>Phonemes are the speech sounds behind each idiom. This app uses ARPABET codes: consonants are plain letters, and vowels usually end with a stress number.</p>
            <p class="help-link-row"><a href="https://en.wikipedia.org/wiki/ARPABET" target="_blank" rel="noreferrer noopener">ARPABET on Wikipedia</a></p>
            <div class="help-example"><span>Example</span><code>K AE1 T = cat</code><span>Phrase</span><strong>let the cat out of the bag</strong></div>
            <div class="phoneme-guide">
              <div class="phoneme-card"><code>AA</code><span>f<u>a</u>ther</span></div>
              <div class="phoneme-card"><code>AE</code><span>c<u>a</u>t</span></div>
              <div class="phoneme-card"><code>AH</code><span>str<u>u</u>t</span></div>
              <div class="phoneme-card"><code>AO</code><span>th<u>ou</u>ght</span></div>
              <div class="phoneme-card"><code>AW</code><span>c<u>ow</u></span></div>
              <div class="phoneme-card"><code>AY</code><span>m<u>y</u></span></div>
              <div class="phoneme-card"><code>EH</code><span>b<u>e</u>d</span></div>
              <div class="phoneme-card"><code>ER</code><span>b<u>ir</u>d</span></div>
              <div class="phoneme-card"><code>EY</code><span>d<u>ay</u></span></div>
              <div class="phoneme-card"><code>IH</code><span>s<u>i</u>t</span></div>
              <div class="phoneme-card"><code>IY</code><span>s<u>ee</u></span></div>
              <div class="phoneme-card"><code>OW</code><span>g<u>o</u></span></div>
              <div class="phoneme-card"><code>OY</code><span>b<u>oy</u></span></div>
              <div class="phoneme-card"><code>UH</code><span>b<u>oo</u>k</span></div>
              <div class="phoneme-card"><code>UW</code><span>t<u>oo</u></span></div>
              <div class="phoneme-card"><code>CH</code><span><u>ch</u>air</span></div>
              <div class="phoneme-card"><code>DH</code><span><u>th</u>is</span></div>
              <div class="phoneme-card"><code>HH</code><span><u>h</u>at</span></div>
              <div class="phoneme-card"><code>JH</code><span><u>j</u>am</span></div>
              <div class="phoneme-card"><code>NG</code><span>si<u>ng</u></span></div>
              <div class="phoneme-card"><code>SH</code><span><u>sh</u>oe</span></div>
              <div class="phoneme-card"><code>TH</code><span><u>th</u>in</span></div>
              <div class="phoneme-card"><code>ZH</code><span>mea<u>s</u>ure</span></div>
            </div>
            <ul>
              <li>Stress numbers attach to vowels: 0 is unstressed, 1 is primary stress, and 2 is secondary stress.</li>
              <li>Consonant codes such as B, K, L, M, P, S, T, and Z are read much like their letters.</li>
              <li>Read a phrase left to right as sounds, not spelling: F OW1 N is phone.</li>
            </ul>
          </section>
          <section id="help-panel-rhyme" class="help-tab-panel" role="tabpanel" aria-labelledby="help-tab-rhyme" data-help-panel="rhyme" hidden>
            <h3>Rhyme key</h3>
            <p>A rhyme key is the ending sound signature for the whole idiom. The app starts at the last stressed vowel and keeps every phoneme to the end.</p>
            <p class="help-link-row"><a href="https://en.wikipedia.org/wiki/Rhyme" target="_blank" rel="noreferrer noopener">Rhyme on Wikipedia</a></p>
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
            <p class="help-link-row"><a href="https://en.wikipedia.org/wiki/Syllable#Onset" target="_blank" rel="noreferrer noopener">Syllable onset on Wikipedia</a></p>
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
            <p class="help-link-row"><a href="https://en.wikipedia.org/wiki/Alliteration" target="_blank" rel="noreferrer noopener">Alliteration on Wikipedia</a></p>
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
            <p class="help-link-row"><a href="https://en.wikipedia.org/wiki/Stress_(linguistics)" target="_blank" rel="noreferrer noopener">Stress (linguistics) on Wikipedia</a></p>
            <div class="help-example"><span>Example</span><code>1 0 1</code><span>Phrase</span><strong>by and by</strong></div>
            <ul>
              <li>ARPABET vowels carry stress numbers: AH0 is unstressed, EH1 is stressed.</li>
              <li>The app treats primary and secondary stress as stressed.</li>
              <li>Stress matters for rhyme because the rhyme key begins near the final stressed vowel.</li>
            </ul>
          </section>
          <section id="help-panel-cleaning" class="help-tab-panel" role="tabpanel" aria-labelledby="help-tab-cleaning" data-help-panel="cleaning" hidden>
            <h3>Data Cleaning</h3>
            <p>To improve phonetic groupings, the system automatically strips dictionary placeholder phrases during its sound analysis (but leaves them in the display names).</p>
            <ul>
              <li><strong>Parentheticals:</strong> Anything enclosed in parentheses (e.g., <code>(oneself)</code>) is removed.</li>
              <li><strong>Exact Matches:</strong> Phrases like <code>someone or something</code>, <code>doing something</code>, and <code>someone's</code> are removed.</li>
              <li><strong>Trailing "something":</strong> If <code>something</code> appears at the very end of an idiom, it is removed.</li>
              <li><strong>Prepositions:</strong> Prepositions attached to placeholders (like the <code>with</code> in <code>with someone or something</code>) are preserved to maintain the core phrasal verb.</li>
            </ul>
          </section>
        </div>
      </div>
    </div>

    <section class="controls static-controls">
      <label><span>Search</span><input id="search" type="text" placeholder="Type an idiom or phrase fragment"></label>
      <label><span>Rhyme Key</span><select id="rhyme-key"><option value="">Any rhyme</option></select></label>
      <label><span>Initial Phoneme</span><select id="initial-phone"><option value="">Any initial</option></select></label>
      <label class="syllable-range-control"><span>Syllables</span><div class="range-slider" data-min="__MIN_SYLLABLES__" data-max="__MAX_SYLLABLES__"><div id="syllable-range-track" class="range-slider-track" style="--range-start:0%;--range-end:100%"></div><div id="syllable-range-ticks" class="range-slider-ticks"></div><input id="min-syllables" type="range" min="__MIN_SYLLABLES__" max="__MAX_SYLLABLES__" step="1" value="__MIN_SYLLABLES__" aria-label="Minimum syllables"><input id="max-syllables" type="range" min="__MIN_SYLLABLES__" max="__MAX_SYLLABLES__" step="1" value="__MAX_SYLLABLES__" aria-label="Maximum syllables"></div></label>
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
        <div class="graph-controls">
          <label title="Distance between connected nodes">
            <span>Link Dist</span>
            <input id="force-link" type="range" min="10" max="150" value="60">
          </label>
          <label title="How strongly nodes repel each other">
            <span>Repulsion</span>
            <input id="force-charge" type="range" min="-200" max="0" value="-80">
          </label>
          <label title="Minimum space between nodes">
            <span>Collision</span>
            <input id="force-collide" type="range" min="1" max="30" value="12">
          </label>
          <label title="Base size multiplier for nodes">
            <span>Node Size</span>
            <input id="node-size" type="range" min="0.5" max="3" step="0.1" value="1">
          </label>
          <label class="toggle-label" title="Show idiom text inside nodes">
            <input id="show-labels" type="checkbox">
            <span>Show Labels</span>
          </label>
        </div>
        <div id="cluster-graph" style="position:relative"></div>
      </section>
    </main>
  </div>

  <script src="./assets/app.js"></script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
