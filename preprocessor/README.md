# Canadian Skills Preprocessor

This folder contains data cleaning scripts that prepare Skills and Competencies Taxonomy Data (SCT) 2025 -Version 1.0 for runtime use. It uses Descriptors - Skills and Competencies Taxonomy - 2025 Version 1.0 - EN and Alternatives Titles - Skills and Competencies Taxonomy - 2023 Version 1.0 - EN-FR as raw data.

Main goal:

- Convert raw CSV files into a final runtime file at `inference/files/skills_ca.csv`

## What This Folder Is For

The preprocessor handles three steps:

1. Clean canonical skills data from `candianSkills.csv`
2. Clean alternative titles from `alternativeTitle.csv`
3. Merge both into one runtime CSV used by inference

## Dependencies

For scripts in `preprocessor/`:

- Python `3.10+`

## Quick Start

Run the full pipeline:

```bash
python3 preprocessor/run_all.py
```

This creates:

- `preprocessor/cleanedData/skillsCa.csv`
- `preprocessor/cleanedData/alternativeTitleCa.csv`
- `inference/files/skills_ca.csv`

## Run Step By Step

### Step 1 Clean canonical skills

Script:

- `preprocessor/process_canadian_skills.py`

Run:

```bash
python3 preprocessor/process_canadian_skills.py
```

Input:

- `preprocessor/rawData/candianSkills.csv`

Output:

- `preprocessor/cleanedData/skillsCa.csv`

### Step 2 Clean alternative titles

Script:

- `preprocessor/process_alternative_titles.py`

Run:

```bash
python3 preprocessor/process_alternative_titles.py
```

Input:

- `preprocessor/rawData/alternativeTitle.csv`

Output:

- `preprocessor/cleanedData/alternativeTitleCa.csv`

### Step 3 Build runtime skills file

Script:

- `preprocessor/build_skills_ca_runtime.py`

Run:

```bash
python3 preprocessor/build_skills_ca_runtime.py
```

Inputs:

- `preprocessor/cleanedData/skillsCa.csv`
- `preprocessor/cleanedData/alternativeTitleCa.csv`

Output:

- `inference/files/skills_ca.csv`

## Additional Local Utilities

These are separate helper scripts and are not part of `run_all.py`

### Find unique program names

Script:

- `preprocessor/find_unique_programs.py`

Run:

```bash
python3 preprocessor/find_unique_programs.py
```

Notes:

- Reads from `~/Documents/CIS4900/RawData/raw1.csv` to `raw5.csv`
- Uses `~/Documents/CIS4900/RawData/columnNames.txt`
- Writes `~/Documents/CIS4900/Cleaned/unique_programs.txt`

### Process career data files

Script:

- `preprocessor/process_career_data.py`

Run:

```bash
python3 preprocessor/process_career_data.py
```

Notes:

- Reads from `~/Documents/CIS4900/RawData/raw1.csv` to `raw5.csv`
- Uses `~/Documents/CIS4900/RawData/columnNames.txt`
- Uses `~/Documents/CIS4900/Cleaned/removeRows.txt`
- Writes cleaned files to `~/Documents/CIS4900/Cleaned/clean1.csv` to `clean5.csv`
