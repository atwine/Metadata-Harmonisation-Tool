# Test Plan — Metadata Harmonisation Tool

Generated: 2025-10-06 (local time)

## Simple Test Guide (Three Tracks)

This guide explains, in plain language, how we check that the software works well in three places and how to read the results. The detailed, technical reference is below.

### Track A — Benchmark (Your Laptop)
- **[What you need]** Your laptop and the project folder open.
- **[What we do]** We run the same set of checks locally:
  - Can we connect to the model service?
  - How fast do we create meanings from text (embeddings) at different sizes?
  - How quickly do different models answer a tiny prompt?
  - How accurate are the automatic matches from your study to the target codebook, using your ground truth file?
- **[What you see]** A set of easy-to-read reports created in the `tests/integration/results/` folder. A combined "dashboard" compares runs and highlights the best choices.

### Track B — Docker (In a Container)
- **[What you need]** The app running in Docker on your machine.
- **[What we do]** We run the exact same checks from inside the container, pointing to the same model service.
- **[Why this matters]** Confirms the app works the same way when packaged for deployment.
- **[What you see]** The same reports in the container's project folder (mounted to your machine) so you can compare results with your laptop runs.

### Track C — Online (VPN/Remote)
- **[What you need]** Access to the remote model service over your network/VPN.
- **[What we do]** We repeat the same checks against the remote service.
- **[Why this matters]** Confirms performance and accuracy over the network and helps choose the best setup for your team.
- **[What you see]** The same reports, plus the dashboard that compares Local vs Docker vs Online.

### What the checks cover (in simple terms)
- **[Connection check]** Can we reach the service and see the available models?
- **[Speed of meanings]** How many items per second can we process? We test different batch sizes and short/medium/long text lengths.
- **[Speed of answers]** How quickly different models respond to a tiny, fixed prompt.
- **[Match accuracy]** Using your "truth" file (e.g., `input/Trial/ground_truth_mappings.csv`), we measure how often the tool picks the right target from the codebook (Top‑1/Top‑3/Top‑5 and ranking quality).

## Technical Reference

## 1. Purpose
- Establish a replicable, robust methodology to evaluate the app locally, over VPN (remote Ollama), and in Docker.
- Produce consistent, timestamped Markdown reports to compare models and configurations, guiding users on best choices.

## 2. Test Scopes
- Local (developer machine, no Docker): OLLAMA at `http://localhost:11434`.
- VPN/Remote: OLLAMA at `https://<remote-host>/ollama` (TLS required).
- Docker: App inside container; OLLAMA via `http://host.docker.internal:11434` or remote URL.

## 3. Prerequisites
- Python 3.10+ with venv.
- pytest installed: `pip install pytest`.
- Ollama installed and running (local tests), with required models.
- Data folder structure for workflow tests:
  - `input/target_variables.csv`
  - `input/<StudyName>/dataset_variables_auto_completed.csv`

## 4. Environment Configuration
- Common variables (set in shell or `.env`):
```
AI_PROVIDER=ollama
AI_REQUEST_TIMEOUT=45
```
- Local (no Docker):
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text:latest
```
- VPN/Remote (HTTPS):
```
OLLAMA_BASE_URL=https://<remote-host>/ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text:latest
```
  - Windows local venv: `pip install python-certifi-win32` (Requests trusts Windows store).
  - (Optional) Diagnostics: temporary `--insecure` in scripts only (do not use in app).
- Docker:
  - Use `http://host.docker.internal:11434` for local Ollama or set remote HTTPS URL.
  - For HTTPS with enterprise CA: mount PEM and set `REQUESTS_CA_BUNDLE=/app/certs/<ca>.pem`.

## 5. Models Under Test
- Embeddings (fixed): `nomic-embed-text:latest`.
- Chat (sweep): discover all non-embedding models via `/api/tags` or use a whitelist:
  - Example: `llama3.1:8b`, `mistral:latest`, `qwen3:8b`, `gemma3:4b`.

## 6. Test Suites and Commands
Run from repo root unless noted.

- Connectivity & Models
```
pytest -q tests/integration/test_connectivity.py
```
Output: `tests/integration/results/connectivity_*.md/json`

- Embeddings Throughput (2D scaling)
```
# Default small/medium sizes
pytest -q tests/integration/test_embeddings_throughput.py

# Optional large sizes (set env flag to enable heavy runs)
# Powershell example:
#   $env:RUN_LARGE="1"; $env:LENGTH_TIER="long"; pytest -q tests/integration/test_embeddings_throughput.py
# LENGTH_TIER in {short, medium, long}; defaults to "medium" if unset.
```
Output: `tests/integration/results/embeddings_throughput_*.md/json`
 
2D scaling matrix:
- **[dataset_size]**: 100, 1,000, 5,000, 10,000, 15,000 (5k/10k/15k gated by `RUN_LARGE=1`).
- **[text_length_tier]**: short (~10 tokens), medium (~50 tokens), long (~200 tokens). Controlled via `LENGTH_TIER`.

- Chat Latency — Model Sweep (deterministic)
```
pytest -q tests/integration/test_chat_latency.py
```
Options used: `temperature=0`, `num_predict=8`
Output: `tests/integration/results/chat_latency_*.md/json`

- PID/Date Workflow Micro-benchmark
```
pytest -q tests/integration/test_pid_date_workflow.py
```
Auto-picks first study folder under `input/` (e.g., `Trial/`).
Output: `tests/integration/results/pid_date_benchmark_<Study>_*.md`

- Dashboard Aggregation (combines all JSON artifacts)
```
pytest -q tests/integration/test_dashboard.py
```
Output: `tests/integration/results/dashboard_*.md`

## 7. Metrics Tracked
- Connectivity: client init and validation elapsed ms.
- Embeddings: items/sec, latency_avg_ms, latency_p95_ms, errors, timeout_s, text_length_tier.
- Chat: per-model elapsed_ms, success (contains "pong").
- Workflow: per-phase elapsed_ms and record counts.
- All reports timestamped; environment (OS, Python, base URL, models) included in Markdown.

### 7.1 Token Tracking
- Chat (`/api/chat`): record `prompt_eval_count` (input tokens) and `eval_count` (output tokens) from the final response. Set `stream=false` to ensure counts are present. [src: Ollama API docs — Chat response fields]
- Embeddings (`/api/embeddings`): token counts are not returned by the API response. Track:
  - `input_chars`: character length of the text.
  - `approx_input_tokens`: `ceil(input_chars / 4)` as a heuristic.
  - Optional: enable a tokenizer (e.g., sentencepiece or `tiktoken`) for more precise estimates if desired.

## 8. Decision Criteria
- Embeddings: prefer higher `items_per_sec` with low `latency_p95_ms` and `errors=0`.
- Chat: prefer lowest `elapsed_ms` with `success=True` (deterministic compliance).
- Workflow: identify dominant phase; improvements target the longest phase.

## 9. Reproducibility
- Deterministic chat parameters: `temperature=0`, `num_predict=8`.
- Two-dimensional scaling:
  - dataset_size: 100, 1,000 (always), optional 5,000 / 10,000 / 15,000 behind `RUN_LARGE=1`.
  - text_length_tier: short/medium/long via `LENGTH_TIER`.
- Results written to `tests/integration/results/` with timestamped filenames.

## 10.1 Accuracy Evaluation (Mapping to Target Codebook)
Goal: quantify how well embeddings-based recommendations map study variables to target codebook variables across Local / VPN / Docker.

### Ground Truth
- Provide `input/<StudyName>/ground_truth_mappings.csv` with columns:
  - `variable_name` (study variable)
  - `target_variable` (expected mapped codebook variable)

### Procedure
1. Ensure embeddings exist:
   - `embed_codebook()` → `input/target_variables_with_embeddings.csv`
   - `embed_study(<StudyName>)` → `input/<StudyName>/dataset_variables_with_embeddings.csv`
2. Generate recommendations:
   - `generate_recommendations(<StudyName>)` → `.../dataset_variables_with_recommendations.csv`
3. Evaluate accuracy:
   - For each `variable_name`, check if `target_variable` appears in the ranked `target_recommendations`.
   - Metrics:
     - Top-1 / Top-3 / Top-5 accuracy
     - MRR@K (Mean Reciprocal Rank), nDCG@K
     - Mean cosine distance of the correct target vs. others (optional)
   - Record counts of missing/invalid embeddings.

### Cross-Environment Runs
- Run the same evaluation under:
  - Local (`http://localhost:11434`)
  - VPN/Remote (`https://<remote-host>/ollama`)
  - Docker (local or remote base URL)
- Output per-environment Markdown + JSON summaries; aggregate into dashboard for side-by-side comparison.

### Token Awareness
- Log per-item `approx_input_tokens` for embeddings and chat token counts when chat is used.
- Report total tokens processed per run to inform cost/perf planning for remote deployments.

## 10. Troubleshooting
- Connection timeouts: verify `OLLAMA_BASE_URL`, server availability, VPN status.
- TLS errors (remote): ensure Windows venv has `python-certifi-win32`; for Docker, set `REQUESTS_CA_BUNDLE` to a valid PEM.
- Missing models: `ollama list` and `ollama pull <model>`.
- Study data missing: ensure required CSVs exist under `input/`.

## 11. Platform Notes
- Windows local: use `python-certifi-win32` for HTTPS trust.
- Docker: prefer `host.docker.internal` for local Ollama; mount CA bundle for HTTPS.
- Linux/macOS: no special steps beyond valid CA for HTTPS.

## 12. Interpreting the Dashboard
- Connectivity Summary: sanity check for endpoint and model listing.
- Embeddings Throughput: compare runs; "Best by dataset size" highlights fastest.
- Chat Latency: per-model comparisons; "Best Chat Model" shows top performer.
- Accuracy: compare Top-K, MRR, nDCG across environments; highlight where environment/model choices improve mapping quality.

## 13. Future Extensions
- Add very large datasets (e.g., 25,000–50,000) behind stronger gating.
- Capture memory usage (psutil) during large embeddings batches.
- Add per-model parameter sweeps (context length, top_p) for deeper tuning.
