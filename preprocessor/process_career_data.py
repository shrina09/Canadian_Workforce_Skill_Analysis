# This script processes the raw career data CSV files by
from __future__ import annotations
import csv
import re
from pathlib import Path


INPUT_DIR = Path.home() / "Documents" / "CIS4900" / "RawData"
OUTPUT_DIR = Path.home() / "Documents" / "CIS4900" / "Cleaned"
COLUMN_NAMES_PATH = INPUT_DIR / "columnNames.txt"
REMOVE_ROWS_PATH = OUTPUT_DIR / "removeRows.txt"
WORD_RE = re.compile(r"\b\w+\b", flags=re.UNICODE)


# Counts how many words are in a text string
def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


# Reads the two column names we need from a text file
def load_column_names(column_names_path):
    if not column_names_path.exists():
        raise FileNotFoundError(f"Column names file not found: {column_names_path}")

    with column_names_path.open("r", encoding="utf-8") as infile:
        lines = [line.strip() for line in infile if line.strip()]

    if len(lines) < 2:
        raise ValueError(
            "columnNames.txt must contain at least two non-empty lines"
        )

    return lines[0], lines[1]


# Loads the list of program names to filter out
def load_programs_to_remove(remove_rows_path):
    if not remove_rows_path.exists():
        raise FileNotFoundError(f"removeRows file not found: {remove_rows_path}")

    with remove_rows_path.open("r", encoding="utf-8") as infile:
        return {line.strip() for line in infile if line.strip()}


# Cleana one csv file and keep only the needed columns and rows
def process_csv(input_path, output_path, description_col, program_col, programs_to_remove):
    with input_path.open("r", encoding="utf-8", newline="") as infile:
        # Skips the first line then use the second line as the header
        next(infile, None)
        reader = csv.DictReader(infile)

        # Makes sure required columns exist before processing rows
        if reader.fieldnames is None:
            raise ValueError("Could not read header row after skipping first line")
        required_columns = [description_col, program_col]
        missing = [col for col in required_columns if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"Missing required column(s): {missing}")

        # Writes cleaned rows into a new csv file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=required_columns)
            writer.writeheader()
            for row in reader:
                description = str(row.get(description_col, "")).strip()
                program = str(row.get(program_col, "")).strip()

                # Drops rows with blocked programs or short descriptions
                if program in programs_to_remove:
                    continue
                if count_words(description) <= 50:
                    continue
                writer.writerow(
                    {
                        description_col: description,
                        program_col: program,
                    }
                )


# Runs the cleaning pipeline for raw1 to raw5
def main() -> None:
    description_col, program_col = load_column_names(COLUMN_NAMES_PATH)
    programs_to_remove = load_programs_to_remove(REMOVE_ROWS_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for idx in range(1, 6):
        input_csv = INPUT_DIR / f"raw{idx}.csv"
        output_csv = OUTPUT_DIR / f"clean{idx}.csv"

        if not input_csv.exists():
            raise FileNotFoundError(f"Input file not found: {input_csv}")

        process_csv(
            input_csv,
            output_csv,
            description_col,
            program_col,
            programs_to_remove,
        )
        print(f"Wrote: {output_csv}")


if __name__ == "__main__":
    main()
