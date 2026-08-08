"""顶层分类（项目）模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class TopCategory(Base):
    """顶层分类（项目）表
    用户自行创建的顶层大分类，如"摄影原图"、"拍照姿势知识库"。
    素材归属到一个顶层分类。
    """
    __tablename__ = "top_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), default="")
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
