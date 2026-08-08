/** 上传工具：预签名 URL 直传 OBS */

import { multipartUpload, shouldMultipart } from './multipartUpload'

interface Credential {
  file_index: number
  upload_url: string
  obs_key: string
}

interface CredentialsResponse {
  upload_id: string
  credentials: Credential[]
}

/**
 * 申请预签名上传凭证
 */
export async function getUploadCredentials(files: { file_name: string; file_size: number; content_type: string }[]): Promise<CredentialsResponse> {
  const token = localStorage.getItem('token')
  const resp = await fetch('/api/upload/credentials', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ files }),
  })
  const data = await resp.json()
  if (data.code !== 0) throw new Error(data.message || '获取上传凭证失败')
  return data.data
}

/**
 * 直传 OBS（预签名 URL）
 * 注意：不能设置 Content-Type 头！OBS V2 签名把 content-type 签为空字符串
 */
export function uploadToObs(uploadUrl: string, file: Blob, onProgress?: (percent: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', uploadUrl)
    // OBS V2 签名默认把 Content-Type 签为空字符串。
    // 必须显式设置空字符串覆盖浏览器自动添加的 Content-Type,
    // 否则签名校验失败 403。
    try {
      xhr.setRequestHeader('Content-Type', '')
    } catch (e) {
      // 部分浏览器不允许空 header，忽略
    }
    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      }
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve()
      } else {
        // 记录响应内容（用于诊断）
        reject(new Error(`上传失败: HTTP ${xhr.status} ${xhr.statusText || ''} | ${(xhr.responseText || '').slice(0, 200)}`))
      }
    }
    xhr.onerror = () => reject(new Error('上传失败: 网络错误（CORS 或连接中断）'))
    xhr.ontimeout = () => reject(new Error('上传失败: 超时'))
    xhr.onabort = () => reject(new Error('上传失败: 中断'))
    xhr.send(file)
  })
}

/**
 * 完成上传回调
 */
export async function completeUpload(uploadId: string, files: { file_index: number; obs_key: string; file_name: string; file_size: number }[]): Promise<string[]> {
  const token = localStorage.getItem('token')
  const resp = await fetch('/api/upload/complete', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ upload_id: uploadId, files }),
  })
  const data = await resp.json()
  if (data.code !== 0) throw new Error(data.message || '完成上传失败')
  return data.data.asset_ids
}

/**
 * 批量导入（多文件直接走后端，支持 ARW/RAW 大文件）
 * 返回导入结果
 */
export async function bulkImport(files: File[], onProgress?: (done: number, total: number) => void): Promise<{ done: number; failed: number; skipped: number }> {
  const token = localStorage.getItem('token')
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }

  const resp = await fetch('/api/import/upload', {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })
  const data = await resp.json()
  if (data.code !== 0) throw new Error(data.message || '导入失败')
  onProgress?.(data.data.done, data.data.total)
  return data.data
}

/** 一站式上传：凭证 → 直传 → 完成回调（>100MB 自动走分片上传） */
export async function uploadFiles(
  files: File[],
  options?: {
    topCategoryId?: string | null
    concurrency?: number
    onFileProgress?: (
      index: number,
      percent: number,
      extra?: { multipart?: boolean; partNumber?: number; totalParts?: number; speed?: number },
    ) => void
    onFileStatus?: (index: number, status: 'uploading' | 'processing' | 'done' | 'failed') => void
  },
): Promise<string[]> {
  const { topCategoryId = null, concurrency = 3, onFileProgress, onFileStatus } = options || {}

  // 判断每个文件的类型
  const videoExts = ['mp4', 'mov', 'avi', 'mkv', 'webm']
  const fileInfos = files.map((f) => {
    const ext = f.name.split('.').pop()?.toLowerCase() || ''
    return {
      file_name: f.name,
      file_size: f.size,
      content_type: f.type || 'application/octet-stream',
      asset_type: videoExts.includes(ext) ? 'video' : 'image',
    }
  })

  // 分两类：小文件走预签名直传（批量凭证），大文件走分片上传
  const smallIndices = files.map((f, i) => (shouldMultipart(f) ? -1 : i)).filter((i) => i >= 0)
  const assetIds: string[] = []
  const token = localStorage.getItem('token')
  let credUploadId = ''

  // 小文件凭证（一次申请）
  let credentials: Credential[] = []
  if (smallIndices.length > 0) {
    const smallInfos = smallIndices.map((i) => fileInfos[i])
    const credResp = await fetch('/api/upload/credentials', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ files: smallInfos, top_category_id: topCategoryId || undefined }),
    })
    const credData = await credResp.json()
    if (credData.code !== 0) throw new Error(credData.message || '获取上传凭证失败')
    credentials = credData.data.credentials
    credUploadId = credData.data.upload_id
  }

  let current = 0
  const total = files.length

  async function worker() {
    while (current < total) {
      const i = current++
      const file = files[i]
      if (!file) continue

      onFileStatus?.(i, 'uploading')
      try {
        if (shouldMultipart(file)) {
          // 大文件：分片上传（自动断点续传）
          const assetId = await multipartUpload(file, {
            topCategoryId,
            onProgress: (p) => {
              onFileProgress?.(i, p.percent, {
                multipart: true,
                partNumber: p.partNumber,
                totalParts: p.totalParts,
                speed: p.speed,
              })
            },
          })
          if (assetId) assetIds.push(assetId)
        } else {
          // 小文件：直传 OBS
          const smallIdx = smallIndices.indexOf(i)
          const cred = credentials[smallIdx]
          if (!cred) throw new Error('缺少上传凭证')
          await uploadToObs(cred.upload_url, file, (p) => onFileProgress?.(i, p))
          onFileStatus?.(i, 'processing')
          const resp = await fetch('/api/upload/complete', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({
              upload_id: credUploadId,
              top_category_id: topCategoryId || undefined,
              files: [
                {
                  file_index: i,
                  obs_key: cred.obs_key,
                  file_name: file.name,
                  file_size: file.size,
                },
              ],
            }),
          })
          const data = await resp.json()
          if (data.code !== 0) throw new Error(data.message || '处理失败')
          assetIds.push(...data.data.asset_ids)
        }
        onFileStatus?.(i, 'done')
      } catch (err) {
        onFileProgress?.(i, -1)
        onFileStatus?.(i, 'failed')
      }
    }
  }

  const workers = Array.from({ length: Math.min(concurrency, total) }, () => worker())
  await Promise.all(workers)

  return assetIds
}
