# Main script to run all preprocessing steps in order
from process_alternative_titles import process_csv as process_alternative_titles
from process_alternative_titles import INPUT_PATH as ALT_INPUT
from process_alternative_titles import OUTPUT_PATH as ALT_OUTPUT
from process_canadian_skills import process_csv as process_canadian_skills
from process_canadian_skills import BASE_DIR as PREPROCESSOR_DIR
from build_skills_ca_runtime import build_runtime_csv
from build_skills_ca_runtime import OUTPUT_PATH as RUNTIME_OUTPUT


def main():
    # Runs all preprocessing steps in order
    skills_input = PREPROCESSOR_DIR / "rawData" / "candianSkills.csv"
    skills_output = PREPROCESSOR_DIR / "cleanedData" / "skillsCa.csv"

    # Cleans source files
    process_canadian_skills(skills_input, skills_output)
    process_alternative_titles(ALT_INPUT, ALT_OUTPUT)

    # Builds final runtime file
    build_runtime_csv(skills_output, ALT_OUTPUT, RUNTIME_OUTPUT)

    # Shows output locations
    print(f"Wrote: {skills_output}")
    print(f"Wrote: {ALT_OUTPUT}")
    print(f"Wrote: {RUNTIME_OUTPUT}")


if __name__ == "__main__":
    main()
