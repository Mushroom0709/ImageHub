/** 上传工具：预签名 URL 直传 OBS */

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
  const resp = await fetch('/api/upload/credentials', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
    xhr.setRequestHeader('Content-Type', '') // 显式空，避免浏览器默认类型
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
        reject(new Error(`上传失败: HTTP ${xhr.status}`))
      }
    }
    xhr.onerror = () => reject(new Error('上传失败: 网络错误'))
    xhr.send(file)
  })
}

/**
 * 完成上传回调
 */
export async function completeUpload(uploadId: string, files: { file_index: number; obs_key: string; file_name: string; file_size: number }[]): Promise<string[]> {
  const resp = await fetch('/api/upload/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ upload_id: uploadId, files }),
  })
  const data = await resp.json()
  if (data.code !== 0) throw new Error(data.message || '完成上传失败')
  return data.data.asset_ids
}

/**
 * 一站式上传：凭证 → 直传 → 完成回调
 */
export async function uploadFiles(
  files: File[],
  onFileProgress?: (index: number, percent: number) => void,
  onFileDone?: (index: number, assetId: string) => void,
): Promise<string[]> {
  const fileInfos = files.map((f) => ({
    file_name: f.name,
    file_size: f.size,
    content_type: f.type || 'application/octet-stream',
  }))

  const { upload_id, credentials } = await getUploadCredentials(fileInfos)

  const assetIds: string[] = []
  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    const cred = credentials[i]
    if (!cred) continue

    try {
      await uploadToObs(cred.upload_url, file, (p) => onFileProgress?.(i, p))
      const ids = await completeUpload(upload_id, [
        {
          file_index: i,
          obs_key: cred.obs_key,
          file_name: file.name,
          file_size: file.size,
        },
      ])
      assetIds.push(...ids)
      onFileDone?.(i, ids[0])
    } catch (err) {
      onFileProgress?.(i, -1) // -1 = 失败
    }
  }

  return assetIds
}
