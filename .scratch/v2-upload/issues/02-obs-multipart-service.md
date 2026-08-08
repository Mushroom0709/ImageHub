# 02 — OBS Multipart Upload 服务封装

**What to build:** `obs_service` 提供 5 个 multipart 方法（init/upload_part/complete/abort/list_parts），后端其他模块可以一键调用 OBS 分片协议。完成后任意业务方都能用 5 行 Python 完成"分片上传一个 1GB 文件"。

**Blocked by:** None — can start immediately（与 #01 并行）

**Status:** ready-for-agent

- [ ] `obs_service.init_multipart_upload(obs_key) -> uploadId`
- [ ] `obs_service.upload_part(obs_key, upload_id, part_number, data) -> etag`
- [ ] `obs_service.complete_multipart_upload(obs_key, upload_id, parts) -> None`（parts 列表含 partNumber+etag）
- [ ] `obs_service.abort_multipart_upload(obs_key, upload_id) -> None`
- [ ] `obs_service.list_uploaded_parts(obs_key, upload_id) -> [{partNumber, etag, size}]`（断点续传用）
- [ ] 单元测试：模拟 5 parts 上传 → list → complete → 实际 OBS 对象可访问