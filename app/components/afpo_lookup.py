"""
AfPO Lookup Engine
Parses data/ontologies/afpo-base.obo once at module load and provides
exact + fuzzy population-name lookup against the African Population Ontology.
"""

import re
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# OBO file location — resolved relative to the project root (two levels up
# from this file: app/components/ → app/ → project root).
# ---------------------------------------------------------------------------
_OBO_PATH = os.path.join(
    Path(__file__).resolve().parent.parent.parent,
    "data", "ontologies", "afpo-base.obo"
)

# Property codes to extract synonyms from
_SYNONYM_PROPS = {"AfPO:0000450", "AfPO:0000458", "AfPO:0000453"}

# Property codes to skip entirely
_SKIP_PROPS = {"AfPO:0000089", "AfPO:0000565", "AfPO:0000233", "AfPO:0000267"}


def _parse_obo(path: str) -> dict:
    """Parse the OBO file and return a flat lookup_table keyed on
    normalised (lower-stripped) name / synonym strings, each mapping to a
    base term dict (without matched_via / matched_term / confidence — those
    are filled at lookup time).
    """
    lookup_table: dict = {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        # Return empty table gracefully if file is missing
        return lookup_table

    # Split on [Term] boundaries
    blocks = content.split("\n[Term]\n")

    for block in blocks[1:]:  # skip the file header before the first [Term]
        lines = block.splitlines()

        afpo_id = None
        canonical_name = None
        synonyms: list = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # --- id ---
            if line.startswith("id: AfPO:"):
                afpo_id = line[len("id: "):].strip()

            # --- canonical name ---
            elif line.startswith("name: "):
                canonical_name = line[len("name: "):].strip()

            # --- property_value lines ---
            elif line.startswith("property_value: AfPO:"):
                # Extract the property code (second token)
                parts = line.split(" ", 2)
                if len(parts) < 3:
                    continue
                prop_code = parts[1]

                # Skip disallowed property codes
                if prop_code in _SKIP_PROPS:
                    continue

                # Only extract from synonym property codes
                if prop_code not in _SYNONYM_PROPS:
                    continue

                # Skip lines containing URLs
                if "http" in line or "https" in line:
                    continue

                match = re.search(r'"([^"]+)"', line)
                if match:
                    val = match.group(1)
                    # Filter out invalid values
                    if "\n" in val:
                        continue
                    if len(val) > 60:
                        continue
                    synonyms.append(val)

            # --- synonym: lines (OBO standard) ---
            elif line.startswith("synonym: "):
                match = re.search(r'synonym: "([^"]+)"', line)
                if match:
                    val = match.group(1)
                    if "\n" in val:
                        continue
                    if len(val) > 60:
                        continue
                    synonyms.append(val)

        # Only add complete terms
        if not afpo_id or not canonical_name:
            continue

        # Base term dict — matched_via / matched_term / confidence filled at lookup time
        base = {
            "afpo_id": afpo_id,
            "canonical_name": canonical_name,
            "matched_via": "",
            "matched_term": "",
            "confidence": 0,
        }

        # Register the canonical name
        key = canonical_name.lower().strip()
        lookup_table[key] = base

        # Register every synonym
        for syn in synonyms:
            syn_key = syn.lower().strip()
            if syn_key and syn_key not in lookup_table:
                lookup_table[syn_key] = base

    return lookup_table


# Parse once at module import
lookup_table: dict = _parse_obo(_OBO_PATH)


def lookup(value: str):
    """Look up a population/ethnicity value against the AfPO ontology.

    Strategy:
        1. Exact match (case-insensitive, stripped)
        2. Fuzzy match via rapidfuzz (WRatio, score_cutoff=85)
        3. No match → return None

    Returns a dict copy with matched_via, matched_term, and confidence
    filled in, or None if no match is found.
    """
    normalised = value.lower().strip()

    # Step 1: exact match
    if normalised in lookup_table:
        result = lookup_table[normalised].copy()
        result["matched_via"] = "exact" if normalised == result["canonical_name"].lower() else "synonym"
        result["matched_term"] = value
        result["confidence"] = 100
        return result

    # Step 2: fuzzy match using rapidfuzz
    try:
        from rapidfuzz import process, fuzz
        best = process.extractOne(
            normalised,
            lookup_table.keys(),
            scorer=fuzz.WRatio,
            score_cutoff=85,
        )
        if best:
            matched_key, score, _ = best
            result = lookup_table[matched_key].copy()
            result["matched_via"] = "fuzzy"
            result["matched_term"] = value
            result["confidence"] = int(score)
            return result
    except ImportError:
        # rapidfuzz not installed — skip fuzzy step silently
        pass

    # Step 3: no match
    return None
