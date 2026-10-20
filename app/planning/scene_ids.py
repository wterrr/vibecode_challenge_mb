"""Safe local normalization of model-authored scene identifiers.

OpenAI-compatible strict Structured Outputs cannot carry Pydantic's regex
pattern constraints. Scene IDs are internal orchestration identifiers, not
creative teaching content. Canonicalize ONLY invalid/duplicate string IDs
before final Pydantic validation, keeping all other model data untouched.
No extra paid provider call is needed for this metadata repair.
"""
from __future__ import annotations

import json

from app.domain.lesson import SCENE_ID_REGEX


def canonicalize_scene_ids(raw_json: str) -> tuple[str, int]:
    """Return (normalized_json, renamed_count), or untouched input if unsafe.

    Invariants:
      * All scene entries must be dicts with string IDs; malformed structure
        still fails Pydantic and remains eligible for explicit paid repair.
      * Valid unique IDs remain unchanged, including model-selected slugs.
      * Only invalid/duplicate scene_id values are replaced; source/narration,
        visual contracts and other fields are not modified.
      * Canonical IDs depend only on their scene order, never untrusted text.
    """
    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError, ValueError):
        return raw_json, 0

    if not isinstance(data, dict) or not isinstance(data.get("scenes"), list):
        return raw_json, 0

    scenes = data["scenes"]
    if not 1 <= len(scenes) <= 99 or any(
        not isinstance(s, dict) or not isinstance(s.get("scene_id"), str)
        for s in scenes
    ):
        return raw_json, 0

    valid_ids = {
        s["scene_id"] for s in scenes if SCENE_ID_REGEX.fullmatch(s["scene_id"])
    }
    seen: set[str] = set()
    replaced = 0

    for index, scene in enumerate(scenes, start=1):
        original = scene["scene_id"]
        if SCENE_ID_REGEX.fullmatch(original) and original not in seen:
            seen.add(original)
            continue
        # Never derive an artifact filename or scene identity from arbitrary
        # provider strings. Reserve every preexisting valid ID first.
        base = f"s{index:02}_scene"
        generated = base
        counter = 2
        while generated in valid_ids or generated in seen:
            generated = f"{base}_{counter}"
            counter += 1
        scene["scene_id"] = generated
        seen.add(generated)
        replaced += 1

    if replaced == 0:
        return raw_json, 0
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")), replaced
