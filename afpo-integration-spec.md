# AfPO Integration Spec — Metadata Harmonisation Tool
*For implementation in Windsurf / Devin*
*Prepared: May 2026*

---

## 0. Overview for Devin

You are adding a new feature to the **Metadata Harmonisation Tool** — a Streamlit application that maps incoming study variables to a target codebook using AI-powered recommendations.

The new feature allows the tool to also map **ethnicity/population values** found inside datasets to the **African Population Ontology (AfPO)** — a standardised vocabulary of African ethnic and population groups. When a value cannot be matched, the tool captures it as a gap and gives the user a one-click way to submit it to the AfPO team via GitHub.

You are working in **one repo only**: the Metadata Harmonisation Tool. Do not modify the AfPO repository.

---

## 1. Repositories

| Repo | Purpose | Your access |
|------|---------|-------------|
| `Metadata-Harmonisation-Tool` | The tool you are modifying | Read + Write |
| `h3abionet/afpo` | AfPO ontology — for context only | Read only |

---

## 2. Background — What AfPO Is

AfPO is a structured vocabulary (ontology) of African population groups. Each term has:
- A unique ID (e.g. `AfPO:0000403`)
- A canonical name (e.g. `Ganda`)
- Synonyms (e.g. `Baganda`, `Muganda`)
- Language codes, country links, genetic data

The ontology is distributed as an `.obo` file. You will parse `data/ontologies/afpo-base.obo` directly — no external API needed.

**Source file to add to the repo:**
Download from `http://purl.obolibrary.org/obo/afpo.obo` and save as:
```
data/ontologies/afpo-base.obo
```

---

## 3. Existing Tool Architecture — What You Need to Know

The tool is a multi-page Streamlit app with this workflow:

```
Page 1: Upload Codebook      → input/target_variables.csv
Page 2: Upload Studies       → input/{study}/dataset_variables.csv
                               input/{study}/example_data.csv  (optional)
Page 3: Initialise           → AI generates embeddings + recommendations
Page 4: Map Studies          → Human reviews AI recommendations, approves mappings
Page 5: Download Results     → results/{study}.csv exported
```

**Key files to read before touching anything:**
- `app/components/map_study.py` — the main mapping UI and logic
- `app/components/get_recommendations.py` — embedding + cosine similarity engine
- `app/components/upload_codebook.py` — how the codebook is ingested
- `app/pages/4_Map_Studies.py` — the Map Studies page
- `input/target_variables.csv` — the current codebook (note: no ethnicity field yet)

**The pattern you must follow:**
The tool uses an "AI suggests, human confirms" pattern throughout. Your AfPO feature must follow the same pattern — never auto-save without user confirmation.

---

## 4. What to Build — The Three Parts

### Part 1 — AfPO Lookup Engine
**File to create:** `app/components/afpo_lookup.py`

A module that parses `afpo-base.obo` and provides a lookup function.

**Requirements:**
- Parse the `.obo` file once at startup and cache the result in memory
- Build a flat lookup structure: every name and synonym maps to its AfPO term
- Lookup strategy (in order):
  1. Exact match (case-insensitive)
  2. Fuzzy match using `rapidfuzz` (threshold: 85 score minimum)
  3. If no match → return `None` (gap)
- Return object when matched:
  ```python
  {
    "afpo_id": "AfPO:0000403",
    "canonical_name": "Ganda",
    "matched_via": "synonym",   # "exact", "synonym", or "fuzzy"
    "matched_term": "Baganda",  # the actual string that matched
    "confidence": 100           # 100 for exact/synonym, fuzzy score for fuzzy
  }
  ```
- Return when not matched:
  ```python
  None
  ```

**Key `.obo` parsing notes:**
- Each term block starts with `[Term]`
- `id:` line gives the AfPO ID
- `name:` line gives the canonical name
- Lines with `property_value: AfPO:0000450` are **exact synonyms** (most common)
- Lines with `synonym:` are also synonyms
- Strip all whitespace and quotes carefully

**Add `rapidfuzz` to `requirements.txt`.**

---

### Part 2 — Ethnicity Column Detection and AfPO Value Mapping UI

**File to modify:** `app/components/map_study.py`

**Trigger condition:**
When the user selects a codebook variable (in the `st.selectbox` for `mapped_variable`) and the selected variable's name contains any of these keywords (case-insensitive):
```python
ETHNICITY_KEYWORDS = ["ethnicity", "ethnic", "population", "tribe", "ancestry", "race"]
```

When triggered, render an **AfPO sub-section** below the standard mapping form, before the Submit button.

**The AfPO sub-section UI must:**

1. **Show a text area** labelled:
   *"Enter ethnicity/population values found in this column (one per line):"*
   - Pre-populate with unique values from `example_data.csv` for this column if available
   - If no example data, leave empty for manual entry

2. **Show a "Look up in AfPO" button**
   - On click: run each entered value through `afpo_lookup.lookup(value)`
   - Display results in a table with columns:
     `Input Value | AfPO ID | Canonical Name | Matched Via | Confidence`
   - Unmatched values show: `"— Not found in AfPO —"` in AfPO ID column, highlighted in orange

3. **For each matched value**, allow the user to confirm or override:
   - Confirmed matches are stored
   - User can type a manual AfPO ID override if they know the correct one

4. **For unmatched values** (gaps):
   - Show a GitHub button (see Part 3) next to each unmatched row
   - Also log it automatically to `logs/afpo_gaps.csv`

**Gap log format (`logs/afpo_gaps.csv`):**
```
timestamp, study, variable_name, unmatched_value, submitted_to_github
```
- `submitted_to_github` starts as `False`, flipped to `True` when the GitHub button is clicked

**AfPO mapping results are saved alongside the standard mapping** when the user clicks Submit. Add these columns to the results CSV:
```
afpo_values_mapped    # JSON string: {"Baganda": "AfPO:0000403", "Acholi": "AfPO:0000374"}
afpo_values_gaps      # JSON string: ["Banyoro", "Batooro"]
```

---

### Part 3 — GitHub Gap Submission

**File to create:** `app/components/afpo_gap_reporter.py`

A utility that generates a pre-filled GitHub Issue URL for an unmatched AfPO value.

**GitHub Issue target:**
```
https://github.com/h3abionet/afpo/issues/new
```

**Pre-filled fields:**
- `title`: `New term request: {unmatched_value}`
- `labels`: `new term`
- `body`: Use this template exactly:

```
## New AfPO Term Request

**Population/ethnicity value not found in AfPO:**
{unmatched_value}

**Encountered in study:**
{study_name}

**Mapped variable:**
{variable_name}

**Suggested parent group (if known):**
(please fill in if you know — e.g. Bantu Eastern, Nilotic Eastern)

**References (if known):**
(Wikipedia link, ISO 639 code, etc.)

---
*This request was generated by the Metadata Harmonisation Tool.*
*AfPO contributing guide: https://github.com/h3abionet/afpo/blob/main/CONTRIBUTING.md*
```

**Render as:**
```python
st.link_button(
    "📋 Submit to AfPO on GitHub",
    url=generated_url,
    help="Opens a pre-filled GitHub Issue for the AfPO team to review this term"
)
```

When the user clicks this button, also update `logs/afpo_gaps.csv` to set `submitted_to_github = True` for that row.

---

## 5. Codebook Change Required

**File to modify:** `input/target_variables.csv`

Add one new row for the ethnicity/population target variable:

```csv
ethnicity,Population group or ethnic identity of the participant,string,AfPO URI,,AfPO:0000403
```

This gives the recommendation engine something to match against when a study has an ethnicity column, and it's what triggers the AfPO sub-section in the mapping UI.

---

## 6. New Dependency

Add to `requirements.txt`:
```
rapidfuzz
```

---

## 7. File Structure After Implementation

```
Metadata-Harmonisation-Tool/
├── data/
│   └── ontologies/
│       └── afpo-base.obo              ← NEW: AfPO ontology file
├── app/
│   └── components/
│       ├── afpo_lookup.py             ← NEW: lookup engine
│       ├── afpo_gap_reporter.py       ← NEW: GitHub issue URL builder
│       └── map_study.py              ← MODIFIED: AfPO sub-section added
├── logs/
│   ├── mapping_audit.jsonl            ← existing
│   └── afpo_gaps.csv                  ← NEW: gap capture log
└── input/
    └── target_variables.csv           ← MODIFIED: ethnicity row added
```

---

## 8. Acceptance Criteria

These must all be true before the feature is considered done:

- [ ] `afpo_lookup.py` correctly parses `afpo-base.obo` and finds `Ganda`, `Baganda`, and `Muganda` — all returning `AfPO:0000403`
- [ ] A fuzzy input like `"baganda people"` returns a match with confidence ≥ 85
- [ ] A value like `"Banyoro"` (not currently in AfPO) returns `None`
- [ ] The AfPO sub-section only appears when the mapped codebook variable contains an ethnicity keyword
- [ ] If `example_data.csv` exists and the ethnicity column is present, its unique values pre-populate the text area
- [ ] Unmatched values are logged to `logs/afpo_gaps.csv` automatically on lookup
- [ ] The GitHub button opens a pre-filled issue URL (verify the URL is correctly encoded)
- [ ] AfPO mapping results are saved in the results CSV alongside the standard mapping
- [ ] The standard mapping flow is completely unaffected when the ethnicity sub-section is not triggered
- [ ] `rapidfuzz` is the only new dependency added

---

## 9. What NOT to Do

- Do not modify the AfPO repository
- Do not use vector embeddings for the AfPO lookup — use rule-based + rapidfuzz only
- Do not auto-submit anything to GitHub — the user must click the button
- Do not block the standard mapping Submit if the AfPO section is incomplete — it is optional
- Do not add any new Streamlit pages — this is a sub-section within the existing Map Studies page
- Do not hardcode API keys or tokens anywhere

---

## 10. Testing the Feature Manually

Use the ACE Uganda example data already in the repo (`example_data/ACE_Uganda/`). The dataset has a `village` column — this won't trigger AfPO. To test:

1. Add a column called `ethnicity` to `example_data/ACE_Uganda/example_data.csv` with values: `Ganda, Baganda, Acholi, Banyoro`
2. Add `ethnicity` to `dataset_variables.csv` with description `Ethnic group of participant`
3. Run the full tool flow
4. On Map Studies, select the `ethnicity` variable
5. Verify the AfPO sub-section appears
6. Click "Look up in AfPO" — Ganda, Baganda, Acholi should match; Banyoro should not
7. Click the GitHub button for Banyoro — verify the URL is correct
8. Submit the mapping — verify `afpo_values_mapped` and `afpo_values_gaps` appear in results CSV