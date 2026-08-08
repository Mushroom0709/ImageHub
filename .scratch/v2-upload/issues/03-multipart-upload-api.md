# 03 — 分片上传后端 API（5 个端点）+ DB 表

**What to build:** 完成"前端 → 后端 → OBS"分片上传的所有后端脚手架：5 个 REST 端点 + `multipart_uploads` / `upload_batches` 两张表 + Alembic 迁移。完成后任意前端（包括 AI 导入脚本）都能调这 5 个端点完成一个分片上传的全流程，断点续传通过 `GET /status` 拿已完成 part 列表实现。

**Blocked by:** #01, #02

**Status:** ready-for-agent

- [ ] Alembic 迁移创建 `multipart_uploads` / `upload_batches` 两张表
- [ ] `POST /api/upload/multipart/init`：body `{fileName,fileSize,contentType,assetType,topCategoryId}` → `{uploadId,obsKey,totalParts,partSize,partUploadUrls:[{partNumber,url}]}`
- [ ] `POST /api/upload/multipart/part-complete`：body `{uploadId,partNumber,etag,size}` → `{ok}`，写 `multipart_uploads.uploaded_parts`
- [ ] `POST /api/upload/multipart/complete`：body `{uploadId,parts}` → 调 OBS complete + 触发缩略图/EXIF/AI打标 + 创建 Asset
- [ ] `POST /api/upload/multipart/abort`：body `{uploadId}` → 调 OBS abort + 标记 `multipart_uploads.status='aborted'`
- [ ] `GET /api/upload/multipart/:id/status`：返回 `{totalParts, partSize, uploadedParts:[{partNumber,etag,size}]}`（断点续传用）
- [ ] 现有 `POST /api/upload/credentials` + `POST /api/upload/complete` + `POST /api/assets` 路径完全保留（AI 导入脚本不破坏）
- [ ] 验收：curl 走完 init → 上传 3 个 part → part-complete → complete 完整流程，DB 有素材记录