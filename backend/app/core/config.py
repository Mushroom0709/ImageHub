"""应用配置"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 基础
    APP_NAME: str = "ImageHub"
    DEBUG: bool = False

    # 数据库
    DATABASE_URL: str = "postgresql+psycopg2://imagehub:imagehub@db:5432/imagehub"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # OBS
    OBS_ACCESS_KEY: str = ""
    OBS_SECRET_KEY: str = ""
    OBS_ENDPOINT: str = ""
    OBS_BUCKET: str = ""
    OBS_PREFIX: str = "ImageHub/"

    # AI
    AI_API_BASE: str = ""
    AI_API_KEY: str = ""
    AI_MODEL: str = "/model"

    # TikHub
    TIKHUB_TOKEN: str = ""
    TIKHUB_BASE_URL: str = "https://api.tikhub.dev"

    # Meilisearch
    MEILISEARCH_HOST: str = "http://meilisearch:7700"
    MEILISEARCH_MASTER_KEY: str = ""

    # JWT
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
