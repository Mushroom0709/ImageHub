"""标签模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.core.database import Base


class Tag(Base):
    """标签表"""
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    category = Column(String(32), default="scene")  # scene/style/clothing/makeup/pose_type/composition/mood/body_focus/info
    parent_id = Column(UUID(as_uuid=True), nullable=True)
    alias = Column(ARRAY(String), default=list)
    status = Column(String(16), default="active")  # active/pending
    sort_order = Column(Integer, default=0)
    asset_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("name", "category", name="uq_tag_name_category"),
        Index("ix_tags_category", "category"),
        Index("ix_tags_status", "status"),
    )


class AssetTag(Base):
    """素材-标签关联表"""
    __tablename__ = "asset_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id"), nullable=False)
    confidence = Column(Float, default=1.0)  # 0-1
    source = Column(String(16), default="manual")  # manual/ai/platform/external_ai
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("asset_id", "tag_id", name="uq_asset_tag"),
        Index("ix_asset_tags_tag_id", "tag_id"),
        Index("ix_asset_tags_asset_id", "asset_id"),
    )
