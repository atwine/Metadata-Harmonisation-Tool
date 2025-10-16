def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _write_sample_codebook(codebook_csv: str, n: int) -> None:
    """Create a small sample target codebook if missing."""
    base = [
        ("AGE_YEARS", "Age of the subject in years"),
        ("DOB", "Date of birth of the subject"),
        ("SUBJECT_ID", "Unique identifier assigned to each participant"),
        ("HEIGHT_CM", "Standing height of the subject in centimeters"),
        ("WEIGHT_KG", "Body weight of the subject in kilograms"),
        ("BP_SYSTOLIC", "Systolic blood pressure in mmHg"),
        ("BP_DIASTOLIC", "Diastolic blood pressure in mmHg"),
        ("SEX", "Biological sex of the subject"),
        ("SMOKER", "Smoking status of the subject"),
        ("DIABETES", "Whether the subject has diabetes"),
    ]
    rows = base.copy()
    # If n is larger than base, synthesize extra generic variables
    i = 1
    while len(rows) < n:
        rows.append((f"FEATURE_{i}", f"Synthetic feature {i} description"))
        i += 1
    rows = rows[:n]
    df = pd.DataFrame(rows, columns=["variable_name", "description"])
    df.to_csv(codebook_csv, index=False)


def _write_sample_study(auto_csv: str, n: int) -> None:
    """Create a sample study variables file if missing."""
    base = [
        ("age", "Age in years"),
        ("dob", "Participant's date of birth"),
        ("patient_id", "Internal participant identifier"),
        ("height", "Height measured in centimeters"),
        ("weight", "Weight measured in kilograms"),
        ("sbp", "Systolic blood pressure"),
        ("dbp", "Diastolic blood pressure"),
        ("sex", "Biological sex recorded at enrollment"),
        ("smoker", "Self-reported smoking status"),
        ("diabetes", "History of diabetes"),
    ]
    rows = base.copy()
    i = 1
    while len(rows) < n:
        rows.append((f"var_{i}", f"Synthetic study variable {i}"))
        i += 1
    rows = rows[:n]
    df = pd.DataFrame(rows, columns=["variable_name", "description"])
    df.to_csv(auto_csv, index=False)


def _write_sample_ground_truth(gt_csv: str, codebook_csv: str, auto_csv: str) -> None:
    """Create a pre-filled ground truth mapping by aligning known pairs from the samples.
    Unknown/synthetic rows are left blank for manual completion.
    """
    cb = pd.read_csv(codebook_csv)
    st = pd.read_csv(auto_csv)

    # Map study variable (left) to codebook description (right)
    pairs = {
        "age": "Age of the subject in years",
        "dob": "Date of birth of the subject",
        "patient_id": "Unique identifier assigned to each participant",
        "height": "Standing height of the subject in centimeters",
        "weight": "Body weight of the subject in kilograms",
        "sbp": "Systolic blood pressure in mmHg",
        "dbp": "Diastolic blood pressure in mmHg",
        "sex": "Biological sex of the subject",
        "smoker": "Smoking status of the subject",
        "diabetes": "Whether the subject has diabetes",
    }

    cb_desc_set = set(cb["description"].astype(str))

    rows = []
    for _, r in st.iterrows():
        vn = str(r.get("variable_name", ""))
        td = pairs.get(vn, "")
        # Only keep target_description if it exists in codebook to avoid typos
        if td not in cb_desc_set:
            td = ""
        # Optional codebook variable name lookup
        tv = ""
        if td:
            match = cb.loc[cb["description"].astype(str) == td]
            if not match.empty:
                tv = str(match.iloc[0]["variable_name"])
        rows.append({
            "variable_name": vn,
            "target_description": td,
            "target_variable": tv,
        })

    out = pd.DataFrame(rows)
    out.to_csv(gt_csv, index=False)
#!/usr/bin/env python
"""
Scaffold a ground truth mapping CSV for a given study.

Creates: input/<Study>/ground_truth_mappings.csv with columns:
  - variable_name (from the study's dataset_variables_auto_completed.csv)
  - target_description (left empty for you to fill; must match codebook description)
  - target_variable (optional; codebook variable name)

Usage:
  python scripts/scaffold_ground_truth.py --study Trial [--force]

Optional (trial data generation for experiments):
  python scripts/scaffold_ground_truth.py --study Trial --generate-sample --n 20
    - If input files are missing, creates:
        input/target_variables.csv (sample codebook)
        input/<Study>/dataset_variables_auto_completed.csv (sample study variables)
        input/<Study>/ground_truth_mappings.csv (pre-filled mappings)

Notes:
  - Will not overwrite an existing ground_truth_mappings.csv unless --force is provided.
  - Without --generate-sample, expects existing files:
      input/<Study>/dataset_variables_auto_completed.csv
      input/target_variables.csv (for your reference when filling target_description)
"""

import argparse
import os
import sys
import pandas as pd

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INPUT_DIR = os.path.join(ROOT_DIR, 'input')


def main():
    parser = argparse.ArgumentParser(description='Scaffold ground truth mapping CSV for a study')
    parser.add_argument('--study', required=True, help='Study name (folder under input/)')
    parser.add_argument('--force', action='store_true', help='Overwrite existing ground_truth_mappings.csv if present')
    parser.add_argument('--generate-sample', action='store_true', help='Generate sample codebook and study files if missing')
    parser.add_argument('--n', type=int, default=20, help='Number of rows to generate for sample data')
    args = parser.parse_args()

    study = args.study
    study_dir = os.path.join(INPUT_DIR, study)
    auto_csv = os.path.join(study_dir, 'dataset_variables_auto_completed.csv')
    gt_csv = os.path.join(study_dir, 'ground_truth_mappings.csv')

    if not os.path.exists(study_dir):
        if args.generate_sample:
            _ensure_dir(study_dir)
        else:
            print(f"ERROR: Study directory not found: {study_dir}")
            sys.exit(1)

    # If asked to generate sample data, create missing inputs
    codebook_csv = os.path.join(INPUT_DIR, 'target_variables.csv')
    if args.generate_sample:
        if not os.path.exists(codebook_csv):
            _ensure_dir(INPUT_DIR)
            _write_sample_codebook(codebook_csv, max(args.n, 10))
        if not os.path.exists(auto_csv):
            _write_sample_study(auto_csv, max(args.n, 10))

    if not os.path.exists(auto_csv):
        print(f"ERROR: Missing file: {auto_csv}")
        sys.exit(1)

    if os.path.exists(gt_csv) and not args.force:
        print(f"REFUSING to overwrite existing file without --force: {gt_csv}")
        sys.exit(2)

    try:
        df = pd.read_csv(auto_csv)
    except Exception as e:
        print(f"ERROR: Failed to read {auto_csv}: {e}")
        sys.exit(1)

    if 'variable_name' not in df.columns:
        print("ERROR: 'variable_name' column not found in dataset_variables_auto_completed.csv")
        sys.exit(1)

    # Build scaffold DataFrame: unique variable names, empty targets
    vars_unique = (
        df['variable_name']
        .astype(str)
        .dropna()
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    out = pd.DataFrame({
        'variable_name': vars_unique,
        'target_description': [''] * len(vars_unique),
        'target_variable': [''] * len(vars_unique),
    })

    # If we generated sample data, also pre-fill ground truth based on known pairs
    if args.generate_sample:
        try:
            _write_sample_ground_truth(gt_csv, codebook_csv, auto_csv)
            print(f"Created sample ground truth with pre-filled mappings: {gt_csv}")
            return
        except Exception as e:
            print(f"WARNING: Could not pre-fill sample ground truth ({e}), falling back to empty scaffold.")

    try:
        out.to_csv(gt_csv, index=False)
    except Exception as e:
        print(f"ERROR: Failed to write {gt_csv}: {e}")
        sys.exit(1)

    print(f"Created scaffold: {gt_csv}")
    print("Fill 'target_description' with the exact codebook description from input/target_variables.csv.")
    print("Optionally fill 'target_variable' with the corresponding codebook variable name.")


if __name__ == '__main__':
    main()
