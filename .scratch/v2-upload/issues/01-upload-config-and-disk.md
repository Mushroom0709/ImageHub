# 01 — 上传配置中心 + 物理盘适配

**What to build:** 把上传相关的所有阈值/路径做成配置中心，物理盘挂载点生效。完成后任何上传路径都从 `settings` 读取 `UPLOAD_MAX_FILE_SIZE` / `UPLOAD_CHUNK_SIZE` / `UPLOAD_MULTIPART_THRESHOLD` / `UPLOAD_TMP_DIR`，可通过 `.env` 环境变量覆盖；docker-compose 挂载宿主 256GB 物理盘到容器 `/data/imagehub-tmp`。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] `backend/app/core/config.py` 新增 4 个字段（带默认值 + 环境变量绑定）
- [ ] `import_api.py` 临时文件改用 `settings.UPLOAD_TMP_DIR` 替代硬编码 `/tmp`
- [ ] `docker-compose.yml` api 服务添加 `volumes: ["/mnt/storage:/data"]`（或环境约定的宿主路径）
- [ ] 启动时校验 `UPLOAD_TMP_DIR` 存在且可写，失败抛清晰错误
- [ ] `.env.example` 加 4 个新变量 + 注释
- [ ] 验收：本地配置生效（打印日志显示）；docker compose up 后 `UPLOAD_TMP_DIR=/data/imagehub-tmp` 写一个 50MB 测试文件不报错