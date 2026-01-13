from fastapi import APIRouter

from app.core.settings import APP_DESCRIPTION, APP_NAME, APP_VERSION

router = APIRouter()


@router.get("/")
async def app_status():
    return {
        "name": APP_NAME,
        "description": APP_DESCRIPTION,
        "version": APP_VERSION,
        "status": "Running Ok!",
    }

@router.get("/health")
async def app_status():
    return {
        "status": "Running Ok!"
    }
