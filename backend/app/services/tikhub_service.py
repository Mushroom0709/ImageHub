"""TikHub 采集服务"""
import httpx
import tempfile
import os
from typing import Optional

from app.core.config import settings


class TikHubService:
    """封装 TikHub REST API"""

    def __init__(self):
        self.base_url = settings.TIKHUB_BASE_URL
        self.token = settings.TIKHUB_TOKEN
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def _get(self, path: str, params: dict) -> dict:
        """GET 请求"""
        try:
            with httpx.Client(timeout=60, follow_redirects=True) as client:
                resp = client.get(
                    f"{self.base_url}{path}",
                    params=params,
                    headers=self.headers,
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") == 200:
                    return data.get("data", {})
                return {}
        except Exception as e:
            print(f"[TikHub] 请求失败 {path}: {e}")
            return {}

    def fetch_xhs_note(self, url: str) -> dict | None:
        """
        抓取小红书笔记详情
        url: 笔记分享链接
        返回: { title, desc, images: [url], author, likes, collects, comments, tags }
        """
        # 支持 share_text 参数（直接传链接）
        data = self._get("/api/v1/xiaohongshu/app_v2/get_image_note_detail", {
            "share_text": url,
        })
        if not data:
            return None

        # 解析返回结构
        note = data.get("note", data) if isinstance(data, dict) else {}

        title = note.get("title", "") or note.get("desc", "")[:50] or "小红书笔记"
        desc = note.get("desc", "") or note.get("title", "")

        # 图片列表
        image_list = note.get("image_list", []) or []
        images = []
        for img in image_list:
            if isinstance(img, dict):
                url_list = img.get("url_list") or img.get("url") or []
                if isinstance(url_list, list) and url_list:
                    images.append(url_list[0])
                elif isinstance(url_list, str):
                    images.append(url_list)
            elif isinstance(img, str):
                images.append(img)

        # 作者
        author = note.get("user", {}) or {}
        author_name = author.get("nickname", "") if isinstance(author, dict) else ""

        # 互动数据
        interact = note.get("interact_info", {}) or {}
        likes = interact.get("liked_count", 0) or 0
        collects = interact.get("collected_count", 0) or 0
        comments = interact.get("comment_count", 0) or 0

        # 话题标签
        topic_list = note.get("topic_list", []) or []
        tags = [t.get("name", "") for t in topic_list if isinstance(t, dict) and t.get("name")]

        return {
            "title": title,
            "desc": desc,
            "images": images,
            "author": author_name,
            "likes": likes,
            "collects": collects,
            "comments": comments,
            "tags": tags,
            "source_id": note.get("note_id", "") or data.get("note_id", ""),
        }

    def fetch_douyin_video(self, url: str) -> dict | None:
        """
        抓取抖音视频详情
        url: 分享链接
        返回: { title, desc, video_url, cover_url, author, likes }
        """
        # 优先用 share_url 接口
        data = self._get("/api/v1/douyin/web/fetch_one_video_by_share_url", {
            "share_url": url,
        })

        # 如果 share_url 接口失败，回退到 demo 接口
        if not data:
            data = self._get("/api/v1/demo/douyin/web/fetch_one_video", {})

        if not data:
            return None

        # demo 接口返回 aweme_detail
        video = data.get("aweme_detail", data) if isinstance(data, dict) else {}
        if not isinstance(video, dict):
            return None

        desc = video.get("desc", "") or "抖音视频"
        author = video.get("author", {}) or {}
        author_name = author.get("nickname", "") if isinstance(author, dict) else ""

        # 视频地址
        video_info = video.get("video", {}) or {}
        play_addr = video_info.get("play_addr", {}) or {}
        video_url_list = play_addr.get("url_list", []) or []
        video_url = video_url_list[0] if video_url_list else ""

        # 封面
        cover = video_info.get("cover", {}) or {}
        cover_url_list = cover.get("url_list", []) or []
        cover_url = cover_url_list[0] if cover_url_list else ""

        # 互动数据
        stats = video.get("statistics", {}) or {}
        likes = stats.get("digg_count", 0) or 0

        return {
            "title": desc[:50],
            "desc": desc,
            "video_url": video_url,
            "cover_url": cover_url,
            "author": author_name,
            "likes": likes,
            "source_id": video.get("aweme_id", ""),
        }

    def download_file(self, url: str) -> str | None:
        """下载文件到临时目录，返回本地路径"""
        try:
            with httpx.Client(timeout=60, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                # 从 URL 推断扩展名
                ext = "jpg"
                path_part = url.split("?")[0].split("/")[-1]
                if "." in path_part:
                    ext = path_part.rsplit(".", 1)[-1][:5]
                tmp = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
                tmp.write(resp.content)
                tmp.close()
                return tmp.name
        except Exception as e:
            print(f"[TikHub] 下载失败: {e}")
            return None


tikhub_service = TikHubService()
