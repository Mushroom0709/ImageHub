# 08 — Vertical slice: 上传 200MB ARW 分片（端到端）

**What to build:** 用户拖一个 200MB ARW 文件 → 自动走分片上传 → 用户能看到 part 进度（如"part 3/25"）→ 服务器自动 dcraw -e 抽预览、生成缩略图、读 EXIF → 完成。端到端验证分片路径。

**Blocked by:** #07（直传通了再上分片）

**Status:** ready-for-agent

- [ ] 端到端：上传 200MB ARW → 自动检测 >100MB → 走 25 个分片 × 8MB
- [ ] 浮动面板显示"分片上传中：part X/25"+ 总进度
- [ ] 服务器处理：缩略图生成（注意 ARW 用 dcraw 抽 JPG 预览）+ EXIF + AI
- [ ] 缩略图能正常显示（不是 RAW 黑图）
- [ ] 验收：上传 200MB ARW 完整跑通，缩略图可见