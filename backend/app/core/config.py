"""应用配置"""
import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
    # AI 标签置信度低于此值 → 进待审核（默认 0.6，V2 从 0.7 下调减少审核量）
    AI_TAG_REVIEW_THRESHOLD: float = 0.6
    # 待审核标签被使用的次数达到该值 → 自动转 active（高频词信任机制）
    TAG_AUTO_APPROVE_MIN_USE: int = 3

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

    # 上传
    # 单文件大小上限（字节），默认 2GB
    UPLOAD_MAX_FILE_SIZE: int = 2 * 1024 * 1024 * 1024
    # 分片大小（字节），默认 8MB
    UPLOAD_CHUNK_SIZE: int = 8 * 1024 * 1024
    # 超过该大小自动走分片上传（字节），默认 100MB
    UPLOAD_MULTIPART_THRESHOLD: int = 100 * 1024 * 1024
    # 上传/处理临时文件目录（建议挂载物理盘，避免容器 tmpfs 占内存）
    UPLOAD_TMP_DIR: str = "/data/imagehub-tmp"

    @model_validator(mode="after")
    def ensure_upload_tmp_dir(self) -> "Settings":
        """启动时校验临时目录存在且可写，失败抛清晰错误"""
        try:
            os.makedirs(self.UPLOAD_TMP_DIR, exist_ok=True)
        except OSError as e:
            raise ValueError(
                f"UPLOAD_TMP_DIR 创建失败: {self.UPLOAD_TMP_DIR} ({e})。"
                "请检查 docker-compose 是否挂载了物理盘目录。"
            )
        if not os.access(self.UPLOAD_TMP_DIR, os.W_OK):
            raise ValueError(
                f"UPLOAD_TMP_DIR 不可写: {self.UPLOAD_TMP_DIR}。"
                "请检查目录权限。"
            )
        return self


settings = Settings()
