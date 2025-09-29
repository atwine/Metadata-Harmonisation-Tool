import argparse
import random
from datetime import datetime, timedelta
import math
import os
import pandas as pd

# Reproducibility
random.seed(42)

VILLAGES = [
    "Kampala", "Entebbe", "Jinja", "Gulu", "Mbarara", "Lira", "Mbale",
    "Arua", "Fort Portal", "Hoima", "Masaka", "Soroti", "Kabale", "Bushenyi"
]

# Schema mirrors dataset_variables.csv
VARIABLES = [
    ("patient_id", "Patient Identifier"),
    ("visit_date", "Visit Date (YYYY-MM-DD)"),
    ("sex", "Sex (M/F)"),
    ("age", "Age in years"),
    ("height_cm", "Height in centimeters"),
    ("weight_kg", "Weight in kilograms"),
    ("sbp", "Systolic blood pressure (mmHg)"),
    ("dbp", "Diastolic blood pressure (mmHg)"),
    ("pulse", "Heart rate (beats per minute)"),
    ("temp_c", "Body temperature in Celsius"),
    ("hiv_status", "HIV status (Positive/Negative)"),
    ("on_art", "On ART treatment (Yes/No)"),
    ("village", "Residence village"),
    ("bmi", "Body Mass Index (kg/m2)"),
]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def gen_row(i: int, start_date: datetime) -> dict:
    pid = f"UG{i+1:04d}"
    date = start_date + timedelta(days=random.randint(0, 120))
    sex = random.choice(["M", "F"])
    age = random.randint(18, 75)
    height_cm = clamp(round(random.normalvariate(168, 9), 1), 145.0, 200.0)
    weight_kg = clamp(round(random.normalvariate(70, 14), 1), 42.0, 130.0)
    sbp = int(clamp(round(random.normalvariate(128, 18)), 90, 200))
    dbp = int(clamp(round(random.normalvariate(82, 12)), 55, 120))
    pulse = int(clamp(round(random.normalvariate(76, 10)), 48, 130))
    temp_c = round(clamp(random.normalvariate(36.8, 0.5), 35.5, 40.0), 1)
    hiv_pos = random.random() < 0.22
    hiv_status = "Positive" if hiv_pos else "Negative"
    # ART more likely if HIV positive
    on_art = "Yes" if (hiv_pos and random.random() < 0.8) or (not hiv_pos and random.random() < 0.05) else "No"
    village = random.choice(VILLAGES)
    bmi = round(weight_kg / ((height_cm / 100.0) ** 2), 1)

    return {
        "patient_id": pid,
        "visit_date": date.strftime("%Y-%m-%d"),
        "sex": sex,
        "age": age,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "sbp": sbp,
        "dbp": dbp,
        "pulse": pulse,
        "temp_c": temp_c,
        "hiv_status": hiv_status,
        "on_art": on_art,
        "village": village,
        "bmi": bmi,
    }


def ensure_variables_table(out_dir: str):
    # Create dataset_variables.csv matching VARIABLES (with index column like CH_SIB)
    df = pd.DataFrame(
        {
            "variable_name": [name for name, _ in VARIABLES],
            "description": [desc for _, desc in VARIABLES],
        }
    )
    df.to_csv(os.path.join(out_dir, "dataset_variables.csv"))


def generate(out_dir: str, n_rows: int):
    start_date = datetime(2024, 6, 1)
    rows = [gen_row(i, start_date) for i in range(n_rows)]
    df = pd.DataFrame(rows)
    # Write with index column to mirror existing example pattern
    df.to_csv(os.path.join(out_dir, "example_data.csv"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate ACE_Uganda example dataset")
    parser.add_argument("--rows", type=int, default=1000, help="Number of rows to generate (default: 1000)")
    parser.add_argument("--out", type=str, default=os.path.dirname(__file__), help="Output directory (default: this folder)")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    ensure_variables_table(args.out)
    generate(args.out, args.rows)
    print(f"Wrote dataset_variables.csv and example_data.csv to {args.out} with {args.rows} rows.")
