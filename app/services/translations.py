from app.repositories.translations import (find_or_create_translation,
                                           link_node_to_translation,
                                           get_all_translations)


def add_caption_to_entity(
    entity_id: str, entity_label: str, language_id: str, caption_text: str
):
    try:
        context = entity_label
        relationship_type = "HAS_CAPTION"
        entity_id_property = f"{entity_label}_id"

        translation_node = find_or_create_translation(
            language_id=language_id, context=context, text=caption_text
        )

        link_node_to_translation(
            source_node_label=entity_label,
            source_node_id_property=entity_id_property,
            source_node_id=entity_id,
            translation=translation_node,
            relationship_type=relationship_type,
        )

        return {
            "status": "success",
            "message": f"Caption successfully added to {entity_label} {entity_id}.",
            "translation_id": translation_node.translation_id,
        }

    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {e}"}


async def get_translations(include_versions: bool = False):
    return get_all_translations()
