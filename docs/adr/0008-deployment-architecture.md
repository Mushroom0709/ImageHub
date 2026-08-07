# ADR 0008 — 部署架构：ECS + Docker Compose + OBS + 本地大模型

**状态：Accepted** · 2026-08-08

## 部署环境

- **服务器**：ECS `ecs-xj-ai-service`
  - SSH: `root@27.18.114.8:10332`
  - 业务端口: `10.20.30.191:10388` → NAT → `27.18.114.8:10388`
  - 工作路径: `/home/workspace/ImageHub/`
  - 2 块 1T 磁盘：`/home/workspace/` + `/var/lib/docker/`

- **服务编排**：Docker Compose，4 个容器
  - `imagehub-web` — 前端（Nginx 静态托管）
  - `imagehub-api` — 后端 FastAPI
  - `imagehub-worker` — 异步任务 worker（同镜像，不同启动命令）
  - `imagehub-db` — PostgreSQL
  - `imagehub-redis` — Redis（缓存 + 队列）

- **存储**：OBS 对象存储（全桶私有，预签名 URL 访问）

- **AI 模型**：本地部署的 Qwen3.6-27B（4× A100-40GB, TP=4）
  - API: `http://10.20.30.191:10203/v1/chat/completions`（内网地址）
  - API Key: `a1bbbc249fba8e2a3bbf04458224bbefbd26e4787e1bf3671edc3857f9d99c6c`
  - 256K 上下文，256 并发

## 端口分配

| 服务 | 容器内端口 | 宿主机端口 | 外网 |
|---|---|---|---|
| 前端 Web | 80 | 10388 | ✅ `27.18.114.8:10388` |
| 后端 API | 8000 | 10389 | 可选（前端同域代理） |
| PostgreSQL | 5432 | 10390 | 不映射外网（仅内网） |
| Redis | 6379 | - | 不映射（仅容器内网） |

> 后端 API 通过前端 Nginx 反代 `/api/`，不需要单独暴露外网端口。
