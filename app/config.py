import logging
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_DEFAULT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    APP_ENV: str = "development"
    BASE_URL: str = "http://localhost:8000"
    SECRET_KEY: str = _DEFAULT_SECRET
    DATABASE_URL: str = "sqlite:///./data/inventory.db"
    FIRST_ADMIN_USER: str = "admin"
    FIRST_ADMIN_PASS: str = "admin123"

    class Config:
        env_file = ".env"


settings = Settings()

if settings.SECRET_KEY == _DEFAULT_SECRET:
    if settings.APP_ENV == "production":
        raise RuntimeError("SECRET_KEY musí být nastaven v produkci! Zkontrolujte .env soubor.")
    else:
        logger.warning("⚠️  SECRET_KEY má výchozí hodnotu — nastavte ji v .env pro produkci!")

if settings.FIRST_ADMIN_PASS == "admin123":
    if settings.APP_ENV == "production":
        logger.warning("⚠️  FIRST_ADMIN_PASS má výchozí hodnotu 'admin123' — změňte ji v .env!")
    else:
        logger.warning("⚠️  FIRST_ADMIN_PASS má výchozí hodnotu — doporučeno změnit v .env")
