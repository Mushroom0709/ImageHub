# 10 — 独立上传页面（/upload 路由 + 骨架）

**What to build:** 用户访问 `/upload` 看到一个完整的上传管理页：左侧是上传批次列表（每次上传是一行），右侧是选中批次的详情。完成后用户有了"上传管理"的概念入口。

**Blocked by:** #04, #06

**Status:** ready-for-agent

- [ ] 新增路由 `/upload` 在 `App.tsx`
- [ ] 新增页面 `frontend/src/pages/UploadPage.tsx`：左 320px 批次列表 + 右自适应详情
- [ ] 顶栏"上传中: X/Y"统计显示（订阅 SSE #04）
- [ ] 浮动面板加"查看全部 →"链接到 `/upload`
- [ ] 顶栏上传按钮旁加链接图标（也可跳 `/upload`）
- [ ] 验收：访问 `/upload` 看到页面骨架（无数据时空态），顶栏统计正确