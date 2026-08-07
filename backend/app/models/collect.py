"""采集任务模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class CollectTask(Base):
    """采集任务表"""
    __tablename__ = "collect_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(32), default="xiaohongshu")  # xiaohongshu/douyin
    url = Column(String(500), default="")
    status = Column(String(16), default="pending")  # pending/running/done/failed
    auto_tag = Column(Boolean, default=True)

    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    skip_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)

    error_message = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    created_by = Column(UUID(as_uuid=True), nullable=True)
