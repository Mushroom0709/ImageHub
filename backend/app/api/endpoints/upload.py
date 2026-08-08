"""上传 API 端点"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.models.upload import UploadLog
from app.models.asset import Asset
from app.services.obs_service import obs_service
from app.schemas.asset import AssetCreate

router = APIRouter(tags=["upload"])


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
        # 生成 OBS key
        ext = file_info.file_name.rsplit(".", 1)[-1] if "." in file_info.file_name else "bin"
        sub_dir = "video" if file_info.asset_type == "video" else "image"
        obs_key = f"raw/{sub_dir}/{today}/{upload_id}_{i}.{ext}"
        # 生成预签名 PUT URL
        # 注意：OBS V2 签名会把 Content-Type 签进 canonical string（默认空字符串）
        # 前端上传时不能带 Content-Type 头，否则签名校验失败（403）
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
def complete_upload(data: CompleteRequest, db: Session = Depends(get_db)):
    """上传完成回调"""
    asset_ids = []
    for file_info in data.files:
        # 登记上传日志
        upload_log = UploadLog(
            upload_id=data.upload_id,
            file_name=file_info.file_name,
            file_size=file_info.file_size,
            obs_key=file_info.obs_key,
            status="processing",
        )
        db.add(upload_log)
        db.flush()

        # 判断素材类型
        ext = file_info.file_name.rsplit(".", 1)[-1].lower() if "." in file_info.file_name else ""
        video_exts = {"mp4", "mov", "avi", "mkv", "webm"}
        is_video = ext in video_exts
        is_arw = ext in {"arw", "raw", "cr2", "nef", "dng"}
        asset_type = "video" if is_video else "image"

        # 创建素材
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
        asset_ids.append(str(asset.id))

        if is_video:
            # 视频处理：抽封面 + 取分辨率
            try:
                from app.services.video_service import video_service
                w, h = video_service.process(file_info.obs_key)
                asset.width = w
                asset.height = h
                upload_log.status = "done"
            except Exception as e:
                upload_log.status = "failed"
                upload_log.error_message = f"视频处理失败: {e}"
        else:
            # 图片：生成缩略图
            try:
                from app.services.thumbnail_service import thumbnail_service
                w, h = thumbnail_service.generate(file_info.obs_key)
                asset.width = w
                asset.height = h
                upload_log.status = "done"
            except Exception as e:
                upload_log.status = "failed"
                upload_log.error_message = str(e)

            # ARW 特殊处理：预留（后续接入 dcraw 提取预览，需从 OBS 下载到本地）
            # if is_arw:
            #     _extract_arw_preview(file_info.obs_key, data.upload_id)

            # EXIF 读取
            try:
                from app.services.exif_service import exif_service
                exif_data = exif_service.read(file_info.obs_key)
                if exif_data:
                    asset.exif = exif_data
                    # 自动打信息类标签（相机/镜头/焦段）
                    _apply_info_tags(db, asset, exif_data)
            except Exception as e:
                print(f"[上传] EXIF 读取异常: {e}")

            # AI 自动打标
            try:
                from app.services.ai_tagging_service import ai_tagging_service
                image_url = obs_service.generate_presigned_url(file_info.obs_key, expires=3600)
                tags = ai_tagging_service.tag_image(image_url, description=file_info.file_name)
                if tags:
                    ai_tagging_service.apply_tags(db, asset.id, tags)
                    upload_log.error_message = f"AI打标 {len(tags)} 个标签"
            except Exception as e:
                print(f"[上传] AI 打标异常: {e}")

        upload_log.asset_id = asset.id
        upload_log.finished_at = datetime.utcnow()

    db.commit()
    return ok({"asset_ids": asset_ids})


@router.post("/from-url")
def upload_from_url(data: FromUrlRequest, db: Session = Depends(get_db)):
    import httpx

    task_id = str(uuid.uuid4())[:8]
    today = datetime.utcnow().strftime("%Y/%m/%d")

    # 解析文件名
    file_name = data.url.split("/")[-1].split("?")[0] or "download.jpg"
    ext = file_name.rsplit(".", 1)[-1] if "." in file_name else "jpg"
    obs_key = f"raw/image/{today}/{task_id}.{ext}"

    # 下载到临时文件
    try:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            resp = client.get(data.url)
            resp.raise_for_status()
            tmp_path = f"/tmp/{task_id}.{ext}"
            with open(tmp_path, "wb") as f:
                f.write(resp.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"下载失败: {str(e)}")

    # 上传到 OBS
    ok_flag = obs_service.upload_file(obs_key, tmp_path)
    if not ok_flag:
        raise HTTPException(status_code=500, detail="上传 OBS 失败")

    # 登记素材
    asset = Asset(
        title=file_name,
        file_name=file_name,
        file_size=len(open(tmp_path, "rb").read()),
        source_type="upload",
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

    # 相机型号
    camera = (exif.get("camera") or "").strip()
    if camera:
        info_tags.append(("相机:" + camera, "info"))

    # 镜头型号
    lens = (exif.get("lens") or "").strip()
    if lens:
        info_tags.append(("镜头:" + lens, "info"))

    # 拍摄时间（年份/月份）
    capture_time = exif.get("capture_time") or ""
    if len(capture_time) >= 7:
        year = capture_time[:4]
        month = capture_time[:7]
        if year.isdigit():
            info_tags.append((f"年份:{year}", "info"))
        if month[:4].isdigit() and month[5:7].isdigit():
            info_tags.append((f"月份:{month}", "info"))

    # 焦段
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
            # 重试 3 次（并发场景下其他事务可能尚未 commit）
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
