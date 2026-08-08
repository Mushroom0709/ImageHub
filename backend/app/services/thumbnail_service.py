"""缩略图服务"""
import io
import os
import subprocess
import tempfile
from PIL import Image, ImageOps

from app.core.config import settings
from app.services.obs_service import obs_service

SIZES = {
    "small": 300,
    "medium": 1200,
}

# RAW 格式后缀（这些 Pillow 不支持，需要 dcraw 抽取预览）
RAW_EXTS = {".arw", ".raw", ".cr2", ".nef", ".dng", ".orf", ".rw2"}


class ThumbnailService:
    """生成 3 档缩略图并上传 OBS"""

    def generate(self, obs_key: str) -> tuple[int, int]:
        """
        下载原图 → 生成 small/medium 缩略图 → 上传 OBS
        返回 (width, height)
        支持 RAW 格式：自动用 dcraw -e 抽取内嵌 JPG 预览
        """
        ext = os.path.splitext(obs_key)[1].lower()
        is_raw = ext in RAW_EXTS

        # 下载原图
        with tempfile.NamedTemporaryFile(suffix=ext or ".img", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            ok_flag = obs_service.download_file(obs_key, tmp_path)
            if not ok_flag:
                raise RuntimeError(f"下载原图失败: {obs_key}")

            if is_raw:
                # RAW 格式：用 dcraw 抽取 JPG 预览作为缩略图源
                width, height = self._handle_raw(tmp_path, obs_key)
            else:
                # 普通图片：Pillow 处理
                width, height = self._handle_image(tmp_path, obs_key)

            return width, height
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _handle_image(self, tmp_path: str, obs_key: str) -> tuple[int, int]:
        """普通图片：Pillow 生成缩略图"""
        with Image.open(tmp_path) as img:
            img = ImageOps.exif_transpose(img)
            width, height = img.size

            for size_name, max_dim in SIZES.items():
                thumb = img.copy()
                thumb.thumbnail((max_dim, max_dim), Image.LANCZOS)
                self._upload_thumb(thumb, obs_key, size_name)

            return width, height

    def _handle_raw(self, tmp_path: str, obs_key: str) -> tuple[int, int]:
        """RAW 格式：用 dcraw -e 抽取内嵌 JPG 预览，再生成缩略图"""
        # dcraw -e 会输出与输入同名的 .preview.jpg 文件
        result = subprocess.run(
            ["dcraw", "-e", tmp_path],
            capture_output=True,
            timeout=60,
            cwd="/tmp",
        )

        base = os.path.basename(tmp_path)
        stem = os.path.splitext(base)[0]
        # dcraw -e 输出文件名可能是 .thumb.jpg 或 .preview.jpg（不同 dcraw 版本）
        candidates = [
            f"/tmp/{stem}.thumb.jpg",
            f"/tmp/{stem}.preview.jpg",
            f"/tmp/{stem}.jpg",
        ]
        preview_path = next((c for c in candidates if os.path.exists(c)), None)
        if not preview_path:
            raise RuntimeError(
                f"dcraw 未生成预览图（exit={result.returncode}，期望 {candidates[0]} 或类似）"
            )

        try:
            # 读取预览图，生成各档缩略图
            with Image.open(preview_path) as img:
                img = ImageOps.exif_transpose(img)
                width, height = img.size

                for size_name, max_dim in SIZES.items():
                    thumb = img.copy()
                    thumb.thumbnail((max_dim, max_dim), Image.LANCZOS)
                    self._upload_thumb(thumb, obs_key, size_name)

                return width, height
        finally:
            if os.path.exists(preview_path):
                os.unlink(preview_path)

    def _upload_thumb(self, thumb_img: Image.Image, obs_key: str, size_name: str):
        """上传单档缩略图到 OBS"""
        thumb_key = self._thumb_key(obs_key, size_name)

        buf = io.BytesIO()
        thumb_img.save(buf, format="JPEG", quality=85)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
            tf.write(buf.getvalue())
            tf_path = tf.name
        try:
            obs_service.upload_file(thumb_key, tf_path)
        finally:
            if os.path.exists(tf_path):
                os.unlink(tf_path)

    def _thumb_key(self, obs_key: str, size_name: str) -> str:
        """缩略图 key：raw/image/xxx → thumb/{size}/xxx"""
        if "raw/" in obs_key:
            return obs_key.replace("raw/", f"thumb/{size_name}/", 1)
        return f"thumb/{size_name}/{obs_key}"


thumbnail_service = ThumbnailService()
