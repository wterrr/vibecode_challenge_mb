"""Shared role and zone semantics for V2-03 simple layout templates."""

from enum import Enum


class ZoneClass(str, Enum):
    """Semantic layout zone classes enforced by the solver and preflight."""

    TITLE = "TITLE"
    CONTENT = "CONTENT"
    CAPTION = "CAPTION"


TITLE_ROLES = frozenset({"title", "safe_title", "header"})
CAPTION_ROLES = frozenset({"caption", "safe_caption", "subtitle"})

TITLE_ZONES = frozenset({"TITLE", "SAFE_TITLE", "TOP_HOOK"})
CONTENT_ZONES = frozenset({"CONTENT", "SAFE_CONTENT", "PRIMARY_CONTENT"})
CAPTION_ZONES = frozenset({"CAPTION", "SAFE_CAPTION", "SUBTITLE_ZONE"})
RESERVED_ITEM_ZONES = frozenset({"SAFE_EDGE", "BOTTOM_UI_SAFE"})


def normalize_semantic_token(value: str | None) -> str:
    """Normalize role/zone tokens for deterministic V2-03 classification."""

    return "" if value is None else str(value).strip()


def role_zone_class(role: str | None) -> ZoneClass:
    """Map a strategy role to its required semantic zone class.

    V2-03 has exactly three ordinary item classes:
    title chrome, content/core, and caption chrome. Any role that is not an
    explicit title/caption alias is ordinary content at this checkpoint.
    """

    role_key = normalize_semantic_token(role).lower()
    if role_key in TITLE_ROLES:
        return ZoneClass.TITLE
    if role_key in CAPTION_ROLES:
        return ZoneClass.CAPTION
    return ZoneClass.CONTENT


def zone_class(zone: str | None) -> ZoneClass | None:
    """Return the semantic class for a named target zone, if it is item-addressable."""

    zone_key = normalize_semantic_token(zone).upper()
    if zone_key in TITLE_ZONES:
        return ZoneClass.TITLE
    if zone_key in CONTENT_ZONES:
        return ZoneClass.CONTENT
    if zone_key in CAPTION_ZONES:
        return ZoneClass.CAPTION
    return None


def canonical_zone_for_role(role: str | None) -> str:
    """Default canonical zone name for a role."""

    cls = role_zone_class(role)
    if cls == ZoneClass.TITLE:
        return "TITLE"
    if cls == ZoneClass.CAPTION:
        return "CAPTION"
    return "CONTENT"


def is_chrome_role(role: str | None) -> bool:
    """Whether the role belongs to title/caption chrome rather than core content."""

    return role_zone_class(role) in {ZoneClass.TITLE, ZoneClass.CAPTION}


def role_zone_details(node_id: str, role: str | None, target_zone: str | None) -> dict[str, str | None]:
    """Safe structured details for role/zone contract errors."""

    expected = role_zone_class(role)
    actual = zone_class(target_zone)
    return {
        "node_id": node_id,
        "role": role,
        "target_zone": target_zone,
        "expected_zone_class": expected.value,
        "actual_zone_class": actual.value if actual is not None else None,
    }


def is_role_zone_compatible(role: str | None, target_zone: str | None) -> bool:
    """True when a zone is an addressable alias for the role's semantic class."""

    actual = zone_class(target_zone)
    return actual is not None and actual == role_zone_class(role)
