"""OBS 老化清理脚本
删除回收站中已超过保留期（默认 15 天）的素材：
1. 删除其 OBS 对象（raw 原图 + thumb 缩略图）
2. 物理删除数据库记录（asset + asset_tags）

用法: python cleanup_obs.py [--days 15] [--dry-run]
"""
import sys
from datetime import datetime, timedelta

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.models.asset import Asset
from app.models.tag import AssetTag
from app.services.obs_service import obs_service

RETENTION_DAYS = 15


def _obj_keys(obs_key: str) -> list[str]:
    """根据 raw 对象 key 推导所有相关对象（raw + 缩略图）"""
    keys = [obs_key]
    if obs_key.startswith("raw/"):
        rel = obs_key[len("raw/"):]
        keys.append(f"thumb/small/{rel}")
        keys.append(f"thumb/medium/{rel}")
    elif obs_key.startswith("thumb/"):
        rel = obs_key[len("thumb/"):]
        keys.append(f"raw/{rel}")
    return keys


def cleanup(days: int, dry_run: bool = False) -> dict:
    db = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(days=days)
    print(f"[老化清理] 扫描 deleted_at < {cutoff} 的素材（保留 {days} 天）")

    # 查询回收站中超过保留期的素材
    expired = (
        db.query(Asset)
        .filter(Asset.deleted_at.isnot(None), Asset.deleted_at < cutoff)
        .all()
    )
    print(f"[老化清理] 发现 {len(expired)} 个过期素材")

    stats = {"assets": 0, "obs_objects": 0, "errors": 0}
    for asset in expired:
        asset_id = str(asset.id)
        print(f"  - {asset.file_name} (删于 {asset.deleted_at})")

        # 删除 OBS 对象
        if asset.obs_key:
            for key in _obj_keys(asset.obs_key):
                try:
                    if not dry_run:
                        obs_service.delete_file(key)
                    stats["obs_objects"] += 1
                    print(f"    ✕ OBS {key}")
                except Exception as e:
                    stats["errors"] += 1
                    print(f"    ! OBS 删除失败 {key}: {e}")

        # 物理删除数据库记录
        if not dry_run:
            db.query(AssetTag).filter(AssetTag.asset_id == asset.id).delete(synchronize_session=False)
            db.delete(asset)
        stats["assets"] += 1

    if not dry_run:
        db.commit()
        print(f"[老化清理] 完成：清理 {stats['assets']} 素材，删除 {stats['obs_objects']} 个 OBS 对象，{stats['errors']} 错误")
    else:
        print(f"[老化清理] DRY-RUN：将清理 {stats['assets']} 素材 / {stats['obs_objects']} 个 OBS 对象（未实际执行）")
    db.close()
    return stats


if __name__ == "__main__":
    days = RETENTION_DAYS
    dry_run = False
    if "--days" in sys.argv:
        try:
            days = int(sys.argv[sys.argv.index("--days") + 1])
        except (ValueError, IndexError):
            pass
    if "--dry-run" in sys.argv:
        dry_run = True

    cleanup(days=days, dry_run=dry_run)
