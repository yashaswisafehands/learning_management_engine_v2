from neomodel import DateTimeProperty, StringProperty, StructuredRel


class LanguageResourceRel(StructuredRel):
    """Relationship model for disabled resources per language.
    
    When a Language has a DISABLED_RESOURCE relationship to a Resource,
    that resource is disabled for that language and won't appear in the manifest.
    """
    disabled_at = DateTimeProperty(default_now=True)
    disabled_by = StringProperty(default="System")
