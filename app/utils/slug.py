import re
import unicodedata


def _normalize_to_ascii(value: str) -> str:
    """Normalize the input to ASCII characters."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_bytes = normalized.encode("ascii", "ignore")
    return ascii_bytes.decode("ascii")


def sanitize_slug_component(value: str | None, fallback: str = "unknown") -> str:
    """Return a slug-safe component without consecutive hyphens."""
    if not value:
        return fallback

    ascii_value = _normalize_to_ascii(value)
    lower_value = ascii_value.lower()
    # Replace any non-alphanumeric characters with hyphen
    cleaned = re.sub(r"[^a-z0-9]+", "-", lower_value)
    # Collapse multiple hyphens into one
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or fallback


def build_slug(prefix: str, *components: str | None, fallback: str = "unknown") -> str:
    """Construct a slug by sanitizing each component and joining with hyphens."""
    if not prefix:
        raise ValueError("Slug prefix must be provided")

    sanitized_prefix = sanitize_slug_component(prefix, fallback)
    sanitized_components = [sanitize_slug_component(c, fallback) for c in components]
    parts = [sanitized_prefix, *sanitized_components]
    return "-".join(parts)


def build_language_slug(country: str | None, language_name: str | None) -> str:
    """Construct the canonical slug for a language using provided components."""
    return build_slug("lan", country, language_name)
