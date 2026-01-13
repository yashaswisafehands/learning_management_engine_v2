from neomodel import (DateTimeProperty, StringProperty, StructuredNode,
                      UniqueIdProperty)


class Entity(StructuredNode):
    entity = StringProperty(required=True)
    entity_id = UniqueIdProperty()
    description = StringProperty()
    icon = StringProperty()

    created_at = DateTimeProperty(default_now=True)
