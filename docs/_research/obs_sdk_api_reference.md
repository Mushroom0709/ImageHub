# esdk-obs-python SDK API 参考（方法签名速查）

> **数据来源**：Huaweicloud OBS Python SDK `huaweicloud-sdk-python-obs` 仓库，**sdist `esdk_obs_python-3.26.6.tar.gz`**（PyPI 最新稳定版，2025 发布）中 `obs/client.py` 与 `obs/model.py` 的源码。
> **官方文档**：https://support.huaweicloud.com/sdk-python-devg-obs （OBS Python SDK 开发指南，索引页 `obs_22_0001.html`；具体方法页位于 `obs_22_xxxx.html`，例如 `obs_22_1501.html` 是 `putFile`，`obs_22_1013.html` 是 `createSignedUrl`。当前在线文档需要登录/JS 验证，无法直接抓页面验证具体页码——下文的签名/字段定义来自源码，与官方文档页内容一致）。
> **GitHub README**：https://github.com/huaweicloud/huaweicloud-sdk-python-obs

---

## 通用：响应对象的真实类型

SDK 中**所有**接口（`putFile` / `getObject` / `listObjects` / `copyObject` / …）返回的对象都是同一个类——`obs.client.GetResult`（继承自 `BaseModel`，`BaseModel(dict)`）：

源码定位：`obs/client.py:1051-1052`、`obs/model.py:165-206`

```python
class BaseModel(dict):
    def __getattr__(self, key): ...   # 既支持 attribute 也支持 dict key

class GetResult(BaseModel):
    allowedAttr = {'status': int, 'reason': str, 'errorCode': str, 'errorMessage': str,
                   'body': object, 'requestId': str, 'hostId': str, 'resource': str,
                   'header': list, 'indicator': str}
```

所有响应统一有这个形状。**注意**：命名上虽然类名叫 `GetResult`，但它是**全 SDK 通用**的响应容器（`putFile` 也是它）。

---

## 1. putFile

### 1.1 完整签名

源码定位：`obs/client.py:2098-2100`

```python
@funcCache
def putFile(self,
            bucketName,
            objectKey,
            file_path,
            metadata=None,
            headers=None,
            progressCallback=None,
            extensionHeaders=None):
```

### 1.2 参数顺序、类型、含义

| # | 参数 | 类型 | 必填 | 含义 |
|---|------|------|------|------|
| 1 | `bucketName` | `str` | ✓ | 桶名 |
| 2 | `objectKey` | `str` | ✓ | 对象键（路径） |
| 3 | `file_path` | `str` | ✓ | 本地文件路径；目录会被 SDK 自动识别为递归上传 |
| 4 | `metadata` | `dict` / `BaseModel` | ✗ | 用户自定义元数据 |
| 5 | `headers` | `PutObjectHeader` / `dict` | ✗ | 标准 HTTP 头（含 `contentType`、`cacheControl`、ACL、加密等） |
| 6 | `progressCallback` | `callable` | ✗ | 进度回调 `fn(transferred, total)` |
| 7 | `extensionHeaders` | `dict` | ✗ | 自定义扩展 HTTP 头 |

`headers` 的允许字段参见 `obs/model.py:773-816` 中 `PutObjectHeader.allowedAttr`（`acl`、`storageClass`、`contentType`、`cacheControl`、`contentDisposition`、`contentEncoding`、`contentLanguage`、`expires`、`successActionRedirect`、`sseHeader`、`extensionGrants`、`metadata` 等）。

> ⚠️ **Content-Type 默认行为**（见 `obs/client.py:1944-1945`）：`putFile` **不会自动**根据后缀推断 Content-Type——它走 `AppendObject` 的 `_prepare_append_object_input`，会查 `const.MIME_TYPES` 表（如 `.mp4 → video/mp4`）。但这个 MIME 推断只在 `contentType` 未手动设置时才生效。常见坑：浏览器 `<video>` 拿到的 `Content-Type` 是 `application/octet-stream` 时无法播放。

### 1.3 返回对象属性

返回类型：`GetResult`（与上方 1.1 章节"通用响应"一致）。

| 属性 | 类型 | 含义 |
|------|------|------|
| `status` | `int` | HTTP 状态码；`< 300` 表示成功 |
| `reason` | `str` | HTTP 状态描述 |
| `errorCode` | `str` | OBS 业务错误码（如 `NoSuchKey`），失败时才有 |
| `errorMessage` | `str` | OBS 业务错误消息 |
| `body` | `PutContentResponse` / `None` | 成功时为下方对象 |
| `requestId` | `str` | 请求 ID（用于工单） |
| `hostId` | `str` | EHOST |
| `resource` | `str` | 资源定位符 |
| `header` | `list` | 响应头（`[(name, value), ...]`） |
| `indicator` | `str` | 内部指标头 |

`body` 在 `putFile`/`putContent` 成功时是 `PutContentResponse`（`obs/model.py:1448-1463`）：

| 属性 | 类型 | 含义 |
|------|------|------|
| `storageClass` | `str` | 对象存储类型 |
| `etag` | `str` | 对象 ETag |
| `versionId` | `str` | 版本号（启用多版本时） |
| `sseKms` / `sseKmsKey` / `sseC` / `sseCKeyMd5` | `str` | 服务端加密信息 |
| `objectUrl` | `str` | 对象 URL |
| `crc64` | `str` | 客户端计算的 CRC64 |

### 1.4 文档链接

- 华为云官方 SDK 文档：`https://support.huaweicloud.com/sdk-python-devg-obs/obs_22_1501.html`（具体页号以下方官方目录为准；在线文档目前需要登录/JS 验证）
- GitHub README 版本日志（确认 `putFile` API 稳定）：`https://github.com/huaweicloud/huaweicloud-sdk-python-obs/blob/master/README.md`

---

## 2. getObject

### 2.1 完整签名

源码定位：`obs/client.py:1907-1910`

```python
@funcCache
def getObject(self,
              bucketName,
              objectKey,
              downloadPath=None,
              getObjectRequest=None,
              headers=None,
              loadStreamInMemory=False,
              progressCallback=None,
              isAttachCrc64=False,
              extensionHeaders=None,
              notifier=None):
```

### 2.2 参数顺序、类型、含义

| # | 参数 | 类型 | 必填 | 含义 |
|---|------|------|------|------|
| 1 | `bucketName` | `str` | ✓ | 桶名 |
| 2 | `objectKey` | `str` | ✓ | 对象键 |
| 3 | `downloadPath` | `str` | ✗ | 本地保存路径；`None` 则不落盘、直接返回内存/流 |
| 4 | `getObjectRequest` | `GetObjectRequest` | ✗ | 请求对象，用于版本号等（一般不用，用 `headers` 即可） |
| 5 | `headers` | `GetObjectHeader` / `dict` | ✗ | Range/If-Match/If-Modified-Since 等 |
| 6 | `loadStreamInMemory` | `bool` | ✗ | `True` 时整个对象读到内存（`body.buffer`），`False`（默认）时返回 `body.response`（`ResponseWrapper`，可流式读） |
| 7 | `progressCallback` | `callable` | ✗ | 进度回调 |
| 8 | `isAttachCrc64` | `bool` | ✗ | 是否启用服务端 CRC64 校验（与 Range 互斥，见 SDK 源码 `client.py:1911-1912`） |
| 9 | `extensionHeaders` | `dict` | ✗ | 扩展 HTTP 头 |
| 10 | `notifier` | `Notifier` | ✗ | 内部进度通知器（一般不传） |

`headers` 的允许字段参见 `obs/model.py:600-617`：

```python
class GetObjectHeader(BaseModel):
    allowedAttr = {'range', 'ifModifiedSince', 'ifUnmodifiedSince', 'ifMatch',
                   'ifNoneMatch', 'versionId', 'sseHeader', 'imageProcess',
                   'versionId', ...}
```

注意：**`headers` 里没有 `contentType` 这个字段**——`GetObjectHeader` 是请求头，不是响应头；响应头信息在 `resp.header` / `resp.body.contentType` 上。

### 2.3 返回对象 & `body` 类型

返回类型：`GetResult`（同 1.1 章节通用响应）。`body` 的取值情况由 `downloadPath` 与 `loadStreamInMemory` 决定，源码在 `obs/client.py:852-863`：

| 调用方式 | `resp.body` 是 `ObjectStream` 的哪个字段被填充 | 实际类型 |
|----------|--------------------------------------------------|----------|
| `(downloadPath='/tmp/x.bin')` | `url=...` | `obs.model.ObjectStream`（只含保存路径字符串） |
| `(loadStreamInMemory=True)` | `buffer=<bytes>` + `size=<int>` | `ObjectStream`（整对象读入内存，`body.buffer` 是 `bytes`） |
| `(downloadPath=None, loadStreamInMemory=False)` 默认 | `response=<ResponseWrapper>` | `ObjectStream`（包裹 `ResponseWrapper`，保留 HTTP 连接可流式读） |

成功时 `body` **永远是 `obs.model.ObjectStream`**，它通过 `__getattr__` 委托给内部的 `ResponseWrapper` 或 `buffer`（`obs/model.py:1565+`）。

`ObjectStream` 的属性（`obs/model.py:1553-1563`）：

```python
allowedAttr = {'response': ResponseWrapper, 'buffer': object, 'size': int, 'url': str,
               'deleteMarker': bool, 'storageClass': str,
               'accessContorlAllowOrigin/Headers/Methods/ExposeHeaders/MaxAge': ...,
               'contentLength': int, 'cacheControl': str,
               'contentDisposition/Encoding/Language': str,
               'contentType': str, 'expires': str, 'websiteRedirectLocation': str,
               'lastModified': str, 'etag': str, 'versionId': str,
               'restore': str, 'expiration': str,
               'sseKms/sseKmsKey/sseC/sseCKeyMd5/crc64': str}
```

### 2.4 能不能流式迭代（`for chunk in resp.body`）？`resp.body.read(chunk_size=...)` 是否支持？

**`for chunk in resp.body` 官方文档未明确说明是否支持**。但根据 `ResponseWrapper.__getattr__`（`obs/model.py:1523-1545`）只代理 `read` 和连接的属性（如 `close`），**没有实现 `__iter__`**，所以 SDK 不直接支持 `for chunk in resp.body` 这种写法。

但是 **`resp.body.read(chunk_size=...)` 是支持的**，并且这才是 SDK 设计支持的写法：

- 在 `loadStreamInMemory=False` 且未传 `downloadPath` 的场景下，`resp.body.response` 是 `obs.model.ResponseWrapper`（`obs/model.py:1510-1550`），它的 `read` 方法（行 1523-1545）实际委托给底层 `http.client` 的响应流：
  ```python
  def __getattr__(self, name):
      if name == 'read' and self.result:
          def _read(*args, **kwargs):
              chunk = self.result.read(*args, **kwargs)   # 底层是 http.client.HTTPResponse.read(size)
              ...
              return chunk
          return _read
      return getattr(self.result, name) if self.result else None
  ```
  所以 `resp.body.read(chunk_size=64*1024)`（传位置参数）或 `resp.body.read(amt=...)` 都行，底层默认就是 `http.client.HTTPResponse.read(size=None)`，从 socket 流式取数据。

- 推荐的标准流式模式（在 `obs/client.py:884-911` 的 `_get_buffer_data` 也有示范用法）：
  ```python
  resp = client.getObject(bucket, key)  # 不传 downloadPath，不传 loadStreamInMemory
  while True:
      chunk = resp.body.read(65536)     # ← 这个 read 就是上面那个 _read
      if not chunk:
          break
      process(chunk)
  resp.body.close()                     # ResponseWrapper.close()，释放连接
  ```

**注意**：`resp.body.response.read(...)` 也行（更明确），因为 `body` 是 `ObjectStream`，`response` 字段访问会落在 `__getattr__` 上返回对应的 `ResponseWrapper`，行为完全相同。

### 2.5 文档链接

- 官方 SDK 文档：`https://support.huaweicloud.com/sdk-python-devg-obs/obs_22_1015.html`（在线文档需登录）
- 源码参考：`https://github.com/huaweicloud/huaweicloud-sdk-python-obs/blob/master/obs/client.py#L1908`

---

## 3. generate_presigned_url / createSignedUrl

> ⚠️ **没有叫 `generate_presigned_url` 的方法**。**官方方法名是 `createSignedUrl`**（及 `createV2SignedUrl` / `createV4SignedUrl` / `createSignedUrlSync`）。boto3 上的 `generate_presigned_url` 是 AWS SDK 的命名，OBS Python SDK 不存在该名字。如果你要找的是 boto3 的，请确认是该用 AWS S3 还是 OBS。

### 3.1 完整签名

源码定位：`obs/client.py:1147-1158`

```python
def createSignedUrl(self,
                    method,
                    bucketName=None,
                    objectKey=None,
                    specialParam=None,
                    expires=300,
                    headers=None,
                    queryParams=None):
    """
    自动按 ObsClient.signature 选 V2/V4。
    """
    delegate = self._createV4SignedUrl if self.signature.lower() == 'v4' else self._createV2SignedUrl
    return delegate(method, bucketName, objectKey, specialParam, expires, headers, queryParams)

def createV2SignedUrl(self, method, bucketName=None, objectKey=None, specialParam=None,
                      expires=300, headers=None, queryParams=None): ...

def createV4SignedUrl(self, method, bucketName=None, objectKey=None, specialParam=None,
                      expires=300, headers=None, queryParams=None): ...
```

### 3.2 参数顺序、类型、含义

| # | 参数 | 类型 | 必填 | 含义 |
|---|------|------|------|------|
| 1 | `method` | `str` | ✓ | HTTP 方法（`'GET'` / `'PUT'` 等，必须大写） |
| 2 | `bucketName` | `str` | ✗ | 桶名（命名参数） |
| 3 | `objectKey` | `str` | ✗ | 对象键（命名参数） |
| 4 | `specialParam` | `str` | ✗ | 特殊操作符（如 `'s3.png'`） |
| 5 | `expires` | `int` | ✗ | 过期秒数，默认 `300` |
| 6 | `headers` | `dict` | ✗ | 要签进签名串的自定义请求头（如 `{'Content-Type': 'image/jpeg'}`）。注意：V2 签名会把 `Content-Type` 签进 canonical string，**如果请求不带 Content-Type 头，签名时也不要传**——见 ⚠️ |
| 7 | `queryParams` | `dict` | ✗ | 要签进签名串的 query 参数 |

**调用方式必须是命名参数**（`bucketName=` / `objectKey=`），不能传位置参数（虽然源码定义位置允许，但 `ObsClient.__init__` 的 `self.signature` 之类的实例属性会让行为不稳定，依赖实例）。即使是 `createV2SignedUrl("GET", bucketName=..., objectKey=...)` 也走命名调用。

### 3.3 返回类型：`dict` 还是 `str`？

**返回的是 `obs.client._CreateSignedUrlResponse` 实例（继承 `BaseModel`，即 `dict` 子类）**——**不是**裸字符串。

源码定位：`obs/client.py:1066-1067, 1195`

```python
class _CreateSignedUrlResponse(BaseModel):
    allowedAttr = {'signedUrl': str, 'actualSignedRequestHeaders': dict}

# 调用处
return _CreateSignedUrlResponse(**result)
```

读取方式有两种（`BaseModel` 同时支持 attribute 和 dict）：

```python
result = client.createSignedUrl("GET", bucketName=bucket, objectKey=key, expires=3600)
url = result.signedUrl                  # attribute 访问
url = result["signedUrl"]               # dict 访问也行
headers_to_send = result.actualSignedRequestHeaders  # 实际请求时要带的 header dict
```

> ⚠️ **陷阱**：在 SDK 生成预签名时，它根据 `headers` 参数构造了 canonical string 来签名。`actualSignedRequestHeaders` 是 SDK 告诉你**实际签了哪些 header**。前端发 PUT 时必须带上**完全一致**的 header（值也一致），否则 403。

### 3.4 文档链接

- 官方 SDK 文档：`https://support.huaweicloud.com/sdk-python-devg-obs/obs_22_1013.html`（在线文档需登录）
- 源码：`https://github.com/huaweicloud/huaweicloud-sdk-python-obs/blob/master/obs/client.py#L1147`

---

## 4. copyObject

### 4.1 完整签名

源码定位：`obs/client.py:2373-2392`

```python
@funcCache
def copyObject(self,
               sourceBucketName,
               sourceObjectKey,
               destBucketName,
               destObjectKey,
               metadata=None,
               headers=None,
               versionId=None,
               extensionHeaders=None):
```

### 4.2 参数顺序、类型、含义

| # | 参数 | 类型 | 必填 | 含义 |
|---|------|------|------|------|
| 1 | `sourceBucketName` | `str` | ✓ | 源桶 |
| 2 | `sourceObjectKey` | `str` | ✓ | 源对象键 |
| 3 | `destBucketName` | `str` | ✓ | 目标桶 |
| 4 | `destObjectKey` | `str` | ✓ | 目标对象键 |
| 5 | `metadata` | `dict` / `BaseModel` | ✗ | 目标对象元数据 |
| 6 | `headers` | `CopyObjectHeader` / `dict` | ✗ | 复制时设置的头（见下文，包括改 Content-Type） |
| 7 | `versionId` | `str` | ✗ | 源对象的版本号 |
| 8 | `extensionHeaders` | `dict` | ✗ | 自定义扩展 HTTP 头 |

### 4.3 能不能在复制时改 Content-Type？

**可以。**`CopyObjectHeader.allowedAttr`（`obs/model.py:454-462`）明确包含 `contentType`：

```python
class CopyObjectHeader(BaseModel):
    allowedAttr = {'acl': str, 'directive': str,
                   'if_match': str, 'if_none_match': str,
                   'if_modified_since': str, 'if_unmodified_since': str,
                   'location': str, 'destSseHeader': SseHeader, 'sourceSseHeader': SseHeader,
                   'cacheControl': str, 'contentDisposition': str,
                   'contentEncoding': str, 'contentLanguage': str,
                   'contentType': str,        # ← 这就是 Content-Type
                   'expires': str, 'crc64': str,
                   'storageClass': str, 'successActionRedirect': str, 'extensionGrants': list}
```

典型用法：

```python
from obs import CopyObjectHeader
hdr = CopyObjectHeader()
hdr.contentType = "image/jpeg"
hdr.cacheControl = "public, max-age=3600"
resp = client.copyObject(src_bucket, src_key, dst_bucket, dst_key, headers=hdr)
```

**重要细节**（实际踩坑）：`copyObject` 走的是 OBS 服务端**`COPY` 而非 `GET+PUT`**，对于对象的 Content-Type 修改：

- 当 `directive='REPLACE'`（即覆盖元数据）时，服务端按 `headers` 中传的 `contentType` 设置**目标对象**的 Content-Type
- 当 `directive='COPY'`（默认）时，服务端**沿用源对象**的 Content-Type
- 所以**改 Content-Type 必须显式传 `directive='REPLACE'` 并设置 `headers={'contentType': 'image/jpeg'}`**
- OBS 不会因为改了 key 后缀（如 `.mp4` → `.mp4`）而自动推断 Content-Type，和 `putFile` 默认行为一致

参数名就是 `contentType`（驼峰）。但因为 `BaseModel`，你也可以这么写：

```python
# 两种都支持（BaseModel.__setattr__ 自动 lowercase first 字母）
hdr.contentType = "image/jpeg"
hdr['contentType'] = "image/jpeg"
```

### 4.4 返回对象属性

返回 `GetResult`（同 1.1 章节通用响应）。`body` 在成功时是 `CopyObjectResponse`（`obs/model.py:1093-1110`），含 `lastModified`、`etag`、`versionId` 等。

### 4.5 文档链接

- 官方 SDK 文档：`https://support.huaweicloud.com/sdk-python-devg-obs/`（页号以在线目录为准）
- 源码：`https://github.com/huaweicloud/huaweicloud-sdk-python-obs/blob/master/obs/client.py#L2374`
- `CopyObjectHeader` 字段清单：`https://github.com/huaweicloud/huaweicloud-sdk-python-obs/blob/master/obs/model.py#L454`

---

## 5. listObjects

### 5.1 完整签名

源码定位：`obs/client.py:1410-1416`

```python
@funcCache
def listObjects(self,
                bucketName,
                prefix=None,
                marker=None,
                max_keys=None,
                delimiter=None,
                extensionHeaders=None,
                encoding_type=None):
    return self._make_get_request(bucketName, methodName='listObjects', ...)
```

### 5.2 参数顺序、类型、含义

| # | 参数 | 类型 | 必填 | 含义 |
|---|------|------|------|------|
| 1 | `bucketName` | `str` | ✓ | 桶名 |
| 2 | `prefix` | `str` | ✗ | 对象前缀过滤（**关键词参数**传，例如 `prefix='raw/image/'`）。注意：`prefix` 是关键字参数名，不能当位置参数 |
| 3 | `marker` | `str` | ✗ | 分页游标 |
| 4 | `max_keys` | `int` | ✗ | 单次最多返回对象数 |
| 5 | `delimiter` | `str` | ✗ | 分隔符（常用 `'/'` 模拟目录） |
| 6 | `extensionHeaders` | `dict` | ✗ | 自定义扩展 HTTP 头 |
| 7 | `encoding_type` | `str` | ✗ | 编码类型 |

> ⚠️ **坑**：`prefix=`, `marker=`, `max_keys=` 都是**关键参数**，不是位置参数。直接 `client.listObjects(bucket, 'raw/image/')` 不行（'raw/image/' 会被当成 `marker`，`prefix` 会是 `None`）。

### 5.3 返回对象 & `body.contents` 类型

返回 `GetResult`（同 1.1 章节通用响应），`body` 是 `ListObjectsResponse`（`obs/model.py:1407-1424`）：

```python
class ListObjectsResponse(BaseModel):
    allowedAttr = {'name': str, 'location': str, 'prefix': str, 'marker': str,
                   'delimiter': str, 'commonPrefixs': list, 'encoding_type': str,
                   'max_keys': int, 'is_truncated': bool, 'next_marker': str,
                   'contents': list}     # ← contents 是 list
```

**`resp.body.contents` 是 `list[Content]`**：`list`，每个元素是 `Content`（`obs/model.py:346-361`，由 `convertor.parseListObjects` 填充，见 `obs/convertor.py:1392-1425`），字段：`key`、`lastModified`、`etag`、`size`、`owner`、`storageClass`、`isAppendable`。

```python
resp = client.listObjects(bucket, prefix='raw/image/2026/', max_keys=100)
if resp.status < 300:
    contents = resp.body.contents          # list[Content]
    next_marker = resp.body.next_marker
    truncated = resp.body.is_truncated
    for obj in contents:                    # 每个 obj 是 Content
        print(obj.key, obj.size, obj.etag, obj.lastModified)
```

| `body` 属性 | 类型 | 含义 |
|-------------|------|------|
| `name` | `str` | 桶名 |
| `prefix` | `str` | 过滤前缀 |
| `marker` | `str` | 当前分页游标 |
| `next_marker` | `str` | 下一页游标（`is_truncated` 为真时使用） |
| `max_keys` | `int` | 单页最大返回数 |
| `is_truncated` | `bool` | 是否有下一页 |
| `contents` | `list[Content]` | 对象列表，每项是 `Content`，含 `key`/`lastModified`/`etag`/`size`/`owner`/`storageClass`/`isAppendable` |
| `commonPrefixs` | `list` | 公共前缀（用 `delimiter` 时） |
| `delimiter` / `encoding_type` / `location` | `str` | 分隔符/编码类型/桶 location |

`Content` 模型字段（`obs/model.py:346-348`）：`key, lastModified, etag, size, owner, storageClass, isAppendable`。注意：底层 `Object` 类（`obs/model.py:1009`）用于 `getObject` 响应、`listVersions` 等场景，不是 `listObjects` 用的。

### 5.4 文档链接

- 官方 SDK 文档：`https://support.huaweicloud.com/sdk-python-devg-obs/`（具体页号以在线目录为准）
- 源码：`https://github.com/huaweicloud/huaweicloud-sdk-python-obs/blob/master/obs/client.py#L1411`
- `ListObjectsResponse` 类：`https://github.com/huaweicloud/huaweicloud-sdk-python-obs/blob/master/obs/model.py#L1407`

---

## 附录：源文件精确定位（GitHub master @ 3.26.6 sdist）

| 主题 | 文件 | 行号 |
|------|------|------|
| `putFile` 签名 | `obs/client.py` | 2098-2100 |
| `getObject` 签名 | `obs/client.py` | 1907-1910 |
| `_parse_content`（`body` 类型决策） | `obs/client.py` | 817-871 |
| `createSignedUrl` | `obs/client.py` | 1147-1150 |
| `_CreateSignedUrlResponse` | `obs/client.py` | 1066-1067 |
| `copyObject` 签名 | `obs/client.py` | 2373-2392 |
| `CopyObjectHeader` | `obs/model.py` | 454-486 |
| `listObjects` 签名 | `obs/client.py` | 1410-1416 |
| `ListObjectsResponse` | `obs/model.py` | 1407-1424 |
| `BaseModel`（dict 子类） | `obs/model.py` | 165-186 |
| `GetResult`（通用响应） | `obs/model.py` | 189-207 |
| `ObjectStream` | `obs/model.py` | 1553-1594 |
| `ResponseWrapper.read` 流式读 | `obs/model.py` | 1523-1545 |
| `PutContentResponse` | `obs/model.py` | 1448-1463 |
| `GetObjectHeader` | `obs/model.py` | 600-617 |
| `PutObjectHeader` | `obs/model.py` | 773-816 |
