# Metadata Harmonisation Tool - Remaining Recommendations Implementation Plan
*Last Updated: December 12, 2025*

This plan is a **revision** of the previous draft. It focuses only on the recommendations that are **not yet implemented** (or are only partially implemented), based on the current codebase.

## What is already done (do not re-implement)
- **AI call timeouts + retries** exist in `AIProviderWrapper` (`_with_timeout`, `_retry_with_backoff`) and are used for chat + embeddings. [src: `app/components/ai_provider.py`]
- **Safe transformation evaluation** exists via `SafeEvaluator` and `ast.literal_eval` for categorical mappings. [src: `app/components/transformation_utils.py`]
- **Upload/study validation UI** exists via `render_validation_widget()`. [src: `app/components/validation.py`]
- **Basic AI usage monitoring** exists (session-scoped counters + rough token estimates). [src: `app/components/monitor.py`]

## Objective 1 — Eliminate remaining unsafe `eval()` usage (security + robustness)
**Why:** The recommendations originally focused on `eval()` in transformations, but the repo still contains a runtime `eval()` when parsing distance arrays during mapping. [src: `app/components/map_study.py`]

- [x] **1.1 Identify and replace all remaining `eval()`**
  - [x] Locate every `eval(` usage in the repo (expect at least one in `map_study.py`).
  - [x] Replace `eval(x)` with `ast.literal_eval(x)` or a shared helper (e.g., `safe_literal_eval`).
  - [x] Ensure failures are handled gracefully (empty list or a clear warning) rather than crashing the page.

- [x] **1.2 Add regression tests for the replacement**
  - [x] Add tests that cover:
    - [x] Valid list string (e.g., `"[0.1, 0.2]"`).
    - [x] Malformed string.
    - [x] Non-string/NaN.
  - [x] Confirm mapping page still sorts variables correctly when parsing succeeds.

- [x] **Acceptance criteria**
  - [x] No remaining runtime uses of `eval()` in `app/` (a raw text search may still match documentation strings mentioning `eval()`).
  - [x] Mapping still works with existing `dataset_variables_with_PID_date_recommendations.csv` files.

## Objective 2 — Cost/usage management improvements (complete the “cost management” recommendation)
**Current state:** `AIMonitor` tracks counts and rough tokens via chars/4, but not **per-provider** breakdown and not any **cost awareness**. [src: `app/components/monitor.py`]

- [ ] **2.3 Add caching for repeat embeddings (minimal + safe)**
  - [ ] Add a session-scoped cache keyed by `(provider, embedding_model, text_hash)`.
  - [ ] Use the cache in embedding-heavy paths (e.g., recommendation generation) to avoid repeated calls.

## Objective 3 — Add an audit trail for “mapping writes” (who/what changed)
**Why:** The analysis flags “No audit trail” as a critical issue. [src: `systemUpdateRecommendations.md`]

Given this is a Streamlit single-user app today, implement the **minimal** useful audit trail first:

- [ ] **3.1 Define the audit record format**
  - [ ] Fields: timestamp, study, study_var, codebook_var, marked, notes, transformation_type, transformation_instructions (or hash), provider info.
  - [ ] Storage: append-only JSONL or CSV under `logs/`.

- [ ] **3.2 Implement audit logging for mapping updates**
  - [ ] Hook into `write_to_results()` so every save appends an audit entry. [src: `app/components/map_study.py`]
  - [ ] Capture both “new value” and “previous value” (read prior row before overwrite).

- [ ] **3.3 Add a simple UI viewer/export**
  - [ ] “Download audit log” button on the Download page.
  - [ ] Optional: a small expander on Map Studies to show last N audit events.

- [ ] **Acceptance criteria**
  - [ ] Every “Mapping saved successfully.” event results in an appended audit entry. [src: `app/components/map_study.py`]
  - [ ] Audit log survives Streamlit reruns.

## Objective 4 — CI test automation (recommended maintenance)
**Current state:** There is a real `tests/` suite, but no GitHub Actions workflow directory present. [src: `.github/`]

- [ ] **4.1 Add GitHub Actions workflow to run tests**
  - [ ] Create `.github/workflows/python-tests.yml`.
  - [ ] Steps:
    - [ ] Checkout.
    - [ ] Setup Python.
    - [ ] Install dependencies.
    - [ ] Run `pytest`.

- [ ] **4.2 Add a minimal “packaging smoke” job**
  - [ ] Run the existing packaging smoke test(s) already present in `tests/`.

- [ ] **Acceptance criteria**
  - [ ] PRs/commits show a green check when tests pass.

## Objective 5 — Documentation alignment (reduce confusion)
**Current state:** README still states “Ollama for all AI functionality”, but the app includes multi-provider configuration UI. [src: `README.md`]

- [ ] **5.1 Update README to reflect multi-provider support**
  - [ ] Document how to use:
    - [ ] Ollama
    - [ ] OpenAI
    - [ ] Anthropic (chat-only)
    - [ ] Azure OpenAI
  - [ ] Add a short “How to set timeouts” note (AI Configuration panel).

- [ ] **5.2 Add “Security notes” section**
  - [ ] Explain that transformations use a restricted evaluator and dict parsing uses `ast.literal_eval`.

- [ ] **Acceptance criteria**
  - [ ] README no longer claims Ollama is the only provider.

## Optional / Deferred (only if you explicitly want these)
These were mentioned in the original analysis, but they are **larger product/architecture changes** and should be treated as separate projects:

- [ ] **D1 — Replace file-based storage with a database-backed store** (DuckDB/SQLite)
- [ ] **D2 — Multi-user accounts and collaboration** (authn/authz)
- [ ] **D3 — External alerting (Slack/email) + ops-grade monitoring**
