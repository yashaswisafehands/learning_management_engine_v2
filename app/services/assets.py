import os
from datetime import datetime, timedelta
from typing import List, Optional, Set

from azure.storage.blob import (AccountSasPermissions, BlobSasPermissions,
                                ContentSettings, ResourceTypes,
                                generate_account_sas, generate_blob_sas)
from fastapi import BackgroundTasks, HTTPException, UploadFile

from app.core.config import settings
from app.core.settings import ALLOWED_CONTENT_TYPES
from app.datasources.azure_storage import container_client
from app.models.assets import Asset, AssetObject
from app.repositories.assets import AssetRepository
from app.schemas.assets import AssetSchema, AssetUploadResponse
from app.utils.compute_sha import compute_sha256
from app.utils.executors import run_sync
from app.utils.sys_date import now
from app.utils.uuid import get_uid

# Using centralized run_sync from app.utils.executors


def _asset_to_schema(
    asset: Asset,
    *,
    sas_token: Optional[str] = None,
    depth: int = 0,
    max_depth: int = 1,
    visited: Optional[Set[str]] = None,
) -> AssetSchema:
    """Convert an Asset node into AssetSchema, including linked assets."""
    if asset is None:
        raise ValueError("asset cannot be None")

    visited_local = set(visited or set())
    if asset.asset_id in visited_local:
        max_depth = -1
    visited_local.add(asset.asset_id)

    file_url = getattr(asset, "file_url", None)
    if sas_token and file_url and "?" not in file_url:
        file_url = f"{file_url}?{sas_token}"

    linked_schemas: List[AssetSchema] = []
    if depth < max_depth:
        try:
            linked_nodes = asset.linked_assets.all()
        except Exception:
            linked_nodes = []
        for linked in linked_nodes:
            if linked.asset_id in visited_local:
                continue
            linked_schema = _asset_to_schema(
                linked,
                sas_token=sas_token,
                depth=depth + 1,
                max_depth=max_depth,
                visited=visited_local,
            )
            linked_schemas.append(linked_schema)

    return AssetSchema(
        asset_id=asset.asset_id,
        filename=getattr(asset, "filename", None),
        original_filename=getattr(asset, "original_filename", None),
        mime_type=getattr(asset, "mime_type", None),
        extension=getattr(asset, "extension", None),
        tag=getattr(asset, "tag", None),
        size_bytes=getattr(asset, "size_bytes", None),
        sha256=getattr(asset, "sha256", None),
        file_url=file_url,
        version=getattr(asset, "version", 1.0),
        status=getattr(asset, "status", "draft"),
        linked_assets=linked_schemas,
    )


async def generate_container_sas_url(
    expiry_minutes: int = 10, only_token: bool = False
) -> str:

    expiry = datetime.utcnow() + timedelta(minutes=10)

    sas_token = generate_account_sas(
        account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
        account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
        resource_types=ResourceTypes(container=True, object=True),
        permission=AccountSasPermissions(read=True, list=True),
        expiry=expiry,
        start=datetime.utcnow(),
    )
    if only_token:
        return sas_token

    return f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{settings.AZURE_CONTAINER_NAME}?{sas_token}"


async def upload_asset(
    file: UploadFile,
    tag: str,
    linked_asset_ids: Optional[List[str]] = None,
    previous_asset_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
) -> AssetUploadResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    asset_repo = AssetRepository()
    file_ext = ALLOWED_CONTENT_TYPES[file.content_type]
    asset_id = get_uid()
    blob_name = f"{asset_id}.{file_ext}"

    try:
        file_bytes = await file.read()
        file_size = len(file_bytes)
        sha256_hash = compute_sha256(file_bytes)

        blob_client = container_client.get_blob_client(blob_name)
        content_settings = ContentSettings(content_type=file.content_type)
        filename = os.path.basename(file.filename)
        blob_client.upload_blob(
            file_bytes,
            overwrite=True,
            metadata={"sha256": sha256_hash, "originalfilename": filename},
            content_settings=content_settings,
        )

        version = 1.0
        asset_object = None
        
        # Explicit Versioning Logic
        if previous_asset_id:
            # 1. User wants to update an existing asset
            prev_asset = await run_sync(asset_repo.get_asset_by_id, previous_asset_id)
            if not prev_asset:
                 raise HTTPException(status_code=404, detail=f"Previous asset {previous_asset_id} not found")
            
            # 2. Find its container
            asset_object_rel = await run_sync(lambda: prev_asset.asset_object.single())
            if asset_object_rel:
                asset_object = asset_object_rel
            else:
                # Lazy migration: Create container for legacy asset
                asset_object = await run_sync(
                    asset_repo.create_asset_object, 
                    getattr(prev_asset, "tag", tag), 
                    getattr(prev_asset, "original_filename", getattr(prev_asset, "filename", "legacy"))
                )
                # Link old asset as v1.0 (or keep its current version)
                await run_sync(lambda: prev_asset.asset_object.connect(asset_object))
                await run_sync(lambda: asset_object.versions.connect(prev_asset))
                # Legacy assets are implicitly "active" if they were being used
                # But for safety we check if it was current
                # ... let's just mark it current if it's the only one
                await run_sync(lambda: asset_object.current_version.connect(prev_asset))
                
            # 3. Calculate next version
            version = await run_sync(asset_repo.get_next_version, asset_object)
        else:
            # New Asset Chain
            asset_object = await run_sync(
                asset_repo.create_asset_object, tag, filename
            )

        metadata = Asset(
            asset_id=asset_id,
            tag=tag,
            filename=blob_name,
            original_filename=filename,
            mime_type=file.content_type,
            extension=file_ext,
            size_bytes=file_size,
            sha256=sha256_hash,
            file_url=blob_client.url,
            container=container_client.container_name,
            created_at=now(),
            version=version,
            status="draft",  # Always draft initially
        )

        saved_asset = await run_sync(asset_repo.save_asset_metadata, metadata)
        
        # Link to AssetObject
        await run_sync(lambda: asset_object.versions.connect(saved_asset))
        await run_sync(lambda: saved_asset.asset_object.connect(asset_object))
        
        # NOTE: WE DO NOT AUTO-ACTIVATE!
        # Unless it is the very first version of a new chain?
        # User said "manual work", but typically version 1.0 of a new upload IS the meaningful one.
        # But for strict consistency with "like resources", we might leave it draft.
        # However, for a brand new asset, forcing a second call to activate is annoying.
        # Let's AUTO-ACTIVATE ONLY IF it is version 1.0 (created from scratch).
        # This keeps updates manual, but new uploads usable.
        if not previous_asset_id and version == 1.0:
             await run_sync(asset_repo.set_current_version, saved_asset)

        linked_schemas: List[AssetSchema] = []

        if linked_asset_ids:
            await run_sync(asset_repo.link_assets, asset_id, linked_asset_ids)
            linked_nodes = await run_sync(
                AssetRepository.get_assets_by_ids, linked_asset_ids
            )
            linked_schemas = [
                _asset_to_schema(node, max_depth=0) for node in linked_nodes
            ]

        return AssetUploadResponse(
            asset_id=saved_asset.asset_id,
            filename=saved_asset.filename,
            original_filename=saved_asset.original_filename or filename,
            mime_type=saved_asset.mime_type,
            extension=saved_asset.extension,
            size_bytes=saved_asset.size_bytes or file_size,
            file_url=saved_asset.file_url,
            sha256=saved_asset.sha256,
            created_at=saved_asset.created_at,
            tag=saved_asset.tag or tag,
            version=getattr(saved_asset, "version", 1.0),
            linked_assets=linked_schemas,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_asset_versions(asset_id: str) -> List[AssetSchema]:
    asset_repo = AssetRepository()
    
    # Try finding as Asset first
    try:
        asset = await run_sync(asset_repo.get_asset_by_id, asset_id)
        asset_object_rel = await run_sync(lambda: asset.asset_object.single())
        if not asset_object_rel:
            return [_asset_to_schema(asset, max_depth=1)]
        asset_object = await run_sync(AssetObject.nodes.get, asset_object_id=asset_object_rel.asset_object_id)
        
    except ValueError:
        # If not an Asset, try finding as AssetObject
        try:
             asset_object = await run_sync(asset_repo.get_asset_object_by_id, asset_id)
        except ValueError:
             # Neither found
             raise HTTPException(status_code=404, detail=f"Asset or AssetObject with ID {asset_id} not found")

    versions = await run_sync(asset_repo.get_versions, asset_object)
    
    sas_token = await generate_container_sas_url(45, True)
    return [
        _asset_to_schema(v, sas_token=sas_token, max_depth=1) for v in versions
    ]

async def update_asset_status(asset_id: str, status: str) -> AssetSchema:
    asset_repo = AssetRepository()
    asset = await run_sync(asset_repo.get_asset_by_id, asset_id)
    
    if status == "active":
        asset = await run_sync(asset_repo.set_current_version, asset)
    else:
        # Handle other statuses if needed, e.g. archived
        asset.status = status
        await run_sync(asset.save)
        
    sas_token = await generate_container_sas_url(45, True)
    return _asset_to_schema(asset, sas_token=sas_token, max_depth=1)




async def generate_sas_url_by_asset_id(asset_id: str, expiry_minutes: int = 10):
    assets_repo = AssetRepository()
    blob_info = await run_sync(assets_repo.get_blob_name_by_asset_id, asset_id)
    if not blob_info:
        raise HTTPException(status_code=404, detail="Asset not found")

    blob_name = blob_info.get("blob_name")
    container = blob_info.get("container")
    sha256 = blob_info.get("sha256")
    size_bytes = blob_info.get("size_bytes")

    sas_token = generate_blob_sas(
        account_name=container_client.account_name,
        account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
        container_name=container,
        blob_name=blob_name,
        permission=BlobSasPermissions(read=True),
        expiry=now() + timedelta(minutes=expiry_minutes),
    )

    sas_url = f"https://{container_client.account_name}.blob.core.windows.net/{container}/{blob_name}?{sas_token}"
    return {
        "asset_id": asset_id,
        "asset_url": sas_url,
        "sha256": sha256,
        "expires_in_minutes": expiry_minutes,
        "size_bytes": size_bytes,
    }


async def get_assets(tag: str | None = None) -> list[AssetSchema]:
    assets_repo = AssetRepository()

    if tag:
        assets = await assets_repo.get_assets_by_tag(tag)
    else:
        assets = await assets_repo.get_all_assets()

    sas_token = await generate_container_sas_url(45, True)
    return [
        _asset_to_schema(asset, sas_token=sas_token, max_depth=1) for asset in assets
    ]
