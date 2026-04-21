from __future__ import annotations
import csv
from pathlib import Path


RAW_DIR = Path.home() / "Documents" / "CIS4900" / "RawData"
CLEANED_DIR = Path.home() / "Documents" / "CIS4900" / "Cleaned"
COLUMN_NAMES_PATH = RAW_DIR / "columnNames.txt"
OUTPUT_PATH = CLEANED_DIR / "unique_programs.txt"


# Reads the program column name from line 2 in columnNames.txt
def load_program_column_name(column_names_path):
    if not column_names_path.exists():
        raise FileNotFoundError(f"Column names file not found: {column_names_path}")

    with column_names_path.open("r", encoding="utf-8") as infile:
        lines = [line.strip() for line in infile if line.strip()]

    if len(lines) < 2:
        raise ValueError("columnNames.txt must contain at least two non-empty lines")

    return lines[1]


def main():
    # Collects unique program values from raw1 to raw5 and save them
    program_col = load_program_column_name(COLUMN_NAMES_PATH)
    unique_programs: set[str] = set()

    for idx in range(1, 6):
        raw_file = RAW_DIR / f"raw{idx}.csv"
        if not raw_file.exists():
            raise FileNotFoundError(f"Raw file not found: {raw_file}")

        with raw_file.open("r", encoding="utf-8", newline="") as infile:
            # Skip first line and use second line as header
            next(infile, None)
            reader = csv.DictReader(infile)
            if reader.fieldnames is None:
                raise ValueError(f"Missing header in raw file after skipping first line: {raw_file}")
            if program_col not in reader.fieldnames:
                raise ValueError(f"Missing column the required raw file")

            for row in reader:
                value = str(row.get(program_col, "")).strip()
                if value:
                    unique_programs.add(value)

    # Sorts results and write them to a text file
    sorted_programs = sorted(unique_programs, key=lambda s: s.lower())
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as outfile:
        for program in sorted_programs:
            outfile.write(program + "\n")

    print(f"Wrote: {OUTPUT_PATH}")
    print(f"Unique programs: {len(sorted_programs)}")


if __name__ == "__main__":
    main()
