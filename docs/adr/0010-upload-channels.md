# ADR 0010 — 上传方式：全渠道支持

**状态：Accepted** · 2026-08-08 · 更新于 2026-08-08

## 决策

支持全部 5 种上传方式：

| 方式 | 状态 | 说明 |
|---|---|---|
| 1. 拖拽上传 | ✅ 已实现 | 拖文件或文件夹到页面任意位置，支持递归读取文件夹 |
| 2. 点击选择文件 | ✅ 已实现 | 上传按钮下拉 → "上传文件"，multiple 多选 |
| 3. 点击选择文件夹 | ✅ 已实现 | 上传按钮下拉 → "上传文件夹"，webkitdirectory 递归 |
| 4. 剪贴板粘贴 | ⏳ 待实现 | Ctrl+V / Cmd+V 粘贴图片 |
| 5. URL 下载 | ✅ 已实现 | `/api/upload/from-url` 端点，后端下载到 OBS |

> 文件夹上传**不保留原目录结构**，所有文件扁平化存入 OBS，按日期 + upload_id 打散。

## 上传流程

预签名 URL 直传 OBS：

```
前端                                  后端                    OBS
 │                                    │                       │
 ├── 1. POST /upload/credentials ─────>│                       │
 │   (文件列表+类型+项目ID)            │                       │
 │                                    ├── 2. 生成预签名PUT URL───>│
 │<── 3. 返回 uploadId + uploadUrls ──┤                       │
 │                                    │                       │
 ├── 4. PUT 直传文件（3并发）──────────────────────────────────>│
 │   (XHR upload.onprogress 实时进度) │                       │
 │                                    │                       │
 ├── 5. POST /upload/complete ───────>│                       │
 │   (uploadId + obsKey列表)          │                       │
 │                                    ├── 6. 写DB + 缩略图 + EXIF──┤
 │                                    ├── 7. AI 打标            │
 │<── 8. 返回 assetIds ───────────────┤                       │
```

**注意：OBS V2 签名的 Content-Type 为空字符串，前端上传时不能设置 Content-Type 请求头，否则签名校验 403。**

## 上传进度（前端实现）

- 并发数：3
- 状态：waiting → uploading → processing → done / failed
- 总进度：按字节计算（已上传总字节 / 总大小）
- 单文件进度：XHR upload.onprogress，百分比
- 展示：右下角浮动面板，可关闭

## 支持的文件格式

| 类别 | 格式 |
|---|---|
| 图片 | JPG, PNG, WebP, GIF, BMP, TIFF |
| RAW | ARW（索尼）、CR2（佳能）、NEF（尼康）、DNG |
| 视频 | MP4, MOV, AVI, MKV, WEBM |

## OBS 存储目录约定

```
ImageHub/
  raw/
    image/
      YYYY/MM/DD/{upload_id}_{index}.{ext}
    video/
      YYYY/MM/DD/{upload_id}_{index}.{ext}
  thumb/
    small/   (300px 等比缩放)
    medium/  (1200px 等比缩放)
```

- 上传时按 `assetType` 参数决定存 image/ 还是 video/ 目录
- 不保留原始文件名（用 upload_id + index 替代，避免重名和路径注入）
- 原始文件名存在 DB 的 `file_name` 字段
