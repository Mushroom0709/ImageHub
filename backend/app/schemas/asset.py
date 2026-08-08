"""素材 Pydantic Schema"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class TagBrief(BaseModel):
    id: UUID
    name: str
    category: str
    confidence: Optional[float] = None

    class Config:
        from_attributes = True


class AssetBase(BaseModel):
    title: str = ""
    description: str = ""
    source_type: str = "upload"
    source_id: str = ""
    source_url: str = ""
    author_name: str = ""
    asset_type: str = "image"
    obs_key: str = ""
    file_name: str = ""
    file_size: int = 0
    width: int = 0
    height: int = 0
    duration: float = 0
    starred: bool = False
    flag_level: int = 0


class AssetCreate(AssetBase):
    auto_tag: bool = True
    content_text: str = ""
    tags: list[dict] = Field(default_factory=list)  # [{tagName, confidence, source}]
    top_category_id: UUID | None = None


class AssetUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    starred: Optional[bool] = None
    flag_level: Optional[int] = None
    top_category_id: Optional[UUID] = None


class Asset(AssetBase):
    id: UUID
    phash: str = ""
    quality_score: float = 0
    top_category_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    tags: list[TagBrief] = Field(default_factory=list)
    # 缩略图 URL（由后端填充预签名 URL）
    thumb_small: str = ""
    thumb_medium: str = ""
    thumb_raw: str = ""

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    items: list[Asset]
    total: int
    page: int
    size: int
