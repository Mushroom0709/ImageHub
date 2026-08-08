"""批量导入 API：接收文件夹/多文件上传"""
import os
import uuid
import tempfile
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.models.asset import Asset
from app.services.obs_service import obs_service

router = APIRouter(tags=["import"])

# 支持的图片格式
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tiff", ".bmp", ".arw", ".raw", ".cr2", ".nef", ".dng"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

SUPPORTED_EXTS = IMAGE_EXTS | VIDEO_EXTS


@router.post("/upload")
async def import_upload(
    files: list[UploadFile] = File(...),
    top_category_id: str | None = Form(None, description="归属项目ID"),
    db: Session = Depends(get_db),
):
    """
    批量导入上传（多文件）
    - 保存原文件到 OBS
    - 生成缩略图 / ARW 预览
    - 读 EXIF
    - AI 打标
    返回导入结果
    """
    today = datetime.utcnow().strftime("%Y/%m/%d")
    upload_id = str(uuid.uuid4())[:8]
    results = []

    for i, file in enumerate(files):
        original_name = file.filename or f"file_{i}"
        ext = os.path.splitext(original_name)[1].lower()

        if ext not in SUPPORTED_EXTS:
            results.append({"file": original_name, "status": "skipped", "reason": f"不支持的格式 {ext}"})
            continue

        # 判断类型
        asset_type = "video" if ext in VIDEO_EXTS else "image"

        try:
            # 读取文件内容
            content = await file.read()

            # 保存到本地临时文件（物理盘）
            from app.core.config import settings
            tmp_path = os.path.join(settings.UPLOAD_TMP_DIR, f"{upload_id}_{i}{ext}")
            with open(tmp_path, "wb") as f:
                f.write(content)

            # 上传 OBS
            obs_key = f"raw/{'video' if asset_type == 'video' else 'image'}/{today}/{upload_id}_{i}{ext}"
            ok_flag = obs_service.upload_file(obs_key, tmp_path)
            if not ok_flag:
                results.append({"file": original_name, "status": "failed", "reason": "OBS 上传失败"})
                continue

            # 创建素材
            asset = Asset(
                title=original_name,
                file_name=original_name,
                file_size=len(content),
                source_type="upload",
                asset_type=asset_type,
                obs_bucket=obs_service.bucket,
                obs_key=obs_key,
                top_category_id=top_category_id,
            )
            db.add(asset)
            db.flush()

            # 处理：缩略图 + EXIF + AI 打标
            try:
                if asset_type == "image":
                    from app.services.thumbnail_service import thumbnail_service
                    w, h = thumbnail_service.generate(obs_key)
                    asset.width = w
                    asset.height = h

                    # ARW 特殊处理：提取内嵌预览
                    if ext == ".arw":
                        _extract_arw_preview(obs_key, tmp_path, today, upload_id, i)

                    # EXIF
                    from app.services.exif_service import exif_service
                    exif_data = exif_service.read(obs_key)
                    if exif_data:
                        asset.exif = exif_data
                elif asset_type == "video":
                    from app.services.video_service import video_service
                    w, h = video_service.process(obs_key)
                    asset.width = w
                    asset.height = h
            except Exception as e:
                print(f"[导入] 处理异常: {e}")

            db.commit()
            results.append({"file": original_name, "status": "done", "asset_id": str(asset.id)})
        except Exception as e:
            db.rollback()
            results.append({"file": original_name, "status": "failed", "reason": str(e)})
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # 汇总
    done = sum(1 for r in results if r["status"] == "done")
    failed = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] == "skipped")

    return ok({
        "total": len(results),
        "done": done,
        "failed": failed,
        "skipped": skipped,
        "results": results,
    })


def _extract_arw_preview(obs_key: str, local_path: str, today: str, upload_id: str, index: int):
    """提取 ARW 内嵌预览 JPG（dcraw -e）并上传为可浏览版本"""
    import subprocess

    from app.core.config import settings

    tmp_dir = settings.UPLOAD_TMP_DIR
    preview_path = os.path.join(tmp_dir, f"{upload_id}_{index}_preview.jpg")
    try:
        # dcraw -e 提取内嵌预览（输出到 cwd）
        result = subprocess.run(
            ["dcraw", "-e", local_path],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=tmp_dir,
        )
        # dcraw 输出与输入同名的 .preview.jpg 或同名 .jpg
        base = os.path.basename(local_path)
        candidates = [
            os.path.join(tmp_dir, f"{os.path.splitext(base)[0]}.preview.jpg"),
            os.path.join(tmp_dir, f"{os.path.splitext(base)[0]}.jpg"),
        ]
        found = next((c for c in candidates if os.path.exists(c)), None)
        if not found:
            return

        # 上传预览 JPG（作为 thumb_raw 的替代）
        preview_key = f"raw/image/preview/{today}/{upload_id}_{index}.jpg"
        obs_service.upload_file(preview_key, found)
        if os.path.exists(found):
            os.unlink(found)
    except FileNotFoundError:
        print("[ARW] dcraw 不可用")
    except Exception as e:
        print(f"[ARW] 提取预览失败: {e}")
    finally:
        if os.path.exists(preview_path):
            os.unlink(preview_path)
