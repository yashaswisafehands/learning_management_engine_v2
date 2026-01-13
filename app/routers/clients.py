from fastapi import APIRouter, Depends
from app.core.auth import validate_token

from app.schemas.clients import ClientManifest
from app.services.clients import get_client_manifest as svc_get_client_manifest

router = APIRouter(prefix="/v1/clients", tags=["Clients"], dependencies=[Depends(validate_token)])


@router.get("/manifest/{language_id}", response_model=ClientManifest)
async def get_client_manifest(language_id: str):
    return await svc_get_client_manifest(language_id)
