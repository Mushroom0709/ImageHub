# 11 — 上传页面状态机 UI（5 阶段可视化）

**What to build:** 独立上传页面右侧文件列表显示每个文件的 5 阶段进度（OBS 上传 / 缩略图 / EXIF / AI 打标 / pHash），每阶段独立 pending/running/done/failed 状态 + 实时网速。完成后用户能看到"哪个文件卡在哪一步"。

**Blocked by:** #10

**Status:** ready-for-agent

- [ ] 阶段进度条组件 `UploadStageProgress.tsx`：5 个阶段，每阶段独立状态
- [ ] 单文件详情卡片：网速 + 当前阶段高亮 + 阶段图标（pending/running/done/failed）
- [ ] 网速 = XHR `(nowLoaded - lastLoaded) / (now - lastTime)` 平滑
- [ ] SSE 推送处理阶段时卡片自动高亮对应阶段
- [ ] 验收：上传 10 个文件，独立页面实时显示每文件的 5 阶段进度