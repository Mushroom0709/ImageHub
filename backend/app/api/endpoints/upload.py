"""上传 API 端点"""
import asyncio
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.config import settings
from app.core.response import ok
from app.models.upload import UploadLog
from app.models.asset import Asset
from app.services.obs_service import obs_service
from app.services.progress_bus import progress_bus
from app.schemas.asset import AssetCreate

router = APIRouter(tags=["upload"])

# AI 打标全局限流信号量（防止并发打爆 Qwen 服务）
_ai_tag_semaphore = asyncio.Semaphore(settings.AI_TAG_CONCURRENCY)


class UploadFileInfo(BaseModel):
    file_name: str
    file_size: int = 0
    content_type: str = ""
    asset_type: str = "image"  # image 或 video


class CredentialsRequest(BaseModel):
    files: list[UploadFileInfo]
    top_category_id: str | None = None


class CompleteFileInfo(BaseModel):
    file_index: int
    obs_key: str
    file_name: str = ""
    file_size: int = 0
    width: int = 0
    height: int = 0


class CompleteRequest(BaseModel):
    upload_id: str
    files: list[CompleteFileInfo]
    top_category_id: str | None = None


class FromUrlRequest(BaseModel):
    url: str
    auto_tag: bool = True


@router.post("/credentials")
def get_credentials(data: CredentialsRequest):
    """生成预签名上传 URL"""
    upload_id = str(uuid.uuid4())[:8]
    credentials = []
    today = datetime.utcnow().strftime("%Y/%m/%d")

    for i, file_info in enumerate(data.files):
        ext = file_info.file_name.rsplit(".", 1)[-1] if "." in file_info.file_name else "bin"
        sub_dir = "video" if file_info.asset_type == "video" else "image"
        obs_key = f"raw/{sub_dir}/{today}/{upload_id}_{i}.{ext}"
        url = obs_service.generate_presigned_url(obs_key, method="PUT", expires=3600)
        credentials.append({
            "file_index": i,
            "upload_url": url,
            "obs_key": obs_key,
        })

    return ok({
        "upload_id": upload_id,
        "credentials": credentials,
    })


@router.post("/complete")
async def complete_upload(
    data: CompleteRequest,
    db: Session = Depends(get_db),
):
    """上传完成回调（立即返回，后台异步处理）

    用 asyncio.create_task 创建真正的协程（BackgroundTasks 不支持 async 函数）
    """
    asset_ids = []
    for file_info in data.files:
        upload_log = UploadLog(
            upload_id=data.upload_id,
            file_name=file_info.file_name,
            file_size=file_info.file_size,
            obs_key=file_info.obs_key,
            status="processing",
        )
        db.add(upload_log)
        db.flush()

        ext = file_info.file_name.rsplit(".", 1)[-1].lower() if "." in file_info.file_name else ""
        video_exts = {"mp4", "mov", "avi", "mkv", "webm"}
        is_video = ext in video_exts
        asset_type = "video" if is_video else "image"

        asset = Asset(
            title=file_info.file_name,
            file_name=file_info.file_name,
            file_size=file_info.file_size,
            width=file_info.width,
            height=file_info.height,
            source_type="upload",
            asset_type=asset_type,
            obs_bucket=obs_service.bucket,
            obs_key=file_info.obs_key,
            top_category_id=data.top_category_id,
        )
        db.add(asset)
        db.flush()
        asset_id = str(asset.id)
        asset_ids.append(asset_id)

        upload_log.asset_id = asset.id

        # 用 asyncio.create_task 创建真正的协程
        asyncio.create_task(
            _process_asset_background(
                asset_id,
                data.upload_id,
                file_info.obs_key,
                file_info.file_name,
                file_info.file_size,
                is_video,
                data.top_category_id,
            )
        )

    db.commit()
    return ok({"asset_ids": asset_ids, "async_processing": True})


async def _process_asset_background(
    asset_id: str,
    upload_id: str,
    obs_key: str,
    file_name: str,
    file_size: int,
    is_video: bool,
    top_category_id: str | None,
):
    """后台异步处理：缩略图/EXIF/AI 打标/pHash，每阶段通过 progress_bus 推送"""
    from app.core.database import SessionLocal

    # 推送初始事件
    await progress_bus.publish(asset_id, "uploaded", {"file_name": file_name, "file_size": file_size})

    db = SessionLocal()
    try:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            await progress_bus.publish(asset_id, "failed", {"error": "asset not found"})
            return
        upload_log = db.query(UploadLog).filter(
            UploadLog.upload_id == upload_id,
            UploadLog.obs_key == obs_key,
        ).first()

        if is_video:
            # 视频：抽封面 + 取分辨率（阻塞调用 → 线程池，避免卡事件循环）
            try:
                from app.services.video_service import video_service
                await progress_bus.publish(asset_id, "thumbnail", {"status": "processing"})
                result = await asyncio.to_thread(video_service.process, obs_key)
                if result:
                    w, h = result
                    asset.width = w
                    asset.height = h
                    await progress_bus.publish(asset_id, "thumbnail", {"status": "done", "width": w, "height": h})
                else:
                    await progress_bus.publish(asset_id, "thumbnail", {"status": "failed", "error": "video_process_returned_none"})
                if upload_log:
                    upload_log.status = "done"
            except Exception as e:
                await progress_bus.publish(asset_id, "thumbnail", {"status": "failed", "error": str(e)})
                if upload_log:
                    upload_log.status = "failed"
                    upload_log.error_message = f"视频处理失败: {e}"
        else:
            # 图片：缩略图（阻塞 PIL → 线程池）
            try:
                from app.services.thumbnail_service import thumbnail_service
                await progress_bus.publish(asset_id, "thumbnail", {"status": "processing"})
                w, h = await asyncio.to_thread(thumbnail_service.generate, obs_key)
                asset.width = w
                asset.height = h
                await progress_bus.publish(asset_id, "thumbnail", {"status": "done", "width": w, "height": h})
            except Exception as e:
                await progress_bus.publish(asset_id, "thumbnail", {"status": "failed", "error": str(e)})
                # 缩略图失败不阻止后续步骤

            # EXIF（阻塞下载+解析 → 线程池）
            try:
                from app.services.exif_service import exif_service
                await progress_bus.publish(asset_id, "exif", {"status": "processing"})
                exif_data = await asyncio.to_thread(exif_service.read, obs_key)
                if exif_data:
                    asset.exif = exif_data
                    _apply_info_tags(db, asset, exif_data)
                await progress_bus.publish(asset_id, "exif", {"status": "done", "has_exif": bool(exif_data)})
            except Exception as e:
                await progress_bus.publish(asset_id, "exif", {"status": "failed", "error": str(e)})

            # AI 打标（同步 httpx → 线程池 + 全局限流）
            try:
                from app.services.ai_tagging_service import ai_tagging_service
                await progress_bus.publish(asset_id, "ai_tagging", {"status": "processing"})
                image_url = obs_service.generate_presigned_url(obs_key, expires=3600)
                async with _ai_tag_semaphore:
                    tags = await asyncio.to_thread(ai_tagging_service.tag_image, image_url, file_name)
                tag_count = 0
                if tags:
                    ai_tagging_service.apply_tags(db, asset.id, tags)
                    tag_count = len(tags)
                await progress_bus.publish(asset_id, "ai_tagging", {"status": "done", "tag_count": tag_count})
                if upload_log and tag_count > 0:
                    upload_log.error_message = f"AI打标 {tag_count} 个标签"
            except Exception as e:
                await progress_bus.publish(asset_id, "ai_tagging", {"status": "failed", "error": str(e)})

        db.commit()
        await progress_bus.publish(asset_id, "done", {})
    except Exception as e:
        db.rollback()
        await progress_bus.publish(asset_id, "failed", {"error": str(e)})
    finally:
        db.close()


@router.get("/events/{asset_id}")
async def upload_events(asset_id: str, request: Request):
    """SSE 端点：订阅单个 asset 的处理进度事件

    客户端断开时（request.is_disconnected）自动退订
    """
    queue = await progress_bus.subscribe(asset_id)

    async def event_generator():
        try:
            # 推送订阅成功标记（前端可用来确认连接）
            yield {"event": "connected", "data": f'{{"asset_id": "{asset_id}"}}'}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    # 15s 无事件 → 发心跳保活（SSE 允许注释行）
                    yield {"event": "ping", "data": "{}"}
                    continue
                yield {
                    "event": event["stage"],
                    "data": f'{event["stage"]}|{event["ts"]}|{event.get("payload", {})}',
                }
                if event["stage"] in ("done", "failed"):
                    break
        finally:
            await progress_bus.unsubscribe(asset_id, queue)

    return EventSourceResponse(event_generator())


@router.post("/from-url")
def upload_from_url(data: FromUrlRequest, db: Session = Depends(get_db)):
    import httpx

    task_id = str(uuid.uuid4())[:8]
    today = datetime.utcnow().strftime("%Y/%m/%d")

    file_name = data.url.split("/")[-1].split("?")[0] or "download.jpg"
    ext = file_name.rsplit(".", 1)[-1] if "." in file_name else "jpg"
    obs_key = f"raw/image/{today}/{task_id}.{ext}"

    from app.core.config import settings
    try:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            resp = client.get(data.url)
            resp.raise_for_status()
            tmp_path = os.path.join(settings.UPLOAD_TMP_DIR, f"{task_id}.{ext}")
            with open(tmp_path, "wb") as f:
                f.write(resp.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"下载失败: {str(e)}")

    ok_flag = obs_service.upload_file(obs_key, tmp_path)
    if not ok_flag:
        raise HTTPException(status_code=500, detail="OBS 上传失败")

    asset = Asset(
        title=file_name,
        file_name=file_name,
        file_size=len(open(tmp_path, "rb").read()),
        source_type="url",
        asset_type="image",
        obs_bucket=obs_service.bucket,
        obs_key=obs_key,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    return ok({"task_id": task_id, "asset_id": str(asset.id)})


def _apply_info_tags(db: Session, asset: Asset, exif: dict):
    """根据 EXIF 自动打信息类标签"""
    from app.models.tag import Tag, AssetTag

    info_tags = []

    camera = (exif.get("camera") or "").strip()
    if camera:
        info_tags.append(("相机:" + camera, "info"))

    lens = (exif.get("lens") or "").strip()
    if lens:
        info_tags.append(("镜头:" + lens, "info"))

    capture_time = exif.get("capture_time") or ""
    if len(capture_time) >= 7:
        year = capture_time[:4]
        month = capture_time[:7]
        if year.isdigit():
            info_tags.append((f"年份:{year}", "info"))
        if month[:4].isdigit() and month[5:7].isdigit():
            info_tags.append((f"月份:{month}", "info"))

    focal = (exif.get("focal_length") or "").strip()
    if focal:
        try:
            mm = float(focal.replace("mm", "").strip())
            if mm < 24:
                info_tags.append(("焦段:广角", "info"))
            elif mm <= 50:
                info_tags.append(("焦段:标准", "info"))
            elif mm <= 135:
                info_tags.append(("焦段:中长焦", "info"))
            else:
                info_tags.append(("焦段:长焦", "info"))
        except ValueError:
            pass

    for name, category in info_tags:
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            from sqlalchemy.exc import IntegrityError
            import time
            for attempt in range(3):
                try:
                    tag = Tag(name=name, category=category, status="pending")
                    db.add(tag)
                    db.flush()
                    break
                except IntegrityError:
                    db.rollback()
                    tag = db.query(Tag).filter(Tag.name == name).first()
                    if tag:
                        break
                    if attempt < 2:
                        time.sleep(0.05 * (attempt + 1))
            if not tag:
                continue
        existing = db.query(AssetTag).filter(
            AssetTag.asset_id == asset.id,
            AssetTag.tag_id == tag.id,
        ).first()
        if not existing:
            from sqlalchemy.exc import IntegrityError as IE2
            try:
                db.add(AssetTag(asset_id=asset.id, tag_id=tag.id, confidence=1.0, source="ai"))
                db.flush()
            except IE2:
                db.rollback()