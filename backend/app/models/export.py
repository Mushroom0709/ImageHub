"""导出任务模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.core.database import Base


class ExportTask(Base):
    """导出任务表"""
    __tablename__ = "export_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(16), default="pending")  # pending/processing/done/failed
    size = Column(String(16), default="raw")  # small/medium/raw

    total_count = Column(Integer, default=0)
    processed_count = Column(Integer, default=0)
    asset_ids = Column(ARRAY(UUID(as_uuid=True)), default=list)

    obs_key = Column(String(500), default="")
    file_size = Column(BigInteger, default=0)
    download_url = Column(String(1000), default="")

    error_message = Column(String(500), default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    created_by = Column(UUID(as_uuid=True), nullable=True)
