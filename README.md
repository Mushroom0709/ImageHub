# ImageHub

纯标签驱动的图片视频分类管理系统（无相册概念）。

## 核心特性

- **纯标签驱动**：场景/风格/服装/妆容/姿势/构图/色调/身材/信息 9 大分类，无限层级标签
- **多路素材来源**：
  - ① 用户上传（预签名直传 OBS + 3 并发 + 实时进度 + AI 打标）
  - ② 外部 AI 批量导入（自带标签，REST API 接入）
  - ③ 小红书/抖音链接采集（TikHub）
  - ④ 文件夹批量上传（按钮选文件夹 / 拖拽文件夹，递归上传，不保留原结构）
- **AI 自动打标**：Qwen 多模态模型，自动识别 8 大维度标签 + 置信度
- **EXIF 完整读取**：相机/镜头/光圈/快门/ISO/焦距/拍摄时间（支持 ARW RAW）
- **缩略图三档**：300px / 1200px / 原图（全桶私有，预签名 URL）
- **全文搜索**：Meilisearch
- **待审核区**：低置信度标签 / AI 新建标签人工审核确认
- **星标/旗标/多选/快捷键/回收站**
- **Lightbox 大图/视频查看**：右侧信息面板（标题/描述/星级/旗标/标签/EXIF/项目/编辑）
- **视频流式播放**：后端 stream 代理 + Range 透传，支持拖拽进度
- **快捷键**：1-5 星标 / 6-9 四色旗标 / 0 清除
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
- ✅ TikHub 采集（小红书图片 / 抖音视频）
- ✅ 上传预签名直传 OBS + 3 并发 + 实时进度面板
- ✅ 文件夹上传（按钮选择 + 拖拽，递归上传，不保留原结构）
- ✅ 缩略图三档（small/medium/raw）
- ✅ EXIF 读取 + 信息标签（支持 ARW RAW）
- ✅ AI 自动打标 + 低置信度待审核
- ✅ 素材/标签 CRUD + 多维筛选 + 全文搜索
- ✅ 瀑布流 + 标签树 + Lightbox 大图
- ✅ 视频 Lightbox + 流式播放（后端 stream 代理 + Range 透传）
- ✅ 星标（1-5 级）+ 四色旗标（红/橙/黄/绿）+ 快捷键（1-5/6-9/0）
- ✅ 软删 + 回收站（15 天）+ OBS 老化清理
- ✅ 用户登录 + JWT + 管理员创建
- ✅ Meilisearch 全文搜索
- ✅ 数据库每日备份（pg_dump + OBS 存 30 天）
- ✅ ECS 生产部署（10388 端口，Docker Compose）
