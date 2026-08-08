# 14 — 端到端压力测试 + hermes verify 全绿

**What to build:** 50 个素材并发上传、混合大小（图片+视频+ARW），所有路径走通，hermes verify 状态为 ok。完成后 V2 上传模块正式可交付。

**Blocked by:** #07, #08, #09, #11, #12, #13

**Status:** ready-for-agent

- [ ] 混合 50 文件上传（10 JPG × 5MB + 10 ARW × 80MB + 10 MP4 × 500MB + 10 PNG × 2MB + 10 HEIC × 3MB）
- [ ] 3 并发路径走通 + 实时网速 + 5 阶段进度可见
- [ ] SSE 在 50 文件批量下不丢事件
- [ ] 物理盘 `/data/imagehub-tmp` 用量监控（写入/清理正常）
- [ ] 5GB 临时文件峰值未爆盘
- [ ] `hermes verify --json` 全绿（build ok / test ok / readiness 200）
- [ ] 验收：50 文件混合上传无失败，无 OBS 临时残留