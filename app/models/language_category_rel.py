from neomodel import IntegerProperty, StructuredRel


class LanguageCategoryRel(StructuredRel):
    order = IntegerProperty(required=True)
