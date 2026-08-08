"""分片上传模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class MultipartUpload(Base):
    """分片上传登记表（断点续传状态持久化）"""
    __tablename__ = "multipart_uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 业务上传 ID（前端生成，同一批文件共享）
    batch_id = Column(String(64), default="")
    # OBS 侧 uploadId
    obs_upload_id = Column(String(128), default="")
    obs_key = Column(String(500), default="")

    file_name = Column(String(500), default="")
    file_size = Column(BigInteger, default=0)
    content_type = Column(String(100), default="")
    asset_type = Column(String(16), default="image")  # image/video

    total_parts = Column(Integer, default=0)
    part_size = Column(BigInteger, default=0)

    # 已上传分片：[{"part_number": 1, "etag": "...", "size": 8388608}]
    uploaded_parts = Column(JSONB, default=list)

    # pending/uploading/completed/aborted/failed
    status = Column(String(16), default="pending")
    error_message = Column(String(500), default="")

    top_category_id = Column(UUID(as_uuid=True), nullable=True)
    asset_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
