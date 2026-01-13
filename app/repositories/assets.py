from typing import List

from fastapi.concurrency import run_in_threadpool
from neomodel import db
from neomodel.exceptions import DoesNotExist

from app.core.error_codes import ErrorCode
from app.models.assets import Asset, AssetObject
from app.utils.version_utils import increment_version


class AssetRepository:
    @staticmethod
    def save_asset_metadata(metadata):
        asset = Asset(
            asset_id=metadata.asset_id,
            filename=metadata.filename,
            original_filename=metadata.original_filename,
            tag=metadata.tag,
            mime_type=metadata.mime_type,
            extension=metadata.extension,
            size_bytes=metadata.size_bytes,
            sha256=metadata.sha256,
            file_url=metadata.file_url,
            container=metadata.container,
            created_at=metadata.created_at,
        )
        return asset.save()

    @staticmethod
    def get_blob_name_by_asset_id(asset_id: str) -> dict | None:
        asset = Asset.nodes.get_or_none(asset_id=asset_id)
        if asset:
            return {
                "blob_name": asset.filename,
                "container": asset.container,
                "sha256": asset.sha256,
                "size_bytes": asset.size_bytes,
            }
        return None

    @staticmethod
    def get_asset_by_id(asset_id: str) -> Asset:
        try:
            return Asset.nodes.get(asset_id=asset_id)
        except DoesNotExist:
            raise ValueError(f"Asset with ID {asset_id} not found")

    @staticmethod
    def get_assets_by_ids(asset_ids: list[str]) -> list[Asset]:
        if not asset_ids:
            return []
        query = "MATCH (a:Asset) WHERE a.asset_id IN $asset_ids RETURN a"
        results, _ = db.cypher_query(query, {"asset_ids": asset_ids})
        assets = [Asset.inflate(row[0]) for row in results]
        if len(assets) != len(asset_ids):
            found_ids = {asset.asset_id for asset in assets}
            missing_ids = set(asset_ids) - found_ids
            raise ValueError(f"Assets with IDs {list(missing_ids)} not found")
        return assets

    @staticmethod
    def link_assets(primary_asset_id: str, linked_asset_ids: list[str]):
        primary_asset = AssetRepository.get_asset_by_id(primary_asset_id)
        linked_assets = AssetRepository.get_assets_by_ids(linked_asset_ids)
        for asset in linked_assets:
            primary_asset.linked_assets.connect(asset)

    @staticmethod
    def get_asset_with_all_linked(asset_id: str) -> List[Asset]:
        try:
            asset = Asset.nodes.get(asset_id=asset_id)
        except DoesNotExist:
            raise ValueError(f"Asset with id '{asset_id}' not found")

        all_assets = {asset.asset_id: asset}

        def _dfs_collect_links(current_asset: Asset):
            for linked in current_asset.linked_assets.all():
                if linked.asset_id not in all_assets:
                    all_assets[linked.asset_id] = linked
                    _dfs_collect_links(linked)

        _dfs_collect_links(asset)

        return list(all_assets.values())

    @staticmethod
    async def get_asset_for_question(question_id: str):
        query = """
        MATCH (q:OnboardingQuestion {question_id: $question_id})-[:USES_COUNTRY_JSON]->(a:Asset)
        RETURN a
        """
        result, meta = db.cypher_query(query, {"question_id": question_id})
        if not result:
            return None

        asset_obj = Asset.inflate(result[0][0])
        return asset_obj

    @staticmethod
    async def get_assets_by_tag(tag: str) -> list["Asset"]:
        def _query():
            return list(Asset.nodes.filter(tag=tag))  # empty list is fine

        return await run_in_threadpool(_query)

    @staticmethod
    async def get_all_assets() -> list["Asset"]:
        def _query():
            return list(Asset.nodes.all())

        return await run_in_threadpool(_query)

    @staticmethod
    def get_asset_object(tag: str, title: str) -> AssetObject | None:
        """Get existing asset object by tag and title (original filename)."""
        return AssetObject.nodes.get_or_none(tag=tag, title=title)

    @staticmethod
    def create_asset_object(tag: str, title: str) -> AssetObject:
        """Create a new asset object container."""
        return AssetObject(tag=tag, title=title).save()
    
    @staticmethod
    def get_next_version(asset_object: AssetObject) -> float:
        """Get next version number for an asset object."""
        versions = asset_object.versions.all()
        if not versions:
            return 1.0
        latest = max(versions, key=lambda v: getattr(v, "version", 1.0))
        return increment_version(getattr(latest, "version", 1.0))

    @staticmethod
    def get_versions(asset_object: AssetObject) -> List[Asset]:
        """Get all versions for an asset object, ordered by version descending."""
        return asset_object.versions.order_by("-version")
        
    @staticmethod
    def get_asset_object_by_id(object_id: str) -> AssetObject:
        """Get asset object by its ID."""
        try:
            return AssetObject.nodes.get(asset_object_id=object_id)
        except DoesNotExist:
            raise ValueError(f"AssetObject with ID {object_id} not found")

    @staticmethod
    def set_current_version(asset: Asset, updated_by: str = "System") -> Asset:
        """
        Set an asset as the current active version.
        Supersedes the existing current version.
        """
        asset_object_rel = asset.asset_object.single()
        if not asset_object_rel:
            raise ValueError(f"Asset {asset.asset_id} is not linked to an AssetObject container")
            
        asset_object = AssetObject.nodes.get(asset_object_id=asset_object_rel.asset_object_id)
        
        # 1. Supersede current active version if any
        current = asset_object.current_version.single()
        if current:
            # Skip if already this version
            if current.asset_id == asset.asset_id:
                if asset.status != "active":
                    asset.status = "active"
                    asset.save()
                return asset
                
            current.status = "superseded"
            current.save()
            asset_object.current_version.disconnect(current)
            
        # 2. Connect new version
        asset.status = "active"
        asset.save()
        asset_object.current_version.connect(asset)
        asset.is_current_of.connect(asset_object)
        
        return asset
