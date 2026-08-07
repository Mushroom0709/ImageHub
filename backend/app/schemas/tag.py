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
