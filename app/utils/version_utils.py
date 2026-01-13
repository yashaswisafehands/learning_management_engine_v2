"""
Version utility functions for handling version increments across repositories.
Handles floating point precision issues and proper semantic versioning.
"""


def increment_version(current_version: float) -> float:
    """
    Increment version by 0.1, handling floating point precision.
    After 1.9, increments to 2.0, not 1.10.

    Args:
        current_version: Current version number (e.g., 1.2, 1.9, 2.0)

    Returns:
        New version number incremented by 0.1

    Examples:
        1.0 -> 1.1
        1.9 -> 2.0
        2.0 -> 2.1
        2.9 -> 3.0
    """
    # Convert to integer representation (multiply by 10) to avoid floating point issues
    version_int = int(current_version * 10)

    # Increment by 1 (equivalent to 0.1)
    new_version_int = version_int + 1

    # Convert back to float
    new_version = new_version_int / 10.0

    return new_version


def get_next_version(slug: str, model_class, version_field: str = "version") -> float:
    """
    Get the next version number for a given slug in a repository.

    Args:
        slug: The slug to check for existing versions
        model_class: The model class to query (e.g., Language, Category)
        version_field: The field name for version (default: "version")

    Returns:
        Next version number (starts at 1.0 if no existing versions)
    """
    # Get existing items with the same slug, ordered by version descending
    filter_kwargs = {"slug": slug, "is_deleted": False}
    existing_items = model_class.nodes.filter(**filter_kwargs).order_by(
        f"-{version_field}"
    )

    if existing_items:
        # Get the highest version and increment it
        current_version = getattr(existing_items[0], version_field)
        return increment_version(current_version)
    else:
        # If no existing items, start with version 1.0
        return 1.0


def get_latest_version(slug: str, model_class, version_field: str = "version") -> float:
    """
    Get the latest version number for a given slug.

    Args:
        slug: The slug to check
        model_class: The model class to query
        version_field: The field name for version (default: "version")

    Returns:
        Latest version number, or 0.0 if no versions exist
    """
    filter_kwargs = {"slug": slug, "is_deleted": False}
    existing_items = model_class.nodes.filter(**filter_kwargs).order_by(
        f"-{version_field}"
    )

    if existing_items:
        return getattr(existing_items[0], version_field)
    else:
        return 0.0
