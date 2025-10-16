# Changelog
All notable changes to this project will be documented in this file.

Format: Keep a Changelog. Versioning: Semantic Versioning.

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
- Optional: preview/dry-run for the initialisation prompt (no file writes).
- Optional: overwrite-policy toggle for existing descriptions (default off).
