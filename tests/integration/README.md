# Integration Test Guide

This guide explains how to run the integration tests, interpret outputs, and compare environments (Local, Docker, Online). All artifacts are written to `tests/integration/results/`.

## 1) Prerequisites
- Python 3.10+
- pip + pytest (`pip install -r requirements.txt` then `pip install pytest`)
- Ollama installed and running (https://ollama.com/). Verify models:
  - `ollama list`
- Data present:
  - `input/target_variables.csv`
  - `input/<Study>/dataset_variables_auto_completed.csv`
  - `input/<Study>/ground_truth_mappings.csv`
- Optional scaffolding (creates sample data + ground truth):
  - `python scripts/scaffold_ground_truth.py --study Trial`

## 2) Environment variables
Set before running tests.

- Required/common:
  - `RUN_LABEL` = Local | Docker | Online (appears in reports)
  - `OLLAMA_BASE_URL` =
    - Local: `http://localhost:11434`
    - Docker (container to host): `http://host.docker.internal:11434`
- Optional toggles:
  - `RUN_LARGE=1` enables large dataset sizes in embeddings throughput.
  - `LENGTH_TIER=short|medium|long` controls synthetic text length.
  - `MAX_MINUTES=<float>` timebox for long embeddings runs (e.g., `5`).
  - `CHAT_MODELS="modelA,modelB"` restricts chat sweep; unset to auto-discover all chat-capable models.
  - `TEST_STUDY=<Study>` select a single study (otherwise the tests auto-pick one directory under `input/`).
  - `OLLAMA_EMBEDDING_MODEL=<model_tag>` to try a different embedding model for accuracy (default `nomic-embed-text:latest`).

Examples
- Git Bash:
```
export RUN_LABEL=Local
export OLLAMA_BASE_URL=http://host.docker.internal:11434
# optional
export RUN_LARGE=1
export LENGTH_TIER=long
export MAX_MINUTES=5
```
- PowerShell:
```
$env:RUN_LABEL="Local"
$env:OLLAMA_BASE_URL="http://host.docker.internal:11434"
# optional
$env:RUN_LARGE="1"
$env:LENGTH_TIER="long"
$env:MAX_MINUTES="5"
```

## 3) Test suite
All commands are run from `tests/integration/`.

- Connectivity
```
pytest -q test_connectivity.py
```
- Embeddings throughput (scales by dataset size and text length)
```
pytest -q test_embeddings_throughput.py
```
- Chat latency (auto-detects chat-capable models via Ollama; excludes embedding-only)
```
# Prefer auto-discovery; or set CHAT_MODELS to restrict
pytest -q test_chat_latency.py
```
- Accuracy vs. ground truth (Top‑1/3/5, MRR@5, nDCG@5)
```
pytest -q test_accuracy_mapping.py
```
- Dashboard aggregation (builds a single Markdown report)
```
pytest -q test_dashboard.py
```

## 4) What gets produced
Artifacts are saved to `tests/integration/results/` with timestamped names:
- `connectivity_*.{md,json}` — endpoint checks and timings.
- `embeddings_throughput_*.{md,json}` — size/tier performance; token estimate; timebox info.
- `chat_latency_*.{md,json}` — per-model latency and success; token counts when available.
- `accuracy_<study>_*.{md,json}` — Top‑K and ranking quality vs. ground truth.
- `dashboard_*.md` — consolidated view with a Snapshot (fastest chat, best embeddings, latest accuracy, token totals).

## 5) Reading the dashboard
Open the latest `dashboard_*.md` and review:
- Connectivity summary
- Embeddings throughput and best-by-size
- Chat Latency (all models) + Best Chat Model
- Accuracy (latest study)
- Token Summary (embeddings estimate; chat in/out)
- Guidance with a Snapshot of key results

## 6) Stress testing
- Increase dataset size (`RUN_LARGE=1`) and text length (`LENGTH_TIER=long`).
- Use `MAX_MINUTES` to cap long runs safely.
- Re-run `test_embeddings_throughput.py` and then `test_dashboard.py`.
- To see accuracy change with embedding model, set `OLLAMA_EMBEDDING_MODEL=<tag>` and re-run `test_accuracy_mapping.py` (this re-embeds and recomputes recommendations).

## 7) Model discovery (chat)
`test_chat_latency.py` discovers all local models via Ollama and auto-filters to chat-capable ones using `/api/show` capabilities (must include `"completion"`). Embedding-only models (e.g., `nomic-embed-text`) are excluded. Set `CHAT_MODELS` to a comma list to test a specific subset.

## 8) Troubleshooting
- Unknown pytest mark warning: add a `pytest.ini` with:
```
[pytest]
markers =
    local_ollama: marks tests that require local/remote Ollama
```
- Empty chat content / success False: ensure `OLLAMA_BASE_URL` is correct; try whitelisting a known model via `CHAT_MODELS`. The test falls back to `generate()` if `chat()` doesn’t reply with the exact token.
- Accuracy = 0: check `ground_truth_mappings.csv` `target_description` values exactly match the codebook descriptions in `input/target_variables.csv`.

## 9) Typical local workflow
```
# Label this run
export RUN_LABEL=Local
export OLLAMA_BASE_URL=http://host.docker.internal:11434

pytest -q test_connectivity.py
pytest -q test_embeddings_throughput.py
pytest -q test_chat_latency.py
pytest -q test_accuracy_mapping.py
pytest -q test_dashboard.py
```

## 10) Docker and Online
- Docker: run tests inside the container with `RUN_LABEL=Docker` and `OLLAMA_BASE_URL=http://host.docker.internal:11434`.
- Online: set `RUN_LABEL=Online` and point `OLLAMA_BASE_URL` to the remote service. Compare dashboards across runs by label.
