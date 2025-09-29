import os
import io
import csv
import shutil
import pandas as pd

from app.components.validation import validate_codebook_file, validate_study_files


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def test_study_validation_ok(tmp_path):
    study = "__test_study__"
    base = tmp_path / "input" / study
    _ensure_dir(base)

    # Create example_data.csv
    ex_path = base / "example_data.csv"
    with open(ex_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["age_months", "sex"])  # columns
        w.writerow([24, "1"])  # data rows
        w.writerow([12, "0"])  # data rows

    # Create dataset_variables_with_PID_date_recommendations.csv
    rec_path = base / "dataset_variables_with_PID_date_recommendations.csv"
    with open(rec_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["variable_name", "description"])  # headers
        w.writerow(["age_months", "Age in months"])  # variable present in example_data

    # Copy these into the project-relative input/ tree so validation can find them
    proj_input = os.path.join("input", study)
    _ensure_dir(proj_input)
    shutil.copy2(str(ex_path), os.path.join(proj_input, "example_data.csv"))
    shutil.copy2(str(rec_path), os.path.join(proj_input, "dataset_variables_with_PID_date_recommendations.csv"))

    try:
        res = validate_study_files(study)
        # Expect no hard errors
        assert isinstance(res, dict)
        assert "errors" in res and "warnings" in res
        assert len(res["errors"]) == 0
    finally:
        # Cleanup created files
        try:
            os.remove(os.path.join(proj_input, "example_data.csv"))
        except FileNotFoundError:
            pass
        try:
            os.remove(os.path.join(proj_input, "dataset_variables_with_PID_date_recommendations.csv"))
        except FileNotFoundError:
            pass
        try:
            os.rmdir(proj_input)
        except OSError:
            pass


def test_codebook_validation_sanity():
    # Do not mutate existing codebook if present. Just exercise the function and assert shape.
    res = validate_codebook_file()
    assert isinstance(res, dict)
    assert "errors" in res and "warnings" in res


def test_codebook_validation_missing_columns_and_restore():
    """Create a temporary codebook with missing columns; restore any existing file after test."""
    import os
    import shutil

    path = os.path.join("input", "target_variables.csv")
    backup_path = os.path.join("input", "target_variables.csv.bak_test")

    # Backup existing file if present
    had_backup = False
    if os.path.exists(path):
        shutil.move(path, backup_path)
        had_backup = True

    try:
        # Write a minimal malformed codebook (missing both name and description)
        _ensure_dir("input")
        with open(path, "w", encoding="utf-8") as f:
            f.write("dType,Categories\n")
            f.write("string,{}\n")

        res = validate_codebook_file()
        assert isinstance(res, dict)
        # Should report missing identifiers
        assert any("must include either a variable name" in w or "must include either a variable name" in e for w in res["warnings"] for e in res["errors"]) or (len(res["errors"]) > 0)
    finally:
        # Cleanup and restore
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        if had_backup:
            shutil.move(backup_path, path)
        else:
            try:
                os.remove(backup_path)
            except FileNotFoundError:
                pass


def test_study_validation_missing_columns(tmp_path):
    study = "__test_study_missing__"
    base = tmp_path / "input" / study
    _ensure_dir(base)

    # example_data.csv present
    ex_path = base / "example_data.csv"
    with open(ex_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["age_months"])  # columns
        w.writerow([24])

    # recommendations missing 'description'
    rec_path = base / "dataset_variables_with_PID_date_recommendations.csv"
    with open(rec_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["variable_name"])  # missing description column
        w.writerow(["age_months"]) 

    proj_input = os.path.join("input", study)
    _ensure_dir(proj_input)
    shutil.copy2(str(ex_path), os.path.join(proj_input, "example_data.csv"))
    shutil.copy2(str(rec_path), os.path.join(proj_input, "dataset_variables_with_PID_date_recommendations.csv"))

    try:
        res = validate_study_files(study)
        assert isinstance(res, dict)
        # Expect a warning about missing description column
        assert any("missing column: description" in w.lower() for w in res["warnings"])
    finally:
        try:
            os.remove(os.path.join(proj_input, "example_data.csv"))
        except FileNotFoundError:
            pass
        try:
            os.remove(os.path.join(proj_input, "dataset_variables_with_PID_date_recommendations.csv"))
        except FileNotFoundError:
            pass
        try:
            os.rmdir(proj_input)
        except OSError:
            pass
