# This script processes the raw alternative titles CSV file
import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "rawData" / "alternativeTitle.csv"
OUTPUT_PATH = BASE_DIR / "cleanedData" / "alternativeTitleCa.csv"
REQUIRED_COLUMNS = {"Code", "Structure Type", "English Name"}
OUTPUT_COLUMNS = ["Code", "English Name", "Alternative Title text"]
ENGLISH_LANGUAGE_ID = "13"

# Cleans alternative titles and keep English titles linked to descriptors
def process_csv(input_path, output_path):
    with input_path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.reader(infile)
        all_rows = list(reader)

    # Finds the real header row because file layout can vary
    header_index = None
    header = []
    for idx, row in enumerate(all_rows):
        row_set = {str(cell).strip() for cell in row}
        if REQUIRED_COLUMNS.issubset(row_set):
            header_index = idx
            header = [str(cell).strip() for cell in row]
            break

    if header_index is None:
        raise ValueError("Could not find expected header row in alternativeTitle.csv")

    data_rows = all_rows[header_index + 1 :]

    rows = []
    current_descriptor_code = ""
    current_descriptor_name = ""
    for row in data_rows:
        # Pads short rows so trailing columns are not lost
        padded = row + [""] * (len(header) - len(row))
        row_dict = {header[i]: padded[i] for i in range(len(header))}
        structure_type = str(row_dict.get("Structure Type", "") or "").strip().lower()
        code = str(row_dict.get("Code", "") or "").strip()
        english_name = str(row_dict.get("English Name", "") or "").strip()
        language_id = str(row_dict.get("Language ID", "") or "").strip()
        alt_title = str(row_dict.get("Alternative Title text", "") or "").strip()

        # Tracks the latest descriptor so continuation rows can reuse it
        if structure_type == "descriptor" and code and english_name:
            current_descriptor_code = code
            current_descriptor_name = english_name

        # Keeps only English alternative titles with valid descriptor context
        if language_id != ENGLISH_LANGUAGE_ID or not alt_title:
            continue
        if not current_descriptor_code or not current_descriptor_name:
            continue

        rows.append(
            {
                "Code": current_descriptor_code,
                "English Name": current_descriptor_name,
                "Alternative Title text": alt_title,
            }
        )

    # Writes cleaned results to output csv
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    # Run the cleaner for alternative titles
    process_csv(INPUT_PATH, OUTPUT_PATH)


if __name__ == "__main__":
    main()
