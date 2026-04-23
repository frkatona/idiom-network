from pathlib import Path

from phonetics import (
    analyze_idiom,
    build_dataset,
    estimate_syllables,
    load_idioms,
    normalize_idiom,
    phones_for_token,
    tokenize_idiom,
)


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "american_idioms_clean_list.csv"


def test_loads_clean_idiom_csv_without_dropping_rows():
    rows = load_idioms(CSV_PATH)

    assert len(rows) == 7389
    assert all(row["idiom"].strip() for row in rows)


def test_normalization_handles_parentheses_commas_and_smart_apostrophes():
    idiom = "Early to bed, early to rise(, makes a man healthy, wealthy, and wise)."

    assert normalize_idiom(idiom) == (
        "early to bed early to rise makes a man healthy wealthy and wise"
    )
    assert tokenize_idiom("one’s head") == ["one's", "head"]


def test_possessive_pronunciation_fallback_handles_smart_apostrophe_token():
    phones, unknown = phones_for_token("one's")

    assert not unknown
    assert phones


def test_known_feature_extraction_for_common_idiom():
    record = analyze_idiom(
        {
            "idiom": "a dime a dozen",
            "dict_page": "1",
            "pdf_page": "1",
            "raw_entry_head": "a dime a dozen",
        }
    )

    assert record["tokens"] == ["a", "dime", "a", "dozen"]
    assert record["syllable_count"] >= 5
    assert record["rhyme_key"]
    assert record["stress_pattern"]
    assert record["unknown_words"] == []


def test_unknown_words_use_syllable_fallback_without_crashing():
    record = analyze_idiom(
        {
            "idiom": "zzzz blorf",
            "dict_page": "0",
            "pdf_page": "0",
            "raw_entry_head": "zzzz blorf",
        }
    )

    assert record["unknown_words"] == ["zzzz", "blorf"]
    assert record["syllable_count"] >= 2
    assert estimate_syllables("blorf") == 1


def test_build_dataset_extracts_related_idioms_for_subset_shape():
    records = build_dataset(CSV_PATH, include_related=False)

    sample = next(record for record in records if record["idiom"] == "above and beyond (something)")
    assert sample["phonemes"]
    assert isinstance(sample["initial_phonemes"], list)
