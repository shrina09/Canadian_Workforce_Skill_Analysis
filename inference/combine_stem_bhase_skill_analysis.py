# Combines the row-level STEM/BHASE skill analysis outputs into a single group comparison file
from __future__ import annotations
import csv
from collections import Counter
from pathlib import Path
from typing import Dict, List


CLEANED_DIR = Path.home() / "Documents" / "CIS4900" / "Cleaned"
ROW_LEVEL_INPUTS = [CLEANED_DIR / f"clean{i}_skills_row_level.csv" for i in range(1, 6)]
GROUP_OUTPUT = CLEANED_DIR / "skills_group_comparison.csv"

# Splits the skills string into a cleaned list
def parse_skills(raw_value):
    if not raw_value.strip():
        return []
    return [item.strip() for item in raw_value.split("|") if item.strip()]


def main():
    # Combines row level STEM BHASE files into one comparison output
    print("Starting final STEM/BHASE comparison combine step...")
    print(f"Row-level inputs: {[str(path) for path in ROW_LEVEL_INPUTS]}")

    group_skill_counts = {"STEM": Counter(), "BHASE": Counter()}
    group_row_counts = {"STEM": 0, "BHASE": 0}
    group_skill_totals = {"STEM": 0, "BHASE": 0}

    total_rows = 0

    # Reads each row level file and count skills by group
    for file_path in ROW_LEVEL_INPUTS:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Missing row-level input file: {file_path}. "
                "Run inference/analyze_stem_bhase_skills.py for that clean file first."
            )

        file_rows = 0
        print(f"Combining {file_path} ...")
        with file_path.open("r", encoding="utf-8", newline="") as infile:
            reader = csv.DictReader(infile)
            required_columns = {"group", "skills"}
            if reader.fieldnames is None or not required_columns.issubset(set(reader.fieldnames)):
                raise ValueError(f"Missing required columns in {file_path}")

            for row in reader:
                group = str(row.get("group", "")).strip()
                if group not in {"STEM", "BHASE"}:
                    continue

                skills = parse_skills(str(row.get("skills", "")))
                group_row_counts[group] += 1
                total_rows += 1
                file_rows += 1

                for skill in skills:
                    group_skill_counts[group][skill] += 1
                    group_skill_totals[group] += 1

        print(f"Done {file_path.name}: rows={file_rows}")

    # Builds comparison rows with counts and normalized frequencies
    all_skills = set(group_skill_counts["STEM"].keys()) | set(group_skill_counts["BHASE"].keys())
    comparison_rows = []

    stem_total = group_skill_totals["STEM"]
    bhase_total = group_skill_totals["BHASE"]

    for skill in sorted(all_skills, key=str.lower):
        stem_count = group_skill_counts["STEM"][skill]
        bhase_count = group_skill_counts["BHASE"][skill]

        stem_freq = (stem_count / stem_total) if stem_total else 0.0
        bhase_freq = (bhase_count / bhase_total) if bhase_total else 0.0
        diff = stem_freq - bhase_freq

        comparison_rows.append(
            {
                "skill": skill,
                "stem_count": str(stem_count),
                "bhase_count": str(bhase_count),
                "stem_freq": f"{stem_freq:.8f}",
                "bhase_freq": f"{bhase_freq:.8f}",
                "freq_diff_stem_minus_bhase": f"{diff:.8f}",
            }
        )

    # Writes final comparison csv
    with GROUP_OUTPUT.open("w", encoding="utf-8", newline="") as outfile:
        fieldnames = [
            "skill",
            "stem_count",
            "bhase_count",
            "stem_freq",
            "bhase_freq",
            "freq_diff_stem_minus_bhase",
        ]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(comparison_rows)

    print(f"Wrote final comparison: {GROUP_OUTPUT}")
    print("Summary:")
    print(f"rows_processed={total_rows}")
    print(f"rows_stem={group_row_counts['STEM']}")
    print(f"rows_bhase={group_row_counts['BHASE']}")
    print(f"total_linked_skills_stem={stem_total}")
    print(f"total_linked_skills_bhase={bhase_total}")
    print(f"unique_skills_compared={len(all_skills)}")
    print(f"Rows by group: STEM={group_row_counts['STEM']} BHASE={group_row_counts['BHASE']}")
    print(f"Total linked skills by group: STEM={stem_total} BHASE={bhase_total}")
    print(f"Unique skills compared: {len(all_skills)}")


if __name__ == "__main__":
    main()
