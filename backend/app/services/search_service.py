"""Meilisearch 搜索服务"""
import meilisearch
from app.core.config import settings

INDEX_NAME = "assets"


class SearchService:
    def __init__(self):
        # Meilisearch SDK 用 master_key 参数（python 版本差异）
        try:
            self.client = meilisearch.Client(
                settings.MEILISEARCH_HOST,
                api_key=settings.MEILISEARCH_MASTER_KEY,
            )
        except TypeError:
            self.client = meilisearch.Client(
                settings.MEILISEARCH_HOST,
                master_key=settings.MEILISEARCH_MASTER_KEY,
            )
        self._ensure_index()

    def _ensure_index(self):
        """确保索引存在"""
        try:
            if not self.client.get_index(INDEX_NAME):
                self.client.create_index(INDEX_NAME, {"primaryKey": "id"})
            # 配置可搜索字段
            self.client.index(INDEX_NAME).update_searchable_attributes(
                ["title", "description", "file_name", "tag_names"]
            )
            self.client.index(INDEX_NAME).update_filterable_attributes(
                ["source_type", "star_level", "flag_level", "asset_type"]
            )
        except Exception as e:
            print(f"[Meilisearch] 初始化失败: {e}")

    def index_asset(self, asset: dict):
        """同步单个素材到索引"""
        try:
            doc = {
                "id": str(asset["id"]),
                "title": asset.get("title", ""),
                "description": asset.get("description", ""),
                "file_name": asset.get("file_name", ""),
                "tag_names": [t["name"] for t in asset.get("tags", [])],
                "source_type": asset.get("source_type", ""),
                "star_level": asset.get("star_level", 0),
                "flag_level": asset.get("flag_level", 0),
                "asset_type": asset.get("asset_type", "image"),
            }
            self.client.index(INDEX_NAME).add_documents([doc])
        except Exception as e:
            print(f"[Meilisearch] 索引失败: {e}")

    def remove_asset(self, asset_id: str):
        """从索引删除素材"""
        try:
            self.client.index(INDEX_NAME).delete_document(str(asset_id))
        except Exception as e:
            print(f"[Meilisearch] 删除索引失败: {e}")

    def search(self, q: str, limit: int = 20) -> list:
        """搜索素材"""
        try:
            result = self.client.index(INDEX_NAME).search(
                q,
                {
                    "limit": limit,
                    "attributesToHighlight": ["title", "description"],
                },
            )
            return result.get("hits", [])
        except Exception as e:
            print(f"[Meilisearch] 搜索失败: {e}")
            return []

    def suggest(self, q: str, limit: int = 8) -> list:
        """搜索建议（返回精简字段）"""
        hits = self.search(q, limit)
        return [
            {
                "id": h["id"],
                "title": h.get("title", ""),
                "file_name": h.get("file_name", ""),
            }
            for h in hits
        ]


search_service = SearchService()
