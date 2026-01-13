from typing import Any, Dict, Optional

from neomodel import db
from app.repositories.assets import AssetRepository


def get_manifest_by_language_id(language_id: str) -> Optional[Dict[str, Any]]:

    try:
        query = """
// 1. Get Language and its version
MATCH (lang:Language {language_id: $language_id})-[:CURRENT_VERSION]->(eff_lv:LanguageVersion)

// 2. Certificate profile
OPTIONAL MATCH (profile:CertificateProfile {country_code: eff_lv.country_code})
               -[:HAS_VERSION]->(cpv:CertificateProfileVersion {status: 'active'})



// 3. Modules (excluding those disabled for this language)
OPTIONAL MATCH (cpv)-[:INCLUDES_MODULE]->(m:Module)
               -[:CURRENT_VERSION]->(mv:ModuleVersion {status: 'active'})
WHERE NOT (lang)-[:DISABLED_MODULE]->(m)

// 4. Category + CategoryVersion
OPTIONAL MATCH (m)-[:INCLUDED_IN_CATEGORY]->(cat_v:CategoryVersion {status: 'active'})
OPTIONAL MATCH (cat:Category)-[:CURRENT_VERSION]->(cat_v)

// 4b. Translation captions on Category
OPTIONAL MATCH (cat)-[:HAS_CAPTION]->(cap:Translation)
WHERE cap.language_id = $language_id
  AND cap.context = "category"

// 5. Module icon
OPTIONAL MATCH (mv)-[:USES_ICON]->(m_icon:Asset)

// 6. Build modules (including key_learning_points)
WITH lang, eff_lv, profile, cat, cat_v, cap,
     COLLECT(
        CASE WHEN m IS NOT NULL AND mv IS NOT NULL THEN {
            module_id: m.module_id,
            slug: m.slug,
            title: mv.title,
            description: mv.description,
            version: mv.version,
            status: mv.status,
            icon: m_icon.asset_id,
            
            // Videos with version resolution
            videos: [
                (mv)-[:HAS_VIDEO]->(r:Resource) 
                WHERE NOT (lang)-[:DISABLED_RESOURCE]->(r) | {
                    resource_id: r.resource_id,
                    slug: r.slug,
                    title: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion) WHERE rv.language_id = $language_id | rv.title]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion) | rv.title]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion) | rv.title]),
                        r.title
                    ),
                    description: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion) WHERE rv.language_id = $language_id | rv.description]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion) | rv.description]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion) | rv.description]),
                        null
                    ),
                    version: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion) WHERE rv.language_id = $language_id | rv.version]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion) | rv.version]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion) | rv.version]),
                        1.0
                    ),
                    content: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion)-[:USES_CONTENT]->(a:Asset) WHERE rv.language_id = $language_id | a.filename]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion)-[:USES_CONTENT]->(a:Asset) | a.filename]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion)-[:USES_CONTENT]->(a:Asset) | a.filename]),
                        null
                    ),
                    icon: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion)-[:USES_ICON]->(a:Asset) WHERE rv.language_id = $language_id | a.filename]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion)-[:USES_ICON]->(a:Asset) | a.filename]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion)-[:USES_ICON]->(a:Asset) | a.filename]),
                        null
                    ),
                    order: 0
                }
            ],
            
            // Action Cards with version resolution
            action_cards: [
                (mv)-[:HAS_ACTION_CARD]->(r:Resource) 
                WHERE NOT (lang)-[:DISABLED_RESOURCE]->(r) | {
                    resource_id: r.resource_id,
                    slug: r.slug,
                    title: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion) WHERE rv.language_id = $language_id | rv.title]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion) | rv.title]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion) | rv.title]),
                        r.title
                    ),
                    description: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion) WHERE rv.language_id = $language_id | rv.description]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion) | rv.description]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion) | rv.description]),
                        null
                    ),
                    version: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion) WHERE rv.language_id = $language_id | rv.version]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion) | rv.version]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion) | rv.version]),
                        1.0
                    ),
                    content: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion)-[:USES_CONTENT]->(a:Asset) WHERE rv.language_id = $language_id | a.filename]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion)-[:USES_CONTENT]->(a:Asset) | a.filename]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion)-[:USES_CONTENT]->(a:Asset) | a.filename]),
                        null
                    ),
                    icon: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion)-[:USES_ICON]->(a:Asset) WHERE rv.language_id = $language_id | a.filename]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion)-[:USES_ICON]->(a:Asset) | a.filename]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion)-[:USES_ICON]->(a:Asset) | a.filename]),
                        null
                    ),
                    order: 0
                }
            ],
            
            // Practical Procedures with version resolution
            practical_procedures: [
                (mv)-[:HAS_PRACTICAL_PROCEDURE]->(r:Resource) 
                WHERE NOT (lang)-[:DISABLED_RESOURCE]->(r) | {
                    resource_id: r.resource_id,
                    slug: r.slug,
                    title: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion) WHERE rv.language_id = $language_id | rv.title]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion) | rv.title]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion) | rv.title]),
                        r.title
                    ),
                    description: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion) WHERE rv.language_id = $language_id | rv.description]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion) | rv.description]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion) | rv.description]),
                        null
                    ),
                    version: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion) WHERE rv.language_id = $language_id | rv.version]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion) | rv.version]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion) | rv.version]),
                        1.0
                    ),
                    content: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion)-[:USES_CONTENT]->(a:Asset) WHERE rv.language_id = $language_id | a.filename]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion)-[:USES_CONTENT]->(a:Asset) | a.filename]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion)-[:USES_CONTENT]->(a:Asset) | a.filename]),
                        null
                    ),
                    icon: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion)-[:USES_ICON]->(a:Asset) WHERE rv.language_id = $language_id | a.filename]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion)-[:USES_ICON]->(a:Asset) | a.filename]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion)-[:USES_ICON]->(a:Asset) | a.filename]),
                        null
                    ),
                    order: 0
                }
            ],
            
            // Drugs with version resolution
            drugs: [
                (mv)-[:HAS_DRUG]->(r:Resource) 
                WHERE NOT (lang)-[:DISABLED_RESOURCE]->(r) | {
                    resource_id: r.resource_id,
                    slug: r.slug,
                    title: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion) WHERE rv.language_id = $language_id | rv.title]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion) | rv.title]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion) | rv.title]),
                        r.title
                    ),
                    description: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion) WHERE rv.language_id = $language_id | rv.description]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion) | rv.description]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion) | rv.description]),
                        null
                    ),
                    version: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion) WHERE rv.language_id = $language_id | rv.version]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion) | rv.version]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion) | rv.version]),
                        1.0
                    ),
                    content: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion)-[:USES_CONTENT]->(a:Asset) WHERE rv.language_id = $language_id | a.filename]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion)-[:USES_CONTENT]->(a:Asset) | a.filename]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion)-[:USES_CONTENT]->(a:Asset) | a.filename]),
                        null
                    ),
                    icon: coalesce(
                        head([(r)-[:CURRENT_TRANSLATION]->(rv:ResourceVersion)-[:USES_ICON]->(a:Asset) WHERE rv.language_id = $language_id | a.filename]),
                        head([(r)-[:CURRENT_ADAPTATION]->(rv:ResourceVersion)-[:USES_ICON]->(a:Asset) | a.filename]),
                        head([(r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion)-[:USES_ICON]->(a:Asset) | a.filename]),
                        null
                    ),
                    order: 0
                }
            ],

            // Key Learning Points for this module
            keylearning_points: [
                (mv)-[:HAS_KEY_LEARNING_POINT]->(klp:KeyLearningPoint) |
                
                // Select the best active version using incoming VERSION_OF relation
                // Priority: 
                // 1. Active version matching language_id
                // 2. Active Adapted version
                // 3. Active Original version
                
                [selected_version IN [
                    head(
                       // Priority 1: Explicit CURRENT_TRANSLATION
                       [(klp)-[:CURRENT_TRANSLATION]->(v:KeyLearningPointVersion) WHERE v.language_id = $language_id | v] +
                       // Priority 2: Active version via VERSION_OF matching language
                       [(klp)<-[:VERSION_OF]-(v:KeyLearningPointVersion {status: 'active'}) WHERE v.language_id = $language_id | v] +
                       // Priority 3: Explicit CURRENT_ADAPTATION
                       [(klp)-[:CURRENT_ADAPTATION]->(v:KeyLearningPointVersion) | v] +
                       // Priority 4: Active version via VERSION_OF matching adapted
                       [(klp)<-[:VERSION_OF]-(v:KeyLearningPointVersion {status: 'active'}) WHERE v.content_type = 'adapted' | v] +
                       // Priority 5: Explicit CURRENT_ORIGINAL
                       [(klp)-[:CURRENT_ORIGINAL]->(v:KeyLearningPointVersion) | v] +
                       // Priority 6: Active version via VERSION_OF matching original
                       [(klp)<-[:VERSION_OF]-(v:KeyLearningPointVersion {status: 'active'}) WHERE v.content_type = 'original' | v]
                    )
                ] | {
                        klp_id: klp.klp_id,
                        slug: coalesce(klp.slug, klp.klp_id),
                        level: coalesce(klp.level, ""),

                        // If version found, use it; else null/fallback
                        title: CASE WHEN selected_version IS NOT NULL THEN selected_version.title ELSE klp.title END,
                        description: CASE WHEN selected_version IS NOT NULL THEN selected_version.description ELSE null END,
                        content_type: CASE WHEN selected_version IS NOT NULL THEN selected_version.content_type ELSE "original" END,
                        version: CASE WHEN selected_version IS NOT NULL THEN selected_version.version ELSE null END,

                        questions: CASE WHEN selected_version IS NOT NULL THEN [
                            (selected_version)-[:HAS_QUESTION]->(q:KLPQuestion) |
                            {
                                question_id: q.question_id,
                                question: q.question,
                                quizz_type: q.quizz_type,
                                icon: head([(q)-[:USES_ICON]->(ai:Asset) | ai.asset_id + '.' + ai.extension]),
                                link: head([(q)-[:LINKS_TO]->(r:Resource) | r.resource_id]),
                                show_toggle: q.show_toggle,
                                essential: q.essential,
                                description: q.description,
                                order: q.order,
                                answers: [
                                    (q)-[:HAS_ANSWER]->(a:KLPAnswer) |
                                    {
                                        answer_id: a.answer_id,
                                        value: a.value,
                                        correct: a.correct,
                                        order: a.order
                                    }
                                ]
                            }
                        ] ELSE [] END
                }][0]
            ]
        } ELSE NULL END
     ) AS modules_for_category
     
// 7. Build categories, screen data, transcriptions
WITH lang, eff_lv, profile,
     COLLECT(
        CASE WHEN cat IS NOT NULL AND cat_v IS NOT NULL THEN {
            category_id: cat.category_id,
            slug: cat.slug,
            title: cat_v.title,
            translated_caption: COALESCE(cap.text, cat_v.title),
            description: cat_v.description,
            modules: [mod IN modules_for_category WHERE mod IS NOT NULL]
        } ELSE NULL END
     ) AS all_categories,

     // Pattern Comprehension for Screen Data
     [
        (lang)-[:HAS_SCREEN_DATA]->(sd:ScreenData)-[:CURRENT_VERSION]->(sdv:ScreenDataVersion)
        |
        {
            data_id: sd.data_id,
            data: sdv.data,
            updated_by: sdv.updated_by
        }
     ] AS all_screen_data,

     // Pattern Comprehension for Transcriptions
     [
        (lang)-[:HAS_TRANSCRIPTION]->(t:Transcription)-[:CURRENT_VERSION]->(tv:TranscriptionVersion)
        |
        {
            data: tv.data
        }
     ] AS all_transcriptions

// 8. Return final manifest
RETURN {
    language: {
        language_id: lang.language_id,
        autonym_script: eff_lv.autonym_script,
        learning_platform: eff_lv.learning_platform,
        country: eff_lv.country,
        country_code: eff_lv.country_code,
        latitude: eff_lv.latitude,
        longitude: eff_lv.longitude,
        version: eff_lv.version
    },
    certificate_profile: CASE WHEN profile IS NULL THEN NULL ELSE {
        certificate_profile_id: profile.certificate_profile_id,
        slug: profile.slug,
        country_code: profile.country_code,
        country_name: profile.country_name,
        certificate_template: [(profile)-[:USES_ASSET]->(pa:Asset) | coalesce(pa.filename, pa.asset_id)],
        current_version: profile.current_version,
        modules: [(cpv)-[rel:INCLUDES_MODULE]->(mod:Module)-[:CURRENT_VERSION]->(modv:ModuleVersion) | {
            module_id: mod.module_id,
            slug: mod.slug,
            title: modv.title,
            weightage: rel.weightage,
            passing_percentage: rel.passing_percentage,
            mandatory: rel.mandatory,
            order: rel.order
        }]
    } END,
    categories: [cat IN all_categories WHERE cat IS NOT NULL],
    onboarding_questions: head([
        (lang)-[:HAS_ONBOARDING_FLOW]->(:OnboardingFlow)-[:CURRENT_VERSION]->(ofv:OnboardingFlowVersion) 
        | ofv.data
    ]),
    transcriptions: [tr IN all_transcriptions WHERE tr IS NOT NULL],
    screen_data: [sd IN all_screen_data WHERE sd IS NOT NULL],
    language_assets: 
        // Assets from OnboardingFlowVersion
        [(lang)-[:HAS_ONBOARDING_FLOW]->(:OnboardingFlow)-[:CURRENT_VERSION]->(ofv:OnboardingFlowVersion)-[:USES_ASSET]->(a:Asset) | a.asset_id + '.' + COALESCE(a.extension, '')] +
        // Assets from ScreenDataVersion  
        [(lang)-[:HAS_SCREEN_DATA]->(:ScreenData)-[:CURRENT_VERSION]->(sdv:ScreenDataVersion)-[:USES_ASSET]->(a:Asset) | a.asset_id + '.' + COALESCE(a.extension, '')],
    UserFeedback: []
} AS result
"""

        rows, _ = db.cypher_query(query, {"language_id": language_id})
        if not rows or not rows[0][0]:
            return None

        manifest = rows[0][0]

        # ----------------- ASSET EXTENSION RESOLVER -----------------
        def add_ext(aid: Optional[str]) -> Optional[str]:
            if not aid:
                return None
            try:
                asset = AssetRepository.get_asset_by_id(aid)
                if asset.extension:
                    return f"{asset.asset_id}.{asset.extension}"
                return asset.asset_id
            except:
                return aid
        # ------------------------------------------------------------

        # Fix module icons
        for category in manifest.get("categories", []):
            for module in category.get("modules", []):
                module["icon"] = add_ext(module.get("icon"))

        import json

        try:
            # Parse JSON data for screen_data
            for sd in manifest.get("screen_data", []):
                if isinstance(sd.get("data"), str):
                    try:
                        sd["data"] = json.loads(sd["data"])
                    except json.JSONDecodeError:
                        sd["data"] = {}
                
                # Resolve asset extensions within data if present
                # Handle if data is a list (monolithic) or dict (single)
                data_items = sd["data"] if isinstance(sd.get("data"), list) else [sd.get("data")] if isinstance(sd.get("data"), dict) else []
                
                for item in data_items:
                    if isinstance(item, dict):
                        item["content"] = add_ext(item.get("content"))
                        item["translated_content"] = add_ext(item.get("translated_content"))
                        item["icon"] = add_ext(item.get("icon"))

            # Resolve assets in onboarding_questions
            onboarding_qs = manifest.get("onboarding_questions")
            if onboarding_qs:
                # If it's a string (JSON), parse it
                if isinstance(onboarding_qs, str):
                    try:
                        onboarding_qs = json.loads(onboarding_qs)
                        manifest["onboarding_questions"] = onboarding_qs
                    except json.JSONDecodeError:
                        onboarding_qs = []
                        manifest["onboarding_questions"] = []
                
                # Iterate and resolve
                if isinstance(onboarding_qs, list):
                    for q in onboarding_qs:
                        if isinstance(q, dict) and q.get("answers"):
                            for ans in q["answers"]:
                                if isinstance(ans, dict):
                                    ans["content"] = add_ext(ans.get("content"))

            # Parse and flatten transcriptions to {key, translated_content} format
            flattened_transcriptions = []
            for tr in manifest.get("transcriptions", []):
                if tr and "data" in tr:
                    data_str = tr["data"]
                    if isinstance(data_str, str):
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                    else:
                        data = data_str
                    
                    # Handle if data is a list (monolithic) or dict (single)
                    items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
                    
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        # Extract key and translated_content with fallback priority
                        key = item.get("key")
                        translated_content = item.get("translated_content") or item.get("adapted_content") or item.get("content")
                        
                        if key:
                            flattened_transcriptions.append({
                                "key": key,
                                "translated_content": translated_content
                            })
            
            manifest["transcriptions"] = flattened_transcriptions
            
            # ---------------- COMPUTE LANGUAGE ASSETS ----------------
            # Collect all asset IDs from onboarding and screen data
            language_asset_ids = set()
            
            # Extract from onboarding_questions
            onboarding_qs = manifest.get("onboarding_questions", [])
            if isinstance(onboarding_qs, list):
                for q in onboarding_qs:
                    if isinstance(q, dict) and q.get("answers"):
                        for ans in q["answers"]:
                            if isinstance(ans, dict) and ans.get("content"):
                                language_asset_ids.add(ans["content"])
            
            # Extract from screen_data
            for sd in manifest.get("screen_data", []):
                if isinstance(sd, dict):
                    data_items = sd.get("data", [])
                    if isinstance(data_items, list):
                        for item in data_items:
                            if isinstance(item, dict):
                                for field in ["content", "translated_content", "icon"]:
                                    if item.get(field):
                                        language_asset_ids.add(item[field])
                    elif isinstance(data_items, dict):
                        for field in ["content", "translated_content", "icon"]:
                            if data_items.get(field):
                                language_asset_ids.add(data_items[field])
            
            # Update manifest with computed language_assets (use this instead of Cypher result)
            manifest["language_assets"] = list(language_asset_ids)
            
        except Exception as e:
            with open("error_log.txt", "w") as f:
                f.write(str(e))
                import traceback
                f.write(traceback.format_exc())
            raise e

        # Transcriptions are now flattened

        # ---------------- CATEGORY ASSET SIZE CALCULATION ------------
        # Collect module icon asset IDs
        asset_ids = set()
        for category in manifest.get("categories", []):
            for module in category.get("modules", []):
                if module.get("icon"):
                    asset_ids.add(module["icon"].split(".")[0])  # remove extension for lookup
                # Collect IDs from resources
                for key in ["videos", "action_cards", "practical_procedures", "drugs"]:
                    for resource in module.get(key, []):
                        if resource.get("content"):
                            asset_ids.add(resource["content"].split(".")[0])
                        if resource.get("icon"):
                            asset_ids.add(resource["icon"].split(".")[0])

        if not asset_ids:
            for category in manifest.get("categories", []):
                category["assets"] = []
                category["download_size_mb"] = 0.0
                for module in category.get("modules", []):
                    module["asset_filenames"] = []
                    module["asset_total_size_mb"] = 0.0
            return manifest

        # Fetch asset metadata
        asset_query = """
            UNWIND $asset_ids as asset_id
            MATCH (a:Asset {asset_id: asset_id})
            RETURN a.asset_id as id, a.filename as filename, a.size_bytes as size
        """
        asset_rows, _ = db.cypher_query(asset_query, {"asset_ids": list(asset_ids)})
        assets_map = {row[0]: {"filename": row[1], "size": row[2]} for row in asset_rows}

        # Inject asset metadata and resolve filenames
        for category in manifest.get("categories", []):
            category_assets = set()
            category_size = 0

            for module in category.get("modules", []):
                module_assets = set()
                module_size = 0

                # Resolve module icon
                icon_id = module.get("icon")
                if icon_id:
                    base_id = icon_id.split(".")[0]
                    if base_id in assets_map:
                        asset = assets_map[base_id]
                        if asset["filename"]:
                            module_assets.add(asset["filename"])
                        module_size += asset["size"] or 0

                # Resolve resource content/icons
                for key in ["videos", "action_cards", "practical_procedures", "drugs"]:
                    for resource in module.get(key, []):
                        # Resolve Content
                        content_id = resource.get("content")
                        if content_id:
                            base_id = content_id.split(".")[0]
                            if base_id in assets_map:
                                asset = assets_map[base_id]
                                resource["content"] = asset["filename"]
                                if asset["filename"]:
                                    module_assets.add(asset["filename"])
                                module_size += asset["size"] or 0
                        
                        # Resolve Icon
                        res_icon_id = resource.get("icon")
                        if res_icon_id:
                            base_id = res_icon_id.split(".")[0]
                            if base_id in assets_map:
                                asset = assets_map[base_id]
                                resource["icon"] = asset["filename"]
                                if asset["filename"]:
                                    module_assets.add(asset["filename"])
                                module_size += asset["size"] or 0

                module["asset_total_size_mb"] = round(module_size / (1024 * 1024), 2)

                category_assets.update(module_assets)
                category_size += module_size

            category["assets"] = list(category_assets)
            category["download_size_mb"] = round(category_size / (1024 * 1024), 2)

        return manifest
    except Exception as e:
        with open("error_log.txt", "w") as f:
            f.write(str(e))
            import traceback
            f.write(traceback.format_exc())
            # Don't try to access locals that might not exist
            pass
        return None




