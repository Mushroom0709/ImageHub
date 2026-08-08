"""素材 API 端点"""
import uuid
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.schemas.asset import Asset, AssetCreate, AssetUpdate, AssetListResponse
from app.schemas.tag import BatchTagRequest
from app.services.asset_service import AssetService

router = APIRouter(tags=["assets"])


@router.get("", response_model_exclude_none=True)
def list_assets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sort: str = Query("newest", pattern="^(newest|oldest|quality|likes)$"),
    tag_ids: str = Query("", description="逗号分隔的 tag ID 列表"),
    keyword: str = "",
    source_type: str | None = None,
    star_level: int | None = Query(None, ge=0, le=5, description="星级 0-5"),
    flag_level: int | None = Query(None, ge=0, le=5),
    trashed: bool = False,
    top_category_id: uuid.UUID | None = Query(None, description="顶层分类（项目）ID"),
    db: Session = Depends(get_db),
):
    """素材列表"""
    svc = AssetService(db)
    tag_id_list = []
    if tag_ids:
        try:
            tag_id_list = [uuid.UUID(t.strip()) for t in tag_ids.split(",") if t.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="tag_ids 格式错误")

    items, total = svc.list_assets(
        page=page, size=size, sort=sort,
        tag_ids=tag_id_list if tag_id_list else None,
        keyword=keyword, source_type=source_type,
        star_level=star_level, flag_level=flag_level, trashed=trashed,
        top_category_id=top_category_id,
    )
    return ok({
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    })


@router.post("")
def create_asset(data: AssetCreate, db: Session = Depends(get_db)):
    """创建素材"""
    svc = AssetService(db)
    asset = svc.create_asset(data)
    return ok(asset)


@router.post("/batch-delete")
def batch_delete(asset_ids: list[uuid.UUID], db: Session = Depends(get_db)):
    """批量删除"""
    svc = AssetService(db)
    count = svc.batch_delete(asset_ids)
    return ok({"ok": True, "count": count})


@router.post("/batch-recover")
def batch_recover(asset_ids: list[uuid.UUID], db: Session = Depends(get_db)):
    """批量恢复"""
    svc = AssetService(db)
    count = svc.batch_recover(asset_ids)
    return ok({"ok": True, "count": count})


@router.post("/batch-tag")
def batch_tag(data: BatchTagRequest, db: Session = Depends(get_db)):
    """批量打标"""
    svc = AssetService(db)
    count = svc.batch_tag(data.asset_ids, data.add_tag_ids, data.remove_tag_ids)
    return ok({"ok": True, "affected_count": count})


@router.get("/{asset_id}")
def get_asset(asset_id: uuid.UUID, db: Session = Depends(get_db)):
    """素材详情"""
    svc = AssetService(db)
    asset = svc.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="素材不存在")
    return ok(asset)


@router.put("/{asset_id}")
def update_asset(asset_id: uuid.UUID, data: AssetUpdate, db: Session = Depends(get_db)):
    """更新素材"""
    svc = AssetService(db)
    asset = svc.update_asset(asset_id, data)
    if not asset:
        raise HTTPException(status_code=404, detail="素材不存在")
    return ok(asset)


@router.delete("/{asset_id}")
def delete_asset(asset_id: uuid.UUID, db: Session = Depends(get_db)):
    """删除素材（软删）"""
    svc = AssetService(db)
    ok_flag = svc.delete_asset(asset_id)
    if not ok_flag:
        raise HTTPException(status_code=404, detail="素材不存在")
    return ok({"ok": True})


@router.get("/{asset_id}/thumb")
def get_thumb(asset_id: uuid.UUID, size: str = Query("medium", pattern="^(small|medium|raw)$"), db: Session = Depends(get_db)):
    """获取缩略图（重定向到预签名 URL）"""
    from fastapi.responses import RedirectResponse
    from app.services.obs_service import obs_service

    svc = AssetService(db)
    asset = svc.get_asset(asset_id)
    if not asset or not asset.obs_key:
        raise HTTPException(status_code=404, detail="素材不存在")

    obs_key = asset.obs_key
    if size == "small":
        obs_key = obs_key.replace("raw/", "thumb/small/") if "raw/" in obs_key else f"thumb/small/{obs_key}"
    elif size == "medium":
        obs_key = obs_key.replace("raw/", "thumb/medium/") if "raw/" in obs_key else f"thumb/medium/{obs_key}"

    url = obs_service.generate_presigned_url(obs_key, expires=3600)
    return RedirectResponse(url=url)


@router.get("/{asset_id}/similar")
def get_similar(asset_id: uuid.UUID, limit: int = Query(12, ge=1, le=100), db: Session = Depends(get_db)):
    """相似素材"""
    svc = AssetService(db)
    items = svc.get_similar(asset_id, limit)
    return ok({"items": items})


@router.get("/{asset_id}/exif")
def get_exif(asset_id: uuid.UUID, db: Session = Depends(get_db)):
    """EXIF 详情"""
    svc = AssetService(db)
    exif = svc.get_exif(asset_id)
    if exif is None:
        raise HTTPException(status_code=404, detail="素材不存在")
    return ok(exif)


# ===== 标签关联 =====

@router.post("/{asset_id}/tags")
def add_tags(asset_id: uuid.UUID, tag_ids: list[uuid.UUID], db: Session = Depends(get_db)):
    """给素材打标签"""
    svc = AssetService(db)
    tags = svc.add_tags(asset_id, tag_ids)
    return ok({"ok": True, "tags": tags})


@router.delete("/{asset_id}/tags/{tag_id}")
def remove_tag(asset_id: uuid.UUID, tag_id: uuid.UUID, db: Session = Depends(get_db)):
    """移除一个标签"""
    svc = AssetService(db)
    ok_flag = svc.remove_tag(asset_id, tag_id)
    if not ok_flag:
        raise HTTPException(status_code=404, detail="关联不存在")
    return ok({"ok": True})


@router.post("/batch-tag")
def batch_tag(data: BatchTagRequest, db: Session = Depends(get_db)):
    """批量打标"""
    svc = AssetService(db)
    count = svc.batch_tag(data.asset_ids, data.add_tag_ids, data.remove_tag_ids)
    return ok({"ok": True, "affected_count": count})
