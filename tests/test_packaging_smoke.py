import io
import zipfile
import pandas as pd

from app.components.transform_engine import generate_validation_report


def test_packaging_smoke():
    # Create dummy dataframes
    original_df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    transformed_df = pd.DataFrame({"A": [1.0, 2.0]})

    # Dummy metrics/warnings
    metrics = {"a": {"success": 2, "errors": 0}}
    warnings = ["Example warning"]

    validation_report = generate_validation_report(metrics, warnings)
    assert "Validation Report" in validation_report
    assert "Total successes" in validation_report

    # Build ZIP in-memory similar to the download page
    memfile = io.BytesIO()
    with zipfile.ZipFile(memfile, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('original_data.csv', original_df.to_csv(index=False))
        zf.writestr('transformed_data.csv', transformed_df.to_csv(index=False))
        zf.writestr('mapping_summary.csv', pd.DataFrame({"k": [1]}).to_csv(index=False))
        zf.writestr('validation_report.txt', validation_report)
        zf.writestr('summary.txt', "Success rate: 100.00%\n")
    memfile.seek(0)

    with zipfile.ZipFile(memfile, 'r') as zf:
        names = set(zf.namelist())
        assert {
            'original_data.csv',
            'transformed_data.csv',
            'mapping_summary.csv',
            'validation_report.txt',
            'summary.txt',
        }.issubset(names)
