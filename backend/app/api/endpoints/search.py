"""搜索 API 端点"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.services.search_service import search_service

router = APIRouter(tags=["search"])


@router.get("/suggest")
def get_suggestions(q: str = Query("", min_length=1), limit: int = Query(8, ge=1, le=20), db: Session = Depends(get_db)):
    """搜索建议（标签 + 素材）"""
    # 标签建议
    from app.models.tag import Tag
    tags = db.query(Tag).filter(
        Tag.status == "active",
        Tag.name.ilike(f"%{q}%"),
    ).order_by(Tag.sort_order).limit(limit).all()

    # 素材建议（Meilisearch）
    assets = search_service.suggest(q, limit)

    return ok({
        "tags": [{"id": str(t.id), "name": t.name, "category": t.category} for t in tags],
        "assets": assets,
    })


@router.get("/assets")
def search_assets(q: str = Query("", min_length=1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """全文搜索素材"""
    hits = search_service.search(q, limit)
    return ok({"items": hits, "total": len(hits)})
