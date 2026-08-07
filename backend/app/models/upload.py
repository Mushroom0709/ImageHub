"""上传日志模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class UploadLog(Base):
    """上传登记表"""
    __tablename__ = "upload_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = Column(String(64), default="")
    file_name = Column(String(500), default="")
    file_size = Column(BigInteger, default=0)
    content_type = Column(String(100), default="")
    obs_key = Column(String(500), default="")
    status = Column(String(16), default="pending")  # pending/uploading/processing/done/failed
    asset_id = Column(UUID(as_uuid=True), nullable=True)
    error_message = Column(String(500), default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    uploader_id = Column(UUID(as_uuid=True), nullable=True)
