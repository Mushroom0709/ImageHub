# ImageHub V2 上传模块升级方案

> 解决大文件上传、AI 导入保持、独立上传页面、物理盘适配、断点续传 5 个核心需求。
> 本文档先于代码实现，需用户确认后再拆 ticket 实施。

**创建日期：** 2026-08-08
**状态：** Draft（待用户确认）

---

## 1. 背景与现状

### 1.1 当前能力（MVP 已交付）

| 功能 | 状态 | 说明 |
|---|---|---|
| 拖拽上传 | ✅ | 递归支持文件夹 |
| 点击选择文件/文件夹 | ✅ | 下拉菜单 |
| 预签名直传 OBS | ✅ | 3 并发 |
| 实时进度面板 | ✅ | 浮动窗口，单文件进度+总进度 |
| AI 自动打标 | ✅ | Qwen3.6-27B，confidence<0.7 进待审核 |
| 缩略图三档 | ✅ | 300/1200/raw |
| EXIF 自动打信息标签 | ✅ | 相机/镜头/焦段/年份/月份 |
| 视频处理 | ✅ | 抽封面 + 取分辨率 |
| AI 导入 API | ✅ | docs/ai-import-guide.md（POST /api/upload/credentials + POST /api/assets） |
| 回收站+老化 | ✅ | 15 天 + crontab |

### 1.2 痛点与限制

| 痛点 | 影响 | 解决方向 |
|---|---|---|
| **大文件无法断点续传** | ARW（50-100MB）、长视频（1GB+）上传中途中断需重头传，浪费时间和带宽 | OBS Multipart Upload + 后端 session |
| **单文件大小硬限** | 当前未硬限但前端缺少友好的大文件提示；OBS 单 PUT 上限 5GB | 放宽到 2GB，可配置；超过 100MB 强制走分片 |
| **进度面板太简化** | 浮动窗口只显示总进度和单文件上传进度，无法看 AI打标/缩略图/OBS 各阶段 | 独立上传页面 + 详细状态机 |
| **AI 导入与用户上传耦合** | AI 导入走的是 `/api/upload/credentials` + `/api/upload/complete`，和用户上传混用 | 保留 API 兼容，添加 `sourceType` 路由 |
| **本地临时盘不确定** | 当前 `import_api.py` 用 `/tmp`，容器内 tmpfs 空间有限 | 配置挂载物理盘（≥256GB） |

---

## 2. 需求详解

### 需求 1：单文件大小 5M → 可配置

**现状**：前端 `<input>` 没硬限，后端 multipart 路径也无硬限，但批量导入路径 `/api/import/upload` 没显式限制。预签名直传路径也没有，但 OBS 单 PUT 上限是 5GB。

**方案**：
- 引入配置文件 `backend/app/core/config.py` 增加：
  - `UPLOAD_MAX_FILE_SIZE` 默认 `2 * 1024 * 1024 * 1024`（2GB）
  - `UPLOAD_CHUNK_SIZE` 默认 `8 * 1024 * 1024`（8MB，OBS 分片最小 5MB）
  - `UPLOAD_MULTIPART_THRESHOLD` 默认 `100 * 1024 * 1024`（100MB，超过走分片）
- 环境变量覆盖：`UPLOAD_MAX_FILE_SIZE=4GB` 等
- 前端校验：选文件时提示大文件，建议分片

### 需求 2：保留 AI 导入 API

**现状**：已支持，路径见 `docs/ai-import-guide.md`。

**方案**：保持现状，**不做任何破坏性改动**。
- AI 导入仍然走 `/api/upload/credentials`（预签名直传）+ `POST /api/assets`（创建素材）
- 用户上传走同一组 API + `POST /api/upload/complete`
- 区分点：`POST /api/assets` 的 `sourceType` 字段（`upload` / `ai_import` / `xiaohongshu` / `douyin`）

### 需求 3：物理盘适配（256GB）

**现状**：上传过程（仅 `import_api.py` 的 multipart 路径）临时文件用 `/tmp`，容器内 tmpfs 空间通常 1-2GB，ARW 单文件 50-100MB 大量并发会爆。

**方案**：
- 新增配置 `UPLOAD_TMP_DIR` 默认 `/data/imagehub-tmp`（挂载物理盘）
- 环境变量：`UPLOAD_TMP_DIR=/mnt/storage/uploads`
- docker-compose.yml 添加 volume：
  ```yaml
  volumes:
    - /mnt/storage/uploads:/data/imagehub-tmp  # 宿主机 256GB 物理盘
  ```
- 所有上传相关临时文件改用 `UPLOAD_TMP_DIR`
- 启动时校验目录存在且可写，不存在则尝试创建，失败则报错

### 需求 4：断点续传（大文件分片上传）

**现状**：预签名 PUT 是单次上传，断点 = 重传。

**方案（OBS Multipart Upload）**：

**OBS 分片上传协议**（华为云 OBS Python SDK）：

```
1. client.initiateMultipartUpload(bucket, key) → uploadId
2. client.uploadPart(bucket, key, uploadId, partNumber, data) → {etag}
   ↑ 可并发上传多个 part，断点续传只需重传未完成的 part
3. client.completeMultipartUpload(bucket, key, uploadId, parts=[{partNumber, etag}])
```

**后端 API 设计**：

| 端点 | 方法 | 用途 |
|---|---|---|
| `POST /api/upload/multipart/init` | POST | 初始化分片上传，返回 uploadId + 每个分片的预签名 URL |
| `POST /api/upload/multipart/part` | POST | 上传完一个分片后回调，记录 partNumber + etag |
| `POST /api/upload/multipart/complete` | POST | 完成分片上传，合并 + 触发后续处理 |
| `POST /api/upload/multipart/abort` | POST | 取消分片上传（清理 OBS 上的 parts） |
| `GET /api/upload/multipart/:uploadId/status` | GET | 查询已上传的 parts（用于断点续传时跳过已完成的） |

**前端流程**：

```
1. 文件 > 100MB → 触发分片上传
2. POST /multipart/init（带文件信息）→ 拿 uploadId + 每个 part 的预签名 URL
3. 文件切片（每片 8MB）→ 并发上传到各 part 的 URL（XHR 进度）
4. 每个 part 成功后 → POST /multipart/part 记录 etag
5. 中断恢复：GET /multipart/:uploadId/status → 拿到已上传 part 列表 → 只传未完成的
6. 全部 part 上传完 → POST /multipart/complete → 合并 + 触发缩略图/EXIF/AI打标
```

**断点续传关键点**：
- `uploadId` 持久化（前端 localStorage + 后端 DB/Redis）
- 每个 part 的 etag 存起来，重连后 GET 拿已完成的列表跳过
- 断点超时：超过 24 小时未完成自动 abort（清理 OBS parts）

**新增 DB 表** `multipart_uploads`：

```sql
CREATE TABLE multipart_uploads (
  id VARCHAR(32) PRIMARY KEY,        -- uploadId
  user_id UUID,
  filename VARCHAR(255),
  file_size BIGINT,
  obs_key VARCHAR(512),
  obs_upload_id VARCHAR(64),          -- OBS 的 uploadId（区别于我们的）
  total_parts INT,
  completed_parts JSONB,              -- [{"partNumber": 1, "etag": "..."}]
  status VARCHAR(16),                 -- active / completed / aborted
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### 需求 5：独立上传页面 + 详细状态

**现状**：只有一个浮动窗口，简单显示总进度。

**方案**：

**新增路由** `/upload`：
- 独立页面（React 组件）
- 左侧：上传任务列表（每次上传一批是一行）
- 右侧：选中任务的详情（每个文件的多阶段进度）

**页面结构**：

```
┌──────────────────────────────────────────────────────────┐
│  ImageHub  🔍 搜索...  [上传中: 12/30] [👤 用户]        │ ← 顶栏显示上传统计
├──────────────────────────────────────────────────────────┤
│ 我的上传                                                  │
│ ┌─────────┬────────────────────────────────────────────┐ │
│ │ 上传列表 │ 批次: 2026-08-08 14:30 (3个文件)         │ │
│ │          │                                            │ │
│ │ ▶ 1. 批 │  IMG_0001.jpg (45 MB)                      │ │
│ │   12/30 │  ┌─────────────────────────────────────┐ │ │
│ │   进行中 │  │ OBS 上传  ▓▓▓▓▓▓▓▓░░ 80% 5.2 MB/s│ │ │
│ │          │  │ 服务器处理 ✓ 缩略图 ✓ EXIF ⟳ AI打标 │ │ │
│ │ ⏸ 2. 批 │  │                                        │ │ │
│ │   已暂停 │  │ IMG_0002.arw (78 MB) [分片上传]       │ │
│ │          │  │ ┌─────────────────────────────────┐ │ │ │
│ │ ✓ 3. 批 │  │ │Part 1/10 ✓  Part 2/10 ⟳ 80%    │ │ │ │
│ │   已完成 │  │ │Part 3/10 ⏳  ...                 │ │ │ │
│ │          │  │ └─────────────────────────────────┘ │ │ │
│ │ ✗ 4. 批 │  │ ...                                    │ │ │
│ │   失败  │  └─────────────────────────────────────┘ │ │
│ └─────────┴────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**状态机设计**：

```typescript
type FileStage =
  | 'queued'              // 排队等待
  | 'init_multipart'      // 初始化分片上传（>100MB）
  | 'uploading_obs'       // 上传到 OBS（直传或分片）
  | 'processing_thumb'    // 生成缩略图
  | 'processing_exif'     // 读取 EXIF
  | 'processing_ai_tag'   // AI 打标
  | 'processing_phash'    // 计算 pHash
  | 'saving_db'           // 写入数据库
  | 'completed'           // 完成
  | 'failed'              // 失败（可重试）
  | 'paused'              // 暂停（用户主动）

interface FileProgress {
  fileIndex: number
  fileName: string
  fileSize: number
  currentStage: FileStage
  stages: {
    obsUpload: { loaded: number; total: number; speed: number }  // 网速
    server: {
      thumb: 'pending' | 'running' | 'done' | 'failed'
      exif: ...
      aiTag: ...
      phash: ...
    }
  }
  error?: string
}
```

**SSE 进度流**（新增）：
- 后端处理每个文件时主动推送：`POST /api/upload/multipart/complete` → 后端开始处理 → SSE 推 `processing_thumb → processing_exif → processing_ai_tag → completed`
- 前端订阅 SSE，实时更新每个文件的状态

**新端点** `GET /api/upload/events?batchId=xxx`（SSE）：
```
event: file_update
data: {fileIndex: 0, stage: "processing_ai_tag", progress: 0.5}

event: file_complete
data: {fileIndex: 0, assetId: "uuid"}

event: batch_complete
data: {total: 10, success: 9, failed: 1}
```

**功能特性**：
1. **暂停/继续**：用户可暂停整个批次或单个文件（分片场景）
2. **重试失败**：失败的文件可点重试
3. **移除**：从列表移除（不删除已上传的 OBS 对象）
4. **查看素材**：完成后点击跳转到素材详情页
5. **上传统计**：顶栏显示"上传中: 12/30"实时更新

---

## 3. 架构决策

### 3.1 总体架构

```
┌──────────┐         ┌──────────────┐         ┌──────────┐
│  浏览器   │ ←─HTTP─→│  FastAPI 后端 │ ←─SDK─→ │  华为云 OBS │
│  React   │ ←─SSE──→│              │         │          │
└──────────┘         └──────┬───────┘         └──────────┘
                            │
                       ┌────┴────┐
                       │PostgreSQL│ (上传 sessions, 进度)
                       │  + Redis │ (队列, 限流)
                       └────┬────┘
                       ┌────┴────┐
                       │  本地盘  │ /data/imagehub-tmp (256GB)
                       └─────────┘
```

### 3.2 关键技术选型

| 议题 | 决策 | 理由 |
|---|---|---|
| 大文件上传协议 | OBS Multipart Upload | 官方支持，断点续传天然支持 |
| 实时进度推送 | XHR upload.onprogress（上传）+ SSE（处理阶段） | 上传阶段 XHR 最实时；处理阶段 SSE 后端主导 |
| 临时文件存储 | 本地物理盘挂载 `/data/imagehub-tmp` | 256GB 足够，避免容器 tmpfs 爆 |
| 单文件上限 | 默认 2GB，可配置 `UPLOAD_MAX_FILE_SIZE` | OBS 单 PUT 上限 5GB，留余量 |
| 分片阈值 | 默认 100MB（>此值走分片） | 小文件没必要分片，省去 part 协调开销 |
| 单 Part 大小 | 默认 8MB，最小 5MB（OBS 限制） | 平衡并发数和 part 数量 |
| 并发上传数 | 直传 3 并发，分片每文件 3 Part 并发 | 后端 + OBS 速率限制 |
| 上传 session 存储 | Redis（TTL 24h）+ DB 持久化 | Redis 自动过期清理，DB 留痕 |
| 已有 API 兼容 | `POST /api/upload/credentials` 等老路径保留 | 不破坏 AI 导入脚本和现有前端 |
| 进度面板共存 | 浮动窗口保留 + 独立页面 `/upload` | 用户习惯不同，提供两种入口 |

### 3.3 数据模型

新增表：

```sql
-- 上传批次（一次拖拽/选择 = 一个批次）
CREATE TABLE upload_batches (
  id VARCHAR(32) PRIMARY KEY,
  user_id UUID,
  total_files INT,
  total_size BIGINT,
  completed_files INT DEFAULT 0,
  failed_files INT DEFAULT 0,
  status VARCHAR(16),                -- active/completed/aborted
  created_at TIMESTAMP,
  finished_at TIMESTAMP
);

-- 分片上传 sessions
CREATE TABLE multipart_uploads (
  id VARCHAR(32) PRIMARY KEY,         -- 我们的 uploadId
  batch_id VARCHAR(32),
  user_id UUID,
  file_name VARCHAR(255),
  file_size BIGINT,
  obs_key VARCHAR(512),
  obs_upload_id VARCHAR(64),
  total_parts INT,
  part_size INT,                       -- 每片大小
  uploaded_parts JSONB DEFAULT '[]',   -- [{partNumber, etag, size}]
  status VARCHAR(16),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

---

## 4. 拆 ticket（待实施）

按 MVP 经验，每个 ticket 1-3 小时完成。**先拆到尽量细**，用户认可后再开工。

### Ticket 1：上传配置 + 物理盘适配（基础设施）
- [ ] `backend/app/core/config.py` 加 3 个配置（MAX_FILE_SIZE / CHUNK_SIZE / MULTIPART_THRESHOLD / TMP_DIR）
- [ ] 环境变量从 `.env` 读取
- [ ] `import_api.py` 用 `UPLOAD_TMP_DIR` 替代硬编码 `/tmp`
- [ ] `docker-compose.yml` 添加物理盘 volume 挂载
- [ ] 启动时校验 TMP_DIR 可写
- [ ] 验证：上传 ARW 100MB 不会写满 tmpfs

### Ticket 2：OBS Multipart Upload 服务封装
- [ ] `backend/app/services/obs_service.py` 加 4 个方法：
  - `init_multipart_upload(obs_key) -> uploadId`
  - `upload_part(obs_key, upload_id, part_number, data) -> etag`
  - `complete_multipart_upload(obs_key, upload_id, parts) -> None`
  - `abort_multipart_upload(obs_key, upload_id) -> None`
- [ ] 单元测试：模拟上传 3 parts → complete → 合并成功

### Ticket 3：分片上传 API（核心）
- [ ] 新增端点 `POST /api/upload/multipart/init`
  - 参数：fileName, fileSize, contentType, assetType, topCategoryId
  - 返回：uploadId, obsKey, totalParts, partSize, partUploadUrls: [{partNumber, url}]
- [ ] 新增端点 `POST /api/upload/multipart/part-complete`
  - 参数：uploadId, partNumber, etag, size
  - 写入 multipart_uploads 表
- [ ] 新增端点 `POST /api/upload/multipart/complete`
  - 参数：uploadId, parts
  - 校验所有 part 已上传 → 调 OBS complete → 创建素材 + 后续处理（缩略图/EXIF/AI）
- [ ] 新增端点 `POST /api/upload/multipart/abort`
- [ ] 新增端点 `GET /api/upload/multipart/:id/status`
  - 返回已上传 part 列表（断点续传用）
- [ ] Alembic 迁移：创建 multipart_uploads + upload_batches 表

### Ticket 4：前端分片上传器
- [ ] `frontend/src/lib/multipartUpload.ts` 新增：
  - `initMultipartUpload()` 拿 uploadId + 各 part URL
  - `uploadPart()` 单个 part 上传（XHR 进度）
  - `getMultipartStatus()` 断点续传用
  - `completeMultipartUpload()` 全部完成
  - `abortMultipartUpload()` 取消
- [ ] 文件 > 100MB 自动走分片
- [ ] 断点恢复：localStorage 存 uploadId + 已完成 part 列表，重连后跳过

### Ticket 5：上传进度事件流（SSE）
- [ ] 新增端点 `GET /api/upload/events?batchId=xxx` (SSE)
- [ ] 后端在 complete 处理流程中发 SSE：
  - `processing_thumb` → `processing_exif` → `processing_ai_tag` → `completed`
- [ ] 前端 EventSource 客户端，断线重连
- [ ] 用于独立上传页面实时刷新

### Ticket 6：独立上传页面骨架
- [ ] 新增路由 `/upload` 在 `App.tsx`
- [ ] 新增页面 `frontend/src/pages/UploadPage.tsx`
- [ ] 左侧：批次列表
- [ ] 右侧：选中批次的文件列表 + 进度详情
- [ ] 顶栏"上传中: 12/30"统计（订阅 SSE）
- [ ] 跳转链接：上传完成后可点击跳到素材详情

### Ticket 7：上传页面状态机 UI
- [ ] 阶段进度条组件（OBS 上传 / 缩略图 / EXIF / AI打标 / pHash）
- [ ] 单文件详情卡片：每阶段独立状态（pending/running/done/failed）
- [ ] 网速显示（XHR 计算 lastLoad - thisLoad / interval）
- [ ] 文件大小 + 已传 + 百分比

### Ticket 8：暂停/继续/重试/移除
- [ ] 暂停按钮：直传场景暂停发送请求，分片场景记录 lastPartNumber
- [ ] 继续按钮：恢复上传
- [ ] 重试按钮：失败文件重新上传
- [ ] 移除按钮：从列表移除（已完成/失败可选）

### Ticket 9：浮动面板与独立页面共存
- [ ] 浮动面板加"查看全部"按钮 → 跳转 `/upload`
- [ ] 独立页面"返回首页"按钮 → 跳转 `/`
- [ ] 浮动面板简化（只显示最近一批 + 快捷入口）

### Ticket 10：端到端验证
- [ ] 上传 50MB JPG（直传路径）→ 验证流程
- [ ] 上传 200MB ARW（分片路径）→ 验证分片流程
- [ ] 上传 1GB MP4（分片路径）→ 验证大文件
- [ ] 中途断网 → 重连 → 验证断点续传（跳过已完成的 part）
- [ ] 上传 10 个文件 → 验证 3 并发 + 进度统计
- [ ] AI 导入脚本仍然走 `credentials + assets` 接口，验证不破坏

### Ticket 11：文档更新
- [ ] `docs/API.md` 新增分片上传 5 个端点
- [ ] `docs/adr/0021-multipart-upload.md` 新建（架构决策）
- [ ] `docs/adr/0022-upload-page.md` 新建（独立页面决策）
- [ ] `docs/ai-import-guide.md` 加"5M 可配置"说明，验证流程不变

---

## 5. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| OBS 分片 API 签名复杂 | 开发周期长 | Ticket 2 先做 POC，确认能用 |
| 断点续传状态一致性 | 多端登录/重连可能冲突 | uploadId 存 Redis 带用户标识 |
| 物理盘容量监控 | 256GB 跑满 | 启动时检查 + 定期 cron 清理 |
| SSE 兼容性（nginx 反代缓冲） | 进度不更新 | nginx 加 `proxy_buffering off` |
| 前端切片内存压力（>1GB 文件） | OOM | 用 `File.slice()` + `Blob` 流式上传，O(1) 内存 |
| 老 API 用户兼容 | AI 导入脚本可能挂 | Ticket 3 不改老端点，新增 `/multipart/*` |

---

## 6. 验收清单

- [ ] 50MB JPG 直传成功，进度面板实时更新
- [ ] 200MB ARW 分片上传成功，断网重连后续传成功
- [ ] 1GB MP4 分片上传成功
- [ ] 10 个 100MB 文件并发上传，进度面板显示网速+总进度
- [ ] 独立 `/upload` 页面可看每个文件的所有阶段状态
- [ ] 浮动窗口可点击跳转到独立页面
- [ ] 物理盘 `/data/imagehub-tmp` 挂载成功，临时文件不写满
- [ ] 单文件大小可通过环境变量配置
- [ ] AI 导入脚本（`docs/ai-import-guide.md`）无需修改仍能跑通
- [ ] 顶栏"上传中: 12/30"实时刷新
- [ ] 失败文件可重试，已完成文件可移除

---

## 7. 待用户确认事项

1. **方案整体是否认可？** 上面 11 个 ticket 是预期工作量
2. **优先级**：断点续传（需求4）和独立上传页面（需求5）哪个先做？
3. **物理盘挂载路径**：`/data/imagehub-tmp` 默认，可以接受？还是想用别的路径？
4. **单文件上限**：默认 2GB 是否合理？（OBS 单 PUT 上限 5GB）
5. **分片阈值**：默认 100MB（>此值走分片），可以吗？
6. **独立上传页面入口**：要不要保留浮动窗口？只保留独立页面？或两者共存？

确认后我会按 ticket 逐个实施，每个 ticket 完成会做**纯视觉验证**（你之前定的硬约束）。