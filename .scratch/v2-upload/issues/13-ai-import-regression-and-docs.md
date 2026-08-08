# 13 — AI 导入脚本回归测试 + docs 更新

**What to build:** 验证 AI 导入脚本（`docs/ai-import-guide.md` 描述的流程）在新架构下仍然可用，并补充文档（API 新增端点、新建 ADR）。

**Blocked by:** #03（API 完成后才能测 AI 导入回归）

**Status:** ready-for-agent

- [ ] 跑 `docs/ai-import-guide.md` 第 7 章的完整 Python 示例脚本，验证预签名直传 + 创建素材流程
- [ ] 验证：sourceType=ai_import 成功入库 + 标签写入
- [ ] `docs/API.md` 补充 5 个新端点（init/part-complete/complete/abort/status）+ SSE events 端点
- [ ] 新建 `docs/adr/0021-multipart-upload.md`（架构决策：为什么用 OBS Multipart）
- [ ] 新建 `docs/adr/0022-upload-page.md`（决策：为什么独立页面 + 浮动窗口共存）
- [ ] 更新 `docs/ai-import-guide.md` 增加"5MB 可配置"说明 + 物理盘环境变量
- [ ] 验收：AI 导入脚本跑通 5 张图片入库，文档 diff 可读