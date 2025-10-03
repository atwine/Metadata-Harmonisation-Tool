#!/usr/bin/env python3
"""
Benchmark initialization pipeline timings and embedding call counts.

Measures per-step wall times for:
- PDF to text conversion (selected studies)
- Embedding generation (codebook + selected studies)
- Recommendations (selected studies)
- PID/Date recommendations (selected studies)

Also counts how many times app.components.get_recommendations.get_embedding() is called,
which indicates provider calls after Phase 1 (dedup + cache).

Usage (local):
  python scripts/benchmark_init.py --fresh --study ACE_Uganda
  python scripts/benchmark_init.py --fresh --study ACE_Uganda --study CH_SIB

Usage (docker):
  docker-compose -f docker/docker-compose.yml exec metadata-harmonisation-tool \
    python scripts/benchmark_init.py --fresh --study ACE_Uganda

Notes:
- This script targets selected studies explicitly (where supported by the underlying code).
- It does NOT modify application code; it monkey-patches get_embedding to count calls during the run.
- For generate_descriptions(), the app's function processes all studies; this script times embeddings/recommendations only.
"""

import argparse
import os
import sys
import time
import json
from pathlib import Path
from typing import List

# Ensure project root is on sys.path
HERE = Path(__file__).resolve()
PROJ_ROOT = HERE.parents[1]
os.chdir(PROJ_ROOT)
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

# Imports from the app
from app.components.get_recommendations import (
    embed_codebook,
    embed_study,
    generate_recommendations,
    generate_PID_date_recommendations,
    get_embedding as gr_get_embedding,
)

# For optional one-off conversion for selected studies
from pdfminer.high_level import extract_text
import streamlit as st
from config import ModelConfig, AIProvider

INPUT_DIR = PROJ_ROOT / "input"
EXAMPLE_DIR = PROJ_ROOT / "example_data"


def _list_studies() -> List[str]:
    if not INPUT_DIR.exists():
        return []
    return sorted([p.name for p in INPUT_DIR.iterdir() if p.is_dir() and not p.name.startswith('.')])


def _ensure_codebook():
    """Ensure input/target_variables.csv exists by staging from example_data if available."""
    target = INPUT_DIR / "target_variables.csv"
    if target.exists():
        return
    # Prefer ACE_Uganda codebook, fallback to generic example
    candidates = [
        EXAMPLE_DIR / "ACE_Uganda" / "target_variables.csv",
        EXAMPLE_DIR / "target_variables.csv",
    ]
    for c in candidates:
        if c.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(c.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Staged codebook from {c.relative_to(PROJ_ROOT)} -> {target.relative_to(PROJ_ROOT)}")
            return
    print("Warning: No codebook found; please place input/target_variables.csv manually.")


def _delete_if_exists(path: Path):
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def _fresh_cleanup(studies: List[str]):
    # Codebook embeddings
    _delete_if_exists(INPUT_DIR / "target_variables_with_embeddings.csv")
    # Per-study artifacts
    for s in studies:
        sp = INPUT_DIR / s
        _delete_if_exists(sp / "dataset_variables_auto_completed.csv")
        _delete_if_exists(sp / "dataset_variables_with_embeddings.csv")
        _delete_if_exists(sp / "dataset_variables_with_recommendations.csv")
        _delete_if_exists(sp / "dataset_variables_with_PID_date_recommendations.csv")


def _stage_study_if_needed(study: str):
    """Ensure input/<study>/ has dataset_variables.csv; if not, copy from example_data.
    Also create dataset_variables_auto_completed.csv if missing (copy of dataset_variables.csv)."""
    sp = INPUT_DIR / study
    sp.mkdir(parents=True, exist_ok=True)
    src_dir = EXAMPLE_DIR / study
    dst_dv = sp / "dataset_variables.csv"
    if not dst_dv.exists():
        src_dv = src_dir / "dataset_variables.csv"
        if src_dv.exists():
            dst_dv.write_text(src_dv.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Staged {study}/dataset_variables.csv from example_data.")
        else:
            print(f"Warning: {src_dv} not found; cannot stage study {study}.")
    # Ensure auto_completed exists (needed by embed_study)
    auto_path = sp / "dataset_variables_auto_completed.csv"
    if not auto_path.exists() and dst_dv.exists():
        auto_path.write_text(dst_dv.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Created {study}/dataset_variables_auto_completed.csv as a copy of dataset_variables.csv.")


def _convert_pdf_to_txt_for(study: str):
    pdf_path = INPUT_DIR / study / "context.pdf"
    txt_path = INPUT_DIR / study / "context.txt"
    if pdf_path.exists() and not txt_path.exists():
        try:
            text = extract_text(str(pdf_path))
            txt_path.write_text(text, encoding="utf-8")
        except Exception:
            pass


def _timeit(label: str, fn):
    t0 = time.perf_counter()
    fn()
    t1 = time.perf_counter()
    return label, t1 - t0


def main():
    parser = argparse.ArgumentParser(description="Benchmark initialization and recommendations")
    parser.add_argument("--fresh", action="store_true", help="Delete derived CSVs to force recompute")
    parser.add_argument("--study", action="append", help="Study name (repeatable). If omitted, uses all studies.")
    parser.add_argument("--ollama-url", type=str, default=os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434"), help="Ollama base URL for provider (use http://ollama:11434 in docker with ollama profile)")
    args = parser.parse_args()

    if args.study:
        # support comma-separated too; use provided names directly (stage later)
        selected = []
        for item in args.study:
            selected.extend([x.strip() for x in item.split(",") if x.strip()])
        # de-dup while preserving order
        seen = set()
        studies = [s for s in selected if not (s in seen or seen.add(s))]
    else:
        studies = _list_studies()

    if args.fresh:
        _fresh_cleanup(studies)

    # Count provider calls by wrapping get_recommendations.get_embedding
    call_count = {"get_recommendations.get_embedding": 0}
    original_gr_get_embedding = gr_get_embedding

    def _counting_gr_get_embedding(*a, **kw):
        call_count["get_recommendations.get_embedding"] += 1
        return original_gr_get_embedding(*a, **kw)

    # Monkey patch for the duration of the benchmark
    import app.components.get_recommendations as gr_mod
    gr_mod.get_embedding = _counting_gr_get_embedding  # type: ignore

    timings = []

    # Ensure inputs exist
    _ensure_codebook()
    for s in studies:
        _stage_study_if_needed(s)
    # After staging, ensure they exist
    studies = [s for s in studies if (INPUT_DIR / s / "dataset_variables.csv").exists()]
    if not studies:
        print("No studies found. Ensure input/<study>/ exists with required files.")
        return

    # Configure AI provider in Streamlit session so get_ai_provider() works in headless benchmark
    mc = ModelConfig()
    mc.provider = AIProvider.OLLAMA
    mc.chat_model = os.environ.get("OLLAMA_CHAT_MODEL", "llama3.1:8b")
    mc.embedding_model = os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    mc.base_url = args.ollama_url
    mc.request_timeout = int(os.environ.get("AI_REQUEST_TIMEOUT", "30"))
    st.session_state.ai_config = mc

    # PDF conversions for selected studies (fast/optional but included for completeness)
    def _pdf_batch():
        for s in studies:
            _convert_pdf_to_txt_for(s)
    timings.append(_timeit("pdf_to_txt(selected)", _pdf_batch))

    # Embedding codebook once
    timings.append(_timeit("embed_codebook", embed_codebook))

    # Embedding selected studies
    def _embed_selected():
        for s in studies:
            embed_study(s)
    timings.append(_timeit("embed_studies(selected)", _embed_selected))

    # Recommendations for selected studies
    def _reco_selected():
        for s in studies:
            generate_recommendations(s)
    timings.append(_timeit("recommendations(selected)", _reco_selected))

    # PID/Date recommendations for selected studies
    def _pid_date_selected():
        for s in studies:
            generate_PID_date_recommendations(s)
    timings.append(_timeit("pid_date_reco(selected)", _pid_date_selected))

    # Restore original function
    gr_mod.get_embedding = original_gr_get_embedding  # type: ignore

    # Report
    total = sum(t for _, t in timings)
    print("\nBenchmark Results")
    print("=================")
    print(f"Studies: {studies}")
    for label, secs in timings:
        print(f"- {label}: {secs:.3f}s")
    print(f"- TOTAL: {total:.3f}s")

    print("\nEmbedding Call Counts")
    print("---------------------")
    for k, v in call_count.items():
        print(f"- {k}: {v}")

    # JSON summary for automated parsing (optional)
    summary = {
        "studies": studies,
        "timings": {label: secs for label, secs in timings},
        "total_seconds": total,
        "call_counts": call_count,
    }
    print("\nJSON Summary\n------------")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
