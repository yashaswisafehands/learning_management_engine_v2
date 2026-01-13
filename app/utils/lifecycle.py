"""Shared lifecycle helper utilities for versioned domain objects.

This module centralizes activation/deactivation semantics used by repositories
(e.g., modules, categories) to reduce duplication and ensure consistent behavior.

Lifecycle statuses supported (canonical set):
    draft, active, superseded, reverted, archived, review

Key behaviors:
    * Activating a version supersedes (older) or reverts (newer) a previously active one.
    * The parent entity's title is synchronized to the active version's title.
    * Deactivating the active version removes current pointer and promotes the
      highest remaining active version if one exists.

The helper is intentionally persistence-agnostic; callers must provide callables
that implement relationship connect/disconnect and persistence saves.
"""

from __future__ import annotations

from typing import Callable, Iterable, Optional, Protocol, TypeVar


class VersionNodeProtocol(Protocol):
    version: float
    status: str
    title: str | None
    created_by: str | None


class ParentNodeProtocol(Protocol):
    title: str | None


V = TypeVar("V", bound=VersionNodeProtocol)
P = TypeVar("P", bound=ParentNodeProtocol)


class CurrentPointerOps(Protocol):
    def get_current(self) -> Optional[V]: ...  # fetch current active version (if any)
    def connect(self, version: V) -> None: ...  # make version current
    def disconnect(self, version: V) -> None: ...  # remove current pointer


def activate_version(
    parent: P,
    version: V,
    pointer: CurrentPointerOps,
    all_versions: Iterable[V],
    updated_by: str | None = None,
    save_parent: Callable[[P], None] | None = None,
    save_version: Callable[[V], None] | None = None,
) -> V:
    """Activate a version applying supersede/revert logic against current.

    Args:
        parent: Parent entity node object.
        version: The candidate version node to activate.
        pointer: Adapter for current version relationship operations.
        all_versions: Iterable of all versions belonging to parent.
        updated_by: Optional user reference performing the action.
        save_parent: Callable to persist parent changes (title update), if needed.
        save_version: Callable to persist version status changes.
    """
    current = pointer.get_current()
    if current and current is not version:
        if version.version > current.version:
            current.status = "superseded"
        elif version.version < current.version:
            current.status = "reverted"
        if save_version:
            save_version(current)
        pointer.disconnect(current)

    # Sync parent title
    if getattr(version, "title", None):
        parent.title = version.title  # type: ignore[assignment]
        if save_parent:
            save_parent(parent)

    version.status = "active"
    if updated_by:
        version.created_by = updated_by  # type: ignore[assignment]
    if save_version:
        save_version(version)
    pointer.connect(version)
    return version


def deactivate_version(
    parent: P,
    version: V,
    pointer: CurrentPointerOps,
    all_versions: Iterable[V],
    new_status: str,
    updated_by: str | None = None,
    save_parent: Callable[[P], None] | None = None,
    save_version: Callable[[V], None] | None = None,
) -> V:
    """Deactivate an active version and promote highest remaining active if any.

    Args mirror activate_version; new_status must not be 'active'.
    """
    current = pointer.get_current()
    if current and current is version:
        pointer.disconnect(current)
        # Choose highest remaining active
        active_remaining = [
            v
            for v in all_versions
            if v is not version and getattr(v, "status", None) == "active"
        ]
        if active_remaining:
            promote = max(active_remaining, key=lambda v: v.version)
            pointer.connect(promote)
            if getattr(promote, "title", None):
                parent.title = promote.title  # type: ignore[assignment]
                if save_parent:
                    save_parent(parent)
    version.status = new_status
    if updated_by:
        version.created_by = updated_by  # type: ignore[assignment]
    if save_version:
        save_version(version)
    return version


VALID_LIFECYCLE_STATUSES = {
    "draft",
    "active",
    "superseded",
    "reverted",
    "archived",
    "review",
}


def validate_status(status: str) -> None:
    if status not in VALID_LIFECYCLE_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_LIFECYCLE_STATUSES))}"  # noqa: E501
        )
