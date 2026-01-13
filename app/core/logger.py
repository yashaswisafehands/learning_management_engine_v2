import logging

from app.core.settings import APP_NAME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(f"${APP_NAME}")
