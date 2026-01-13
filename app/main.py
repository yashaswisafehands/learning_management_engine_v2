from contextlib import asynccontextmanager

import os

from fastapi import BackgroundTasks  # noqa: F401
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppException
from app.core.logger import logger
from app.datasources.neo4j import create_indexes_from_models
from app.routers import (assets, categories, certificate_profiles, clients,
                         defaults, entities, key_learning_points, languages,
                         modules, resources, translations,
                         user_feedbacks)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🔍 Ensuring Neo4j indexes...")
    create_indexes_from_models()
    logger.info("✅ Indexes ensured")
    yield


def _normalize_root_path(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if not value.startswith("/"):
        value = f"/{value}"
    value = value.rstrip("/")
    return "" if value == "/" else value


_configured_root_path = _normalize_root_path(os.getenv("FASTAPI_ROOT_PATH", ""))


app = FastAPI(title="SDA LME", lifespan=lifespan, root_path=_configured_root_path)

# List of allowed origins
origins = [
    "http://localhost:5173",  # your React dev server
    "http://127.0.0.1:5173",
    # Add your production frontend domain here later
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 👈 allowed origins
    allow_credentials=True,  # allow cookies/auth headers
    allow_methods=["*"],  # allow all HTTP methods (GET, POST, PUT, DELETE…)
    allow_headers=["*"],  # allow all headers (Content-Type, Authorization…)
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response


@app.middleware("http")
async def forwarded_prefix_root_path(request: Request, call_next):
    if not _configured_root_path:
        forwarded_prefix = request.headers.get("x-forwarded-prefix")
        if forwarded_prefix:
            request.scope["root_path"] = _normalize_root_path(forwarded_prefix)
    return await call_next(request)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"code: {exc.status_code} {str(exc)}")
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"code: {ErrorCode.UNKNOWN_ERROR} {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "code": ErrorCode.UNKNOWN_ERROR,
            "message": "Something went wrong.",
        },
    )


# Include routers
app.include_router(defaults.router)
app.include_router(clients.router)
app.include_router(assets.router)
app.include_router(resources.router)
app.include_router(modules.router)
app.include_router(categories.router)
app.include_router(languages.router)
app.include_router(translations.router)
app.include_router(key_learning_points.router)
app.include_router(entities.router)
# app.include_router(onboarding_flows.router)
app.include_router(certificate_profiles.router)
app.include_router(user_feedbacks.router)

# GraphQL router
# app.include_router(graphql_app, prefix="/graphql")
