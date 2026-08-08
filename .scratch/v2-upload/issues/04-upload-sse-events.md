# 04 — 上传进度事件流（SSE 端点）

**What to build:** 独立 SSE 端点，前端订阅后实时接收后端处理阶段（缩略图/EXIF/AI打标/pHash）的进度推送。完成后任意页面都可以订阅"某批次"的进度更新，UI 不轮询、不延迟。

**Blocked by:** #01

**Status:** ready-for-agent

- [ ] `GET /api/upload/events?batchId=xxx` (SSE) 端点
- [ ] 后端处理管线（缩略图/EXIF/AI/入库）每完成一阶段推 SSE 事件
- [ ] SSE 事件类型：`file_update`（阶段变化）/`file_complete`（文件完成）/`batch_complete`（整批完成）
- [ ] 数据格式：`{fileIndex, stage, progress, assetId?, message?}`
- [ ] 断开重连：客户端记录 lastEventId，服务端从 Redis 补发未确认事件
- [ ] 验收：手动开 SSE 客户端订阅，发起上传，能看到 5 个文件依次推进 `obs→thumb→exif→ai→completed` 事件