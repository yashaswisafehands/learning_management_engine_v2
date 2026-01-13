"""Utility helpers for safe Neo4j relationship traversal.

These helpers avoid triggering Neo4j warnings about unknown relationship
labels by checking the catalog of relationship types before executing a
pattern that references them. Neo4j emits
`Neo.ClientNotification.Statement.UnknownRelationshipTypeWarning` when a
query references a relationship type that has never been created. That in
turn can have a measurable performance penalty. The helpers below provide a
small cached lookup so we only issue queries when the relationship type is
known to exist.
"""

from __future__ import annotations

import time
from typing import Any, Iterable, List, Optional

from neomodel import db

_CACHE_TTL_SECONDS = 60.0
_relationship_cache: dict[str, tuple[bool, float]] = {}


def relationship_type_exists(rel_type: str) -> bool:
    """Return True if ``rel_type`` exists in the database.

    Results are cached for a short window (60 seconds) to avoid repeatedly
    calling ``CALL db.relationshipTypes`` on every request. When a type is
    first created the cache will refresh automatically after the TTL expires.
    """

    now = time.monotonic()
    cached = _relationship_cache.get(rel_type)
    if cached and now - cached[1] <= _CACHE_TTL_SECONDS:
        return cached[0]

    try:
        result, _ = db.cypher_query("CALL db.relationshipTypes()")
        seen_types = {row[0] for row in result}
        for rel in seen_types:
            _relationship_cache[rel] = (True, now)
        exists = rel_type in seen_types
        _relationship_cache[rel_type] = (exists, now)
        return exists
    except Exception:
        # On failure we assume the relationship type does not exist to stay safe
        _relationship_cache[rel_type] = (False, now)
        return False


def _deduce_relationship_type(
    rel_manager: Any, fallback: Optional[str]
) -> Optional[str]:
    """Extract relationship type metadata from a neomodel relationship manager."""

    if fallback:
        return fallback

    definition = getattr(rel_manager, "definition", None)
    if isinstance(definition, dict):
        rel_type = definition.get("relationship_type") or definition.get(
            "relation_type"
        )
        if rel_type:
            return rel_type

    rel_type = getattr(rel_manager, "relationship_type", None)
    if rel_type:
        return rel_type

    rel_type = getattr(rel_manager, "relation_type", None)
    if rel_type:
        return rel_type

    return fallback


def safe_relationship_all(
    source: Any,
    rel_identifier: str,
    rel_type: Optional[str] = None,
    *,
    suppress_warning: bool = False,
) -> List:
    """Return related nodes while suppressing missing-relationship warnings.

    ``source`` can be a neomodel relationship manager (``.all()``) *or* a node
    with a relationship attribute named ``rel_identifier``. ``rel_type`` can be
    provided explicitly; otherwise the helper attempts to infer it from the
    relationship metadata. ``suppress_warning`` is currently a no-op but kept
    for backwards compatibility with earlier call sites.
    """

    if source is None:
        return []

    if hasattr(source, "all") and callable(getattr(source, "all", None)):
        rel_manager = source
        relationship_type = _deduce_relationship_type(
            rel_manager, rel_type or rel_identifier
        )
    else:
        rel_manager = getattr(source, rel_identifier, None)
        if rel_manager is None:
            return []
        relationship_type = _deduce_relationship_type(rel_manager, rel_type)

    if relationship_type and not relationship_type_exists(relationship_type):
        return []

    try:
        all_func = getattr(rel_manager, "all", None)
        if callable(all_func):
            results: Optional[Iterable] = all_func()
            if results is None:
                return []
            return list(results)
    except Exception:
        return []

    return []


def safe_relationship_first(
    source: Any,
    rel_identifier: str,
    rel_type: Optional[str] = None,
) -> Optional[Any]:
    """Return the first related node when the relationship type exists."""

    results = safe_relationship_all(
        source,
        rel_identifier,
        rel_type=rel_type,
    )
    return results[0] if results else None
