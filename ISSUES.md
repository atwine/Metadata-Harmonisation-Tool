# Known Issues & Pending Fixes

## [OPEN] AfPO gap rows not rendering fully in the UI

**Date logged:** 2026-05-28  
**Component:** `app/components/map_study.py` → `render_afpo_section()`  
**Severity:** Medium — feature partially works but gaps are not visible to the user

### Observed behaviour

After clicking "Look up in AfPO", the matched values table renders correctly. However, the unmatched (gap) rows — which should appear individually below a "Not found in AfPO" header — are either not rendering at all or only the first gap is shown (e.g. only `Bafumbira` visible even when 21+ gaps are expected).

### Expected behaviour

Every value that returns `None` from the AfPO lookup should render as a separate row containing:
- A warning label (`<value> — not found in AfPO`)
- An editable text field pre-filled with the raw value
- A "📋 Submit to AfPO" link button

### Suspected cause

Likely a **Streamlit rendering/widget-key conflict**. Each gap row creates a `st.text_input` and `st.link_button` inside a loop. If widget keys are not unique across Streamlit reruns, only the first widget in the loop may render; the rest are silently dropped or collapsed.

Candidate lines to inspect:
- The `for i, gap in enumerate(gaps):` loop in `render_afpo_section()`
- Widget key generation: `key=f"afpo_gap_{i}"` — confirm `i` is truly unique per rerun (session state index vs loop index mismatch possible)
- Whether `st.columns()` inside a loop causes layout collapse for large gap counts

### Steps to reproduce

1. Load either `AfPO_Uganda_Clinical` or `AfPO_Uganda_PopSurvey` test study.
2. Map the `tribe` / `ethnic_group` column to the `ethnicity` codebook variable.
3. In the AfPO sub-section, click "Look up in AfPO".
4. Observe: matched table shows correctly; gap section shows only 1 row (Bafumbira) instead of 21+.

### Related fix already applied

- `[:20]` cap on unique values pre-fill was removed (2026-05-28) — confirmed data now passes all 33/35 values to the lookup. The rendering issue is a separate, downstream problem.

### Next steps

- [ ] Add `st.write(len(gaps))` debug line temporarily to confirm gap list is being built correctly before the render loop
- [ ] Audit widget keys in the gap rendering loop for uniqueness
- [ ] Test with a small hard-coded gap list (2–3 items) to isolate whether the loop itself or the data pipeline is at fault
- [ ] Check if wrapping gap rows in `st.container()` resolves the collapse
