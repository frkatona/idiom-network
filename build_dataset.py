from __future__ import annotations

import argparse
import json
from pathlib import Path

from phonetics import build_dataset, build_indices, dataset_stats, write_csv, write_json


DEFAULT_INPUT = Path("american_idioms_clean_list.csv")
DEFAULT_OUTPUT_DIR = Path("output")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build phonetic feature data for the American idiom explorer."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Input idiom CSV. Defaults to american_idioms_clean_list.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated JSON, CSV, and index files.",
    )
    parser.add_argument(
        "--max-related",
        type=int,
        default=8,
        help="Number of related idioms to retain per record.",
    )
    parser.add_argument(
        "--skip-related",
        action="store_true",
        help="Build features without computing related idioms.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = build_dataset(
        args.input,
        include_related=not args.skip_related,
        max_related=args.max_related,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "idioms_phonetic.json"
    csv_path = args.output_dir / "idioms_phonetic.csv"
    index_path = args.output_dir / "idioms_indices.json"
    stats_path = args.output_dir / "dataset_stats.json"

    write_json(records, json_path)
    write_csv(records, csv_path)

    with index_path.open("w", encoding="utf-8") as handle:
        json.dump(build_indices(records), handle, ensure_ascii=False, indent=2)

    stats = dataset_stats(records)
    with stats_path.open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, ensure_ascii=False, indent=2)

    print(f"Built {stats['records']} idiom records")
    print(f"Unknown pronunciation records: {stats['unknown_record_count']}")
    print(f"Unique unknown words: {stats['unique_unknown_words']}")
    print(f"Rhyme clusters with 2+ idioms: {stats['rhyme_cluster_count']}")
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {index_path}")
    print(f"Wrote {stats_path}")


if __name__ == "__main__":
    main()
