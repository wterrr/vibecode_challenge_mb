"""Deterministic, conservative normalization for concept identities and aliases."""

import hashlib
import re
import unicodedata


def normalize_concept_alias(text: str) -> str:
    """Normalize a concept string or alias deterministically and conservatively.

    Rules:
    - Unicode NFKC normalization
    - Strip leading and trailing whitespace
    - Collapse contiguous internal whitespace to a single space
    - Casefold for robust, diacritic-preserving case insensitivity

    Explicitly forbidden:
    - Fuzzy matching
    - Synonym guessing or semantic merging
    - Stripping Vietnamese diacritics (diacritics distinguish meanings)
    - Embeddings or LLM-based inferences
    """
    if not text:
        return ""
    # 1. Unicode NFKC
    normalized = unicodedata.normalize("NFKC", text)
    # 2. Trim whitespace
    normalized = normalized.strip()
    # 3. Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized)
    # 4. Casefold
    return normalized.casefold()


def normalize_canonical_key(raw_label: str) -> str:
    """Derive a canonical key from a raw label or key string.

    Format: concept:<slug_or_clean_text>
    Example: 'Loss Function' -> 'concept:loss_function'
    """
    norm = normalize_concept_alias(raw_label)
    if norm.startswith("concept:"):
        key_body = norm.removeprefix("concept:").strip()
    else:
        key_body = norm

    # Replace spaces and punctuation with underscores for key body
    clean_body = re.sub(r"[^\w\u00C0-\u1EF9]+", "_", key_body).strip("_")
    if not clean_body:
        clean_body = "unnamed"
    return f"concept:{clean_body}"


def deterministic_concept_id(canonical_key: str) -> str:
    """Derive a stable, process-independent concept_id from a canonical key.

    Uses SHA-256 to ensure identical identifiers across Python runs, machines,
    and restarts, avoiding Python's randomized hash() seed or UUIDs.
    """
    norm_key = normalize_concept_alias(canonical_key)
    digest = hashlib.sha256(norm_key.encode("utf-8")).hexdigest()[:10]

    # Clean prefix for human legibility in debug/logs
    clean_prefix = re.sub(r"[^a-z0-9]", "", norm_key.removeprefix("concept:"))[:10]
    if clean_prefix:
        return f"c_{clean_prefix}_{digest}"
    return f"c_{digest}"
