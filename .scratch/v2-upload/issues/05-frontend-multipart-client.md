# 05 — 前端分片上传器（带断点续传）

**What to build:** `multipartUpload()` 工具函数，自动判断文件大小走直传或分片，自动并发、自动恢复断点。完成后前端调用 `uploadFiles()` 传任意大小的文件都能"撒手不管"，网络断了重连后自动续传。

**Blocked by:** #03

**Status:** ready-for-agent

- [ ] `frontend/src/lib/multipartUpload.ts`：`initMultipartUpload()` / `uploadPart()` / `completeMultipartUpload()` / `getMultipartStatus()`
- [ ] 文件 > 100MB 自动走分片，否则走原有预签名直传
- [ ] 单文件分片：每片 8MB，3 并发上传
- [ ] 断点恢复：localStorage 存 `{uploadId, fileName, obsKey, uploadedParts}`，下次上传同文件先查 status 跳过已传 part
- [ ] 网速计算：每个 part 维护 lastLoaded+timestamp，rate = delta/seconds
- [ ] 取消：每个 part 的 XHR 持有 ref，用户取消时 abort 所有
- [ ] 验收：浏览器 devtools 模拟 200MB ARW 上传 → 主动断网 → 重连 → 自动从 part 5 续传完成