/**
 * 分片上传工具（断点续传）
 *
 * 流程：init(拿全部 part 预签名 URL) → 3 并发直传 part → part-complete 回执 → complete
 * 断点续传：localStorage 记录 {batchId, fileKey}，重传时先 GET status 跳过已传 part
 */

const THRESHOLD = 100 * 1024 * 1024 // 超过 100MB 走分片（与后端 UPLOAD_MULTIPART_THRESHOLD 一致）
const PART_CONCURRENCY = 3

/** 分片上传会话状态（从 /status 恢复） */
interface MultipartSession {
  batch_id: string
  obs_key: string
  file_name: string
  file_size: number
  total_parts: number
  part_size: number
  uploaded_parts: { part_number: number; etag: string; size: number }[]
  status: string
}

interface MultipartProgress {
  /** 0-100 整体百分比 */
  percent: number
  /** 已传字节（含当前 part 内） */
  loaded: number
  /** 总字节 */
  total: number
  /** 当前分片号 */
  partNumber: number
  /** 分片总数 */
  totalParts: number
  /** 网速 bytes/s */
  speed: number
}

interface MultipartOptions {
  topCategoryId?: string | null
  onProgress?: (p: MultipartProgress) => void
  onPartDone?: (partNumber: number, done: number, total: number) => void
  signal?: AbortSignal
}

/** 读取本地断点记录 */
function getResumeRecord(file: File): { batchId: string } | null {
  try {
    const key = `mp-resume:${file.name}:${file.size}:${file.lastModified}`
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function saveResumeRecord(file: File, batchId: string) {
  try {
    const key = `mp-resume:${file.name}:${file.size}:${file.lastModified}`
    localStorage.setItem(key, JSON.stringify({ batchId, savedAt: Date.now() }))
  } catch {
    // localStorage 满则忽略
  }
}

function clearResumeRecord(file: File) {
  try {
    const key = `mp-resume:${file.name}:${file.size}:${file.lastModified}`
    localStorage.removeItem(key)
  } catch {
    // ignore
  }
}

async function api<T = any>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token')
  const resp = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options?.headers || {}),
    },
  })
  const data = await resp.json()
  if (data.code !== 0) throw new Error(data.message || '请求失败')
  return data.data as T
}

/** 单分片直传 OBS（预签名 PUT，不带 Content-Type） */
function uploadPartToObs(
  url: string,
  blob: Blob,
  onProgress?: (loaded: number, total: number) => void,
  signal?: AbortSignal,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', url)
    try {
      xhr.setRequestHeader('Content-Type', '')
    } catch (e) {
      // 部分浏览器不允许空 header，忽略
    }
    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(e.loaded, e.total)
      }
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve()
      else reject(new Error(`分片上传失败: HTTP ${xhr.status} | ${(xhr.responseText || '').slice(0, 200)}`))
    }
    xhr.onerror = () => reject(new Error('分片上传失败: 网络错误'))
    xhr.ontimeout = () => reject(new Error('分片上传失败: 超时'))
    xhr.onabort = () => reject(new Error('上传已取消'))
    if (signal) {
      signal.addEventListener('abort', () => xhr.abort(), { once: true })
    }
    xhr.send(blob)
  })
}

/** 分片上传单个文件（>100MB）。返回 assetId */
export async function multipartUpload(file: File, options?: MultipartOptions): Promise<string> {
  const { topCategoryId = null, onProgress, onPartDone, signal } = options || {}
  const videoExts = ['mp4', 'mov', 'avi', 'mkv', 'webm']
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  const assetType = videoExts.includes(ext) ? 'video' : 'image'

  // 断点恢复：同文件（名+大小+修改时间）有记录则复用 batchId
  const resume = getResumeRecord(file)
  let batchId = resume?.batchId || ''

  const speedCtx = { lastLoaded: 0, lastTime: Date.now(), speed: 0 }

  // init（有 batchId 时后端复用进行中的会话，返回已传 parts）
  const initData = await api<MultipartSession & { part_upload_urls: { part_number: number; url: string }[] }>(
    '/api/upload/multipart/init',
    {
      method: 'POST',
      body: JSON.stringify({
        batch_id: batchId,
        file_name: file.name,
        file_size: file.size,
        content_type: file.type || 'application/octet-stream',
        asset_type: assetType,
        top_category_id: topCategoryId || undefined,
      }),
    },
  )
  batchId = initData.batch_id
  saveResumeRecord(file, batchId)

  const { total_parts, part_size, uploaded_parts, part_upload_urls } = initData
  const urlMap = new Map(part_upload_urls.map((p) => [p.part_number, p.url]))
  const doneParts = new Set(uploaded_parts.map((p) => p.part_number))

  // 计算已传字节（进度起始值）
  const doneBytes = uploaded_parts.reduce((s, p) => s + (p.size || 0), 0)

  let nextPart = 1
  let sentBytes = doneBytes
  const lock = new Map<number, Promise<void>>()

  async function worker() {
    while (nextPart <= total_parts) {
      const n = nextPart++
      if (doneParts.has(n)) continue

      const start = (n - 1) * part_size
      const chunk = file.slice(start, Math.min(start + part_size, file.size))
      const url = urlMap.get(n)

      // 网速基准（并发下取整体）
      const t0 = Date.now()
      let partLoaded = 0

      try {
        if (!url) throw new Error(`分片 ${n} 无上传 URL`)
        await uploadPartToObs(
          url,
          chunk,
          (loaded) => {
            partLoaded = loaded
            const now = Date.now()
            const dt = (now - speedCtx.lastTime) / 1000
            if (dt > 0.5) {
              const dl = sentBytes + partLoaded - speedCtx.lastLoaded
              speedCtx.speed = dl / dt
              speedCtx.lastLoaded = sentBytes + partLoaded
              speedCtx.lastTime = now
            }
            const totalLoaded = sentBytes + partLoaded
            onProgress?.({
              percent: Math.min(99, Math.round((totalLoaded / file.size) * 100)),
              loaded: totalLoaded,
              total: file.size,
              partNumber: n,
              totalParts: total_parts,
              speed: speedCtx.speed,
            })
          },
          signal,
        )

        // 回执（etag 可选，complete 时后端以 OBS listParts 为准）
        await api('/api/upload/multipart/part-complete', {
          method: 'POST',
          body: JSON.stringify({ batch_id: batchId, part_number: n, size: chunk.size }),
        })

        sentBytes += chunk.size
        onPartDone?.(n, sentBytes, file.size)
        onProgress?.({
          percent: Math.min(99, Math.round((sentBytes / file.size) * 100)),
          loaded: sentBytes,
          total: file.size,
          partNumber: n,
          totalParts: total_parts,
          speed: speedCtx.speed,
        })
      } catch (err) {
        if (signal?.aborted) throw new Error('上传已取消')
        // 单个 part 失败重试 2 次
        let retried = false
        for (let attempt = 0; attempt < 2; attempt++) {
          if (signal?.aborted) throw new Error('上传已取消')
          try {
            const newUrl = await api<{ url: string }>('/api/upload/multipart/part-url', {
              method: 'POST',
              body: JSON.stringify({ batch_id: batchId, part_number: n }),
            })
            await uploadPartToObs(newUrl.url, chunk, undefined, signal)
            await api('/api/upload/multipart/part-complete', {
              method: 'POST',
              body: JSON.stringify({ batch_id: batchId, part_number: n, size: chunk.size }),
            })
            sentBytes += chunk.size
            retried = true
            break
          } catch (e) {
            // 继续重试
          }
        }
        if (!retried) throw err
      }
    }
  }

  // 3 并发 worker
  const workers = Array.from({ length: Math.min(PART_CONCURRENCY, total_parts) }, () => worker())
  await Promise.all(workers)

  // complete（合并分片 + 素材创建；同步处理可能 >10s，用长超时）
  const done = await api<{ asset_ids: string[] }>('/api/upload/multipart/complete', {
    method: 'POST',
    body: JSON.stringify({ batch_id: batchId }),
  })

  clearResumeRecord(file)
  onProgress?.({
    percent: 100,
    loaded: file.size,
    total: file.size,
    partNumber: total_parts,
    totalParts: total_parts,
    speed: 0,
  })
  return done.asset_ids[0]
}

/** 判断是否走分片 */
export function shouldMultipart(file: File): boolean {
  return file.size > THRESHOLD
}
