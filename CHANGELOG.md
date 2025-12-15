# Changelog
All notable changes to this project will be documented in this file.

Format: Keep a Changelog. Versioning: Semantic Versioning.

## [0.4.1] - 2025-12-12
### Fixed
- Removed remaining unsafe runtime `eval()` usage in Map Studies sorting logic.
  - Replaced with safe parsing via `ast.literal_eval()` with graceful fallback.
  - File: `app/components/map_study.py`

- Map Studies page: study selector visibility and study switching regression.
  - Moved study selector above the AI configuration panel to avoid it being pushed out of view.
  - Simplified `st.selectbox` session state handling to prevent selection being overridden on reruns.
  - File: `app/pages/4_Map_Studies.py`

- Download Results page: show all initialized studies (from `input/`) and prevent render failures.
  - List studies from `input/` even when no `results/<study>.csv` exists yet.
  - Added option to create an empty results CSV when missing.
  - Fixed indentation errors that prevented the Download Results page from rendering.
  - File: `app/components/download.py`

### Added
- Session-scoped embedding cache to reduce repeat embedding calls.
  - Cache key: provider + embedding model + sha256(text) (stored in `st.session_state`).
  - File: `app/components/ai_provider.py`

- Append-only audit trail for mapping writes.
  - Logs previous vs new mapping values to `logs/mapping_audit.jsonl` on each Submit.
  - Captures operator name and active AI provider info for traceability.
  - Added Download page button to export the audit log.
  - Files: `app/components/map_study.py`, `app/components/download.py`

- Map Studies UI safeguards:
  - Hide target codebook variables already used in any non-`To do` mapping status to reduce accidental duplicate mappings.
  - Added inline “How Relational Mode works (example)” help expander when Relational Mode is enabled.
  - File: `app/components/map_study.py`

### Removed
- Removed “Auto Generate Transformation Instructions” from Map Studies (manual transformations only).
  - File: `app/components/map_study.py`


### Tests
- Added regression tests for safe parsing/sorting of `target_distances`.
  - File: `tests/test_map_study_safe_sort.py`

## [0.4.0] - 2025-10-16
### Fixed
- Map Studies page showing empty/“not initialized” due to path inconsistencies between tests and app runtime.
  - Unified input/results path resolution to prefer local app CWD when present, else repo root.
  - Files touched: `app/components/get_recommendations.py`, `app/components/upload_codebook.py`, `app/components/initialise_mapping_app.py`.
  - Scope: strictly paths; no functional or layout changes otherwise.

### Added
- Sample image under “Codebook CSV format (required columns)” on Upload Codebook page.
  - File: `app/components/upload_codebook.py`
  - Source image: `assets/images/sample_data.png` (usage guarded by existence check).

- Initialisation Prompt guidance on Initialise page:
  - Impact note explaining effects and when to re-run.
  - “Reset to default” button.
  - “Prompt tips” expander.
  - File: `app/components/initialise_mapping_app.py`

- Verification scripts for quick health checks:
  - `scripts/verify_unix.sh` (Docker daemon, Ollama reachability, app health endpoint)
  - `scripts/verify_windows.ps1` (PowerShell equivalent with parameters `-AppName`, `-OllamaBaseUrl`)

### Documentation
- `docker/README.md` updates:
  - Windows quick start (PowerShell/CMD) build/run examples.
  - "Run the image directly (host Ollama)" instructions with volume mounts.
  - Windows-specific notes (Docker Hub login per shell, Git Bash path quirks).
  - Verification sections and manual checks for Docker/Ollama/app health.

### Notes
- Dockerfile/Compose required no changes; existing configs remain valid.
- Path behavior: prefers `app/input` and `app/results` when running the app; falls back to repo-root `input` and `results` to support tests/CI.

## [Unreleased]
- Docker/Compose reliability fixes and Ollama bootstrap:
  - Added repo-root `.dockerignore` so build context exclusions apply correctly (avoid baking in `venv/` and `.env`), while keeping runtime-required `about.md`.
  - Dockerfile: create `/app/results` (instead of `/app/output`) to match runtime paths.
  - Compose: mount `results/` for persistence (instead of `output/`) and keep `input/` writable in production because uploads create new studies.
  - Compose: removed dev code bind-mounts from base config (kept in `docker-compose.dev.yml`) to avoid leaking into production merges.
  - Compose: publish Ollama on host port `11435` by default (configurable via `OLLAMA_PUBLISHED_PORT`) to avoid conflicts with a host Ollama using `11434`.
  - Ollama: enabled by default; added one-shot `ollama-init` to pre-pull `llama3.1:8b` and `nomic-embed-text` on first run; fixed Ollama healthcheck to use `ollama ls`.
- Documentation updates (Ollama modes + troubleshooting):
  - Make Docker Compose the recommended/primary run method; move direct `docker run` to an alternative path.
  - Document both Ollama options (Ollama in Compose vs host Ollama) and the correct base URLs for each.
  - Add troubleshooting steps for failed Connection Test when Ollama is reachable but models are missing, including manual model pull commands.
- Optional: preview/dry-run for the initialisation prompt (no file writes).
- Optional: overwrite-policy toggle for existing descriptions (default off).
