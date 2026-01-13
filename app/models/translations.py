from neomodel import StringProperty, StructuredNode, UniqueIdProperty


class Translation(StructuredNode):
    translation_id = UniqueIdProperty()
    language_id = StringProperty(required=True, index=True)
    text = StringProperty(required=True)
    context = StringProperty()  # optional e.g. "category"
