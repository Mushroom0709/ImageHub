"""标签 API 端点"""
import uuid
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.models.tag import Tag, AssetTag
from app.schemas.tag import TagCreate, TagUpdate, TagMergeRequest

router = APIRouter(tags=["tags"])


def _to_dict(tag: Tag, asset_count: int = 0) -> dict:
    return {
        "id": str(tag.id),
        "name": tag.name,
        "category": tag.category,
        "parent_id": str(tag.parent_id) if tag.parent_id else None,
        "alias": tag.alias or [],
        "status": tag.status,
        "sort_order": tag.sort_order,
        "asset_count": asset_count,
    }


@router.get("/tree")
def get_tag_tree(category: str | None = None, db: Session = Depends(get_db)):
    """标签分类树"""
    query = db.query(Tag).filter(Tag.status == "active")
    if category:
        query = query.filter(Tag.category == category)
    tags = query.order_by(Tag.category, Tag.sort_order, Tag.name).all()

    # 统计每个标签的素材数
    counts = dict(
        db.query(AssetTag.tag_id, func.count(AssetTag.id))
        .group_by(AssetTag.tag_id)
        .all()
    )

    # 构建树
    by_parent: dict = {}
    for tag in tags:
        parent_key = str(tag.parent_id) if tag.parent_id else "root"
        by_parent.setdefault(parent_key, []).append(_to_dict(tag, counts.get(tag.id, 0)))

    # 按分类组织
    result = {}
    for tag in tags:
        if tag.parent_id is None:
            cat = tag.category
            result.setdefault(cat, []).append(tag.id)

    # 组装树结构
    def build_children(parent_id: str) -> list:
        children = by_parent.get(parent_id, [])
        for child in children:
            child["children"] = build_children(child["id"])
        return children

    # 按分类返回
    categories = {}
    for tag in tags:
        if tag.parent_id is None:
            node = _to_dict(tag, counts.get(tag.id, 0))
            node["children"] = build_children(node["id"])
            categories.setdefault(tag.category, []).append(node)

    return ok(categories)


@router.get("/search")
def search_tags(q: str = Query("", min_length=0), category: str | None = None, limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    """标签搜索联想"""
    query = db.query(Tag).filter(Tag.status == "active")
    if category:
        query = query.filter(Tag.category == category)
    if q:
        # 名称或别名匹配
        query = query.filter(Tag.name.ilike(f"%{q}%"))
    tags = query.order_by(Tag.sort_order).limit(limit).all()

    counts = dict(
        db.query(AssetTag.tag_id, func.count(AssetTag.id))
        .group_by(AssetTag.tag_id)
        .all()
    )
    return ok([_to_dict(t, counts.get(t.id, 0)) for t in tags])


@router.get("/{tag_id}")
def get_tag(tag_id: uuid.UUID, db: Session = Depends(get_db)):
    """标签详情"""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    count = db.query(AssetTag).filter(AssetTag.tag_id == tag_id).count()
    return ok(_to_dict(tag, count))


@router.post("")
def create_tag(data: TagCreate, db: Session = Depends(get_db)):
    """创建标签"""
    # 查重
    existing = db.query(Tag).filter(Tag.name == data.name, Tag.category == data.category).first()
    if existing:
        raise HTTPException(status_code=409, detail="标签已存在")

    tag = Tag(
        name=data.name,
        category=data.category,
        parent_id=data.parent_id,
        alias=data.alias or [],
        sort_order=data.sort_order,
        status="active",
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return ok(_to_dict(tag))


@router.put("/{tag_id}")
def update_tag(tag_id: uuid.UUID, data: TagUpdate, db: Session = Depends(get_db)):
    """修改标签"""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tag, key, value)
    db.commit()
    db.refresh(tag)
    return ok(_to_dict(tag))


@router.delete("/{tag_id}")
def delete_tag(tag_id: uuid.UUID, db: Session = Depends(get_db)):
    """删除标签（级联删除关联）"""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")

    # 删除所有关联
    affected = db.query(AssetTag).filter(AssetTag.tag_id == tag_id).delete(synchronize_session=False)
    # 删除子标签（简单起见只删一层）
    children = db.query(Tag).filter(Tag.parent_id == tag_id).all()
    for child in children:
        db.query(AssetTag).filter(AssetTag.tag_id == child.id).delete(synchronize_session=False)
        db.delete(child)
    db.delete(tag)
    db.commit()
    return ok({"ok": True, "affected_count": affected})


@router.post("/{tag_id}/merge")
def merge_tag(tag_id: uuid.UUID, data: TagMergeRequest, db: Session = Depends(get_db)):
    """合并标签：把当前标签合并到目标标签"""
    source = db.query(Tag).filter(Tag.id == tag_id).first()
    target = db.query(Tag).filter(Tag.id == data.target_tag_id).first()
    if not source or not target:
        raise HTTPException(status_code=404, detail="标签不存在")
    if source.id == target.id:
        raise HTTPException(status_code=400, detail="不能合并到自身")

    # 把 source 的所有关联转移到 target（去重）
    merged = 0
    source_links = db.query(AssetTag).filter(AssetTag.tag_id == source.id).all()
    for link in source_links:
        existing = db.query(AssetTag).filter(
            AssetTag.asset_id == link.asset_id,
            AssetTag.tag_id == target.id,
        ).first()
        if not existing:
            link.tag_id = target.id
            merged += 1
        else:
            db.delete(link)
            merged += 1

    # 子标签转移
    db.query(Tag).filter(Tag.parent_id == source.id).update({"parent_id": target.id})

    # 删除 source
    db.delete(source)
    db.commit()
    return ok({"ok": True, "merged_count": merged})
