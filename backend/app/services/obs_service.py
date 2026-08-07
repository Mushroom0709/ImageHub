"""OBS 服务"""
from obs import ObsClient
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

    def generate_presigned_url(self, key: str, method: str = "GET", expires: int = 3600, headers: dict | None = None) -> str:
        """生成预签名 URL"""
        full_key = self._full_key(key)
        result = self.client.createSignedUrl(
            method=method,
            bucketName=self.bucket,
            objectKey=full_key,
            expires=expires,
            headers=headers,
        )
        return result["signedUrl"]


# 全局单例
obs_service = ObsService()
