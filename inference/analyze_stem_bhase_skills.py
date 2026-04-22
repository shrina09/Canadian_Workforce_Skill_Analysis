# Analyzes STEM BHASE skills by linking description text to public skills and grouping by program tags, then saves row-level results to CSV
from __future__ import annotations
import argparse
import csv
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple
from inference.public_entity_linker import PublicEntityLinker


RAW_DIR = Path.home() / "Documents" / "CIS4900" / "RawData"
CLEANED_DIR = Path.home() / "Documents" / "CIS4900" / "Cleaned"
COLUMN_NAMES_PATH = RAW_DIR / "columnNames.txt"
TAGGED_PATH = CLEANED_DIR / "taged.txt"
INPUT_FILES = [CLEANED_DIR / f"clean{i}.csv" for i in range(1, 6)]


# Public linker settings
THRESHOLD = 0.50
TOP_K_CANDIDATES = 100
PROGRESS_EVERY_N_ROWS = 100


# Reads description and program column names from columnNames.txt
def load_column_names(path):
    if not path.exists():
        raise FileNotFoundError(f"Column names file not found: {path}")

    with path.open("r", encoding="utf-8") as infile:
        lines = [line.strip() for line in infile if line.strip()]

    if len(lines) < 2:
        raise ValueError("columnNames.txt must contain at least two non-empty lines ")
    
    return lines[0], lines[1]


# Loads program to group tags from taged.txt
def load_program_groups(path):
    if not path.exists():
        raise FileNotFoundError(f"Tagged mapping file not found: {path}")

    mapping: Dict[str, str] = {}
    line_re = re.compile(r'^(?P<program>.+?)\s+"(?P<group>STEM|BHASE)"\s*$')

    with path.open("r", encoding="utf-8") as infile:
        for line_number, raw_line in enumerate(infile, start=1):
            line = raw_line.strip()
            if not line:
                continue

            match = line_re.match(line)
            if not match:
                raise ValueError(f"Invalid taged.txt format at line {line_number}: {line!r}. ")

            program = match.group("program").strip()
            group = match.group("group")

            if program in mapping and mapping[program] != group:
                raise ValueError(f"Conflicting tags for program in taged.txt")
            mapping[program] = group

    if not mapping:
        raise ValueError(f"No program-group mappings found in {path}")
    return mapping


# Builds cli parser for optional single file processing
def build_parser():
    parser = argparse.ArgumentParser(
        description="Run public skill extraction for one cleaned file or all cleaned files."
    )
    parser.add_argument(
        "--file",
        choices=[path.name for path in INPUT_FILES],
        help="Process only one cleaned CSV file, for example clean3.csv",
    )
    return parser


# Returns one file if selected otherwise return all input files
def get_selected_files(selected_name: str | None) -> List[Path]:
    if selected_name is None:
        return INPUT_FILES

    for path in INPUT_FILES:
        if path.name == selected_name:
            return [path]
    raise ValueError(f"Unsupported file selection: {selected_name}")


# Builds output filename based on one file or all files mode
def build_output_path(selected_files):
    if len(selected_files) == 1:
        stem = selected_files[0].stem
        return CLEANED_DIR / f"{stem}_skills_row_level.csv"
    return CLEANED_DIR / "skills_row_level.csv"


# Runs STEM BHASE skill extraction and save row level results
def main():
    args = build_parser().parse_args()
    start_time = time.perf_counter()
    print("Starting STEM/BHASE skill analysis...")

    description_col, program_col = load_column_names(COLUMN_NAMES_PATH)
    print(f"Loaded column names from {COLUMN_NAMES_PATH}")
    print(f"Description column: {description_col}")
    print(f"Program column: {program_col}")

    program_to_group = load_program_groups(TAGGED_PATH)
    print(f"Loaded {len(program_to_group)} tagged programs from {TAGGED_PATH}")
    selected_files = get_selected_files(args.file)
    row_level_output = build_output_path(selected_files)
    print(f"Input files: {[str(path) for path in selected_files]}")
    print(f"Row-level output: {row_level_output}")

    # Loads linker model once and reuse it across all rows
    print("Loading PublicEntityLinker model...")
    linker = PublicEntityLinker()
    print("PublicEntityLinker is ready.")

    group_row_counts = {"STEM": 0, "BHASE": 0}
    unmapped_programs= {}
    row_level_rows = []

    for file_path in selected_files:
        if not file_path.exists():
            raise FileNotFoundError(f"Input cleaned file not found: {file_path}")

        file_start = time.perf_counter()
        file_rows_seen = 0
        file_rows_mapped = 0
        file_rows_unmapped = 0
        file_rows_skipped_missing = 0

        print(f"Processing {file_path} ...")
        with file_path.open("r", encoding="utf-8", newline="") as infile:
            reader = csv.DictReader(infile)
            if reader.fieldnames is None:
                raise ValueError(f"Missing header row in {file_path}")
            if description_col not in reader.fieldnames:
                raise ValueError(f"Missing description column '{description_col}' in {file_path}")
            if program_col not in reader.fieldnames:
                raise ValueError(f"Missing program column '{program_col}' in {file_path}")

            for row_number, row in enumerate(reader, start=1):
                file_rows_seen += 1
                description = str(row.get(description_col, "")).strip()
                program = str(row.get(program_col, "")).strip()

                # Skips rows missing required text
                if not description or not program:
                    file_rows_skipped_missing += 1
                    continue

                # Skips rows where program has no STEM BHASE tag
                group = program_to_group.get(program)
                if group is None:
                    unmapped_programs[program] = unmapped_programs.get(program, 0) + 1
                    file_rows_unmapped += 1
                    continue

                # Links skills from description text
                linked = linker.link_and_group(
                    description, threshold=THRESHOLD, top_k_candidates=TOP_K_CANDIDATES
                )
                skills = [str(item["skill"]).strip() for item in linked if str(item.get("skill", "")).strip()]

                group_row_counts[group] = group_row_counts.get(group, 0) + 1
                file_rows_mapped += 1

                row_level_rows.append(
                    {
                        "source_file": file_path.name,
                        "row_number": str(row_number),
                        "program": program,
                        "group": group,
                        "skills_count": str(len(skills)),
                        "skills": " | ".join(skills),
                    }
                )

                if file_rows_seen % PROGRESS_EVERY_N_ROWS == 0:
                    elapsed = time.perf_counter() - file_start
                    print(
                            f"  {file_path.name}: seen={file_rows_seen} mapped={file_rows_mapped} "
                            f"unmapped={file_rows_unmapped} elapsed={elapsed:.1f}s"
                    )

        file_elapsed = time.perf_counter() - file_start
        print(
            f"Done {file_path.name}: seen={file_rows_seen} mapped={file_rows_mapped} "
            f"unmapped={file_rows_unmapped} missing={file_rows_skipped_missing} "
            f"time={file_elapsed:.1f}s"
        )

    # Writes final row level output csv
    row_level_output.parent.mkdir(parents=True, exist_ok=True)
    with row_level_output.open("w", encoding="utf-8", newline="") as outfile:
        fieldnames = [
            "source_file",
            "row_number",
            "program",
            "group",
            "skills_count",
            "skills",
        ]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(row_level_rows)

    print(f"Wrote row-level output: {row_level_output}")
    print(f"Rows processed (mapped): {sum(group_row_counts.values())}")
    print(f"Rows by group: STEM={group_row_counts.get('STEM', 0)} BHASE={group_row_counts.get('BHASE', 0)}")
    print(f"Unmapped programs skipped: {sum(unmapped_programs.values())}")
    total_elapsed = time.perf_counter() - start_time
    print(f"Total elapsed time: {total_elapsed:.1f}s")


if __name__ == "__main__":
    main()
