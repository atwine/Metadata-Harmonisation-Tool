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

- [x] **3.1 Define the audit record format**
  - [x] Fields: timestamp, study, study_var, codebook_var, marked, notes, transformation_type, transformation_instructions (or hash), provider info.
  - [x] Storage: append-only JSONL or CSV under `logs/`.

- [x] **3.2 Implement audit logging for mapping updates**
  - [x] Hook into `write_to_results()` so every save appends an audit entry. [src: `app/components/map_study.py`]
  - [x] Capture both “new value” and “previous value” (read prior row before overwrite).

- [x] **3.3 Add a simple UI viewer/export**
  - [x] “Download audit log” button on the Download page.
  - [x] Optional: a small expander on Map Studies to show last N audit events.

- [x] **Acceptance criteria**
  - [x] Every “Mapping saved successfully.” event results in an appended audit entry. [src: `app/components/map_study.py`]
  - [x] Audit log survives Streamlit reruns.


## Objective 5 — Documentation alignment (reduce confusion)
**Current state:** README still states “Ollama for all AI functionality”, but the app includes multi-provider configuration UI. [src: `README.md`]

- [x] **5.1 Update README to reflect multi-provider support**
  - [x] Document how to use:
    - [x] Ollama
    - [x] OpenAI
    - [x] Anthropic (chat-only)
    - [x] Azure OpenAI
  - [x] Add a short “How to set timeouts” note (AI Configuration panel).

- [x] **5.2 Add “Security notes” section**
  - [x] Explain that transformations use a restricted evaluator and dict parsing uses `ast.literal_eval`.

- [x] **Acceptance criteria**
  - [x] README no longer claims Ollama is the only provider.


