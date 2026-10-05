"""Finite taxonomic enumerations and compatibility matrix for LearnFlow V2 Motion Grammar."""

from enum import Enum
from types import MappingProxyType


class MotionTier(str, Enum):
    """Capability tiers for LearnFlow V2 Motion Grammar."""

    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"


class MotionVerb(str, Enum):
    """Finite taxonomic categories/verbs of semantic animation."""

    # Tier-1 supported verbs
    ENTER = "ENTER"
    EMPHASIZE = "EMPHASIZE"
    RELATION = "RELATION"
    TRANSFORM = "TRANSFORM"
    EXIT = "EXIT"

    # Reserved for future tiers (Tier 2/3 - deferred)
    CAMERA = "CAMERA"


class MotionStyle(str, Enum):
    """Finite taxonomic styles/actions for semantic animation."""

    # Tier-1 supported styles
    FADE = "FADE"
    SLIDE = "SLIDE"
    REVEAL = "REVEAL"
    HIGHLIGHT = "HIGHLIGHT"
    PULSE = "PULSE"
    FOCUS = "FOCUS"
    DRAW_EDGE = "DRAW_EDGE"
    PROPAGATE = "PROPAGATE"
    MOVE = "MOVE"

    # Reserved for future tiers (Tier 2/3 - deferred)
    SCALE_IN = "SCALE_IN"
    DRAW = "DRAW"
    GLOW = "GLOW"
    UNDERLINE = "UNDERLINE"
    RESIZE = "RESIZE"
    MORPH = "MORPH"
    REPLACE = "REPLACE"
    TRACE_PATH = "TRACE_PATH"
    PUSH = "PUSH"
    PAN = "PAN"
    FOCUS_REGION = "FOCUS_REGION"
    RESET = "RESET"
    COLLAPSE = "COLLAPSE"


class MotionTargetKind(str, Enum):
    """Finite taxonomic kinds of motion target entities in SceneGraph."""

    NODE = "NODE"
    RELATION = "RELATION"


# =========================================================================
# Authoritative Tier-1 Grammar Compatibility Table (Immutable Schema Contract)
# =========================================================================

TIER_1_MOTION_GRAMMAR: MappingProxyType[MotionVerb, frozenset[MotionStyle]] = MappingProxyType({
    MotionVerb.ENTER: frozenset({
        MotionStyle.FADE,
        MotionStyle.SLIDE,
        MotionStyle.REVEAL,
    }),
    MotionVerb.EMPHASIZE: frozenset({
        MotionStyle.HIGHLIGHT,
        MotionStyle.PULSE,
        MotionStyle.FOCUS,
    }),
    MotionVerb.RELATION: frozenset({
        MotionStyle.DRAW_EDGE,
        MotionStyle.PROPAGATE,
    }),
    MotionVerb.TRANSFORM: frozenset({
        MotionStyle.MOVE,
    }),
    MotionVerb.EXIT: frozenset({
        MotionStyle.FADE,
    }),
})

TIER_2_3_RESERVED_VERBS: frozenset[MotionVerb] = frozenset({
    MotionVerb.CAMERA,
})

TIER_2_3_RESERVED_STYLES: frozenset[MotionStyle] = frozenset({
    MotionStyle.SCALE_IN,
    MotionStyle.DRAW,
    MotionStyle.GLOW,
    MotionStyle.UNDERLINE,
    MotionStyle.RESIZE,
    MotionStyle.MORPH,
    MotionStyle.REPLACE,
    MotionStyle.TRACE_PATH,
    MotionStyle.PUSH,
    MotionStyle.PAN,
    MotionStyle.FOCUS_REGION,
    MotionStyle.RESET,
    MotionStyle.COLLAPSE,
})

VERB_TARGET_KIND_MAP: MappingProxyType[MotionVerb, MotionTargetKind] = MappingProxyType({
    MotionVerb.ENTER: MotionTargetKind.NODE,
    MotionVerb.EMPHASIZE: MotionTargetKind.NODE,
    MotionVerb.TRANSFORM: MotionTargetKind.NODE,
    MotionVerb.EXIT: MotionTargetKind.NODE,
    MotionVerb.RELATION: MotionTargetKind.RELATION,
})


def is_tier_1_verb(verb: MotionVerb | str) -> bool:
    """Check if a verb is a supported Tier-1 motion verb."""
    try:
        v = MotionVerb(verb) if isinstance(verb, str) else verb
        return v in TIER_1_MOTION_GRAMMAR
    except ValueError:
        return False


def is_tier_1_style(style: MotionStyle | str) -> bool:
    """Check if a style is supported in Tier-1."""
    try:
        s = MotionStyle(style) if isinstance(style, str) else style
        return any(s in allowed for allowed in TIER_1_MOTION_GRAMMAR.values())
    except ValueError:
        return False


def is_tier_1_combination(verb: MotionVerb | str, style: MotionStyle | str) -> bool:
    """Check if a (verb, style) pair is valid in Tier-1 Motion Grammar."""
    try:
        v = MotionVerb(verb) if isinstance(verb, str) else verb
        s = MotionStyle(style) if isinstance(style, str) else style
        allowed = TIER_1_MOTION_GRAMMAR.get(v)
        return allowed is not None and s in allowed
    except ValueError:
        return False
