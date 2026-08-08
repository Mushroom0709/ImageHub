"""顶层分类（项目）API 端点"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.models.top_category import TopCategory
from app.models.asset import Asset

router = APIRouter(tags=["top-categories"])


class TopCategoryCreate(BaseModel):
    name: str
    description: str = ""


class TopCategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    sort_order: int | None = None


@router.get("")
def list_top_categories(db: Session = Depends(get_db)):
    """顶层分类列表（含素材数）"""
    cats = db.query(TopCategory).order_by(TopCategory.sort_order, TopCategory.created_at).all()
    counts = dict(
        db.query(Asset.top_category_id, func.count(Asset.id))
        .filter(Asset.deleted_at.is_(None))
        .group_by(Asset.top_category_id)
        .all()
    )
    return ok([
        {
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
            "asset_count": int(counts.get(c.id, 0)),
            "created_at": c.created_at.isoformat(),
        }
        for c in cats
    ])


@router.post("")
def create_top_category(data: TopCategoryCreate, db: Session = Depends(get_db)):
    """创建顶层分类（项目）"""
    existing = db.query(TopCategory).filter(TopCategory.name == data.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="分类已存在")

    cat = TopCategory(name=data.name, description=data.description)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return ok({"id": str(cat.id), "name": cat.name, "description": cat.description, "asset_count": 0})


@router.put("/{cat_id}")
def update_top_category(cat_id: uuid.UUID, data: TopCategoryUpdate, db: Session = Depends(get_db)):
    """修改顶层分类"""
    cat = db.query(TopCategory).filter(TopCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cat, key, value)
    db.commit()
    db.refresh(cat)
    return ok({"id": str(cat.id), "name": cat.name, "description": cat.description})


@router.delete("/{cat_id}")
def delete_top_category(cat_id: uuid.UUID, db: Session = Depends(get_db)):
    """删除顶层分类（该分类下素材变为未分类）"""
    cat = db.query(TopCategory).filter(TopCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")

    # 该分类下素材的 top_category_id 置空
    affected = db.query(Asset).filter(Asset.top_category_id == cat_id).update(
        {"top_category_id": None}, synchronize_session=False
    )
    db.delete(cat)
    db.commit()
    return ok({"ok": True, "affected_assets": affected})
