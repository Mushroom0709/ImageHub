"""标签 Pydantic Schema"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class TagBase(BaseModel):
    name: str
    category: str = "scene"
    parent_id: Optional[UUID] = None
    alias: list[str] = []
    sort_order: int = 0


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = None
    alias: Optional[list[str]] = None
    parent_id: Optional[UUID] = None
    sort_order: Optional[int] = None


class Tag(TagBase):
    id: UUID
    status: str = "active"
    asset_count: int = 0
    children: list["Tag"] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TagMergeRequest(BaseModel):
    target_tag_id: UUID


class BatchTagRequest(BaseModel):
    asset_ids: list[UUID]
    add_tag_ids: list[UUID] = []
    remove_tag_ids: list[UUID] = []


class BatchMoveRequest(BaseModel):
    """批量修改所属项目（top_category_id=None 表示移出项目）"""
    asset_ids: list[UUID]
    top_category_id: Optional[UUID] = None


class BatchStarRequest(BaseModel):
    """批量修改星级（0=清除，1-5=星级）"""
    asset_ids: list[UUID]
    star_level: int


class BatchFlagRequest(BaseModel):
    """批量修改旗标（0=清除，1-5=颜色旗标）"""
    asset_ids: list[UUID]
    flag_level: int


class BatchExportRequest(BaseModel):
    """批量导出（返回 OBS 预签名 URL 列表）"""
    asset_ids: list[UUID]
    export_type: str = "original"  # original=原文件 / medium=中等缩略图
