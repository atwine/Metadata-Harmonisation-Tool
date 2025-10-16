import os
import sys
import time
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from config import ModelConfig, AIProvider  # noqa: E402
from .utils import ensure_results_dir, write_markdown_report, write_json_report, format_table, timestamp_id  # noqa: E402


@pytest.mark.local_ollama
def test_connectivity_and_models():
    # Ensure base env for local integration
    os.environ.setdefault("AI_PROVIDER", "ollama")
    os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
    os.environ.setdefault("OLLAMA_CHAT_MODEL", "llama3.1:8b")
    os.environ.setdefault("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest")
    os.environ.setdefault("AI_REQUEST_TIMEOUT", "45")

    cfg = ModelConfig()
    # Use env-driven setup for realistic behavior
    cfg.setup_from_env()

    # Hard-set provider enum for safety
    cfg.provider = AIProvider.OLLAMA

    t0 = time.perf_counter()
    client = cfg.get_client()
    t1 = time.perf_counter()

    assert client is not None, "Failed to initialize Ollama client"

    ok, msg = cfg.validate_models()
    t2 = time.perf_counter()

    # Write a short report
    rid = timestamp_id()
    rows = [
        {
            "phase": "client_init",
            "elapsed_ms": round((t1 - t0) * 1000, 2),
            "message": "initialized",
        },
        {
            "phase": "validate_models",
            "elapsed_ms": round((t2 - t1) * 1000, 2),
            "message": msg,
        },
    ]
    section = "## Connectivity and Model Validation\n\n" + format_table(rows, ["phase", "elapsed_ms", "message"])  # type: ignore
    summary = (
        "## Summary\n\n"
        f"- **[run_label]** {os.getenv('RUN_LABEL', '')}\n"
        f"- **[endpoint]** {os.getenv('OLLAMA_BASE_URL', '')}\n"
        f"- **[result]** {'OK' if ok else 'Failed'} — {msg}\n"
    )
    ensure_results_dir()
    write_markdown_report(
        filename=f"connectivity_{rid}.md",
        title="Local Connectivity & Model Validation",
        sections=[section, summary],
    )

    # JSON artifact
    write_json_report(
        filename=f"connectivity_{rid}.json",
        data={
            "type": "connectivity",
            "timestamp": rid,
            "phases": rows,
            "base_url": os.getenv("OLLAMA_BASE_URL", ""),
            "run_label": os.getenv("RUN_LABEL", ""),
        },
    )

    assert ok, f"Model validation failed: {msg}"
