import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SKILLS_CA_PATH = BASE_DIR / "cleanedData" / "skillsCa.csv"
ALT_CA_PATH = BASE_DIR / "cleanedData" / "alternativeTitleCa.csv"
OUTPUT_PATH = BASE_DIR.parent / "inference" / "files" / "skills_ca.csv"


# Normalizes codes by lowercasing and removing non-alphanumeric characters
def _normalize_code(code):
    return "".join(ch.lower() for ch in code if ch.isalnum())


# Loads canonical skills and create code normalization map
def build_runtime_csv(skills_path: Path, alt_path: Path, output_path: Path) -> None:
    canonical_rows = []
    canonical_code_map = {}
    with skills_path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            code = str(row.get("Code", "")).strip()
            name = str(row.get("Name", "")).strip()
            if not code or not name:
                continue
            canonical_rows.append({"skills": name, "code": code})
            canonical_code_map[_normalize_code(code)] = {"code": code, "name": name}

    runtime_rows = list(canonical_rows)

    # Loads alternative English titles and map them to canonical code/name where possible
    with alt_path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            raw_code = str(row.get("Code", "")).strip()
            alt_title = str(row.get("Alternative Title text", "")).strip()
            if not raw_code or not alt_title:
                continue

            mapped = canonical_code_map.get(_normalize_code(raw_code))
            code = mapped["code"] if mapped else raw_code
            runtime_rows.append({"skills": alt_title, "code": code})

    # Removes duplicate skills text (case-insensitive), keeping first occurrence
    deduped = []
    seen_skills = set()
    for row in runtime_rows:
        key = row["skills"].strip().lower()
        if not key:
            continue
        if key in seen_skills:
            continue
        seen_skills.add(key)
        deduped.append(row)
    
    # Writes results to output CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=["skills", "code"])
        writer.writeheader()
        writer.writerows(deduped)


def main():
    build_runtime_csv(SKILLS_CA_PATH, ALT_CA_PATH, OUTPUT_PATH)


if __name__ == "__main__":
    main()
