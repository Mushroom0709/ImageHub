# ImageHub

纯标签驱动的图片视频分类管理系统（无相册概念）。

## 核心特性

- **纯标签驱动**：场景/风格/服装/妆容/姿势/构图/色调/身材/信息 9 大分类，无限层级标签
- **多路素材来源**：
  - ① 用户上传（直传 OBS + 后端 AI 打标）
  - ② 外部 AI 批量导入（自带标签）
  - ③ 小红书/抖音链接采集（TikHub）
  - ④ 批量导入（文件夹拖拽，支持 ARW/RAW）
- **AI 自动打标**：Qwen 多模态模型，自动识别 8 大维度标签 + 置信度
- **EXIF 完整读取**：相机/镜头/光圈/快门/ISO/焦距/拍摄时间（支持 ARW RAW）
- **缩略图三档**：300px / 1200px / 原图（全桶私有，预签名 URL）
- **全文搜索**：Meilisearch
- **待审核区**：低置信度标签 / AI 新建标签人工审核确认
- **星标/旗标/多选/快捷键/回收站**
- **移动端适配**：底部导航 + 响应式

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + Tailwind v4 + Zustand + React Router |
| 后端 | Python FastAPI + SQLAlchemy 2.0 + Alembic |
| 数据库 | PostgreSQL 15 |
| 缓存/队列 | Redis |
| 搜索 | Meilisearch |
| 对象存储 | 华为云 OBS（官方 SDK，预签名直传） |
| AI 打标 | Qwen 多模态（本地部署） |
| 采集 | TikHub REST API（小红书/抖音） |
| 图片处理 | Pillow + exiftool + dcraw + imageio-ffmpeg |
| 部署 | Docker Compose（ECS 端口 10388） |

## 部署

```bash
# 环境变量（复制 .env.example 为 .env 并填写）
cp .env.example .env

# 启动
docker compose up -d

# 初始化数据库
docker compose exec api alembic upgrade head
docker compose exec api python init_db.py seed
docker compose exec api python create_admin.py admin <password>

# 数据库每日备份（自动）
# crontab 已配置，每日凌晨 3 点执行 scripts/backup_db.sh
```

## 目录结构

```
backend/
  app/
    api/endpoints/     # API 路由
    models/            # SQLAlchemy 模型
    schemas/           # Pydantic 模型
    services/          # 业务逻辑
    core/              # 配置/数据库
    data/              # 种子数据
  alembic/             # 数据库迁移
frontend/
  src/
    components/        # React 组件
    pages/             # 页面
    stores/            # Zustand store
    hooks/             # 自定义 hooks
    lib/               # API 客户端
scripts/               # 测试/备份脚本
docs/                  # 设计文档/ADR/API
```

## 验收状态

- ✅ OBS 连通性全流程
- ✅ AI 模型（Qwen 多模态 + 结构化输出）
- ✅ TikHub 采集（小红书/抖音）
- ✅ 上传直传 OBS + 缩略图
- ✅ EXIF 读取 + 信息标签
- ✅ AI 自动打标
- ✅ 素材/标签 CRUD + 筛选
- ✅ 瀑布流 + 标签树 + Lightbox
- ✅ 抖音视频采集 + 封面帧
- ✅ 批量导入（含 ARW）
- ✅ 用户登录 + JWT
- ✅ 待审核区
- ✅ 搜索（Meilisearch）
- ✅ 数据库每日备份
- ✅ ECS 生产部署（10388）
