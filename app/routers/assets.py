from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.core.auth import validate_token

from pydantic import BaseModel
from app.schemas.assets import (AssetDownloadResponse, AssetSASResponse,
                                AssetSchema, AssetUploadResponse)
from app.services import assets as assets_service

router = APIRouter(prefix="/assets", tags=["Assets"], dependencies=[Depends(validate_token)])


@router.post("/{tag}/upload/", response_model=AssetUploadResponse)
async def upload_asset(
    tag: str,
    file: UploadFile = File(...),
    linked_asset_ids: Optional[str] = Form(None),
    previous_asset_id: Optional[str] = Form(None),
):

    linked_asset_list = linked_asset_ids.split(",") if linked_asset_ids else []

    return await assets_service.upload_asset(
        file, tag, linked_asset_list, previous_asset_id=previous_asset_id
    )


@router.get("/{id}/download", response_model=AssetDownloadResponse)
async def get_sas_url(id: str):
    return await assets_service.generate_sas_url_by_asset_id(id)

@router.get("/{id}/versions", response_model=List[AssetSchema])
async def get_asset_versions(id: str):
    """Get all versions of an asset chain."""
    return await assets_service.get_asset_versions(id)

@router.put("/{id}/status", response_model=AssetSchema)
async def update_asset_status(id: str, status: str = Form(...)): # Or body? Simple Form is good for now
    """Update asset status (e.g. to 'active')."""
    return await assets_service.update_asset_status(id, status)
    
class AssetStatusUpdate(BaseModel):
    status: str

@router.put("/{id}/status-json", response_model=AssetSchema)
async def update_asset_status_json(id: str, payload: AssetStatusUpdate):
    """Update asset status via JSON body"""
    return await assets_service.update_asset_status(id, payload.status)


@router.get("/generate-sas-url", response_model=AssetSASResponse)
async def get_sas_url_for_container():
    sas_url = await assets_service.generate_container_sas_url()
    return {"sas_url": sas_url}


@router.get("/", response_model=List[AssetSchema])
async def get_assets(filter: str | None = None):
    return await assets_service.get_assets(filter)
