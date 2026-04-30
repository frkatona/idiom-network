from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import networkx as nx
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback_context, dash_table, dcc, html
from rapidfuzz import fuzz

from phonetics import build_dataset, build_indices, dataset_stats, write_csv, write_json

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "american_idioms_clean_list.csv"
OUTPUT_DIR = ROOT / "output"
DATA_PATH = OUTPUT_DIR / "idioms_phonetic.json"
CSV_OUTPUT_PATH = OUTPUT_DIR / "idioms_phonetic.csv"
INDEX_OUTPUT_PATH = OUTPUT_DIR / "idioms_indices.json"
STATS_OUTPUT_PATH = OUTPUT_DIR / "dataset_stats.json"


def ensure_dataset() -> None:
    if DATA_PATH.exists() and CSV_OUTPUT_PATH.exists():
        return

    records = build_dataset(CSV_PATH)
    write_json(records, DATA_PATH)
    write_csv(records, CSV_OUTPUT_PATH)
    with INDEX_OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(build_indices(records), handle, ensure_ascii=False, indent=2)
    with STATS_OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(dataset_stats(records), handle, ensure_ascii=False, indent=2)


def load_records() -> list[dict[str, Any]]:
    ensure_dataset()
    with DATA_PATH.open(encoding="utf-8") as handle:
        records = json.load(handle)
    for index, record in enumerate(records):
        record["id"] = index
        record["_search_text"] = " ".join(
            [
                record["idiom"],
                record["normalized_idiom"],
                record.get("raw_entry_head", ""),
            ]
        ).lower()
    return records


RECORDS = load_records()
RECORD_BY_ID = {record["id"]: record for record in RECORDS}
MIN_SYLLABLES = min(record["syllable_count"] for record in RECORDS)
MAX_SYLLABLES = max(record["syllable_count"] for record in RECORDS)


def all_initials(record: dict[str, Any], ignore_stopwords: bool) -> list[str]:
    key = "initial_phonemes" if ignore_stopwords else "initial_phonemes_with_stopwords"
    return record.get(key, [])


def alliteration_value(record: dict[str, Any], ignore_stopwords: bool) -> float:
    key = "alliteration_score" if ignore_stopwords else "alliteration_score_with_stopwords"
    return float(record.get(key) or 0)


def dominant_initial(record: dict[str, Any], ignore_stopwords: bool) -> str:
    key = "dominant_initial" if ignore_stopwords else "dominant_initial_with_stopwords"
    return record.get(key, "")


def make_rhyme_options() -> list[dict[str, str]]:
    counts = Counter(record["rhyme_key"] for record in RECORDS if record["rhyme_key"])
    return [
        {"label": f"{key} ({count})", "value": key}
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if count > 1
    ]


def make_initial_options() -> list[dict[str, str]]:
    initials = sorted(
        {
            phone
            for record in RECORDS
            for phone in (
                record.get("initial_phonemes", [])
                + record.get("initial_phonemes_with_stopwords", [])
            )
        }
    )
    return [{"label": phone, "value": phone} for phone in initials]


def search_matches(record: dict[str, Any], query: str) -> bool:
    query = query.strip().lower()
    if not query:
        return True
    if query in record["_search_text"]:
        return True
    return len(query) >= 3 and fuzz.partial_ratio(query, record["_search_text"]) >= 82


def filter_records(
    query: str | None,
    syllable_range: list[int] | None,
    rhyme_key: str | None,
    initial_phone: str | None,
    alliteration_threshold: float | None,
    options: list[str] | None,
) -> list[dict[str, Any]]:
    options = options or []
    ignore_stopwords = "ignore_stopwords" in options
    hide_unknown = "hide_unknown" in options
    syllable_range = syllable_range or [MIN_SYLLABLES, MAX_SYLLABLES]
    low, high = syllable_range
    threshold = alliteration_threshold or 0

    filtered = []
    for record in RECORDS:
        if not search_matches(record, query or ""):
            continue
        if not low <= record["syllable_count"] <= high:
            continue
        if rhyme_key and record["rhyme_key"] != rhyme_key:
            continue
        if initial_phone and initial_phone not in all_initials(record, ignore_stopwords):
            continue
        if alliteration_value(record, ignore_stopwords) < threshold:
            continue
        if hide_unknown and record["unknown_words"]:
            continue
        filtered.append(record)

    return sorted(filtered, key=lambda item: (item["syllable_count"], item["idiom"].lower()))


def table_rows(records: list[dict[str, Any]], ignore_stopwords: bool) -> list[dict[str, Any]]:
    rows = []
    for record in records[:500]:
        rows.append(
            {
                "id": record["id"],
                "idiom": record["idiom"],
                "syllables": record["syllable_count"],
                "rhyme_key": record["rhyme_key"],
                "initials": " ".join(all_initials(record, ignore_stopwords)),
                "stress": "".join(str(bit) for bit in record["stress_pattern"]),
                "alliteration": alliteration_value(record, ignore_stopwords),
            }
        )
    return rows


def default_active_cell(table_data: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not table_data:
        return None
    first_row = table_data[0]
    return {
        "row": 0,
        "column": 0,
        "column_id": "idiom",
        "row_id": first_row["id"],
    }


def active_cell_for_data(
    table_data: list[dict[str, Any]],
    current_active_cell: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not table_data:
        return None

    if current_active_cell and current_active_cell.get("row_id") is not None:
        active_row_id = current_active_cell["row_id"]
        for row_index, row in enumerate(table_data):
            if row["id"] == active_row_id:
                return {
                    "row": row_index,
                    "column": current_active_cell.get("column", 0),
                    "column_id": current_active_cell.get("column_id", "idiom"),
                    "row_id": active_row_id,
                }

    return default_active_cell(table_data)


def table_style(selected_row_id: int | None) -> list[dict[str, Any]]:
    styles = [
        {
            "if": {"state": "active"},
            "backgroundColor": "#dbe9e6",
            "border": "1px solid #33776b",
        }
    ]
    if selected_row_id is not None:
        styles.append(
            {
                "if": {"filter_query": f"{{id}} = {selected_row_id}"},
                "backgroundColor": "#dbe9e6",
            }
        )
    return styles


def group_list(title: str, groups: list[tuple[str, list[dict[str, Any]]]]) -> html.Div:
    if not groups:
        return html.Div("No matching groups.", className="empty-state")

    return html.Div(
        [
            html.Div(
                [
                    html.H3([html.Span(name), html.Small(f"{len(items)} idioms")]),
                    html.Ul([html.Li(item["idiom"]) for item in items[:8]]),
                ],
                className="group-block",
            )
            for name, items in groups[:12]
        ],
        className="group-list",
        title=title,
    )


def rhyme_groups(records: list[dict[str, Any]]) -> html.Div:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record["rhyme_key"]:
            grouped[record["rhyme_key"]].append(record)
    groups = sorted(
        ((key, items) for key, items in grouped.items() if len(items) > 1),
        key=lambda item: (-len(item[1]), item[0]),
    )
    return group_list("Rhyme groups", groups)


def alliteration_groups(
    records: list[dict[str, Any]],
    ignore_stopwords: bool,
    threshold: float,
) -> html.Div:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    floor = max(0.5, threshold)
    for record in records:
        key = dominant_initial(record, ignore_stopwords)
        if key and alliteration_value(record, ignore_stopwords) >= floor:
            grouped[key].append(record)
    groups = sorted(
        ((key, items) for key, items in grouped.items() if len(items) > 1),
        key=lambda item: (-len(item[1]), item[0]),
    )
    return group_list("Alliteration groups", groups)


HELP_TOPICS = [
    {
        "value": "phonemes",
        "label": "Phonemes",
        "title": "Phoneme pronunciation guide",
        "example": "K AE1 T = cat",
        "phrase": "let the cat out of the bag",
        "copy": "Phonemes are the speech sounds behind each idiom. This app uses ARPABET codes: consonants are plain letters, and vowels usually end with a stress number.",
        "wikipedia_label": "ARPABET on Wikipedia",
        "wikipedia_url": "https://en.wikipedia.org/wiki/ARPABET",
        "guide": [
            {"phone": "AA", "segments": [("f", False), ("a", True), ("ther", False)]},
            {"phone": "AE", "segments": [("c", False), ("a", True), ("t", False)]},
            {"phone": "AH", "segments": [("s", False), ("u", True), ("n", False)]},
            {"phone": "AO", "segments": [("l", False), ("aw", True)]},
            {"phone": "AW", "segments": [("c", False), ("ow", True)]},
            {"phone": "AY", "segments": [("m", False), ("y", True)]},
            {"phone": "EH", "segments": [("b", False), ("e", True), ("d", False)]},
            {"phone": "ER", "segments": [("b", False), ("ir", True), ("d", False)]},
            {"phone": "EY", "segments": [("d", False), ("ay", True)]},
            {"phone": "IH", "segments": [("s", False), ("i", True), ("t", False)]},
            {"phone": "IY", "segments": [("s", False), ("ee", True)]},
            {"phone": "OW", "segments": [("g", False), ("o", True)]},
            {"phone": "OY", "segments": [("b", False), ("oy", True)]},
            {"phone": "UH", "segments": [("p", False), ("u", True), ("t", False)]},
            {"phone": "UW", "segments": [("bl", False), ("ue", True)]},
            {"phone": "CH", "segments": [("ch", True), ("air", False)]},
            {"phone": "DH", "segments": [("th", True), ("is", False)]},
            {"phone": "HH", "segments": [("h", True), ("at", False)]},
            {"phone": "JH", "segments": [("j", True), ("am", False)]},
            {"phone": "NG", "segments": [("si", False), ("ng", True)]},
            {"phone": "SH", "segments": [("sh", True), ("oe", False)]},
            {"phone": "TH", "segments": [("th", True), ("in", False)]},
            {"phone": "ZH", "segments": [("mea", False), ("s", True), ("ure", False)]},
        ],
        "notes": [
            "Stress numbers attach to vowels: 0 is unstressed, 1 is primary stress, and 2 is secondary stress.",
            "Consonant codes such as B, K, L, M, P, S, T, and Z are read much like their letters.",
            "Read a phrase left to right as sounds, not spelling: F OW1 N is phone.",
        ],
    },
    {
        "value": "rhyme",
        "label": "Rhyme Key",
        "title": "Rhyme key",
        "example": "EH1 F ER0 T",
        "phrase": "an A for effort",
        "copy": "A rhyme key is the ending sound signature for the whole idiom. The app starts at the last stressed vowel and keeps every phoneme to the end.",
        "wikipedia_label": "Rhyme on Wikipedia",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Rhyme",
        "notes": [
            "Use it to find idioms whose endings sound alike.",
            "Spelling does not matter; the ARPABET sound codes do.",
            "Blank keys mean the app could not find enough pronunciation data.",
        ],
    },
    {
        "value": "initials",
        "label": "Initials",
        "title": "Initials",
        "example": "L K B",
        "phrase": "let the cat out of the bag (stopwords ignored)",
        "copy": "Initials are first consonant sounds from counted words, not first letters. Sound is what matters: cat and kite share K, and phone and fun share F even though they do not share the same first letter.",
        "wikipedia_label": "Syllable onset on Wikipedia",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Syllable#Onset",
        "notes": [
            "Words that begin with a vowel may not add an initial consonant.",
            "The stopword option can skip small words such as a, the, of, and to.",
            "Use the Initial Phoneme filter to gather idioms that start with a chosen sound.",
        ],
    },
    {
        "value": "alliteration",
        "label": "Alliteration Floor",
        "title": "Alliteration floor",
        "example": "0.67 (D F F)",
        "phrase": "add fuel to the fire",
        "copy": "The floor is the minimum repeated-initial score an idiom must reach. The score is the share of counted words using the most common initial sound.",
        "wikipedia_label": "Alliteration on Wikipedia",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Alliteration",
        "notes": [
            "0.00 lets every idiom through.",
            "0.50 keeps idioms where at least half of the counted initials match.",
            "1.00 keeps only phrases where every counted initial matches.",
        ],
    },
    {
        "value": "stress",
        "label": "Stress",
        "title": "Stress",
        "example": "1 0 1",
        "phrase": "by and by",
        "copy": "Stress marks show which syllables are emphasized in pronunciation. Here, 1 means stressed and 0 means unstressed.",
        "wikipedia_label": "Stress (linguistics) on Wikipedia",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Stress_(linguistics)",
        "notes": [
            "ARPABET vowels carry stress numbers: AH0 is unstressed, EH1 is stressed.",
            "The app treats primary and secondary stress as stressed.",
            "Stress matters for rhyme because the rhyme key begins near the final stressed vowel.",
        ],
    },
]


def phoneme_segments_markup(segments: list[tuple[str, bool]]) -> html.Span:
    return html.Span(
        [
            html.U(text) if underlined else text
            for text, underlined in segments
        ]
    )


def help_topic(topic: dict[str, Any]) -> html.Div:
    return html.Div(
        [
            html.H3(topic["title"]),
            html.P(topic["copy"]),
            html.P(
                html.A(
                    topic["wikipedia_label"],
                    href=topic["wikipedia_url"],
                    target="_blank",
                    rel="noreferrer noopener",
                ),
                className="help-link-row",
            ),
            html.Div(
                [
                    html.Span("Example"),
                    html.Code(topic["example"]),
                    *(
                        [html.Span("Phrase"), html.Strong(topic["phrase"])]
                        if topic.get("phrase")
                        else []
                    ),
                ],
                className="help-example",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Code(guide_item["phone"]),
                            phoneme_segments_markup(guide_item["segments"]),
                        ],
                        className="phoneme-card",
                    )
                    for guide_item in topic.get("guide", [])
                ],
                className="phoneme-guide",
            )
            if topic.get("guide")
            else None,
            html.Ul([html.Li(note) for note in topic["notes"]]),
        ],
        className="help-tab-panel",
    )


def help_modal() -> html.Div:
    return html.Div(
        [
            html.Button(
                "",
                id="help-backdrop",
                className="help-backdrop",
                title="Close phonetics guide",
                type="button",
                tabIndex=-1,
                **{"aria-label": "Close phonetics guide"},
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.P("Phonetic Guide", className="help-kicker"),
                                    html.H2("How the sound filters work", id="help-title"),
                                ]
                            ),
                            html.Button(
                                "x",
                                id="help-close",
                                className="help-close-button",
                                title="Close help",
                                **{"aria-label": "Close help"},
                            ),
                        ],
                        className="help-modal-header",
                    ),
                    html.Button(
                        "",
                        id="help-escape-signal",
                        className="help-escape-signal",
                        title="Escape close signal",
                        type="button",
                        tabIndex=-1,
                        **{"aria-hidden": "true"},
                    ),
                    html.P(
                        "These labels are sound-based. Read the phoneme codes as compact pronunciation hints, then use the filters to compare idioms by how they sound.",
                        className="help-intro",
                    ),
                    dcc.Tabs(
                        id="help-tabs",
                        value=HELP_TOPICS[0]["value"],
                        parent_className="help-tabs-shell",
                        className="help-tabs",
                        children=[
                            dcc.Tab(
                                label=topic["label"],
                                value=topic["value"],
                                className="help-tab",
                                selected_className="help-tab help-tab-selected",
                                children=help_topic(topic),
                            )
                            for topic in HELP_TOPICS
                        ],
                    ),
                ],
                className="help-dialog",
                role="dialog",
                **{"aria-modal": "true", "aria-labelledby": "help-title"},
            ),
        ],
        id="help-modal",
        className="help-modal",
    )


def blank_figure(message: str) -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 16},
    )
    figure.update_layout(
        height=520,
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        xaxis={"visible": False},
        yaxis={"visible": False},
        plot_bgcolor="#f7f4ef",
        paper_bgcolor="#f7f4ef",
    )
    return figure


def network_figure(records: list[dict[str, Any]], ignore_stopwords: bool) -> go.Figure:
    if not records:
        return blank_figure("No idioms match the current filters.")

    selected = records[:90]
    selected_ids = {record["id"] for record in selected}
    graph = nx.Graph()
    for record in selected:
        graph.add_node(record["id"])

    by_rhyme: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in selected:
        if record["rhyme_key"]:
            by_rhyme[record["rhyme_key"]].append(record)

    for cluster in by_rhyme.values():
        if len(cluster) < 2:
            continue
        cluster = sorted(cluster, key=lambda item: item["idiom"].lower())
        anchor = cluster[0]
        for item in cluster[1:10]:
            graph.add_edge(anchor["id"], item["id"], relation="rhyme")

    for record in selected:
        for related in record.get("related_idioms", []):
            target = next(
                (
                    candidate
                    for candidate in selected
                    if candidate["idiom"] == related["idiom"]
                ),
                None,
            )
            if target and target["id"] in selected_ids and related["score"] >= 0.4:
                graph.add_edge(record["id"], target["id"], relation="similar")

    if graph.number_of_edges() > 0:
        positions = nx.spring_layout(graph, seed=42, k=0.55)
    else:
        positions = {
            record["id"]: (
                record["syllable_count"],
                alliteration_value(record, ignore_stopwords),
            )
            for record in selected
        }

    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    node_x = []
    node_y = []
    node_text = []
    node_color = []
    node_size = []
    for record in selected:
        x, y = positions[record["id"]]
        node_x.append(x)
        node_y.append(y)
        node_text.append(
            "<br>".join(
                [
                    f"<b>{record['idiom']}</b>",
                    f"Syllables: {record['syllable_count']}",
                    f"Rhyme: {record['rhyme_key'] or 'none'}",
                    f"Initials: {' '.join(all_initials(record, ignore_stopwords)) or 'none'}",
                    f"Alliteration: {alliteration_value(record, ignore_stopwords):.2f}",
                ]
            )
        )
        node_color.append(record["syllable_count"])
        node_size.append(10 + 18 * alliteration_value(record, ignore_stopwords))

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line={"width": 1, "color": "#a9a29a"},
            hoverinfo="none",
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers",
            marker={
                "size": node_size,
                "color": node_color,
                "colorscale": "Viridis",
                "line": {"width": 1, "color": "#2f3437"},
                "colorbar": {"title": "Syllables"},
            },
            text=node_text,
            hovertemplate="%{text}<extra></extra>",
            showlegend=False,
        )
    )
    figure.update_layout(
        height=520,
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        xaxis={"visible": False},
        yaxis={"visible": False},
        plot_bgcolor="#f7f4ef",
        paper_bgcolor="#f7f4ef",
    )
    return figure


def detail_panel(
    table_data: list[dict[str, Any]] | None,
    active_cell: dict[str, Any] | None,
):
    if not table_data:
        return html.Div("Select filters that return at least one idiom.", className="empty-state")

    row_id = active_cell.get("row_id") if active_cell else None
    visible_row_ids = {row["id"] for row in table_data}
    if row_id is None or row_id not in visible_row_ids:
        row_id = table_data[0]["id"]
    record = RECORD_BY_ID[row_id]
    related = record.get("related_idioms", [])

    return html.Div(
        [
            html.H2(record["idiom"]),
            html.Div(
                [
                    html.Span(f"{record['syllable_count']} syllables"),
                    html.Span(record["rhyme_key"] or "no rhyme key"),
                    html.Span("unknown words" if record["unknown_words"] else "CMUdict covered"),
                ],
                className="detail-badges",
            ),
            html.H3("Tokens"),
            html.Code(" | ".join(record["tokens"])),
            html.H3("Phonemes"),
            html.Code(" ".join(record["phonemes"]) or "None"),
            html.H3("Stress"),
            html.Code("".join(str(bit) for bit in record["stress_pattern"]) or "None"),
            html.H3("Initial Phonemes"),
            html.Code(" ".join(record["initial_phonemes"]) or "None"),
            html.H3("Unknown Words"),
            html.Code(", ".join(record["unknown_words"]) or "None"),
            html.H3("Related Idioms"),
            html.Ul(
                [
                    html.Li(
                        [
                            html.Span(item["idiom"]),
                            html.Small(
                                f" {item['score']:.2f} - {', '.join(item['reasons'])}"
                            ),
                        ]
                    )
                    for item in related[:8]
                ]
            )
            if related
            else html.Div("No strong related idioms found.", className="empty-state"),
        ],
        className="detail-content",
    )


app = Dash(__name__)
app.title = "Idiom Phonetics Explorer"

syllable_marks = {
    value: str(value)
    for value in range(MIN_SYLLABLES, MAX_SYLLABLES + 1)
    if value in {MIN_SYLLABLES, MAX_SYLLABLES} or value % 2 == 1
}

app.layout = html.Div(
    [
        html.Header(
            [
                html.Div(
                    [
                        html.H1("Idiom Phonetics Explorer"),
                        html.P(
                            f"{len(RECORDS):,} American idioms indexed by syllables, rhyme, initial phonemes, and phonetic similarity."
                        ),
                    ],
                    className="masthead-copy",
                ),
                html.Div(
                    [
                        html.Button(
                            "?",
                            id="help-open",
                            className="help-button",
                            title="Open phonetics guide",
                            **{
                                "aria-label": "Open phonetics guide",
                                "aria-haspopup": "dialog",
                                "aria-expanded": "false",
                            },
                        ),
                        html.Div(
                            [
                                html.Span("CSV"),
                                html.Strong(CSV_PATH.name),
                                html.Span("Output"),
                                html.Strong(str(DATA_PATH.relative_to(ROOT))),
                            ],
                            className="dataset-meta",
                        ),
                    ],
                    className="masthead-tools",
                ),
            ],
            className="masthead",
        ),
        help_modal(),
        html.Section(
            [
                html.Label(
                    [
                        html.Span("Search"),
                        dcc.Input(
                            id="search",
                            type="text",
                            placeholder="Type an idiom or phrase fragment",
                            debounce=True,
                        ),
                    ]
                ),
                html.Label(
                    [
                        html.Span("Rhyme Key"),
                        dcc.Dropdown(
                            id="rhyme-key",
                            options=make_rhyme_options(),
                            placeholder="Any rhyme",
                            clearable=True,
                            optionHeight=30,
                        ),
                    ]
                ),
                html.Label(
                    [
                        html.Span("Initial Phoneme"),
                        dcc.Dropdown(
                            id="initial-phone",
                            options=make_initial_options(),
                            placeholder="Any initial",
                            clearable=True,
                            optionHeight=30,
                        ),
                    ]
                ),
                html.Label(
                    [
                        html.Span("Syllable Range"),
                        dcc.RangeSlider(
                            id="syllable-range",
                            min=MIN_SYLLABLES,
                            max=MAX_SYLLABLES,
                            step=1,
                            value=[MIN_SYLLABLES, MAX_SYLLABLES],
                            marks=syllable_marks,
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),
                    ],
                    className="wide-control",
                ),
                html.Label(
                    [
                        html.Span("Alliteration Floor"),
                        dcc.Slider(
                            id="alliteration-threshold",
                            min=0,
                            max=1,
                            step=0.05,
                            value=0,
                            marks={0: "0", 0.5: "0.5", 1: "1"},
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),
                    ],
                    className="wide-control",
                ),
                dcc.Checklist(
                    id="options",
                    options=[
                        {
                            "label": "Ignore stopwords for alliteration",
                            "value": "ignore_stopwords",
                        },
                        {"label": "Hide unknown pronunciations", "value": "hide_unknown"},
                    ],
                    value=["ignore_stopwords"],
                    className="checklist",
                ),
            ],
            className="controls",
        ),
        html.Main(
            [
                html.Section(
                    [
                        html.Div(id="results-summary", className="summary-bar"),
                        dash_table.DataTable(
                            id="idiom-table",
                            columns=[
                                {"name": "Idiom", "id": "idiom"},
                                {"name": "Syllables", "id": "syllables", "type": "numeric"},
                                {"name": "Rhyme Key", "id": "rhyme_key"},
                                {"name": "Initials", "id": "initials"},
                                {"name": "Stress", "id": "stress"},
                                {
                                    "name": "Alliteration",
                                    "id": "alliteration",
                                    "type": "numeric",
                                    "format": {"specifier": ".2f"},
                                },
                            ],
                            data=[],
                            page_size=15,
                            active_cell=None,
                            sort_action="native",
                            filter_action="native",
                            style_as_list_view=True,
                            style_cell={
                                "fontFamily": "Inter, Segoe UI, sans-serif",
                                "fontSize": 13,
                                "padding": "8px",
                                "whiteSpace": "normal",
                                "height": "auto",
                            },
                            style_header={
                                "backgroundColor": "#efe8dc",
                                "fontWeight": 700,
                                "border": "0",
                            },
                            style_data={
                                "backgroundColor": "#fffdf9",
                                "border": "0",
                                "borderBottom": "1px solid #e1d8cb",
                            },
                            style_data_conditional=[
                                {
                                    "if": {"state": "active"},
                                    "backgroundColor": "#dbe9e6",
                                    "border": "1px solid #33776b",
                                }
                            ],
                        ),
                    ],
                    className="panel table-panel",
                ),
                html.Aside(id="detail-panel", className="panel detail-panel"),
                html.Section(
                    [
                        html.H2("Rhyme Groups"),
                        html.Div(id="rhyme-groups"),
                    ],
                    className="panel",
                ),
                html.Section(
                    [
                        html.H2("Alliteration Groups"),
                        html.Div(id="alliteration-groups"),
                    ],
                    className="panel",
                ),
                html.Section(
                    [
                        html.H2("Cluster View"),
                        dcc.Graph(id="cluster-graph", config={"displayModeBar": False}),
                    ],
                    className="panel graph-panel",
                ),
            ],
            className="workspace",
        ),
    ],
    className="app-shell",
)


@app.callback(
    Output("results-summary", "children"),
    Output("idiom-table", "data"),
    Output("idiom-table", "active_cell"),
    Output("rhyme-groups", "children"),
    Output("alliteration-groups", "children"),
    Output("cluster-graph", "figure"),
    Input("search", "value"),
    Input("syllable-range", "value"),
    Input("rhyme-key", "value"),
    Input("initial-phone", "value"),
    Input("alliteration-threshold", "value"),
    Input("options", "value"),
    State("idiom-table", "active_cell"),
)
def update_results(
    query,
    syllable_range,
    selected_rhyme,
    selected_initial,
    threshold,
    options,
    current_active_cell,
):
    options = options or []
    ignore_stopwords = "ignore_stopwords" in options
    records = filter_records(
        query,
        syllable_range,
        selected_rhyme,
        selected_initial,
        threshold,
        options,
    )

    summary = html.Div(
        [
            html.Strong(f"{len(records):,} matches"),
            html.Span("Table shows the first 500 matches; refine filters for tighter exploration."),
        ]
    )
    rows = table_rows(records, ignore_stopwords)
    return (
        summary,
        rows,
        active_cell_for_data(rows, current_active_cell),
        rhyme_groups(records),
        alliteration_groups(records, ignore_stopwords, threshold or 0),
        network_figure(records, ignore_stopwords),
    )


@app.callback(
    Output("detail-panel", "children"),
    Output("idiom-table", "style_data_conditional"),
    Input("idiom-table", "derived_viewport_data"),
    Input("idiom-table", "active_cell"),
)
def update_detail(table_data, active_cell):
    row_id = active_cell.get("row_id") if active_cell else None
    visible_row_ids = {row["id"] for row in table_data} if table_data else set()
    if (row_id is None or row_id not in visible_row_ids) and table_data:
        row_id = table_data[0]["id"]
    return detail_panel(table_data, active_cell), table_style(row_id)


@app.callback(
    Output("help-modal", "className"),
    Output("help-open", "aria-expanded"),
    Input("help-open", "n_clicks"),
    Input("help-close", "n_clicks"),
    Input("help-backdrop", "n_clicks"),
    Input("help-escape-signal", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_help(open_clicks, close_clicks, backdrop_clicks, escape_clicks):
    trigger = callback_context.triggered[0]["prop_id"].split(".")[0]
    if trigger == "help-open":
        return "help-modal is-open", "true"
    return "help-modal", "false"


if __name__ == "__main__":
    port = 8050
    app.run(debug=False, host="127.0.0.1", port=port)
