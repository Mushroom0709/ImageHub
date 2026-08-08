"""素材模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, Float, Boolean, DateTime, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Asset(Base):
    """素材表"""
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), default="")
    description = Column(Text, default="")

    # 来源
    source_type = Column(String(32), default="upload")  # upload/xiaohongshu/douyin/ai_import
    source_id = Column(String(200), default="")
    source_url = Column(String(500), default="")
    author_name = Column(String(100), default="")
    author_id = Column(String(100), default="")

    # 文件信息
    asset_type = Column(String(16), default="image")  # image/video
    obs_bucket = Column(String(100), default="")
    obs_key = Column(String(500), default="")
    file_name = Column(String(500), default="")
    file_size = Column(BigInteger, default=0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    duration = Column(Float, default=0)  # 视频时长(秒)

    # 处理状态
    phash = Column(String(32), default="")  # 64位十六进制
    exif = Column(JSON, default=dict)
    quality_score = Column(Float, default=0)

    # 用户操作
    starred = Column(Boolean, default=False)
    flag_level = Column(Integer, default=0)  # 0无/1红/2橙/3黄/4绿/5蓝
    uploader_id = Column(UUID(as_uuid=True), nullable=True)

    # 顶层分类（项目）归属
    top_category_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_assets_source", "source_type", "source_id"),
        Index("ix_assets_phash", "phash"),
        Index("ix_assets_created", "created_at"),
        Index("ix_assets_starred", "starred"),
        Index("ix_assets_flag", "flag_level"),
        Index("ix_assets_deleted", "deleted_at"),
    )
