from typing import Any, Dict

from fastapi import HTTPException

from app.repositories.clients import get_manifest_by_language_id
from app.schemas.clients import ClientManifest
from app.utils.executors import run_sync


async def get_client_manifest(language_id: str) -> Dict[str, Any]:
    data = await run_sync(get_manifest_by_language_id, language_id=language_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Manifest not found")
    # Validate/shape via Pydantic schema before returning
    return ClientManifest(**data).model_dump()
