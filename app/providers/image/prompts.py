"""Deterministic prompt construction for AI image generation."""

from app.domain.lesson import IllustrationSpec, ScenePlan


def build_illustration_prompt(scene: ScenePlan, spec: IllustrationSpec) -> str:
    """Build a structured, constrained prompt for educational scene illustration.

    Guarantees that the model focuses purely on conceptual visual subjects and
    composition, leaving text, titles, subtitles, and badges to deterministic overlays.
    """
    concept = scene.concept.strip() if scene.concept else scene.title.strip()
    visual_description = spec.prompt.strip()

    prompt = (
        "Create a clean educational illustration for a short learning video.\n\n"
        f"Topic:\n{concept}\n\n"
        f"Visual description:\n{visual_description}\n\n"
        "Composition:\n"
        "- landscape 16:9\n"
        "- one clear focal concept\n"
        "- simple visual hierarchy\n"
        "- uncluttered, modern flat or clean semi-detailed educational style\n"
        "- suitable for framing with overlay educational text\n"
        "- no decorative borders or frames\n"
        "- no interface elements or computer window chrome\n"
        "- no logos or watermarks\n\n"
        "Avoid:\n"
        "- embedded paragraphs or sentences\n"
        "- tiny unreadable labels\n"
        "- presentation slide layout\n"
        "- artificial text overlays\n"
        "- photorealistic pseudo-text"
    )
    return prompt
