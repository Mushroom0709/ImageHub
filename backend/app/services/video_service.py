"""视频处理服务"""
import os
import subprocess
import tempfile

from app.services.obs_service import obs_service
from app.services.thumbnail_service import thumbnail_service


class VideoService:
    """视频封面帧抽取 + 缩略图"""

    def process(self, obs_key: str) -> tuple[int, int] | None:
        """
        处理视频：抽封面帧 → 生成缩略图 → 上传 OBS
        返回 (width, height)
        """
        with tempfile.NamedTemporaryFile(suffix=".video", delete=False) as tmp:
            video_path = tmp.name
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp2:
            frame_path = tmp2.name

        try:
            # 下载视频
            ok_flag = obs_service.download_file(obs_key, video_path)
            if not ok_flag:
                raise RuntimeError(f"下载视频失败: {obs_key}")

            # 使用 imageio-ffmpeg 静态二进制（避免 apt 安装大依赖）
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

            # 抽第 1 秒的帧
            result = subprocess.run(
                [
                    ffmpeg_path, "-y",
                    "-ss", "1",
                    "-i", video_path,
                    "-frames:v", "1",
                    "-q:v", "2",
                    frame_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0 or not os.path.exists(frame_path):
                raise RuntimeError(f"抽帧失败: {result.stderr[-200:]}")

            # 读取封面帧尺寸
            from PIL import Image
            with Image.open(frame_path) as img:
                width, height = img.size

            # 上传封面帧（作为视频的"原图"）
            frame_key = self._frame_key(obs_key)
            obs_service.upload_file(frame_key, frame_path)

            # 生成缩略图
            thumbnail_service.generate(frame_key)

            return width, height
        finally:
            for p in [video_path, frame_path]:
                if os.path.exists(p):
                    os.unlink(p)

    def _frame_key(self, obs_key: str) -> str:
        """封面帧 key: raw/video/xxx.mp4 → raw/video/xxx_cover.jpg"""
        base = obs_key.rsplit(".", 1)[0] if "." in obs_key else obs_key
        return f"{base}_cover.jpg"


video_service = VideoService()
