# AI 批量导入指南

> 外部 AI 系统（如 minimax、deepseek、自定义爬虫）将图片/视频及已打好的标签批量导入 ImageHub 的完整说明。

---

## 1. 什么是 AI 导入

AI 导入是指**外部 AI 程序**（不是 ImageHub 内置的 AI 打标）将自己采集、生成或处理好的素材连同标签一起写入 ImageHub。

**与内置 AI 打标的区别：**

| | 内置 AI 打标 | AI 导入（外部） |
|---|---|---|
| 触发方 | 用户上传后自动触发 | 外部 AI 主动调用 API |
| 打标方 | ImageHub 后端的 Qwen 模型 | 外部 AI 自己打好标签传过来 |
| 标签来源 | AI 自动识别 9 大维度 | 外部 AI 自定义（可遵循 9 大分类，也可自建） |
| 素材来源标记 | `upload` / `xiaohongshu` / `douyin` | `ai_import` |

**适用场景：**
- 你有自己的 AI 采集脚本（爬取某个网站/平台）
- 你有本地批量处理好的素材 + 标签数据
- 第三方 AI 生成工具（如 Midjourney / SD 批量出图）需要归档
- 多套 AI 流水线需要汇聚到同一个 ImageHub

---

## 2. 两种导入方式对比

### 方式 A：预签名直传 OBS（推荐）⭐

```
AI 脚本 ──1. 申请凭证──> ImageHub API
   │                           │
   │<──2. 返回预签名 PUT URL───┤
   │                           │
   └──────3. PUT 直传文件────────────> OBS（华为云）
   │                           │
   └──4. 注册素材+标签────────> ImageHub API
```

**优点：**
- 大文件不走 ImageHub 服务器带宽，速度快
- 并发不受后端限制，可多线程上传
- 符合 ImageHub 的标准上传路径，处理流水线一致
- 支持视频和图片

**缺点：**
- 需要 3-4 步 API 调用，稍复杂

### 方式 B：multipart 走后端（适合小文件批量）

```
AI 脚本 ──multipart 多文件 POST──> ImageHub API ──> OBS
                                   └─> 缩略图/EXIF/入库
```

**优点：**
- 一步到位，调用简单
- 后端自动处理缩略图/EXIF/AI打标（如果需要）

**缺点：**
- 文件经过后端中转，占用服务器带宽
- 大文件（>50MB）可能超时
- 单请求有大小限制

### 选型建议

| 文件大小 | 数量 | 推荐方式 |
|---|---|---|
| < 10MB | 少量（<10个） | 方式 B（简单） |
| < 10MB | 大量（>100个） | 方式 A（并发快） |
| > 10MB / 视频 | 任意 | 方式 A（必选） |
| ARW / RAW 大文件 | 任意 | 方式 A（必选） |

---

## 3. 前置准备

### 3.1 获取账号

找管理员创建一个 AI 专用账号（建议角色 `user`，不要用 `admin`）。每个 AI 流水线用独立账号，方便追溯素材来源。

### 3.2 获取 Token

调用登录接口获取 JWT Token：

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "ai_bot_1",
  "password": "your_password"
}
```

**响应：**
```json
{
  "code": 0,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user": {
      "id": "uuid",
      "username": "ai_bot_1",
      "role": "user"
    }
  }
}
```

**Token 有效期：默认 7 天。** 过期后重新登录获取。所有后续请求在 Header 中携带：

```
Authorization: Bearer <access_token>
```

### 3.3 确认目标项目 ID（可选）

如果要把导入的素材归入某个项目（顶层分类），先获取项目列表找到 `topCategoryId`：

```http
GET /api/top-categories
Authorization: Bearer <token>
```

返回的 `id` 字段就是项目 ID。

---

## 4. 方式 A：预签名直传（详细步骤）

### 步骤 1：申请上传凭证

批量申请，一次最多 100 个文件（建议每次 20-50 个）。

```http
POST /api/upload/credentials
Content-Type: application/json
Authorization: Bearer <token>

{
  "files": [
    {
      "fileName": "IMG_0001.jpg",
      "fileSize": 2457600,
      "contentType": "image/jpeg",
      "assetType": "image"
    },
    {
      "fileName": "video_001.mp4",
      "fileSize": 52428800,
      "contentType": "video/mp4",
      "assetType": "video"
    }
  ],
  "topCategoryId": "项目ID或null"
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| files | array | ✅ | 文件列表，每次建议 ≤ 50 个 |
| files[].fileName | string | ✅ | 原始文件名（含扩展名） |
| files[].fileSize | number | ✅ | 文件大小（字节） |
| files[].contentType | string | | MIME 类型，传了也不用于签名（OBS V2 签空字符串） |
| files[].assetType | string | ✅ | `image` 或 `video`，决定存在 image/ 还是 video/ 目录 |
| topCategoryId | string | | 归属项目 ID，不传则归入"未分类" |

**响应：**
```json
{
  "code": 0,
  "data": {
    "uploadId": "a1b2c3d4",
    "credentials": [
      {
        "fileIndex": 0,
        "uploadUrl": "https://obs-mushroom.obs.cn-central-221.ovaijisuan.com/ImageHub/raw/image/2026/08/08/a1b2c3d4_0.jpg?Expires=...&AccessKeyId=...&Signature=...",
        "obsKey": "raw/image/2026/08/08/a1b2c3d4_0.jpg"
      },
      {
        "fileIndex": 1,
        "uploadUrl": "https://obs-mushroom.obs.cn-central-221.ovaijisuan.com/ImageHub/raw/video/2026/08/08/a1b2c3d4_1.mp4?Expires=...",
        "obsKey": "raw/video/2026/08/08/a1b2c3d4_1.mp4"
      }
    ]
  }
}
```

### 步骤 2：上传文件到 OBS

用拿到的 `uploadUrl` 直接 PUT 文件内容到 OBS。

**⚠️ 重要：PUT 请求不要设置 Content-Type 头。**
OBS V2 签名把 Content-Type 签为空字符串，如果请求带了 Content-Type，签名校验会失败（HTTP 403）。

**Python 示例：**
```python
import httpx

# 单个文件上传
def upload_to_obs(upload_url: str, file_path: str) -> bool:
    with open(file_path, 'rb') as f:
        content = f.read()

    # 不要设置 Content-Type！
    r = httpx.put(upload_url, content=content, timeout=300)
    return r.status_code in (200, 201)
```

**curl 示例：**
```bash
curl -X PUT "$UPLOAD_URL" \
  --data-binary @IMG_0001.jpg \
  -H "Content-Type:"   # 强制清空 Content-Type
```

**并发上传建议：** 同时上传 3-5 个文件，不宜过多（OBS 有速率限制）。

### 步骤 3：注册素材 + 标签

文件上传成功后，调用创建素材接口登记元数据和标签。

**可以逐个注册，也可以批量循环调用。**

```http
POST /api/assets
Content-Type: application/json
Authorization: Bearer <token>

{
  "title": "IMG_0001",
  "description": "AI 自动采集的人像照片",
  "sourceType": "ai_import",
  "sourceId": "external_bot_001_IMG_0001",
  "sourceUrl": "https://example.com/post/123",
  "assetType": "image",
  "obsKey": "raw/image/2026/08/08/a1b2c3d4_0.jpg",
  "fileName": "IMG_0001.jpg",
  "fileSize": 2457600,
  "topCategoryId": "项目ID或null",
  "width": 2048,
  "height": 1365,
  "autoTag": false,
  "tags": [
    { "tagName": "户外", "confidence": 0.95, "source": "ai" },
    { "tagName": "全身照", "confidence": 0.88, "source": "ai" },
    { "tagName": "JK制服", "confidence": 0.92, "source": "ai" },
    { "tagName": "甜妹", "confidence": 0.75, "source": "ai" }
  ]
}
```

**字段说明（AI 导入常用）：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| title | string | | 标题，不传则用 fileName |
| description | string | | 描述/文案 |
| sourceType | string | ✅ | **必须为 `"ai_import"`**，标记为 AI 导入来源 |
| sourceId | string | | 外部系统的唯一 ID（用于去重/溯源） |
| sourceUrl | string | | 原始来源链接 |
| assetType | string | ✅ | `image` 或 `video` |
| obsKey | string | ✅ | 步骤 1 返回的 obsKey，必须完全一致 |
| fileName | string | ✅ | 原始文件名 |
| fileSize | number | ✅ | 文件大小（字节） |
| topCategoryId | string | | 归属项目 ID |
| width / height | number | | 宽高（像素），不传则后端自动读取 |
| autoTag | boolean | | **AI 导入建议设为 `false`**，标签由你自己传入 |
| tags | array | | 标签列表（见下方标签规范） |
| starred | number | | 星标等级 0-5（0=无） |
| flagLevel | number | | 旗标等级 0-4（0=无，1红2橙3黄4绿） |

**响应：**
```json
{
  "code": 0,
  "data": {
    "id": "uuid",
    "title": "IMG_0001",
    "assetType": "image",
    "tags": [...],
    ...
  }
}
```

### 步骤 4（可选）：调用 complete 批量注册

如果你的所有文件都上传完了，也可以用 `/api/upload/complete` 一次性注册所有素材。但这个接口不会附带自定义标签，只做素材登记 + 缩略图 + EXIF + AI打标。**有自定义标签需求请用 `POST /api/assets` 逐个注册。**

---

## 5. 方式 B：multipart 批量导入

适合小文件、数量不多的场景。一步到位。

```http
POST /api/import/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

top_category_id: 项目ID（可选）
files: <文件1>
files: <文件2>
files: <文件3>
...
```

**Python 示例：**
```python
import httpx

url = "http://your-imagehub-domain/api/import/upload"
headers = {"Authorization": "Bearer " + token}

files = []
for path in file_paths:
    files.append(("files", (os.path.basename(path), open(path, "rb"))))

data = {"top_category_id": top_category_id}  # 可选

r = httpx.post(url, headers=headers, files=files, data=data, timeout=300)
result = r.json()
```

**响应：**
```json
{
  "code": 0,
  "data": {
    "total": 3,
    "done": 2,
    "failed": 0,
    "skipped": 1,
    "results": [
      { "file": "IMG_0001.jpg", "status": "done", "asset_id": "uuid" },
      { "file": "IMG_0002.jpg", "status": "done", "asset_id": "uuid" },
      { "file": "README.txt", "status": "skipped", "reason": "不支持的格式 .txt" }
    ]
  }
}
```

**注意：**
- 此方式后端会自动做缩略图、EXIF、AI 打标（走内置 AI）
- 不能自定义标签（标签由内置 AI 打）
- 不支持 sourceType 设为 ai_import（来源标记为 `upload`）
- **文件很多时请分批上传**，每批建议 ≤ 20 个小文件

---

## 6. 标签规范

### 6.1 标签对象结构

```json
{
  "tagName": "标签名称",
  "confidence": 0.95,
  "source": "ai"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| tagName | string | ✅ | 标签名称，最大 64 字符 |
| confidence | number | | 置信度 0-1，默认 1.0 |
| source | string | | 来源：`ai`（AI 打标）/ `manual`（人工）/ `auto`（系统），AI 导入传 `"ai"` |

### 6.2 9 大分类（可选遵循）

ImageHub 内置 9 大标签分类。你可以选择遵循这套体系，也可以完全自定义。遵循的好处是标签自动归入正确分类，前端筛选体验好。

| 分类英文 | 分类中文 | 示例 |
|---|---|---|
| `scene` | 场景 | 户外、室内、街拍、海边、森林、城市 |
| `style` | 风格 | 日系、胶片、复古、暗黑、清新、赛博朋克 |
| `clothing` | 服装 | JK制服、洛丽塔、汉服、旗袍、卫衣、连衣裙 |
| `makeup` | 妆容 | 淡妆、浓妆、素颜、烟熏妆、纯欲 |
| `pose_type` | 姿势 | 全身照、半身照、特写、坐姿、站姿、回眸 |
| `composition` | 构图 | 对称构图、三分法、俯拍、仰拍、留白 |
| `mood` | 色调/情绪 | 暖色调、冷色调、治愈、忧郁、活力 |
| `body_focus` | 身材/身体 | 大长腿、小蛮腰、直角肩、梨形身材 |
| `info` | 信息类 | 相机/镜头/焦段等自动标签 |

**标签分类是自动推断的**：如果你的标签名在已有标签库中存在，自动归入对应分类。如果是新标签，默认归入 `pending` 状态（待审核），由用户在后台手动指定分类。

### 6.3 低置信度与待审核

- `confidence < 0.7` 的标签 → 自动标记为"待审核"，用户在审核区可以看到
- 新创建的标签（标签库中不存在的）→ 标记为 `pending` 状态
- 这是渐进式审核机制——标签立即生效可用，用户有空再批量审阅

---

## 7. 完整 Python 示例（方式 A）

```python
"""
ImageHub AI 批量导入脚本（预签名直传方式）
"""
import os
import httpx
from pathlib import Path

# ====== 配置 ======
API_BASE = "http://your-imagehub-domain/api"
USERNAME = "ai_bot_1"
PASSWORD = "your_password"
TOP_CATEGORY_ID = None  # 项目ID，或者 None 表示未分类
CONCURRENCY = 3
BATCH_SIZE = 20  # 每次申请凭证的文件数
# ==================


def login() -> str:
    """登录获取 token"""
    r = httpx.post(f"{API_BASE}/auth/login", json={
        "username": USERNAME,
        "password": PASSWORD,
    })
    r.raise_for_status()
    data = r.json()
    if data["code"] != 0:
        raise Exception(f"登录失败: {data['message']}")
    return data["data"]["access_token"]


def get_credentials(token: str, files_info: list, top_category_id: str = None) -> dict:
    """批量申请上传凭证"""
    body = {
        "files": files_info,
    }
    if top_category_id:
        body["topCategoryId"] = top_category_id

    r = httpx.post(
        f"{API_BASE}/upload/credentials",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
    )
    r.raise_for_status()
    data = r.json()
    if data["code"] != 0:
        raise Exception(f"申请凭证失败: {data['message']}")
    return data["data"]


def upload_file(upload_url: str, file_path: str) -> bool:
    """上传单个文件到 OBS（不要设置 Content-Type！）"""
    with open(file_path, "rb") as f:
        content = f.read()

    # 不要加 Content-Type header
    r = httpx.put(upload_url, content=content, timeout=300)
    return r.status_code in (200, 201)


def create_asset(token: str, asset_data: dict) -> str:
    """创建素材并打标签"""
    r = httpx.post(
        f"{API_BASE}/assets",
        headers={"Authorization": f"Bearer {token}"},
        json=asset_data,
    )
    r.raise_for_status()
    data = r.json()
    if data["code"] != 0:
        raise Exception(f"创建素材失败: {data['message']}")
    return data["data"]["id"]


def import_folder(folder_path: str, token: str):
    """批量导入一个文件夹中的所有图片"""
    folder = Path(folder_path)
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

    # 收集所有图片文件
    all_files = []
    for p in folder.rglob("*"):  # 递归子目录
        if p.is_file() and p.suffix.lower() in image_exts:
            all_files.append(p)

    print(f"找到 {len(all_files)} 个图片文件")

    # 分批处理
    for batch_start in range(0, len(all_files), BATCH_SIZE):
        batch = all_files[batch_start:batch_start + BATCH_SIZE]
        print(f"处理第 {batch_start}-{batch_start + len(batch)} 个...")

        # 1. 准备文件信息
        files_info = []
        for p in batch:
            files_info.append({
                "fileName": p.name,
                "fileSize": p.stat().st_size,
                "contentType": "image/jpeg",
                "assetType": "image",
            })

        # 2. 申请凭证
        creds_data = get_credentials(token, files_info, TOP_CATEGORY_ID)
        upload_id = creds_data["uploadId"]
        credentials = creds_data["credentials"]

        # 3. 并发上传
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            futures = {}
            for i, (p, cred) in enumerate(zip(batch, credentials)):
                f = executor.submit(upload_file, cred["uploadUrl"], str(p))
                futures[f] = (i, p, cred)

            for f in concurrent.futures.as_completed(futures):
                i, p, cred = futures[f]
                try:
                    ok = f.result()
                    if not ok:
                        print(f"  ✗ {p.name}: 上传失败")
                        continue
                except Exception as e:
                    print(f"  ✗ {p.name}: 上传异常 {e}")
                    continue

                # 4. 注册素材 + 标签
                try:
                    asset_id = create_asset(token, {
                        "title": p.stem,
                        "sourceType": "ai_import",
                        "sourceId": f"batch_{upload_id}_{i}",
                        "assetType": "image",
                        "obsKey": cred["obsKey"],
                        "fileName": p.name,
                        "fileSize": p.stat().st_size,
                        "topCategoryId": TOP_CATEGORY_ID,
                        "autoTag": False,
                        "tags": [
                            # 在这里放你的标签
                            # {"tagName": "标签名", "confidence": 0.9, "source": "ai"},
                        ],
                    })
                    print(f"  ✓ {p.name}: {asset_id}")
                except Exception as e:
                    print(f"  ✗ {p.name}: 注册失败 {e}")


if __name__ == "__main__":
    token = login()
    import_folder("/path/to/your/images", token)
    print("导入完成")
```

---

## 8. 视频导入

视频导入流程和图片完全一致，只需：

1. `assetType` 设为 `"video"`
2. `POST /assets` 时传入 `width`、`height`、`duration`（秒）
3. 如果不传宽高，后端会自动读取（需要下载视频第一帧，较慢）

支持的视频格式：**MP4, MOV, AVI, MKV, WEBM**

---

## 9. 错误处理

### 常见错误码

| HTTP | code | 场景 | 处理方式 |
|---|---|---|---|
| 401 | - | Token 过期或无效 | 重新登录获取 token |
| 403 | - | 权限不足 | 检查账号权限 |
| 400 | 非 0 | 参数错误 | 检查请求体字段是否正确 |
| 500 | - | 服务器内部错误 | 重试，持续失败联系管理员 |

### OBS 上传 403 Forbidden

最常见原因：**PUT 请求带了 Content-Type 头**。
- 确保请求没有 Content-Type 头
- 确保 uploadUrl 没有过期（有效期 1 小时）
- 确保文件大小和申请凭证时的 fileSize 一致（不要求完全一致，但必须是同一个文件）

### 重试策略

```python
import time

def retry(func, max_retries=3, delay=1):
    for i in range(max_retries):
        try:
            return func()
        except Exception as e:
            if i == max_retries - 1:
                raise
            time.sleep(delay * (2 ** i))  # 指数退避
```

**建议：**
- 网络超时 → 重试 3 次
- 4xx 错误（参数/权限）→ 不要重试，修复参数
- 5xx 错误 → 重试 2-3 次
- 403 OBS 签名错误 → 不要重试，重新申请凭证

---

## 10. 速率限制与最佳实践

### 速率建议

| 操作 | 建议速率 | 说明 |
|---|---|---|
| 申请凭证 | ≤ 1 次/秒 | 每次最多 50 个文件 |
| 文件上传 | 3-5 并发 | OBS 并发建议 ≤ 10 |
| 创建素材 | ≤ 5 次/秒 | 避免 DB 写入压力过大 |
| 批量导入（方式 B） | ≤ 1 批/10 秒 | 每批 ≤ 20 个小文件 |

### 去重

ImageHub 尚未自动去重（pHash 去重规划中）。AI 导入请自行去重：

- 用 `sourceId` 字段记录外部系统的唯一 ID
- 导入前可通过 `GET /assets?keyword=xxx` 或 `sourceId` 检查是否已存在
- 重复素材可以跳过或更新

### 数据校验

导入完成后，建议：

1. 统计成功数量 vs 预期数量
2. 随机抽查几个素材，确认标签、分类、宽高等信息正确
3. 检查错误日志，处理失败的文件

---

## 11. 导入后能在哪看到

AI 导入的素材：
- 首页瀑布流可以看到（按时间排序）
- 来源筛选选 `ai_import` 可只看 AI 导入的
- 标签筛选可以按你传入的标签筛选
- 低置信度的标签 → 待审核区
- 新建的标签 → 待确认状态（用户在后台审核）

---

## 12. API 速查表

| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/auth/login` | POST | 登录获取 token |
| `/api/upload/credentials` | POST | 申请预签名上传凭证 |
| `obs uploadUrl` | PUT | 直传文件到 OBS（不用 token） |
| `/api/assets` | POST | 创建素材 + 打标签 |
| `/api/import/upload` | POST | multipart 批量导入（小文件） |
| `/api/assets` | GET | 查询素材列表（去重检查用） |
| `/api/top-categories` | GET | 获取项目列表 |
| `/api/tags/tree` | GET | 获取标签分类树（参考标签体系用） |

完整 API 文档见：`docs/API.md`


---

## 13. V2 上传模块（2026-08 更新）

针对**大文件 + 断点续传 + 进度可视化**的 V2 上传模块已上线。

### 13.1 三种上传方式对比

| 方式 | 适用场景 | 单文件上限 | 进度可见 |
|---|---|---|---|
| **方式 A**（预签名直传） | 中等图片/视频 | 2GB（可配） | 前端 XHR onprogress |
| **方式 B**（multipart 批量） | 小文件批量 | 单次请求总大小受 web server 限制 | 无（同步阻塞） |
| **方式 C**（V2 multipart OBS） | **大文件 + 断网恢复 + 进度可视化** | **2GB**（可配） | **OBS 分片 + SSE 后端阶段** |

### 13.2 V2 multipart 上传 API（方式 C）

> 100MB 自动走 multipart 上传（阈值 `UPLOAD_MULTIPART_THRESHOLD`，默认 100MB，可配）。
> 分片大小默认 8MB（满足 OBS 业务规则：除最后一片外每片 ≥5MB）。

#### Step 1: 初始化（可复用会话，断点续传）

```http
POST /api/upload/multipart/init
Authorization: Bearer ***
Content-Type: application/json

{
  "batch_id": "可选：已有 batchId 时复用",
  "file_name": "IMG_0001.ARW",
  "file_size": 209715200,
  "content_type": "image/x-sony-arw",
  "asset_type": "image",
  "top_category_id": "项目ID（可选）"
}
```

**响应：**
```json
{
  "code": 0,
  "data": {
    "batch_id": "vs60-178...",
    "obs_key": "raw/image/2026/08/08/vs60-178...arw",
    "total_parts": 25,
    "part_size": 8388608,
    "uploaded_parts": [],          // 已传分片（断点续传时非空）
    "status": "uploading",
    "part_upload_urls": [
      { "part_number": 1, "url": "https://obs-...?partNumber=1&uploadId=..." },
      ...
    ]
  }
}
```

#### Step 2: 直传每个分片到 OBS

```http
PUT <part_upload_url>   // OBS 预签名 URL
Content-Type: 不要设置（V2 签名禁忌，否则 403）
Body: <8MB 二进制>
```

#### Step 3: 每个分片回执

```http
POST /api/upload/multipart/part-complete
Authorization: Bearer ***
Content-Type: application/json

{
  "batch_id": "vs60-178...",
  "part_number": 1,
  "size": 8388608,
  "etag": "可选：前端从 XHR ETag header 拿"
}
```

#### Step 4: 单分片 URL 重签（断点续传/URL 过期）

```http
POST /api/upload/multipart/part-url
Authorization: Bearer ***
Content-Type: application/json

{
  "batch_id": "vs60-178...",
  "part_number": 1
}
```

#### Step 5: 合并分片 + 素材入库（异步处理）

```http
POST /api/upload/multipart/complete
Authorization: Bearer ***
Content-Type: application/json

{ "batch_id": "vs60-178..." }
```

**响应：** 立即返回（不阻塞后端处理）：
```json
{ "code": 0, "data": { "asset_ids": ["uuid"], "async_processing": true } }
```

#### Step 6: SSE 订阅后端处理进度（可选）

```http
GET /api/upload/events/{asset_id}
Accept: text/event-stream

event: connected
data: {"asset_id": "..."}

event: uploaded
data: uploaded|ts|{"file_name":"...","file_size":209715200}

event: thumbnail
data: thumbnail|ts|{"status":"processing"}

event: thumbnail
data: thumbnail|ts|{"status":"done","width":6000,"height":4000}

event: exif
data: exif|ts|{"status":"processing"}

event: exif
data: exif|ts|{"status":"done","has_exif":true}

event: ai_tagging
data: ai_tagging|ts|{"status":"processing"}

event: ai_tagging
data: ai_tagging|ts|{"status":"done","tag_count":9}

event: done
data: done|ts|{}
```

5 个阶段：`uploaded → thumbnail → exif → ai_tagging → done`
15s 心跳保活（无事件时 `event: ping`）

### 13.3 配置参数（环境变量）

| 变量 | 默认值 | 含义 |
|---|---|---|
| `UPLOAD_MAX_FILE_SIZE` | 2147483648 (2GB) | 单文件硬上限 |
| `UPLOAD_CHUNK_SIZE` | 8388608 (8MB) | 分片大小 |
| `UPLOAD_MULTIPART_THRESHOLD` | 104857600 (100MB) | 超过此大小走 multipart |
| `UPLOAD_TMP_DIR` | /data/imagehub-tmp | 物理盘临时目录（vdb1 1T） |

### 13.4 前端 UI（2026-08）

- **悬浮窗**：`右下角小圆按钮`，上传中显示环形进度
- **独立页**：`/upload` 路由，全屏表格
  - 每行：文件名/大小/状态/5 阶段进度环/总进度条/操作按钮
  - failed 项：`↻ 重试`（file picker 选文件复用原 item.id）+ `✕ 移除`
  - 队列持久化：zustand persist + localStorage（`imagehub-upload-queue`），刷新不丢
  - TopBar `📤 上传页` 链接 + 活跃任务徽标

### 13.5 端到端验证记录

- **#58 VS 50MB JPG 直传**：0.2s/204MB/s + 9 标签入库
- **#59 VS 200MB ARW 分片**：25 parts × 8MB init → 25 PUT (83MB/s) → complete → 200MB 入库
- **#60 VS 1GB MP4 断点续传**：30 parts → 模拟崩溃 → init 复用会话（uploaded_parts[1..30]）→ 99 parts 续传 (84.7MB/s) → complete → 1030.5MB 入库

### 13.6 V2 上传踩坑记录（开发必读）

1. **OBS Multipart 至少 5MB/片**（除最后一片）：SDK 会拒绝
2. **complete 必须 `obs.model.CompletePart(partNum=, etag=)` 对象**（非 Part、非 dict）：SDK convertor 按属性读取
3. **part-complete etag 可选**：complete 时从 OBS listParts 取权威值（断网恢复友好）
4. **预签名 URL 禁忌 Content-Type**：V2 签名签空字符串，带 Content-Type 会 403。前端 XHR 必须 setRequestHeader('Content-Type', '')
5. **续传 init 必须返回完整 part_upload_urls**：否则前端无法上传剩余分片（#60 修）
6. **BackgroundTasks 不支持 async def**：必须 asyncio.create_task 创建协程（#54 SSE 改造遗留 bug）
7. **PIL DecompressionBomb**：阈值 89M 像素会拒绝大图，需 main.py 启动时设置 Image.MAX_IMAGE_PIXELS = 200M

