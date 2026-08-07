"""采集 API 端点（小红书/抖音）"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.models.collect import CollectTask
from app.models.asset import Asset
from app.services.tikhub_service import tikhub_service
from app.services.obs_service import obs_service

router = APIRouter(tags=["collect"])


class CollectRequest(BaseModel):
    url: str
    auto_tag: bool = True


@router.post("/xiaohongshu")
def collect_xiaohongshu(data: CollectRequest, db: Session = Depends(get_db)):
    """小红书单条链接采集"""
    task = CollectTask(
        platform="xiaohongshu",
        url=data.url,
        auto_tag=data.auto_tag,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        note = tikhub_service.fetch_xhs_note(data.url)
        if not note or not note.get("images"):
            task.status = "failed"
            task.error_message = "笔记抓取失败或没有图片"
            task.finished_at = datetime.utcnow()
            db.commit()
            return ok({"task_id": str(task.id), "status": "failed", "message": task.error_message})

        task.total_count = len(note["images"])
        db.commit()

        asset_ids = []
        for i, img_url in enumerate(note["images"]):
            try:
                # 下载图片
                local_path = tikhub_service.download_file(img_url)
                if not local_path:
                    task.fail_count += 1
                    continue

                # 上传 OBS
                today = datetime.utcnow().strftime("%Y/%m/%d")
                obs_key = f"raw/image/collect/{today}/{task.id}_{i}.jpg"
                ok_flag = obs_service.upload_file(obs_key, local_path)
                os.unlink(local_path) if os.path.exists(local_path) else None
                if not ok_flag:
                    task.fail_count += 1
                    continue

                # 创建素材
                asset = Asset(
                    title=note.get("title", "") or f"小红书笔记 {i+1}",
                    description=note.get("desc", ""),
                    source_type="xiaohongshu",
                    source_id=note.get("source_id", ""),
                    source_url=data.url,
                    author_name=note.get("author", ""),
                    asset_type="image",
                    obs_bucket=obs_service.bucket,
                    obs_key=obs_key,
                    file_name=f"{note.get('title', 'note')}_{i+1}.jpg",
                )
                db.add(asset)
                db.flush()

                # 打平台原始话题标签
                from app.models.tag import Tag, AssetTag
                for tag_name in note.get("tags", [])[:5]:
                    tag = db.query(Tag).filter(Tag.name == tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name, category="other", status="pending")
                        db.add(tag)
                        db.flush()
                    db.add(AssetTag(asset_id=asset.id, tag_id=tag.id, confidence=1.0, source="platform"))

                asset_ids.append(str(asset.id))
                task.success_count += 1
            except Exception as e:
                task.fail_count += 1
                print(f"[采集] 图片 {i} 处理失败: {e}")

        task.status = "done"
        task.finished_at = datetime.utcnow()
        db.commit()

        return ok({
            "task_id": str(task.id),
            "status": "done",
            "success_count": task.success_count,
            "fail_count": task.fail_count,
            "asset_ids": asset_ids,
        })
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.finished_at = datetime.utcnow()
        db.commit()
        return ok({"task_id": str(task.id), "status": "failed", "message": str(e)})


@router.post("/douyin")
def collect_douyin(data: CollectRequest, db: Session = Depends(get_db)):
    """抖音单条链接采集"""
    task = CollectTask(
        platform="douyin",
        url=data.url,
        auto_tag=data.auto_tag,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        video = tikhub_service.fetch_douyin_video(data.url)
        if not video or not video.get("video_url"):
            task.status = "failed"
            task.error_message = "视频抓取失败"
            task.finished_at = datetime.utcnow()
            db.commit()
            return ok({"task_id": str(task.id), "status": "failed", "message": task.error_message})

        # 下载视频
        local_path = tikhub_service.download_file(video["video_url"])
        if not local_path:
            task.status = "failed"
            task.error_message = "视频下载失败"
            task.finished_at = datetime.utcnow()
            db.commit()
            return ok({"task_id": str(task.id), "status": "failed", "message": task.error_message})

        # 上传 OBS
        today = datetime.utcnow().strftime("%Y/%m/%d")
        ext = local_path.rsplit(".", 1)[-1] if "." in local_path else "mp4"
        obs_key = f"raw/video/{today}/{task.id}.{ext}"
        ok_flag = obs_service.upload_file(obs_key, local_path)
        os.unlink(local_path) if os.path.exists(local_path) else None
        if not ok_flag:
            task.status = "failed"
            task.error_message = "视频上传 OBS 失败"
            task.finished_at = datetime.utcnow()
            db.commit()
            return ok({"task_id": str(task.id), "status": "failed", "message": task.error_message})

        # 创建素材
        asset = Asset(
            title=video.get("title", "抖音视频"),
            description=video.get("desc", ""),
            source_type="douyin",
            source_id=video.get("source_id", ""),
            source_url=data.url,
            author_name=video.get("author", ""),
            asset_type="video",
            obs_bucket=obs_service.bucket,
            obs_key=obs_key,
            file_name=f"douyin_{task.id}.{ext}",
        )
        db.add(asset)
        db.flush()

        # 抽封面帧 + 生成缩略图
        try:
            from app.services.video_service import video_service
            w, h = video_service.process(obs_key)
            if w and h:
                asset.width = w
                asset.height = h
        except Exception as e:
            print(f"[采集] 视频封面处理失败: {e}")

        db.commit()
        db.refresh(asset)

        task.success_count = 1
        task.status = "done"
        task.finished_at = datetime.utcnow()
        db.commit()

        return ok({
            "task_id": str(task.id),
            "status": "done",
            "asset_ids": [str(asset.id)],
        })
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.finished_at = datetime.utcnow()
        db.commit()
        return ok({"task_id": str(task.id), "status": "failed", "message": str(e)})


@router.get("/tasks")
def list_tasks(page: int = 1, size: int = 20, db: Session = Depends(get_db)):
    """采集任务列表"""
    tasks = db.query(CollectTask).order_by(CollectTask.created_at.desc()).offset((page - 1) * size).limit(size).all()
    total = db.query(CollectTask).count()
    return ok({
        "items": [
            {
                "id": str(t.id),
                "platform": t.platform,
                "url": t.url,
                "status": t.status,
                "total_count": t.total_count,
                "success_count": t.success_count,
                "skip_count": t.skip_count,
                "fail_count": t.fail_count,
                "error_message": t.error_message,
                "created_at": t.created_at.isoformat(),
            }
            for t in tasks
        ],
        "total": total,
        "page": page,
        "size": size,
    })


@router.get("/tasks/{task_id}")
def get_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    """采集任务详情"""
    task = db.query(CollectTask).filter(CollectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return ok({
        "id": str(task.id),
        "platform": task.platform,
        "url": task.url,
        "status": task.status,
        "total_count": task.total_count,
        "success_count": task.success_count,
        "skip_count": task.skip_count,
        "fail_count": task.fail_count,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    })
