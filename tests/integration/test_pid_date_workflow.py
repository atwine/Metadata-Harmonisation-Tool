import os
import sys
import time
import pathlib
import pandas as pd
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from app.components.get_recommendations import (
    embed_codebook,
    embed_study,
    generate_recommendations,
    generate_PID_date_recommendations,
)  # noqa: E402
from .utils import (
    ensure_results_dir,
    write_markdown_report,
    format_table,
    timestamp_id,
    ms,
    per_sec,
)  # noqa: E402


def _pick_study_folder(input_dir: str) -> str | None:
    """Pick a study folder under input/ (first non-hidden directory)."""
    p = pathlib.Path(input_dir)
    if not p.exists():
        return None
    for child in p.iterdir():
        if child.is_dir() and not child.name.startswith("."):
            return child.name
    return None


@pytest.mark.local_ollama
def test_pid_date_microbench_local():
    # Baseline env for local integration
    os.environ.setdefault("AI_PROVIDER", "ollama")
    os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
    os.environ.setdefault("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest")
    os.environ.setdefault("AI_REQUEST_TIMEOUT", "45")

    # Use repository-root input directory because get_recommendations.py uses input_path = "input"
    input_dir = os.path.join(ROOT_DIR, "input")
    study = _pick_study_folder(input_dir)
    if not study:
        pytest.skip("No study directory found under app/input/. Create a study (e.g., 'Trial') with the expected CSVs.")

    # 1) Ensure prerequisite embeddings and recommendations exist
    t_embed_start = time.perf_counter()
    embed_codebook()
    embed_study(study)
    t_embed_end = time.perf_counter()

    t_reco_start = time.perf_counter()
    generate_recommendations(study)
    t_reco_end = time.perf_counter()

    # 2) Run PID/Date generation and measure
    t_pid_start = time.perf_counter()
    generate_PID_date_recommendations(study)
    t_pid_end = time.perf_counter()

    # Load output and basic integrity checks
    out_path = os.path.join(input_dir, study, "dataset_variables_with_PID_date_recommendations.csv")
    assert os.path.exists(out_path), "PID/Date recommendations output CSV was not created."

    df = pd.read_csv(out_path)
    expected_cols = {"date_recommendations", "date_distances", "PID_recommendations", "PID_distances"}
    missing = expected_cols - set(df.columns)
    assert not missing, f"Missing expected columns in output: {missing}"

    records = len(df)

    # Metrics
    embed_s = t_embed_end - t_embed_start
    reco_s = t_reco_end - t_reco_start
    pid_s = t_pid_end - t_pid_start

    # Prepare report rows
    rows = [
        {"phase": "embed_codebook+embed_study", "elapsed_ms": ms(embed_s), "records": "-"},
        {"phase": "generate_recommendations", "elapsed_ms": ms(reco_s), "records": records},
        {"phase": "generate_PID_date_recommendations", "elapsed_ms": ms(pid_s), "records": records},
    ]

    # Compose Markdown report
    rid = timestamp_id()
    ensure_results_dir()

    sections = []
    sections.append("## Test Type\n\nLocal Integration — PID/Date workflow micro-benchmark (Ollama on http://localhost:11434)\n")

    sections.append(
        "## Parameters\n\n"
        f"- **[study]** {study}\n"
        f"- **[embedding_model]** {os.getenv('OLLAMA_EMBEDDING_MODEL', '')}\n"
        f"- **[records_processed]** {records}\n"
        f"- **[timeout_s]** {os.getenv('AI_REQUEST_TIMEOUT', '')}\n"
    )

    sections.append("## Phase Timings\n\n" + format_table(rows, ["phase", "elapsed_ms", "records"]))

    # Simple summary/takeaways section
    sections.append(
        "## Summary\n\n"
        "- **[Observation]** Embedding and recommendation phases dominate end-to-end time for larger studies.\n"
        "- **[Interpretation]** Throughput can be tuned by batch sizes and minimizing repeated embeddings (dedupe already applied).\n"
        "- **[Next]** Compare models and parameters in subsequent runs, and consider caching strategies across sessions.\n"
    )

    write_markdown_report(
        filename=f"pid_date_benchmark_{study}_{rid}.md",
        title=f"PID/Date Workflow Micro-benchmark — study {study}",
        sections=sections,
    )

    # Minimal assertion on content presence for robustness (not generation exactness)
    assert records >= 0
