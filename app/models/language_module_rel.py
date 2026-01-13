from neomodel import DateTimeProperty, StringProperty, StructuredRel


class LanguageModuleRel(StructuredRel):
    """Relationship model for disabled modules per language.
    
    When a Language has a DISABLED_MODULE relationship to a Module,
    that module is disabled for that language and won't appear in the manifest.
    """
    disabled_at = DateTimeProperty(default_now=True)
    disabled_by = StringProperty(default="System")
