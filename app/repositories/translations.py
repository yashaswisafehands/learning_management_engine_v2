from neomodel import db

from app.models.translations import Translation


def find_or_create_translation(
    language_id: str, context: str, text: str
) -> Translation:

    query = """
        MATCH (t:Translation {language_id: $language_id, context: $context})
        RETURN t LIMIT 1
    """
    params = {"language_id": language_id, "context": context}
    results, meta = db.cypher_query(query, params)

    if results:
        t = Translation.inflate(results[0][0])

        t.text = text
        t.save()
        return t
    else:
        return Translation(language_id=language_id, context=context, text=text).save()


def link_node_to_translation(
    source_node_label: str,
    source_node_id_property: str,
    source_node_id: str,
    translation: Translation,
    relationship_type: str,
):
    source_node_label_cap = source_node_label.capitalize()

    query = f"""
        MATCH (s:{source_node_label_cap} {{{source_node_id_property}: $source_id}})
        MATCH (t:Translation {{translation_id: $translation_id}})
        MERGE (s)-[r:{relationship_type}]->(t)
        RETURN r
    """
    params = {
        "source_id": source_node_id,
        "translation_id": translation.translation_id,
    }

    results, _ = db.cypher_query(query, params)

    return results


def get_all_translations() -> list[dict]:
    query = """
        MATCH (n)-[:HAS_CAPTION]->(t:Translation)
        RETURN t, properties(n) as node_props, labels(n) as node_labels
    """
    results, _ = db.cypher_query(query)
    translations = []
    
    for row in results:
        t_node = Translation.inflate(row[0])
        node_props = row[1]
        node_labels = row[2]
        
        # Determine entity info
        entity_label = node_labels[0] if node_labels else "Unknown"
        
        # Try to find ID
        entity_id = "unknown"
        # Heuristic: look for a property that looks like an ID (e.g., matches label_id)
        # or just take the first property ending in _id
        for key, val in node_props.items():
            if key == f"{entity_label.lower()}_id":
                entity_id = val
                break
            if key.endswith("_id") and key != "language_id":
                 entity_id = val
        
        translations.append({
            "translation_id": t_node.translation_id,
            "entity_id": entity_id,
            "entity_label": entity_label,
            "language_id": t_node.language_id,
            "text": t_node.text
        })
        
    return translations
