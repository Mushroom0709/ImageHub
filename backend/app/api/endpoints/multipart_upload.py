"""分片上传 API（断点续传支持）"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.response import ok
from app.models.multipart import MultipartUpload
from app.services.obs_service import obs_service

router = APIRouter(tags=["upload-multipart"])


class InitRequest(BaseModel):
    batch_id: str = ""  # 前端生成的文件级 ID（同一文件断点续传复用）
    file_name: str
    file_size: int
    content_type: str = ""
    asset_type: str = "image"  # image/video
    top_category_id: str | None = None


class PartCompleteRequest(BaseModel):
    batch_id: str
    part_number: int
    etag: str = ""  # 可选：前端从 XHR getResponseHeader('ETag') 拿；空时后端从 OBS listParts 取
    size: int = 0


class PartUrlRequest(BaseModel):
    batch_id: str
    part_number: int


class BatchRequest(BaseModel):
    batch_id: str


@router.post("/multipart/init")
def init_multipart_upload(data: InitRequest, db: Session = Depends(get_db)):
    """初始化分片上传：OBS init + 生成各分片预签名 URL + 落库"""
    if not data.batch_id:
        data.batch_id = str(uuid.uuid4())[:8]

    # 已有会话（断点续传场景，前端重新 init 时直接复用）
    existing = (
        db.query(MultipartUpload)
        .filter(MultipartUpload.batch_id == data.batch_id)
        .first()
    )
    if existing and existing.status == "uploading":
        # 续传：生成所有分片 URL（前端按需用 part-url 重签也可）
        part_urls = []
        for n in range(1, existing.total_parts + 1):
            url = obs_service.generate_presigned_url(
                existing.obs_key,
                method="PUT",
                expires=86400,
                query_params={"uploadId": existing.obs_upload_id, "partNumber": n},
            )
            part_urls.append({"part_number": n, "url": url})
        return ok(_session_payload(existing, part_urls=part_urls))

    # OBS key：raw/{image|video}/YYYY/MM/DD/{batch_id}.{ext}
    ext = data.file_name.rsplit(".", 1)[-1].lower() if "." in data.file_name else "bin"
    sub_dir = "video" if data.asset_type == "video" else "image"
    today = datetime.utcnow().strftime("%Y/%m/%d")
    obs_key = f"raw/{sub_dir}/{today}/{data.batch_id}.{ext}"

    # 分片参数
    part_size = settings.UPLOAD_CHUNK_SIZE  # 默认 8MB（>5MB 满足 OBS 规则）
    total_parts = max(1, (data.file_size + part_size - 1) // part_size)

    # OBS init
    init = obs_service.initiate_multipart_upload(obs_key, content_type=data.content_type)
    obs_upload_id = init["upload_id"]

    # 各分片预签名 PUT URL（24h 有效）
    part_urls = []
    for n in range(1, total_parts + 1):
        url = obs_service.generate_presigned_url(
            obs_key,
            method="PUT",
            expires=86400,
            query_params={"uploadId": obs_upload_id, "partNumber": n},
        )
        part_urls.append({"part_number": n, "url": url})

    # 落库
    record = MultipartUpload(
        batch_id=data.batch_id,
        obs_upload_id=obs_upload_id,
        obs_key=obs_key,
        file_name=data.file_name,
        file_size=data.file_size,
        content_type=data.content_type,
        asset_type=data.asset_type,
        total_parts=total_parts,
        part_size=part_size,
        uploaded_parts=[],
        status="uploading",
        top_category_id=data.top_category_id,
    )
    db.add(record)
    db.commit()

    return ok(_session_payload(record, part_urls=part_urls))


@router.post("/multipart/part-url")
def get_part_url(data: PartUrlRequest, db: Session = Depends(get_db)):
    """获取单个分片的预签名 PUT URL（断点续传/URL 过期后重签）"""
    record = (
        db.query(MultipartUpload)
        .filter(MultipartUpload.batch_id == data.batch_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="上传会话不存在")
    if data.part_number < 1 or data.part_number > record.total_parts:
        raise HTTPException(status_code=400, detail="分片号越界")

    url = obs_service.generate_presigned_url(
        record.obs_key,
        method="PUT",
        expires=86400,
        query_params={
            "uploadId": record.obs_upload_id,
            "partNumber": data.part_number,
        },
    )
    return ok({"batch_id": data.batch_id, "part_number": data.part_number, "url": url})


@router.post("/multipart/part-complete")
def part_complete(data: PartCompleteRequest, db: Session = Depends(get_db)):
    """前端直传单个分片到 OBS 后回执，记录已传分片"""
    record = (
        db.query(MultipartUpload)
        .filter(MultipartUpload.batch_id == data.batch_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="上传会话不存在")

    parts = record.uploaded_parts or []
    # 去重（同分片号重传覆盖）
    parts = [p for p in parts if p.get("part_number") != data.part_number]
    parts.append(
        {"part_number": data.part_number, "etag": data.etag, "size": data.size}
    )
    record.uploaded_parts = sorted(parts, key=lambda p: p["part_number"])
    db.commit()

    return ok({"uploaded": len(record.uploaded_parts), "total": record.total_parts})


@router.post("/multipart/complete")
async def complete_multipart(data: BatchRequest, db: Session = Depends(get_db)):
    """合并分片 + 素材创建 + 缩略图/EXIF/AI（复用 upload.py 管线）

    async 因为 upload.py.complete_upload 是 async def（#54 SSE 改造）
    """
    record = (
        db.query(MultipartUpload)
        .filter(MultipartUpload.batch_id == data.batch_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="上传会话不存在")
    if record.status == "completed":
        return ok({"asset_ids": [str(record.asset_id)] if record.asset_id else []})

    parts = record.uploaded_parts or []
    if len(parts) != record.total_parts:
        raise HTTPException(
            status_code=400,
            detail=f"分片不完整: 已传 {len(parts)}/{record.total_parts}",
        )

    # 从 OBS 侧拉取权威分片列表（含 etag，断点续传/前端丢失记录都能恢复）
    # 前端回执的 uploaded_parts 仅作进度参考，etag 以 OBS 为准
    try:
        obs_parts = obs_service.list_uploaded_parts(
            record.obs_key, record.obs_upload_id
        )
        if len(obs_parts) != record.total_parts:
            raise HTTPException(
                status_code=400,
                detail=f"OBS 分片不完整: {len(obs_parts)}/{record.total_parts}",
            )
        # 按 part_number 排序，保证合并顺序
        obs_parts.sort(key=lambda p: p["part_number"])
    except HTTPException:
        raise
    except Exception as e:
        record.status = "failed"
        record.error_message = f"查询分片失败: {e}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"查询分片失败: {e}")

    # OBS 合并分片
    try:
        obs_service.complete_multipart_upload(
            record.obs_key, record.obs_upload_id, obs_parts
        )
    except Exception as e:
        record.status = "failed"
        record.error_message = f"合并失败: {e}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"合并分片失败: {e}")

    # 复用 upload.py 的素材创建 + 处理管线
    from app.api.endpoints.upload import CompleteFileInfo, CompleteRequest, complete_upload

    try:
        result = await complete_upload(
            CompleteRequest(
                upload_id=record.batch_id,
                files=[
                    CompleteFileInfo(
                        file_index=0,
                        obs_key=record.obs_key,
                        file_name=record.file_name,
                        file_size=record.file_size,
                    )
                ],
                top_category_id=str(record.top_category_id) if record.top_category_id else None,
            ),
            db=db,
        )
        asset_ids = result["data"]["asset_ids"]
    except Exception as e:
        record.status = "failed"
        record.error_message = f"素材处理失败: {e}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"素材处理失败: {e}")

    record.status = "completed"
    record.asset_id = asset_ids[0] if asset_ids else None
    record.finished_at = datetime.utcnow()
    db.commit()

    return ok({"asset_ids": asset_ids})


@router.post("/multipart/abort")
def abort_multipart(data: BatchRequest, db: Session = Depends(get_db)):
    """取消分片上传：OBS abort + 状态标记"""
    record = (
        db.query(MultipartUpload)
        .filter(MultipartUpload.batch_id == data.batch_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="上传会话不存在")

    try:
        obs_service.abort_multipart_upload(record.obs_key, record.obs_upload_id)
    except Exception as e:
        print(f"[multipart] abort 失败: {e}")

    record.status = "aborted"
    record.finished_at = datetime.utcnow()
    db.commit()
    return ok({"batch_id": data.batch_id, "status": "aborted"})


@router.get("/multipart/{batch_id}/status")
def multipart_status(batch_id: str, db: Session = Depends(get_db)):
    """查询分片上传状态（断点续传：跳过已传分片）"""
    record = (
        db.query(MultipartUpload)
        .filter(MultipartUpload.batch_id == batch_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="上传会话不存在")
    return ok(_session_payload(record))


def _session_payload(record: MultipartUpload, part_urls: list | None = None) -> dict:
    """构造会话响应体（不含 URL 时为断点查询）"""
    return {
        "batch_id": record.batch_id,
        "obs_key": record.obs_key,
        "file_name": record.file_name,
        "file_size": record.file_size,
        "asset_type": record.asset_type,
        "total_parts": record.total_parts,
        "part_size": record.part_size,
        "uploaded_parts": record.uploaded_parts or [],
        "status": record.status,
        "part_upload_urls": part_urls or [],
    }
