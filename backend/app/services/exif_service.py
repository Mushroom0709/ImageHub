"""EXIF 读取服务"""
import tempfile
import os
import subprocess
import json

from app.services.obs_service import obs_service


class ExifService:
    """用 exiftool 读取 EXIF 信息"""

    def read(self, obs_key: str) -> dict:
        """
        从 OBS 下载文件读取 EXIF
        返回结构化 EXIF（不含二进制缩略图）
        """
        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            ok_flag = obs_service.download_file(obs_key, tmp_path)
            if not ok_flag:
                raise RuntimeError(f"下载失败: {obs_key}")

            return self._read_from_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _read_from_file(self, file_path: str) -> dict:
        """用 exiftool 读取 EXIF"""
        try:
            result = subprocess.run(
                ["exiftool", "-json", "-G", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {}
            data = json.loads(result.stdout)
            if not data:
                return {}
            return self._extract_interesting(data[0])
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            # exiftool 不可用或解析失败
            return self._read_with_fallback(file_path)

    def _extract_interesting(self, raw: dict) -> dict:
        """提取关键 EXIF 字段（key 可能带分组前缀如 EXIF:Make）"""
        def get(*keys):
            """按多个可能的 key 查找"""
            for k in keys:
                # 精确匹配
                if k in raw and raw[k]:
                    return raw[k]
                # 匹配带前缀的 (如 EXIF:Make, IFD0:Model)
                for rk, rv in raw.items():
                    if rk.endswith(":" + k) and rv:
                        return rv
            return ""

        make = get("Make")
        model = get("Model")
        interesting = {
            "camera": f"{make} {model}".strip(),
            "lens": get("LensModel", "Lens"),
            "aperture": get("Aperture", "FNumber"),
            "shutter": get("ShutterSpeed", "ExposureTime"),
            "iso": get("ISO"),
            "focal_length": get("FocalLength"),
            "focal_length_35mm": get("FocalLengthIn35mmFormat"),
            "white_balance": get("WhiteBalance"),
            "capture_time": get("DateTimeOriginal"),
            "gps_lat": get("GPSLatitude"),
            "gps_lng": get("GPSLongitude"),
            "flash": get("Flash"),
            "color_space": get("ColorSpace"),
            "exposure_bias": get("ExposureCompensation"),
        }
        # 过滤空值
        return {k: v for k, v in interesting.items() if v}

    def _read_with_fallback(self, file_path: str) -> dict:
        """备用：用 PIL 读基础信息"""
        try:
            from PIL import Image, ExifTags
            with Image.open(file_path) as img:
                result = {"width": img.width, "height": img.height}
                exif = img._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                        if tag_name in ("Make", "Model", "DateTimeOriginal", "ISOSpeedRatings"):
                            result[tag_name] = str(value)
                return result
        except Exception:
            return {}


exif_service = ExifService()
