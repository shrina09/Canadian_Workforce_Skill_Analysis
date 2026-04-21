# This script processes the raw Canadian skills data CSV
import csv
from pathlib import Path


EXCLUDED_STRUCTURE_TYPES = {
    "category",
    "sub-category",
    "similarity group",
}


BASE_DIR = Path(__file__).resolve().parent


# Cleans the Canadian skills csv and keep descriptor rows only
def process_csv(input_path: Path, output_path: Path) -> None:
    # Source files uses semicolon delimiter and has one placeholder header row
    with input_path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.reader(infile, delimiter=";")
        # Skips placeholder header row
        next(reader, None)
        # Uses second row as actual header
        header = next(reader, None)
        if not header:
            raise ValueError("Could not read header row from input CSV.")
        rows = [dict(zip(header, row)) for row in reader]

    if not rows:
        raise ValueError("No rows found after reading input CSV.")

    if "Structure Type" not in rows[0]:
        raise ValueError("Missing required column: 'Structure Type'")

    # Keeps only descriptor rows and remove unused columns
    output_rows = []
    for row in rows:
        structure_type = str(row.get("Structure Type", "")).strip().lower()
        if structure_type != "descriptor":
            continue
        if structure_type in EXCLUDED_STRUCTURE_TYPES:
            continue

        cleaned = {
            key: value
            for key, value in row.items()
            if key not in {"Description", "Structure Type"}
        }
        output_rows.append(cleaned)

    # Writes cleaned files to the output csv
    output_path.parent.mkdir(parents=True, exist_ok=True)


    fieldnames = list(output_rows[0].keys()) if output_rows else []
    with output_path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)


def main() -> None:
    input_path = BASE_DIR / "rawData" / "candianSkills.csv"
    output_path = BASE_DIR / "cleanedData" / "skillsCa.csv"
    process_csv(input_path, output_path)


if __name__ == "__main__":
    main()
