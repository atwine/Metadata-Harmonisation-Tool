import os
import sys
import time
import math
from typing import List
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from app.components.get_recommendations import get_embedding  # noqa: E402
from .utils import ensure_results_dir, write_markdown_report, write_json_report, format_table, timestamp_id, ms, per_sec, p95  # noqa: E402


@pytest.mark.local_ollama
@pytest.mark.parametrize("dataset_size", [100, 1000, 5000, 10000, 15000])
def test_embeddings_throughput(dataset_size: int):
    # Ensure env for local integration
    os.environ.setdefault("AI_PROVIDER", "ollama")
    os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
    os.environ.setdefault("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest")
    os.environ.setdefault("AI_REQUEST_TIMEOUT", "45")

    # Skip large sizes unless explicitly enabled
    if dataset_size > 1000 and os.getenv("RUN_LARGE", "0") != "1":
        pytest.skip("Large run skipped (set RUN_LARGE=1 to enable 5k/10k/15k)")

    # Text length tier controls approximate length of each input
    tier = os.getenv("LENGTH_TIER", "medium").lower()
    tokens_by_tier = {"short": 10, "medium": 50, "long": 200}
    target_tokens = tokens_by_tier.get(tier, 50)

    def make_text(i: int) -> str:
        # Create a deterministic string of ~target_tokens words
        base = f"Study embeddings throughput item {i}. "
        filler = " ".join([f"w{j}" for j in range(target_tokens)])
        return (base + filler).strip()

    # Create unique texts to avoid cache effects on size scaling
    texts: List[str] = [make_text(i) for i in range(dataset_size)]

    per_item_lat = []
    errors = 0
    processed = 0
    max_minutes = None
    try:
        max_minutes = float(os.getenv("MAX_MINUTES", ""))
    except ValueError:
        max_minutes = None

    t0 = time.perf_counter()
    for t in texts:
        s0 = time.perf_counter()
        emb = get_embedding(t)
        s1 = time.perf_counter()
        per_item_lat.append(s1 - s0)
        # Basic sanity: embedding must be a list
        if not isinstance(emb, list) or len(emb) == 0:
            errors += 1
        processed += 1
        if max_minutes is not None:
            if (time.perf_counter() - t0) > (max_minutes * 60.0):
                break
    t1 = time.perf_counter()

    total_s = t1 - t0
    approx_tokens_total = int(math.ceil(sum(len(t) for t in texts) / 4.0))

    timebox_reached = bool(max_minutes is not None and processed < dataset_size)

    row = {
        "dataset_size": dataset_size,
        "processed": processed,
        "latency_avg_ms": ms(sum(per_item_lat) / max(len(per_item_lat), 1)),
        "latency_p95_ms": ms(p95(per_item_lat)),
        "items_per_sec": per_sec(processed, total_s),
        "errors": errors,
        "timeout_s": os.getenv("AI_REQUEST_TIMEOUT", ""),
        "text_length_tier": tier,
        "approx_input_tokens_total": approx_tokens_total,
        "timebox_minutes": max_minutes if max_minutes is not None else "",
        "timebox_reached": timebox_reached,
    }

    # Write report
    rid = timestamp_id()
    section = "## Embeddings Throughput\n\n" + format_table([row], [
        "dataset_size", "processed", "latency_avg_ms", "latency_p95_ms", "items_per_sec", "errors", "timeout_s"
    ])
    summary = (
        "## Summary\n\n"
        f"- **[run_label]** {os.getenv('RUN_LABEL', '')}\n"
        f"- **[tier]** {tier} — **[size]** {dataset_size} — **[processed]** {processed}\n"
        f"- **[tokens_est]** {approx_tokens_total}\n"
        f"- **[timebox]** {'reached' if timebox_reached else 'not used'}\n"
    )
    ensure_results_dir()
    write_markdown_report(
        filename=f"embeddings_throughput_{dataset_size}_{rid}.md",
        title=f"Embeddings Throughput (nomic-embed-text) — size {dataset_size} — {tier}",
        sections=[section, summary],
    )
    # JSON artifact for dashboard aggregation
    write_json_report(
        filename=f"embeddings_throughput_{dataset_size}_{rid}.json",
        data={
            "type": "embeddings_throughput",
            "dataset_size": dataset_size,
            "metrics": row,
            "timestamp": rid,
            "model": os.getenv("OLLAMA_EMBEDDING_MODEL", ""),
            "run_label": os.getenv("RUN_LABEL", ""),
        },
    )

    # Keep test resilient: allow a few errors but not many
    assert errors == 0, f"Embedding errors encountered: {errors}"
