"""待审核素材 API"""
import uuid
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.response import ok
from app.models.asset import Asset
from app.models.tag import Tag, AssetTag

router = APIRouter(tags=["review"])

# 低置信度审核阈值（配置化，默认 0.6）
REVIEW_THRESHOLD = settings.AI_TAG_REVIEW_THRESHOLD


@router.get("/assets")
def list_review_assets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    待审核素材列表：
    - 含有 pending 标签（AI 新建待确认）
    - 或含有低置信度（< AI_TAG_REVIEW_THRESHOLD，默认 0.6）标签
    """
    # 找出所有 pending 标签
    pending_tags = db.query(Tag).filter(Tag.status == "pending").all()
    pending_tag_ids = [t.id for t in pending_tags]

    # 找出含 pending 标签或低置信度关联的素材
    query = db.query(Asset).filter(Asset.deleted_at.is_(None))

    # pending 标签 OR 低置信度，两者取并集（之前只查其一，会漏）
    from sqlalchemy import or_

    conditions = [AssetTag.confidence < REVIEW_THRESHOLD]
    if pending_tag_ids:
        conditions.append(AssetTag.tag_id.in_(pending_tag_ids))
    subq = db.query(AssetTag.asset_id).filter(or_(*conditions)).distinct()
    query = query.filter(Asset.id.in_(subq))

    total = query.count()
    assets = query.order_by(Asset.created_at.desc()).offset((page - 1) * size).limit(size).all()

    # 加载标签
    result = []
    for asset in assets:
        tags = db.query(Tag, AssetTag.confidence, AssetTag.source).join(
            AssetTag, AssetTag.tag_id == Tag.id
        ).filter(AssetTag.asset_id == asset.id).all()

        review_tags = []
        for tag, confidence, source in tags:
            needs_review = tag.status == "pending" or (confidence is not None and confidence < REVIEW_THRESHOLD)
            review_tags.append({
                "id": str(tag.id),
                "name": tag.name,
                "category": tag.category,
                "status": tag.status,
                "confidence": confidence,
                "source": source,
                "needs_review": bool(needs_review),
            })

        result.append({
            "id": str(asset.id),
            "title": asset.title,
            "file_name": asset.file_name,
            "asset_type": asset.asset_type,
            "obs_key": asset.obs_key,
            "created_at": asset.created_at.isoformat(),
            "tags": review_tags,
            "pending_count": sum(1 for t in review_tags if t["needs_review"]),
        })

    return ok({"items": result, "total": total, "page": page, "size": size})


@router.post("/tags/{tag_id}/confirm")
def confirm_tag(tag_id: uuid.UUID, db: Session = Depends(get_db)):
    """确认标签（pending → active，低置信度 → 1.0）"""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")

    tag.status = "active"
    # 该标签所有低置信度关联提升到 1.0
    db.query(AssetTag).filter(
        AssetTag.tag_id == tag_id,
        AssetTag.confidence < REVIEW_THRESHOLD,
    ).update({"confidence": 1.0}, synchronize_session=False)

    db.commit()
    return ok({"ok": True})


@router.post("/tags/{tag_id}/reject")
def reject_tag(tag_id: uuid.UUID, db: Session = Depends(get_db)):
    """拒绝标签（删除该标签及其所有关联）"""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")

    db.query(AssetTag).filter(AssetTag.tag_id == tag_id).delete(synchronize_session=False)
    db.delete(tag)
    db.commit()
    return ok({"ok": True})
