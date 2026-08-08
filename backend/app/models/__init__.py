from app.core.database import Base  # noqa: F401

# 导入所有模型，确保 Alembic 能检测到
from app.models.asset import Asset  # noqa: F401
from app.models.tag import Tag, AssetTag  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.collect import CollectTask  # noqa: F401
from app.models.upload import UploadLog  # noqa: F401
from app.models.multipart import MultipartUpload  # noqa: F401
from app.models.export import ExportTask  # noqa: F401
from app.models.top_category import TopCategory  # noqa: F401
