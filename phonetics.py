from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pronouncing

TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")
VOWEL_RE = re.compile(r"\d$")

STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "off",
    "on",
    "or",
    "out",
    "over",
    "the",
    "this",
    "that",
    "to",
    "up",
    "with",
}

VOICED_FINALS = {
    "AA",
    "AE",
    "AH",
    "AO",
    "AW",
    "AY",
    "B",
    "D",
    "DH",
    "EH",
    "ER",
    "EY",
    "G",
    "IY",
    "IH",
    "JH",
    "L",
    "M",
    "N",
    "NG",
    "OW",
    "OY",
    "R",
    "TH",
    "UH",
    "UW",
    "V",
    "W",
    "Y",
    "Z",
    "ZH",
}


def normalize_apostrophes(text: str) -> str:
    return (
        text.replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u02bc", "'")
        .replace("`", "'")
        .replace("\u00b4", "'")
    )


def normalize_idiom(idiom: str) -> str:
    text = normalize_apostrophes(idiom).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[-\u2010-\u2015/]", " ", text)
    text = re.sub(r"[^a-z'\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize_idiom(idiom: str) -> list[str]:
    return TOKEN_RE.findall(normalize_idiom(idiom))


def load_idioms(csv_path: str | Path) -> list[dict[str, str]]:
    path = Path(csv_path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    required = {"idiom", "dict_page", "pdf_page", "raw_entry_head"}
    missing = required - set(rows[0].keys() if rows else [])
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    clean_rows = []
    for row in rows:
        idiom = row["idiom"].strip()
        if not idiom:
            continue
        normalized = normalize_idiom(idiom)
        if not normalized:
            continue
        clean_rows.append(
            {
                "idiom": idiom,
                "dict_page": row["dict_page"].strip(),
                "pdf_page": row["pdf_page"].strip(),
                "raw_entry_head": row["raw_entry_head"].strip(),
            }
        )
    return clean_rows


def is_vowel_phone(phone: str) -> bool:
    return bool(VOWEL_RE.search(phone))


def strip_stress(phone: str) -> str:
    return re.sub(r"\d$", "", phone)


def count_phone_syllables(phones: list[str]) -> int:
    return sum(1 for phone in phones if is_vowel_phone(phone))


def estimate_syllables(word: str) -> int:
    clean = re.sub(r"[^a-z]", "", word.lower())
    if not clean:
        return 0
    if len(clean) <= 3:
        return 1

    if clean.endswith("es") and len(clean) > 4:
        clean = clean[:-2]
    elif clean.endswith("e") and not clean.endswith(("le", "ye")):
        clean = clean[:-1]

    groups = re.findall(r"[aeiouy]+", clean)
    count = len(groups)
    if clean.endswith("le") and len(clean) > 2 and clean[-3] not in "aeiouy":
        count += 1
    return max(1, count)


def phones_for_token(token: str) -> tuple[list[str], bool]:
    word = normalize_apostrophes(token.lower())
    phones = pronouncing.phones_for_word(word)
    if phones:
        return phones[0].split(), False

    if word.endswith("'s") and len(word) > 2:
        base_phones, base_unknown = phones_for_token(word[:-2])
        if base_phones and not base_unknown:
            suffix = possessive_suffix_phone(base_phones[-1])
            return base_phones + suffix, False

    contraction_suffixes = {
        "'d": ["D"],
        "'ll": ["L"],
        "'m": ["M"],
        "'re": ["ER0"],
        "'ve": ["V"],
        "n't": ["N", "T"],
    }
    for suffix, suffix_phones in contraction_suffixes.items():
        if word.endswith(suffix) and len(word) > len(suffix):
            base_phones, base_unknown = phones_for_token(word[: -len(suffix)])
            if base_phones and not base_unknown:
                return base_phones + suffix_phones, False

    return [], True


def possessive_suffix_phone(last_phone: str) -> list[str]:
    base = strip_stress(last_phone)
    if base in {"S", "Z", "SH", "ZH", "CH", "JH"}:
        return ["IH0", "Z"]
    return ["Z"] if base in VOICED_FINALS else ["S"]


def rhyme_key(phonemes: list[str]) -> str:
    for index in range(len(phonemes) - 1, -1, -1):
        phone = phonemes[index]
        if phone.endswith(("1", "2")):
            return " ".join(phonemes[index:])
    for index in range(len(phonemes) - 1, -1, -1):
        if is_vowel_phone(phonemes[index]):
            return " ".join(phonemes[index:])
    return ""


def stress_pattern(phonemes: list[str]) -> list[int]:
    return [
        1 if phone.endswith(("1", "2")) else 0
        for phone in phonemes
        if is_vowel_phone(phone)
    ]


def first_consonant_phone(phones: list[str]) -> str:
    for phone in phones:
        if not is_vowel_phone(phone):
            return strip_stress(phone)
    return ""


def initial_phonemes(
    tokens: list[str],
    phonemes_by_word: list[list[str]],
    ignore_stopwords: bool = True,
) -> list[str]:
    initials = []
    for token, phones in zip(tokens, phonemes_by_word):
        if ignore_stopwords and token in STOPWORDS:
            continue
        initial = first_consonant_phone(phones)
        if initial:
            initials.append(initial)
    return initials


def alliteration_score(initials: list[str]) -> float:
    if len(initials) < 2:
        return 0.0
    most_common = Counter(initials).most_common(1)[0][1]
    return round(most_common / len(initials), 3)


def dominant_initial(initials: list[str]) -> str:
    if not initials:
        return ""
    return Counter(initials).most_common(1)[0][0]


def analyze_idiom(row: dict[str, str]) -> dict[str, Any]:
    tokens = tokenize_idiom(row["idiom"])
    normalized = " ".join(tokens)
    phonemes_by_word: list[list[str]] = []
    unknown_words: list[str] = []
    syllable_count = 0

    for token in tokens:
        phones, unknown = phones_for_token(token)
        phonemes_by_word.append(phones)
        if unknown:
            unknown_words.append(token)
            syllable_count += estimate_syllables(token)
        else:
            syllable_count += count_phone_syllables(phones)

    phonemes = [phone for word_phones in phonemes_by_word for phone in word_phones]
    initials_without_stopwords = initial_phonemes(tokens, phonemes_by_word, True)
    initials_with_stopwords = initial_phonemes(tokens, phonemes_by_word, False)

    return {
        **row,
        "normalized_idiom": normalized,
        "tokens": tokens,
        "phonemes": phonemes,
        "phonemes_by_word": phonemes_by_word,
        "syllable_count": syllable_count,
        "rhyme_key": rhyme_key(phonemes),
        "initial_phonemes": initials_without_stopwords,
        "initial_phonemes_with_stopwords": initials_with_stopwords,
        "dominant_initial": dominant_initial(initials_without_stopwords),
        "dominant_initial_with_stopwords": dominant_initial(initials_with_stopwords),
        "alliteration_score": alliteration_score(initials_without_stopwords),
        "alliteration_score_with_stopwords": alliteration_score(initials_with_stopwords),
        "stress_pattern": stress_pattern(phonemes),
        "unknown_words": unknown_words,
        "unknown_pronunciation": bool(unknown_words),
    }


def phoneme_ngrams(phonemes: list[str], n: int = 2) -> set[tuple[str, ...]]:
    if len(phonemes) < n:
        return set()
    return {tuple(strip_stress(phone) for phone in phonemes[i : i + n]) for i in range(len(phonemes) - n + 1)}


def jaccard(left: set[Any], right: set[Any]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def similarity_score(left: dict[str, Any], right: dict[str, Any]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    if left["rhyme_key"] and left["rhyme_key"] == right["rhyme_key"]:
        score += 0.45
        reasons.append("same rhyme")

    syllable_delta = abs(left["syllable_count"] - right["syllable_count"])
    if syllable_delta == 0:
        score += 0.2
        reasons.append("same syllables")
    elif syllable_delta == 1:
        score += 0.1
        reasons.append("near syllables")

    left_initials = set(left["initial_phonemes"])
    right_initials = set(right["initial_phonemes"])
    initial_overlap = jaccard(left_initials, right_initials)
    if initial_overlap:
        score += 0.15 * initial_overlap
        reasons.append("shared initials")

    ngram_overlap = jaccard(
        set(left.get("phoneme_bigrams", [])),
        set(right.get("phoneme_bigrams", [])),
    )
    if ngram_overlap:
        score += 0.2 * ngram_overlap
        reasons.append("phoneme overlap")

    return round(score, 3), reasons


def build_indices(records: list[dict[str, Any]]) -> dict[str, dict[str, list[int]]]:
    indices: dict[str, dict[str, list[int]]] = {
        "syllable_count": defaultdict(list),
        "rhyme_key": defaultdict(list),
        "initial_phoneme": defaultdict(list),
        "dominant_initial": defaultdict(list),
        "phoneme_bigram": defaultdict(list),
    }

    for index, record in enumerate(records):
        indices["syllable_count"][str(record["syllable_count"])].append(index)
        if record["rhyme_key"]:
            indices["rhyme_key"][record["rhyme_key"]].append(index)
        for phone in set(record["initial_phonemes"]):
            indices["initial_phoneme"][phone].append(index)
        if record["dominant_initial"]:
            indices["dominant_initial"][record["dominant_initial"]].append(index)
        bigrams = record.get("phoneme_bigrams")
        if not bigrams:
            bigrams = sorted(" ".join(ngram) for ngram in phoneme_ngrams(record["phonemes"]))
        for bigram in set(bigrams):
            indices["phoneme_bigram"][bigram].append(index)

    return {name: dict(values) for name, values in indices.items()}


def candidate_indices(
    record: dict[str, Any],
    index: int,
    indices: dict[str, dict[str, list[int]]],
) -> set[int]:
    candidates: set[int] = set()

    if record["rhyme_key"]:
        candidates.update(indices["rhyme_key"].get(record["rhyme_key"], []))

    for phone in set(record["initial_phonemes"]):
        candidates.update(indices["initial_phoneme"].get(phone, []))

    for bigram in set(record.get("phoneme_bigrams", [])):
        candidates.update(indices["phoneme_bigram"].get(bigram, []))

    candidates.discard(index)
    return candidates


def add_related_idioms(
    records: list[dict[str, Any]],
    max_related: int = 8,
) -> list[dict[str, Any]]:
    for record in records:
        record["phoneme_bigrams"] = sorted(
            " ".join(ngram) for ngram in phoneme_ngrams(record["phonemes"])
        )

    indices = build_indices(records)

    for index, record in enumerate(records):
        related = []
        for candidate_index in candidate_indices(record, index, indices):
            score, reasons = similarity_score(record, records[candidate_index])
            if score >= 0.2:
                related.append(
                    {
                        "idiom": records[candidate_index]["idiom"],
                        "score": score,
                        "reasons": reasons,
                    }
                )
        record["related_idioms"] = sorted(
            related,
            key=lambda item: (-item["score"], item["idiom"].lower()),
        )[:max_related]

    return records


def build_dataset(
    csv_path: str | Path,
    include_related: bool = True,
    max_related: int = 8,
) -> list[dict[str, Any]]:
    rows = load_idioms(csv_path)
    records = [analyze_idiom(row) for row in rows]
    if include_related:
        add_related_idioms(records, max_related=max_related)
    return records


def write_json(records: list[dict[str, Any]], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)


def write_csv(records: list[dict[str, Any]], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "idiom",
        "normalized_idiom",
        "dict_page",
        "pdf_page",
        "raw_entry_head",
        "tokens",
        "phonemes",
        "syllable_count",
        "rhyme_key",
        "initial_phonemes",
        "alliteration_score",
        "stress_pattern",
        "unknown_words",
        "related_idioms",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "idiom": record["idiom"],
                    "normalized_idiom": record["normalized_idiom"],
                    "dict_page": record["dict_page"],
                    "pdf_page": record["pdf_page"],
                    "raw_entry_head": record["raw_entry_head"],
                    "tokens": " | ".join(record["tokens"]),
                    "phonemes": " ".join(record["phonemes"]),
                    "syllable_count": record["syllable_count"],
                    "rhyme_key": record["rhyme_key"],
                    "initial_phonemes": " ".join(record["initial_phonemes"]),
                    "alliteration_score": record["alliteration_score"],
                    "stress_pattern": "".join(str(bit) for bit in record["stress_pattern"]),
                    "unknown_words": " | ".join(record["unknown_words"]),
                    "related_idioms": " | ".join(
                        f"{item['idiom']} ({item['score']})"
                        for item in record.get("related_idioms", [])
                    ),
                }
            )


def dataset_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    unknown_records = [record for record in records if record["unknown_words"]]
    unknown_words = Counter(
        word for record in unknown_records for word in record["unknown_words"]
    )
    rhyme_clusters = Counter(
        record["rhyme_key"] for record in records if record["rhyme_key"]
    )

    return {
        "records": len(records),
        "unknown_record_count": len(unknown_records),
        "unknown_record_rate": round(len(unknown_records) / len(records), 4)
        if records
        else math.nan,
        "unique_unknown_words": len(unknown_words),
        "top_unknown_words": unknown_words.most_common(20),
        "rhyme_cluster_count": sum(1 for count in rhyme_clusters.values() if count > 1),
        "max_syllable_count": max((record["syllable_count"] for record in records), default=0),
    }
