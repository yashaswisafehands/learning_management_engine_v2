from neomodel import IntegerProperty, StructuredRel


class ModuleResourceRel(StructuredRel):
    order = IntegerProperty(required=True)
