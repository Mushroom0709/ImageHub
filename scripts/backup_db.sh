#!/bin/bash
# ImageHub 数据库每日备份脚本
# 用法: ./backup_db.sh [--manual]
# 自动: crontab 每日凌晨 3 点执行
set -e

cd "$(dirname "$0")"

# 配置
BACKUP_DIR="/tmp/imagehub-backups"
RETENTION_DAYS=30
TODAY=$(date +%Y%m%d)
BACKUP_FILE="${BACKUP_DIR}/imagehub-db-${TODAY}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始备份数据库..."

# 1. pg_dump 备份
echo "[1/4] pg_dump 备份..."
docker compose exec -T db pg_dump -U imagehub -d imagehub --no-owner --no-privileges | gzip > "$BACKUP_FILE"

# 验证备份非空
SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE")
if [ "$SIZE" -lt 1000 ]; then
    echo "❌ 备份文件过小（${SIZE} bytes），疑似失败"
    rm -f "$BACKUP_FILE"
    exit 1
fi
echo "✅ 备份完成: ${BACKUP_FILE} (${SIZE} bytes)"

# 2. 上传到 OBS
echo "[2/4] 上传到 OBS backup/ 目录..."
# 备份文件在宿主机，需要先复制进容器
docker cp "$BACKUP_FILE" imagehub-api-1:/tmp/backup-current.sql.gz
CONTAINER_FILE="/tmp/backup-current.sql.gz"
docker compose exec -T api python3 -c "
import sys
sys.path.insert(0, '/app')
from app.services.obs_service import obs_service

file_path = '$CONTAINER_FILE'
key = 'backup/db/' + '$BACKUP_FILE'.split('/')[-1]
ok = obs_service.upload_file(key, file_path)
print(f'上传 {\"成功\" if ok else \"失败\"}: {key}')
if not ok:
    sys.exit(1)
" || exit 1

# 3. 清理本地旧备份
echo "[3/4] 清理本地 30 天前的备份..."
find "$BACKUP_DIR" -name 'imagehub-db-*.sql.gz' -mtime +"$RETENTION_DAYS" -delete

# 4. 清理 OBS 上 30 天前的备份
echo "[4/4] 清理 OBS 30 天前的备份..."
docker compose exec -T api python3 -c "
import sys
sys.path.insert(0, '/app')
from datetime import datetime, timedelta
from app.services.obs_service import obs_service

cutoff = datetime.utcnow() - timedelta(days=$RETENTION_DAYS)
objects = obs_service.list_objects('backup/db/', max_keys=1000)
deleted = 0
for obj in objects:
    # 解析文件名里的日期: imagehub-db-YYYYMMDD.sql.gz
    key = obj['key']
    try:
        date_str = key.split('-')[-3]  # 20260808
        obj_date = datetime.strptime(date_str, '%Y%m%d')
        if obj_date < cutoff:
            obs_service.delete_file(key)
            deleted += 1
            print(f'删除旧备份: {key}')
    except (ValueError, IndexError):
        continue
print(f'清理完成，删除 {deleted} 个旧备份')
"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 备份全部完成"
