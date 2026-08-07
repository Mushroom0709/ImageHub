"""素材服务"""
import uuid
from datetime import datetime
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.tag import Tag, AssetTag
from app.schemas.asset import AssetCreate, AssetUpdate
from app.services.obs_service import obs_service


class AssetService:
    def __init__(self, db: Session):
        self.db = db

    def get_asset(self, asset_id: uuid.UUID) -> Asset | None:
        """获取素材详情（含标签）"""
        asset = self.db.query(Asset).filter(Asset.id == asset_id, Asset.deleted_at.is_(None)).first()
        if not asset:
            return None
        # 加载标签
        asset.tags = self._get_asset_tags(asset_id)
        # 填充缩略图 URL
        self._fill_thumb_urls(asset)
        return asset

    def list_assets(
        self,
        page: int = 1,
        size: int = 20,
        sort: str = "newest",
        tag_ids: list[uuid.UUID] | None = None,
        keyword: str = "",
        source_type: str | None = None,
        starred: bool | None = None,
        flag_level: int | None = None,
        trashed: bool = False,
    ) -> tuple[list[Asset], int]:
        """素材列表（分页+筛选）"""
        query = self.db.query(Asset)

        # 回收站过滤
        if trashed:
            query = query.filter(Asset.deleted_at.isnot(None))
        else:
            query = query.filter(Asset.deleted_at.is_(None))

        # 标签筛选（交集）
        if tag_ids:
            # 子查询：每个 tag_id 都存在关联
            for tag_id in tag_ids:
                subq = select(AssetTag.asset_id).where(AssetTag.tag_id == tag_id).scalar_subquery()
                query = query.filter(Asset.id.in_(subq))

        # 关键词过滤（标题 + 描述，MVP 先简单 LIKE）
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(Asset.title.ilike(like), Asset.description.ilike(like)))

        # 来源过滤
        if source_type:
            query = query.filter(Asset.source_type == source_type)

        # 星标过滤
        if starred is not None:
            query = query.filter(Asset.starred == starred)

        # 旗标过滤
        if flag_level is not None:
            query = query.filter(Asset.flag_level == flag_level)

        # 总数
        total = query.count()

        # 排序
        if sort == "oldest":
            query = query.order_by(Asset.created_at.asc())
        elif sort == "quality":
            query = query.order_by(Asset.quality_score.desc())
        else:  # newest
            query = query.order_by(Asset.created_at.desc())

        # 分页
        offset = (page - 1) * size
        items = query.offset(offset).limit(size).all()

        # 批量加载标签
        if items:
            asset_ids = [a.id for a in items]
            tags_map = self._get_assets_tags_map(asset_ids)
            for asset in items:
                asset.tags = tags_map.get(asset.id, [])

        # 填充缩略图 URL
        for asset in items:
            self._fill_thumb_urls(asset)

        return items, total

    def create_asset(self, data: AssetCreate) -> Asset:
        """创建素材"""
        asset = Asset(
            title=data.title,
            description=data.description,
            source_type=data.source_type,
            source_id=data.source_id,
            source_url=data.source_url,
            author_name=data.author_name,
            asset_type=data.asset_type,
            obs_key=data.obs_key,
            file_name=data.file_name,
            file_size=data.file_size,
            width=data.width,
            height=data.height,
            duration=data.duration,
            starred=data.starred,
            flag_level=data.flag_level,
        )
        self.db.add(asset)
        self.db.flush()

        # 直接传入的标签
        if data.tags:
            for tag_data in data.tags:
                tag_name = tag_data.get("tagName", "")
                confidence = tag_data.get("confidence", 1.0)
                source = tag_data.get("source", "external_ai")
                if not tag_name:
                    continue
                # 找已有标签或创建
                tag = self.db.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name, category="other", status="pending")
                    self.db.add(tag)
                    self.db.flush()
                # 关联
                existing = self.db.query(AssetTag).filter(
                    AssetTag.asset_id == asset.id,
                    AssetTag.tag_id == tag.id,
                ).first()
                if not existing:
                    self.db.add(AssetTag(
                        asset_id=asset.id,
                        tag_id=tag.id,
                        confidence=confidence,
                        source=source,
                    ))

        self.db.commit()
        self.db.refresh(asset)

        # 加载标签
        asset.tags = self._get_asset_tags(asset.id)
        self._fill_thumb_urls(asset)

        # TODO: 触发 AI 打标异步任务（如果 auto_tag=True）
        return asset

    def update_asset(self, asset_id: uuid.UUID, data: AssetUpdate) -> Asset | None:
        """更新素材"""
        asset = self.get_asset(asset_id)
        if not asset:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(asset, key, value)
        self.db.commit()
        self.db.refresh(asset)
        asset.tags = self._get_asset_tags(asset.id)
        self._fill_thumb_urls(asset)
        return asset

    def delete_asset(self, asset_id: uuid.UUID) -> bool:
        """软删除素材"""
        asset = self.db.query(Asset).filter(Asset.id == asset_id, Asset.deleted_at.is_(None)).first()
        if not asset:
            return False
        asset.deleted_at = datetime.utcnow()
        self.db.commit()
        return True

    def batch_delete(self, asset_ids: list[uuid.UUID]) -> int:
        """批量软删除"""
        assets = self.db.query(Asset).filter(
            Asset.id.in_(asset_ids),
            Asset.deleted_at.is_(None),
        ).all()
        now = datetime.utcnow()
        for asset in assets:
            asset.deleted_at = now
        self.db.commit()
        return len(assets)

    def batch_recover(self, asset_ids: list[uuid.UUID]) -> int:
        """批量恢复"""
        assets = self.db.query(Asset).filter(
            Asset.id.in_(asset_ids),
            Asset.deleted_at.isnot(None),
        ).all()
        for asset in assets:
            asset.deleted_at = None
        self.db.commit()
        return len(assets)

    def get_similar(self, asset_id: uuid.UUID, limit: int = 12) -> list[Asset]:
        """相似素材（pHash 汉明距离）"""
        # MVP 简单实现：先拿 phash，然后用 PG 函数算距离
        # 后续可优化为预计算 + 索引
        asset = self.get_asset(asset_id)
        if not asset or not asset.phash:
            return []

        # 简单起见，先返回空，等 T13 再做
        return []

    def get_exif(self, asset_id: uuid.UUID) -> dict | None:
        """获取 EXIF"""
        asset = self.get_asset(asset_id)
        if not asset:
            return None
        return asset.exif or {}

    def add_tags(self, asset_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> list[Tag]:
        """给素材加标签"""
        existing = {
            at.tag_id
            for at in self.db.query(AssetTag).filter(AssetTag.asset_id == asset_id).all()
        }
        for tag_id in tag_ids:
            if tag_id not in existing:
                self.db.add(AssetTag(asset_id=asset_id, tag_id=tag_id, source="manual"))
        self.db.commit()
        return self._get_asset_tags(asset_id)

    def remove_tag(self, asset_id: uuid.UUID, tag_id: uuid.UUID) -> bool:
        """移除标签"""
        at = self.db.query(AssetTag).filter(
            AssetTag.asset_id == asset_id,
            AssetTag.tag_id == tag_id,
        ).first()
        if not at:
            return False
        self.db.delete(at)
        self.db.commit()
        return True

    def batch_tag(self, asset_ids: list[uuid.UUID], add_tag_ids: list[uuid.UUID], remove_tag_ids: list[uuid.UUID]) -> int:
        """批量打标"""
        count = 0
        for asset_id in asset_ids:
            # 添加
            for tag_id in add_tag_ids:
                existing = self.db.query(AssetTag).filter(
                    AssetTag.asset_id == asset_id,
                    AssetTag.tag_id == tag_id,
                ).first()
                if not existing:
                    self.db.add(AssetTag(asset_id=asset_id, tag_id=tag_id, source="manual"))
                    count += 1
            # 移除
            if remove_tag_ids:
                self.db.query(AssetTag).filter(
                    AssetTag.asset_id == asset_id,
                    AssetTag.tag_id.in_(remove_tag_ids),
                ).delete(synchronize_session=False)
                count += len(remove_tag_ids)
        self.db.commit()
        return count

    # ===== 内部方法 =====

    def _get_asset_tags(self, asset_id: uuid.UUID) -> list:
        """获取素材的标签列表"""
        from app.schemas.asset import TagBrief
        rows = self.db.query(Tag, AssetTag.confidence, AssetTag.source).join(
            AssetTag, AssetTag.tag_id == Tag.id
        ).filter(
            AssetTag.asset_id == asset_id,
            Tag.status != "deleted",
        ).order_by(Tag.category, Tag.name).all()
        return [TagBrief(
            id=tag.id,
            name=tag.name,
            category=tag.category,
            confidence=confidence,
        ) for tag, confidence, source in rows]

    def _get_assets_tags_map(self, asset_ids: list[uuid.UUID]) -> dict[uuid.UUID, list]:
        """批量获取多个素材的标签"""
        from app.schemas.asset import TagBrief
        rows = self.db.query(AssetTag.asset_id, Tag, AssetTag.confidence).join(
            Tag, AssetTag.tag_id == Tag.id
        ).filter(
            AssetTag.asset_id.in_(asset_ids),
            Tag.status != "deleted",
        ).all()
        result: dict = {}
        for asset_id, tag, confidence in rows:
            if asset_id not in result:
                result[asset_id] = []
            result[asset_id].append(TagBrief(
                id=tag.id,
                name=tag.name,
                category=tag.category,
                confidence=confidence,
            ))
        return result

    def _fill_thumb_urls(self, asset: Asset):
        """填充缩略图预签名 URL"""
        if not asset.obs_key:
            return
        try:
            base_key = asset.obs_key
            if asset.asset_type == "video":
                # 视频用封面帧作为缩略图源
                cover_key = base_key.rsplit(".", 1)[0] + "_cover.jpg" if "." in base_key else base_key + "_cover"
                asset.thumb_small = obs_service.generate_presigned_url(
                    cover_key.replace("raw/", "thumb/small/", 1) if "raw/" in cover_key else f"thumb/small/{cover_key}",
                    expires=3600,
                )
                asset.thumb_medium = obs_service.generate_presigned_url(
                    cover_key.replace("raw/", "thumb/medium/", 1) if "raw/" in cover_key else f"thumb/medium/{cover_key}",
                    expires=3600,
                )
                asset.thumb_raw = obs_service.generate_presigned_url(cover_key, expires=3600)
                return

            # 图片: raw/image/xxx → thumb/small/xxx
            small_key = base_key.replace("raw/", "thumb/small/", 1) if "raw/" in base_key else f"thumb/small/{base_key}"
            medium_key = base_key.replace("raw/", "thumb/medium/", 1) if "raw/" in base_key else f"thumb/medium/{base_key}"
            asset.thumb_small = obs_service.generate_presigned_url(small_key, expires=3600)
            asset.thumb_medium = obs_service.generate_presigned_url(medium_key, expires=3600)
            asset.thumb_raw = obs_service.generate_presigned_url(base_key, expires=3600)
        except Exception:
            pass
