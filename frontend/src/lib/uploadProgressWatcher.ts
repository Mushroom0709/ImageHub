/**
 * 上传进度 SSE 全局监视器（模块级单例）
 *
 * 为什么是模块级单例而不是组件内 useEffect：
 * 1. /upload 页和首页悬浮窗都需要订阅，组件卸载不能断开连接
 * 2. 页面导航切换时 EventSource 保持存活，处理完成后仍能更新持久化 store
 * 3. 后端 progress_bus 订阅时回放历史，重连不丢事件
 *
 * done/failed 时派发 window 事件 imagehub-asset-done，首页用它刷新瀑布流。
 */
import { useUploadStore } from '../stores/uploadStore'

// assetId → EventSource（活跃订阅）
const activeSubs = new Map<string, EventSource>()

/** 确保某个 asset 的 SSE 订阅存在（幂等） */
export function ensureProgressWatch(assetId: string, itemId: string): void {
  if (activeSubs.has(assetId)) return

  const es = new EventSource(`/api/upload/events/${assetId}`)
  activeSubs.set(assetId, es)

  // 兜底看门狗：120s 后仍在终态 → 直接查素材接口确认（应对 API 重启丢 SSE 历史）
  let settled = false
  const watchdog = setTimeout(async () => {
    if (settled) return
    try {
      const token = localStorage.getItem('token')
      const resp = await fetch(`/api/assets/${assetId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!resp.ok) return
      const data = await resp.json()
      if (data.code !== 0) return
      const asset = data.data
      // 有宽高（缩略图完成）或有标签 → 视为处理完成
      const hasThumb = asset.width > 0 || asset.height > 0
      const hasTags = Array.isArray(asset.tags) && asset.tags.length > 0
      if (hasThumb || hasTags) {
        const { updateItem, updateStage } = useUploadStore.getState()
        updateStage(itemId, 'thumbnail', { status: hasThumb ? 'done' : 'processing', progress: hasThumb ? 100 : 0 })
        updateStage(itemId, 'exif', { status: 'done', progress: 100 })
        updateStage(itemId, 'ai_tagging', { status: hasTags ? 'done' : 'failed', progress: hasTags ? 100 : 0 })
        updateStage(itemId, 'phash', { status: 'pending' })
        updateItem(itemId, { status: 'done', overallProgress: 100 })
        window.dispatchEvent(new CustomEvent('imagehub-asset-done', { detail: { assetId, itemId } }))
        cleanup()
      }
    } catch {
      // 网络问题忽略，等 SSE 或下次 sync
    }
  }, 120_000)

  const handleEvent = (eventName: string, payloadStr: string) => {
    const { updateItem, updateStage } = useUploadStore.getState()
    // payload 格式: "{stage}|{ts}|{payload_dict}"
    const parts = payloadStr.split('|')
    let payload: Record<string, any> = {}
    if (parts[2]) {
      try {
        payload = JSON.parse(parts[2].replace(/'/g, '"'))
      } catch {
        payload = {}
      }
    }

    if (eventName === 'uploaded') {
      updateStage(itemId, 'obs', { status: 'done', progress: 100 })
      updateItem(itemId, { overallProgress: 60, status: 'processing' })
    } else if (eventName === 'thumbnail') {
      updateStage(itemId, 'thumbnail', {
        status: payload.status === 'done' ? 'done' : payload.status === 'failed' ? 'failed' : 'processing',
      })
      if (payload.status === 'done') {
        updateStage(itemId, 'thumbnail', { status: 'done', progress: 100, payload })
        updateItem(itemId, { overallProgress: 80 })
      }
    } else if (eventName === 'exif') {
      updateStage(itemId, 'exif', {
        status: payload.status === 'done' ? 'done' : payload.status === 'failed' ? 'failed' : 'processing',
        payload,
      })
      if (payload.status === 'done') {
        updateStage(itemId, 'exif', { status: 'done', progress: 100 })
        updateItem(itemId, { overallProgress: 88 })
      }
    } else if (eventName === 'ai_tagging') {
      updateStage(itemId, 'ai_tagging', {
        status: payload.status === 'done' ? 'done' : payload.status === 'failed' ? 'failed' : 'processing',
        payload,
      })
      if (payload.status === 'done') {
        updateStage(itemId, 'ai_tagging', { status: 'done', progress: 100 })
        updateItem(itemId, { overallProgress: 95 })
      }
    } else if (eventName === 'done') {
      settled = true
      clearTimeout(watchdog)
      updateStage(itemId, 'phash', { status: 'pending' }) // pHash 未实装，保持 pending
      updateItem(itemId, { status: 'done', overallProgress: 100 })
      window.dispatchEvent(new CustomEvent('imagehub-asset-done', { detail: { assetId, itemId } }))
      cleanup()
    } else if (eventName === 'failed') {
      settled = true
      clearTimeout(watchdog)
      updateItem(itemId, { status: 'failed', errorMessage: payload.error || '后端处理失败' })
      window.dispatchEvent(new CustomEvent('imagehub-asset-done', { detail: { assetId, itemId } }))
      cleanup()
    }
  }

  const cleanup = () => {
    es.close()
    activeSubs.delete(assetId)
  }

  es.addEventListener('connected', () => {})
  es.addEventListener('uploaded', (e) => handleEvent('uploaded', (e as MessageEvent).data))
  es.addEventListener('thumbnail', (e) => handleEvent('thumbnail', (e as MessageEvent).data))
  es.addEventListener('exif', (e) => handleEvent('exif', (e as MessageEvent).data))
  es.addEventListener('ai_tagging', (e) => handleEvent('ai_tagging', (e as MessageEvent).data))
  es.addEventListener('done', (e) => handleEvent('done', (e as MessageEvent).data))
  es.addEventListener('failed', (e) => handleEvent('failed', (e as MessageEvent).data))
}

/** 扫描 store，为所有 processing 状态的 item 建立订阅 */
export function syncProgressWatches(): void {
  const { items } = useUploadStore.getState()
  for (const item of items) {
    if (item.assetId && item.status === 'processing') {
      ensureProgressWatch(item.assetId, item.id)
    }
  }
}

/** 当前活跃订阅数（调试用） */
export function activeWatchCount(): number {
  return activeSubs.size
}
