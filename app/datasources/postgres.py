from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.error_codes import ErrorCode
from app.core.exceptions import AppException
from app.core.logger import logger

engine = create_async_engine(settings.PG_DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    try:
        async with async_session() as session:
            yield session
    except OSError as e:
        if e.errno == 65:
            logger.error("Network error: No route to host. Could not create session.")
        else:
            logger.error(f"Error while creating session: {e}")
        raise AppException(ErrorCode.DATABASE_ERROR, detail=str(e))


async def init_db() -> None:
    try:
        async with engine.begin() as conn:
            # sync create_all method inside an async context
            await conn.run_sync(SQLModel.metadata.create_all)
    except OSError as e:
        if e.errno == 65:
            logger.error(
                f"Network error: No route to host. Could not connect to {settings.POSTGRES_HOST}."
            )
        else:
            logger.error(f"An OSError occurred: {e}")
        raise AppException(ErrorCode.DATABASE_ERROR, detail=str(e))
    except OperationalError as e:
        logger.error(f"OperationalError: Could not connect to the database. {e}")
        raise AppException(ErrorCode.DATABASE_ERROR, detail=str(e))
    except Exception as e:
        # Catch all other exceptions and log them
        logger.error(f"Unexpected error: {e}")
        raise AppException(ErrorCode.DATABASE_ERROR, detail=str(e))


async def close_db() -> None:
    await engine.dispose()
