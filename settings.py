from pydantic_settings import BaseSettings, SettingsConfigDict
import pytz
from datetime import datetime


class Settings(BaseSettings):
    """
    Settings for the application.
    """
    # Debug
    DEBUG: bool = True

    # Server
    HOST: str = 'localhost'
    PORT: int = 8000

    # Database
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # Timezone
    TZ: str = 'Asia/Tashkent'

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 60 * 24 * 14  # 14 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 60 * 24 * 7  # 7 days

    @property
    def DATABASE_URL_asyncpg(self):
        """Async database URL for SQLAlchemy (AsyncPG driver)"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def DATABASE_URL_asycpg(self):
        """Alias for compatibility (typo version)"""
        return self.DATABASE_URL_asyncpg

    @property
    def DATABASE_URL_psycopg(self):
        """Sync database URL for Alembic migrations (Psycopg2 driver)"""
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def get_tz(self):
        """Get current time in configured timezone"""
        tz = pytz.timezone(self.TZ)
        return datetime.now(tz)

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra="allow"
    )


settings = Settings()
