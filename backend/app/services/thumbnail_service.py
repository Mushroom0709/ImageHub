"""缩略图服务"""
import io
import os
import tempfile
from PIL import Image, ImageOps

from app.core.config import settings
from app.services.obs_service import obs_service

SIZES = {
    "small": 300,
    "medium": 1200,
}


class ThumbnailService:
    """生成 3 档缩略图并上传 OBS"""

    def generate(self, obs_key: str) -> tuple[int, int]:
        """
        下载原图 → 生成 small/medium 缩略图 → 上传 OBS
        返回 (width, height)
        """
        # 下载原图
        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            ok_flag = obs_service.download_file(obs_key, tmp_path)
            if not ok_flag:
                raise RuntimeError(f"下载原图失败: {obs_key}")

            # 打开图片
            with Image.open(tmp_path) as img:
                # EXIF 方向修正
                img = ImageOps.exif_transpose(img)
                width, height = img.size

                # 生成各档缩略图
                for size_name, max_dim in SIZES.items():
                    thumb = img.copy()
                    thumb.thumbnail((max_dim, max_dim), Image.LANCZOS)
                    thumb_key = self._thumb_key(obs_key, size_name)

                    # 转成 JPEG bytes
                    buf = io.BytesIO()
                    thumb.save(buf, format="JPEG", quality=85)
                    buf.seek(0)

                    # 上传（用临时文件方式）
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                        tf.write(buf.getvalue())
                        tf_path = tf.name
                    try:
                        obs_service.upload_file(thumb_key, tf_path)
                    finally:
                        os.unlink(tf_path)

                return width, height
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _thumb_key(self, obs_key: str, size_name: str) -> str:
        """缩略图 key：raw/image/xxx → thumb/{size}/xxx"""
        if "raw/" in obs_key:
            return obs_key.replace("raw/", f"thumb/{size_name}/", 1)
        return f"thumb/{size_name}/{obs_key}"


thumbnail_service = ThumbnailService()
