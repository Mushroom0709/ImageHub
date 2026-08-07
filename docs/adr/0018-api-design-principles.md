# ADR 0018 — API 设计原则：后端厚前端薄 + 参数化接口

**状态：Accepted** · 2026-08-08

## 决策

### 核心原则
- **前端薄，后端厚**：前端只做展示和交互，所有业务逻辑在后端
- **API 参数化**：同一接口通过参数开关控制行为，避免重复接口
- **三种素材来源走同一套核心 API**，通过参数区分

### 核心创建接口

`POST /api/assets` — 统一的素材创建接口，通过参数适配三种来源：

| 参数 | 作用 | 用户上传 | AI 导入 | 链接采集 |
|---|---|---|---|---|
| `source_type` | 来源类型 | `upload` | `ai_import` | `xiaohongshu` / `douyin` |
| `auto_tag` | 是否启用 AI 打标 | ✅ true | ❌ false | ✅ true |
| `tags` | 直接传入的标签 | 空 | 外部 AI 标签 | 平台原始标签（可选）|
| `content_text` | AI 打标参考文本 | 空 | 可选 | 标题+文案+话题 |

### 采集接口
- `POST /api/collect/xiaohongshu` — 小红书单条链接采集
- `POST /api/collect/douyin` — 抖音单条链接采集
- `POST /api/collect/search` — 关键词搜索批量采集

所有采集统一走 **TikHub** 接口，后端封装 `CollectorService` 管理。

### 实时进度
所有异步操作（上传、采集、批量打标）通过 **SSE** 向前端推送进度。
见 ADR 0017。
