"""OBS 服务"""
import os

from obs import ObsClient
from obs.model import CompleteMultipartUploadRequest, CompletePart

from app.core.config import settings


class ObsService:
    """OBS 对象存储服务封装"""

    def __init__(self):
        self.client = ObsClient(
            access_key_id=settings.OBS_ACCESS_KEY,
            secret_access_key=settings.OBS_SECRET_KEY,
            server=settings.OBS_ENDPOINT,
        )
        self.bucket = settings.OBS_BUCKET
        self.prefix = settings.OBS_PREFIX

    def close(self):
        self.client.close()

    def _full_key(self, key: str) -> str:
        """拼接前缀"""
        return f"{self.prefix.rstrip('/')}/{key.lstrip('/')}" if self.prefix else key

    def upload_file(self, key: str, file_path: str) -> bool:
        """上传文件"""
        full_key = self._full_key(key)
        resp = self.client.putFile(self.bucket, full_key, file_path)
        return resp.status < 300

    def download_file(self, key: str, save_path: str) -> bool:
        """下载文件"""
        full_key = self._full_key(key)
        resp = self.client.getObject(self.bucket, full_key, save_path)
        return resp.status < 300

    def delete_file(self, key: str) -> bool:
        """删除文件"""
        full_key = self._full_key(key)
        resp = self.client.deleteObject(self.bucket, full_key)
        return resp.status < 300

    def list_objects(self, prefix: str = "", max_keys: int = 100) -> list:
        """列出对象"""
        full_prefix = self._full_key(prefix)
        resp = self.client.listObjects(self.bucket, prefix=full_prefix, max_keys=max_keys)
        if resp.status >= 300:
            return []
        contents = getattr(resp.body, "contents", []) or []
        return [
            {"key": obj.key.replace(self._full_key(""), "", 1), "size": int(obj.size)}
            for obj in contents
        ]

    def generate_presigned_url(
        self,
        key: str,
        method: str = "GET",
        expires: int = 3600,
        headers: dict | None = None,
        query_params: dict | None = None,
    ) -> str:
        """生成预签名 URL

        query_params: 附加查询参数（如分片上传的 uploadId/partNumber）
        """
        full_key = self._full_key(key)
        result = self.client.createSignedUrl(
            method=method,
            bucketName=self.bucket,
            objectKey=full_key,
            expires=expires,
            headers=headers,
            queryParams=query_params,
        )
        return result["signedUrl"]

    # ---------- 分片上传（Multipart Upload） ----------

    def initiate_multipart_upload(self, key: str, content_type: str = "") -> dict:
        """初始化分片上传，返回 upload_id"""
        full_key = self._full_key(key)
        kwargs = {"contentType": content_type} if content_type else {}
        resp = self.client.initiateMultipartUpload(self.bucket, full_key, **kwargs)
        if resp.status >= 300:
            raise RuntimeError(
                f"initiateMultipartUpload 失败: {resp.errorCode} {resp.errorMessage}"
            )
        return {"upload_id": resp.body.uploadId, "obs_key": key}

    def upload_part(
        self,
        key: str,
        upload_id: str,
        part_number: int,
        data: bytes | None = None,
        file_path: str | None = None,
        part_size: int | None = None,
        offset: int = 0,
    ) -> dict:
        """上传单个分片，返回 etag。

        两种传数方式：
        - data: bytes 内存数据
        - file_path: 本地文件路径（配合 offset/part_size 分片读取）
        """
        full_key = self._full_key(key)
        if file_path:
            size = part_size or (os.path.getsize(file_path) - offset)
            resp = self.client.uploadPart(
                self.bucket, full_key,
                partNumber=part_number, uploadId=upload_id,
                object=file_path, isFile=True,
                partSize=size, offset=offset,
            )
        elif data is not None:
            resp = self.client.uploadPart(
                self.bucket, full_key,
                partNumber=part_number, uploadId=upload_id,
                content=data,
            )
        else:
            raise ValueError("upload_part 需要 data 或 file_path 之一")
        if resp.status >= 300:
            raise RuntimeError(
                f"uploadPart 失败: {resp.errorCode} {resp.errorMessage}"
            )
        return {"part_number": part_number, "etag": resp.body.etag}

    def complete_multipart_upload(self, key: str, upload_id: str, parts: list[dict]) -> str:
        """合并分片，返回最终对象 etag。

        parts: [{'part_number': 1, 'etag': '"..."'}]。
        注意：SDK 内部用 CompletePart(partNum=, etag=) 对象序列化。
        """
        full_key = self._full_key(key)
        part_objs = [
            CompletePart(partNum=p["part_number"], etag=p["etag"])
            for p in parts
        ]
        request = CompleteMultipartUploadRequest(parts=part_objs)
        resp = self.client.completeMultipartUpload(
            self.bucket, full_key, upload_id, request
        )
        if resp.status >= 300:
            raise RuntimeError(
                f"completeMultipartUpload 失败: {resp.errorCode} {resp.errorMessage}"
            )
        return resp.body.etag

    def abort_multipart_upload(self, key: str, upload_id: str) -> bool:
        """取消分片上传，清理 OBS 侧已传分片"""
        full_key = self._full_key(key)
        resp = self.client.abortMultipartUpload(self.bucket, full_key, upload_id)
        return resp.status < 300

    def list_uploaded_parts(self, key: str, upload_id: str) -> list[dict]:
        """列出已上传分片（断点续传时跳过已传部分）"""
        full_key = self._full_key(key)
        resp = self.client.listParts(self.bucket, full_key, upload_id)
        if resp.status >= 300:
            return []
        parts = getattr(resp.body, "parts", None) or []
        return [
            {
                "part_number": int(p.partNumber),
                "etag": p.etag,
                "size": int(p.size or 0),
            }
            for p in parts
        ]


# 全局单例
obs_service = ObsService()
