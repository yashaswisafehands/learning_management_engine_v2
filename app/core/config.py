import logging
from urllib.parse import quote_plus

from neomodel import config
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # secrets_dir allows reading from a mounted ConfigMap/Secret (key=filename, value=content)
    # env_file allows reading from a .env file (local dev)
    # Environment variables take precedence over both (unless configured otherwise)
    model_config = SettingsConfigDict(
        env_file=".env", secrets_dir="/app/config", extra="ignore"
    )

    # --- Database Configuration ---
    POSTGRES_HOST: str
    DB_USERNAME: str
    DB_PASSWORD: str
    DB: str
    DB_ENGINE: str = "postgresql+asyncpg"

    # --- Redis Configuration ---
    REDIS_PASSWORD: str

    # --- Neo4j Configuration ---
    NEO4J_HOST: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str
    NEO4J_PORT: int = 7687

    # --- Azure Storage Configuration ---
    AZURE_TENANT_ID: str
    AZURE_CLIENT_ID: str
    AZURE_CLIENT_SECRET: str
    AZURE_STORAGE_ACCOUNT_NAME: str
    AZURE_CONTAINER_NAME: str
    AZURE_STORAGE_ACCOUNT_KEY: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    @computed_field
    @property
    def PG_DATABASE_URL(self) -> str:
        return f"{self.DB_ENGINE}://{self.DB_USERNAME}:{quote_plus(self.DB_PASSWORD)}@{self.POSTGRES_HOST}/{self.DB}"

    @computed_field
    @property
    def NEO4J_URI(self) -> str:
        return f"bolt://{self.NEO4J_USERNAME}:{quote_plus(self.NEO4J_PASSWORD)}@{self.NEO4J_HOST}:{self.NEO4J_PORT}"


settings = Settings()

# Neo4j connection
config.DATABASE_URL = settings.NEO4J_URI
