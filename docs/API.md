# API 设计文档

> ImageHub 后端 API 完整列表。共 9 模块 · 38 接口。

## 通用约定

- 基础路径：`/api`
- 鉴权：Bearer Token（JWT），除 `/auth/login` 和 `/health` 外都需要登录
- 响应格式：`{ code: 0, data: {...}, message: "" }`
- 分页：`?page=1&size=20`，响应 `{ items: [], total: number, page: number, size: number }`
- 排序：`?sort=newest`（newest / oldest / quality / likes）
- 错误码：0 成功，非 0 失败，message 为错误描述

---

## 1. 认证 Auth — 3 个

### POST /auth/login
用户登录
```
Body:  { username: string, password: string }
Return: { token: string, user: User }
```

### GET /auth/me
获取当前用户信息
```
Return: User { id, username, avatar, role, createdAt }
```

### PUT /auth/password
修改密码
```
Body:  { oldPassword: string, newPassword: string }
Return: { ok: true }
```

---

## 2. 用户管理 Users — 3 个

> 仅管理员可调用

### GET /users
用户列表
```
Query: page, size
Return: { items: User[], total }
```

### POST /users
创建用户
```
Body:  { username: string, password: string, role?: 'user'|'admin' }
Return: User
```

### DELETE /users/:id
禁用/删除用户
```
Return: { ok: true }
```

---

## 3. 素材 Assets — 10 个

### GET /assets
素材列表（分页 + 筛选 + 排序 + 搜索）
```
Query:
  - page, size           分页
  - sort                 排序: newest / oldest / quality / likes
  - tagIds               标签 ID 列表，逗号分隔（AND 语义）
  - keyword              全文搜索关键词
  - sourceType           来源类型: upload / xiaohongshu / douyin / ai_import
  - starred              星标过滤: true / false / 不传
  - flagLevel            旗标等级过滤: 1-5 / 不传
  - trashed              是否看回收站: true（默认 false）
Return: { items: Asset[], total, page, size }
```

### GET /assets/:id
素材详情
```
Return: Asset {
  id, title, description, sourceType, sourceUrl,
  assetType: image/video, width, height, duration?,
  thumbUrl_small, thumbUrl_medium, thumbUrl_raw,  // 预签名 URL，短期有效
  starred, flagLevel,
  tags: Tag[],
  exif: {...},
  phash,
  createdAt, updatedAt, deletedAt
}
```

### POST /assets
创建素材（AI 导入 / 采集完成后调用）
```
Body: {
  title?, description?,
  sourceType, sourceUrl?, sourceId?,
  assetType: image/video,
  obsKey: string,           // OBS 原始文件路径
  fileName, fileSize,
  width, height, duration?,
  topCategoryId?: string,   // 归属项目 ID
  autoTag: boolean,                   // 是否启用 AI 自动打标
  contentText?: string,              // AI 打标参考文本（标题+文案+话题）
  tags?: [{ tagName, confidence, source }],  // 直接传入的标签
  starred?, flagLevel?,
}
Return: Asset
```

### PUT /assets/:id
修改素材信息
```
Body: { title?, description?, starred?, flagLevel? }
Return: Asset
```

### DELETE /assets/:id
删除素材（软删到回收站）
```
Return: { ok: true }
```

### POST /assets/batch-delete
批量删除
```
Body: { ids: string[] }
Return: { ok: true, count: number }
```

### POST /assets/batch-recover
批量恢复（从回收站）
```
Body: { ids: string[] }
Return: { ok: true, count: number }
```

### GET /assets/:id/thumb
获取缩略图（302 重定向到预签名 URL）
```
Query: size: small (300px) / medium (1200px) / raw (原图)
Return: 302 Redirect to OBS signed URL
```

### GET /assets/:id/stream
流式获取原图/原视频（后端代理，支持 Range 206）
```
Header: Range: bytes=start-end  (可选，如 Range: bytes=0-1048575)
Return: 二进制流 (image/* 或 video/mp4)
        支持 Range: 206 Partial Content + Content-Range
        Accept-Ranges: bytes
```
> 用途：Lightbox 视频流式播放、跨域场景下的大图加载。
> 同源请求，无 CORS 问题；视频可边下边播。

### GET /assets/:id/similar
相似素材（按 pHash）
```
Query: limit: number (默认 12)
Return: { items: Asset[] }
```

### GET /assets/:id/exif
EXIF 详情
```
Return: {
  camera: string, lens: string,
  aperture: string, shutter: string, iso: number, focalLength: string,
  captureTime: string, gps?: { lat, lng },
  raw: {...}  // 完整 EXIF
}
```

---

## 4. 标签 Tags — 7 个

### GET /tags/tree
标签分类树
```
Query: category?: scene|style|clothing|makeup|pose_type|composition|mood|body_focus|info
       不传返回所有分类的树
Return: TagTree {
  [category]: [{ id, name, children: [...] }, ...]
}
```

### GET /tags/:id
标签详情
```
Return: Tag { id, name, category, parentId, alias: string[], status, sortOrder, assetCount }
```

### POST /tags
创建标签
```
Body: { name, category, parentId?, alias?: string[] }
Return: Tag
```

### PUT /tags/:id
修改标签
```
Body: { name?, alias?, parentId?, sortOrder? }
Return: Tag
```

### DELETE /tags/:id
删除标签（同时移除所有素材的该标签关联）
```
Return: { ok: true, affectedCount: number }
```

### POST /tags/:id/merge
合并标签（把当前标签合并到目标标签）
```
Body: { targetTagId: string }
Return: { ok: true, mergedCount: number }
```

### GET /tags/search
标签搜索联想
```
Query: q: string, category?: string, limit?: number (默认 10)
Return: Tag[]
```

---

## 5. 素材-标签关联 Asset Tags — 3 个

### POST /assets/:id/tags
给素材打标签（批量添加）
```
Body: { tagIds: string[] }
Return: { ok: true, tags: Tag[] }
```

### DELETE /assets/:id/tags/:tagId
移除一个标签
```
Return: { ok: true }
```

### POST /assets/batch-tag
批量打标
```
Body: {
  assetIds: string[],
  addTagIds?: string[],     // 要添加的标签
  removeTagIds?: string[],  // 要移除的标签
}
Return: { ok: true, affectedCount: number }
```

---

## 6. 上传 Upload — 3 个

### POST /upload/credentials
申请上传凭证（批量预签名 URL）
```
Body: {
  files: [{ fileName, fileSize, contentType, assetType: 'image' | 'video' }],
  topCategoryId?: string,   // 归属项目 ID
}
Return: {
  uploadId: string,
  credentials: [{ fileIndex, uploadUrl, obsKey }]
  // 前端用 uploadUrl 直传 OBS，obsKey 是完成回调时用的标识
}
```
> 上传时不要设置 Content-Type 请求头（OBS V2 签名签空字符串，带了会 403）。

### POST /upload/complete
上传完成回调
```
Body: {
  uploadId: string,
  topCategoryId?: string,   // 归属项目 ID
  files: [{ fileIndex, obsKey, fileName, fileSize, width?, height? }]
}
Return: {
  assetIds: string[],   // 已创建的素材 ID（按 fileIndex 顺序）
}
```
> 触发后续处理：缩略图生成 + EXIF 读取 + AI 打标
> 视频会抽封面帧 + 取分辨率

### POST /upload/from-url
从 URL 下载上传
```
Body: { url: string, autoTag?: boolean }
Return: { taskId: string }  // 异步任务，通过 SSE 或任务查询看进度
```

---

## 7. 采集 Collect — 5 个

### POST /collect/xiaohongshu
小红书单条链接采集
```
Body: { url: string, autoTag?: boolean = true }
Return: { taskId: string }
```

### POST /collect/douyin
抖音单条链接采集
```
Body: { url: string, autoTag?: boolean = true }
Return: { taskId: string }
```

### GET /collect/tasks
采集任务列表
```
Query: page, size, platform?, status?
Return: { items: CollectTask[], total }
```

### GET /collect/tasks/:id
采集任务详情
```
Return: CollectTask {
  id, platform, url, status: pending|running|done|failed,
  totalCount, successCount, skipCount, failCount,
  assets: Asset[],   // 采集到的素材（前 N 个）
  errorMessage?,
  createdAt, startedAt, finishedAt
}
```

### GET /collect/tasks/:id/stream
SSE 采集进度流
```
Server-Sent Events:
  - progress: { current, total, step, message }
  - asset: Asset  (每成功一个推一个)
  - done: { successCount, failCount, skipCount }
  - error: { message }
```

---

## 8. 搜索 Search — 1 个

### GET /search/suggest
搜索建议（标签 + 素材标题）
```
Query: q: string, limit?: number (默认 8)
Return: {
  tags: Tag[],
  assets: Asset[]  // 只返回 id + title + thumb
}
```

> 素材全文搜索直接用 `GET /assets?keyword=xxx`

---

## 9. 导出 Export — 2 个

### POST /assets/export
批量导出（打包 zip 上传到 OBS）
```
Body: { assetIds: string[], size?: 'small'|'medium'|'raw' = 'raw' }
Return: { taskId: string }
```

### GET /exports/:id
导出任务状态 + 下载链接
```
Return: {
  id, status: pending|processing|done|failed,
  totalCount, processedCount,
  downloadUrl?: string,   // 预签名下载链接，任务完成后有
  fileSize?: number,
  createdAt, finishedAt?
}
```

---

## 10. 系统 System — 1 个

### GET /health
健康检查
```
Return: {
  status: 'ok',
  version: string,
  database: 'ok' | 'error',
  redis: 'ok' | 'error',
  obs: 'ok' | 'error',
  meilisearch: 'ok' | 'error',
}
```

---

## SSE 接口汇总

| 路径 | 用途 |
|---|---|
| GET /upload/progress | 上传 + 处理进度 |
| GET /collect/tasks/:id/stream | 采集任务进度 |

SSE 事件格式：
```
event: progress
data: { step: 'uploading'|'processing'|'tagging'|'done', current, total, message, assetId? }
```

---

## 数据模型摘要

### Asset
```ts
{
  id: string
  title: string
  description: string
  sourceType: 'upload' | 'xiaohongshu' | 'douyin' | 'ai_import'
  sourceId: string
  sourceUrl: string
  assetType: 'image' | 'video'
  obsBucket: string
  obsKey: string
  fileSize: number
  width: number
  height: number
  duration: number | null   // 视频时长(秒)
  phash: string | null      // 64位十六进制
  exif: Record<string, any> | null
  starred: boolean
  flagLevel: number | null  // 1-5
  qualityScore: number      // 0-100
  tags: Tag[]
  uploaderId: string
  createdAt: Date
  updatedAt: Date
  deletedAt: Date | null
}
```

### Tag
```ts
{
  id: string
  name: string
  category: 'scene' | 'style' | 'clothing' | 'makeup' | 'pose_type' | 'composition' | 'mood' | 'body_focus' | 'info'
  parentId: string | null
  alias: string[]
  status: 'active' | 'pending'
  sortOrder: number
  assetCount: number
  createdAt: Date
}
```

### User
```ts
{
  id: string
  username: string
  passwordHash: string
  avatar: string
  role: 'admin' | 'user'
  createdAt: Date
}
```

### CollectTask
```ts
{
  id: string
  platform: 'xiaohongshu' | 'douyin'
  url: string
  status: 'pending' | 'running' | 'done' | 'failed'
  totalCount: number
  successCount: number
  skipCount: number
  failCount: number
  errorMessage: string | null
  createdAt: Date
  startedAt: Date | null
  finishedAt: Date | null
}
```
