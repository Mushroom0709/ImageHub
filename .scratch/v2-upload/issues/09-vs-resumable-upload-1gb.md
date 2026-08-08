# 09 — Vertical slice: 上传 1GB MP4 分片 + 断点续传（端到端）

**What to build:** 上传 1GB 视频时主动断网 → 重连后自动续传，不重传已完成的 part → 全部完成后服务器抽封面帧、生成缩略图。端到端验证大文件断点续传场景。

**Blocked by:** #08

**Status:** ready-for-agent

- [ ] 端到端：上传 1GB MP4 → 走到 part 30 时 kill 浏览器网络 → 重连 → 验证只上传 part 31+，跳过 1-30
- [ ] 验证 `localStorage` 存了 `uploadId`/`uploadedParts`，重连后查询 status 跳过
- [ ] 服务器抽封面 + 缩略图正常（视频同样走分片）
- [ ] OBS 上最终对象完整可播放
- [ ] 验收：devtools 模拟网络中断 2 次，3 次上传完成，OBS 对象大小=上传总和（无重复 part）