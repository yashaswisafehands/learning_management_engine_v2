from app.models.entities import Entity
from app.schemas.entities import EntityCreateSchema, EntityPatchSchema


class EntityRepository:

    @staticmethod
    def create_entity(data: EntityCreateSchema) -> Entity:
        entity = Entity(
            entity=data.entity,
            description=data.description,
            icon=data.icon,
        ).save()
        return entity

    @staticmethod
    def get_entities() -> list[Entity]:
        return Entity.nodes.all()

    @staticmethod
    def patch_entity(entity_id: str, data: EntityPatchSchema) -> Entity:
        entity = Entity.nodes.get(entity_id=entity_id)
        if data.entity is not None:
            entity.entity = data.entity
        if data.description is not None:
            entity.description = data.description
        if data.icon is not None:
            entity.icon = data.icon
        entity.save()
        return entity

    @staticmethod
    def delete_entity(entity_id: str) -> None:
        entity = Entity.nodes.get(entity_id=entity_id)
        entity.delete()
        return None
