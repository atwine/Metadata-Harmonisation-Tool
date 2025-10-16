import os
import sys
import time
import ast
import math
import pytest
import pandas as pd

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from app.components.get_recommendations import (
    embed_codebook,
    embed_study,
    generate_recommendations,
)
from .utils import (
    ensure_results_dir,
    write_markdown_report,
    write_json_report,
    format_table,
    timestamp_id,
)


def _pick_study_folder(input_dir: str) -> str | None:
    try:
        for name in os.listdir(input_dir):
            if name.startswith("."):
                continue
            full = os.path.join(input_dir, name)
            if os.path.isdir(full):
                return name
    except FileNotFoundError:
        return None
    return None


def _mrr_at_k(ranks: list[int], k: int) -> float:
    if not ranks:
        return 0.0
    score = 0.0
    for r in ranks:
        if r > 0 and r <= k:
            score += 1.0 / r
    return round(score / len(ranks), 4)


def _ndcg_at_k(ranks: list[int], k: int) -> float:
    # Single relevant item case; DCG = 1/log2(1+rank) if rank<=k else 0; iDCG=1
    def dcg(r: int) -> float:
        if r <= 0 or r > k:
            return 0.0
        return 1.0 / math.log2(1 + r)
    if not ranks:
        return 0.0
    val = sum(dcg(r) for r in ranks) / max(len(ranks), 1)
    return round(val, 4)


@pytest.mark.local_ollama
def test_accuracy_mapping():
    os.environ.setdefault("AI_PROVIDER", "ollama")
    os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
    os.environ.setdefault("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest")
    os.environ.setdefault("AI_REQUEST_TIMEOUT", "45")

    input_dir = os.path.join(ROOT_DIR, "input")
    study = os.getenv("TEST_STUDY") or _pick_study_folder(input_dir)
    if not study:
        pytest.skip("No study directory found under input/. Create a study (e.g., 'Trial').")

    # Ensure prerequisites
    t0 = time.perf_counter()
    embed_codebook()
    embed_study(study)
    generate_recommendations(study)
    t1 = time.perf_counter()

    rec_csv = os.path.join(input_dir, study, "dataset_variables_with_recommendations.csv")
    gt_csv = os.path.join(input_dir, study, "ground_truth_mappings.csv")
    if not os.path.exists(gt_csv):
        pytest.skip(f"Missing ground truth file: {gt_csv}")

    rec_df = pd.read_csv(rec_csv)
    gt_df = pd.read_csv(gt_csv)

    # Index recommendations by variable_name
    rec_idx = {str(r["variable_name"]): r for _, r in rec_df.iterrows()}

    total = 0
    valid = 0
    missing = 0
    ranks: list[int] = []

    for _, row in gt_df.iterrows():
        total += 1
        var_name = str(row.get("variable_name", ""))
        target_desc = str(row.get("target_description", ""))
        if not var_name or not target_desc:
            missing += 1
            continue
        rec_row = rec_idx.get(var_name)
        if rec_row is None:
            missing += 1
            continue
        try:
            recs = rec_row.get("target_recommendations")
            if isinstance(recs, str):
                recs = ast.literal_eval(recs)
            if not isinstance(recs, list):
                missing += 1
                continue
        except Exception:
            missing += 1
            continue
        # Find rank (1-based) of the correct description
        try:
            rnk = recs.index(target_desc) + 1
        except ValueError:
            rnk = 0  # not found
        ranks.append(rnk)
        valid += 1

    def topk(k: int) -> float:
        if valid == 0:
            return 0.0
        hits = sum(1 for r in ranks if r > 0 and r <= k)
        return round(hits / valid, 4)

    metrics = {
        "study": study,
        "total": total,
        "valid": valid,
        "missing": total - valid,
        "top1": topk(1),
        "top3": topk(3),
        "top5": topk(5),
        "mrr@5": _mrr_at_k(ranks, 5),
        "ndcg@5": _ndcg_at_k(ranks, 5),
        "prep_elapsed_ms": round((t1 - t0) * 1000.0, 2),
    }

    # Markdown
    rid = timestamp_id()
    ensure_results_dir()
    rows = [{
        "study": metrics["study"],
        "total": metrics["total"],
        "valid": metrics["valid"],
        "top1": metrics["top1"],
        "top3": metrics["top3"],
        "top5": metrics["top5"],
        "mrr@5": metrics["mrr@5"],
        "ndcg@5": metrics["ndcg@5"],
    }]
    section = "## Accuracy (Mapping to Target Codebook)\n\n" + format_table(rows, ["study", "total", "valid", "top1", "top3", "top5", "mrr@5", "ndcg@5"]) \
        + f"\nPrep elapsed ms: {metrics['prep_elapsed_ms']}\n"

    # Short narrative
    narrative = (
        "## Summary\n\n"
        f"- **[study]** {study}\n"
        f"- **[what worked]** Scored {metrics['valid']} items; computed Top‑K and ranking quality.\n"
        f"- **[needs attention]** {metrics['missing']} items had missing references or recommendations.\n"
    )

    write_markdown_report(
        filename=f"accuracy_{study}_{rid}.md",
        title=f"Accuracy — {study}",
        sections=[section, narrative],
    )

    # JSON
    write_json_report(
        filename=f"accuracy_{study}_{rid}.json",
        data={
            "type": "accuracy",
            "timestamp": rid,
            "run_label": os.getenv("RUN_LABEL", ""),
            "study": study,
            "metrics": metrics,
        },
    )
