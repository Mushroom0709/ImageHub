import { forwardRef, useImperativeHandle, useRef, useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadFiles } from '../../lib/upload'
import { useUIStore } from '../../stores/uiStore'
import { useUploadStore, newUploadItem } from '../../stores/uploadStore'

interface Props {
  onUploaded: () => void
}

const VIDEO_EXTS = ['mp4', 'mov', 'avi', 'mkv', 'webm']
const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'tiff', 'bmp', 'arw', 'raw', 'cr2', 'nef', 'dng']
const SUPPORTED_EXTS = new Set([...IMAGE_EXTS, ...VIDEO_EXTS])

function isSupported(name: string): boolean {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  return SUPPORTED_EXTS.has(ext)
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

function formatSpeed(bytesPerSec: number): string {
  if (!bytesPerSec || bytesPerSec <= 0) return ''
  if (bytesPerSec < 1024) return `${Math.round(bytesPerSec)} B/s`
  if (bytesPerSec < 1024 * 1024) return `${(bytesPerSec / 1024).toFixed(0)} KB/s`
  return `${(bytesPerSec / 1024 / 1024).toFixed(1)} MB/s`
}

// 模块级单例：跟踪正在订阅 SSE 的 assetId（避免 useEffect 重复订阅）
const activeSSESubs = new Set<string>()

export const UploadZone = forwardRef<{ openFiles: () => void; openFolder: () => void }, Props>(
  function UploadZone({ onUploaded }, ref) {
    const navigate = useNavigate()
    const [dragging, setDragging] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)
    const folderInputRef = useRef<HTMLInputElement>(null)
    const currentTopCategoryId = useUIStore((s: any) => s.currentTopCategoryId)

    // 来自 store（持久化）
    const items = useUploadStore((s) => s.items)
    const panelCollapsed = useUploadStore((s) => s.panelCollapsed)
    const setPanelCollapsed = useUploadStore((s) => s.setPanelCollapsed)
    const addItems = useUploadStore((s) => s.addItems)
    const updateItem = useUploadStore((s) => s.updateItem)
    const updateStage = useUploadStore((s) => s.updateStage)

    useImperativeHandle(ref, () => ({
      openFiles: () => fileInputRef.current?.click(),
      openFolder: () => folderInputRef.current?.click(),
    }))

    // 后端 SSE 阶段订阅：每个 uploading/processing 的 item 订阅一次
    useEffect(() => {
      const sources: EventSource[] = []
      for (const item of items) {
        const assetId = item.assetId
        if (!assetId || item.status !== 'processing') continue
        // 模块级单例去重（React strict mode 会双跑 effect + items 变化时重跑）
        if (activeSSESubs.has(assetId)) continue
        activeSSESubs.add(assetId)

        const url = `/api/upload/events/${assetId}`
        const es = new EventSource(url)
        sources.push(es)

        const handleEvent = (eventName: string, payloadStr: string) => {
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
            updateStage(item.id, 'obs', { status: 'done', progress: 100 })
            updateItem(item.id, { overallProgress: 60, status: 'processing' })
          } else if (eventName === 'thumbnail') {
            updateStage(item.id, 'thumbnail', {
              status: payload.status === 'done' ? 'done' : payload.status === 'failed' ? 'failed' : 'processing',
            })
            if (payload.status === 'done') {
              updateStage(item.id, 'thumbnail', { status: 'done', progress: 100, payload })
              updateItem(item.id, { overallProgress: 80 })
            }
          } else if (eventName === 'exif') {
            updateStage(item.id, 'exif', {
              status: payload.status === 'done' ? 'done' : payload.status === 'failed' ? 'failed' : 'processing',
              payload,
            })
            if (payload.status === 'done') {
              updateStage(item.id, 'exif', { status: 'done', progress: 100 })
              updateItem(item.id, { overallProgress: 88 })
            }
          } else if (eventName === 'ai_tagging') {
            updateStage(item.id, 'ai_tagging', {
              status: payload.status === 'done' ? 'done' : payload.status === 'failed' ? 'failed' : 'processing',
              payload,
            })
            if (payload.status === 'done') {
              updateStage(item.id, 'ai_tagging', { status: 'done', progress: 100 })
              updateItem(item.id, { overallProgress: 95 })
            }
          } else if (eventName === 'done') {
            // 后端全部处理完（即便 ai failed 也 done）
            updateStage(item.id, 'phash', { status: 'pending' }) // pHash 未实装，保持 pending
            updateItem(item.id, { status: 'done', overallProgress: 100 })
            onUploaded()
            activeSSESubs.delete(assetId)
            es.close()
          } else if (eventName === 'failed') {
            updateItem(item.id, { status: 'failed', overallProgress: item.overallProgress, errorMessage: payload.error })
            activeSSESubs.delete(assetId)
            es.close()
          }
        }

        es.addEventListener('connected', () => {})
        es.addEventListener('uploaded', (e) => handleEvent('uploaded', (e as MessageEvent).data))
        es.addEventListener('thumbnail', (e) => handleEvent('thumbnail', (e as MessageEvent).data))
        es.addEventListener('exif', (e) => handleEvent('exif', (e as MessageEvent).data))
        es.addEventListener('ai_tagging', (e) => handleEvent('ai_tagging', (e as MessageEvent).data))
        es.addEventListener('done', (e) => handleEvent('done', (e as MessageEvent).data))
        es.addEventListener('failed', (e) => handleEvent('failed', (e as MessageEvent).data))
      }
      return () => sources.forEach((s) => s.close())
    }, [items, updateItem, updateStage, onUploaded])

    // 开始上传
    const startUpload = useCallback(
      async (files: File[]) => {
        const supported = files.filter((f) => isSupported(f.name))
        if (supported.length === 0) {
          alert('没有支持的图片或视频文件')
          return
        }

        // 创建 store items
        const newItems = supported.map((f) =>
          newUploadItem(f.webkitRelativePath || f.name, f.size),
        )
        addItems(newItems)
        setPanelCollapsed(false)

        try {
          // 构造 server item 索引映射：files → item.id
          await uploadFiles(supported, {
            topCategoryId: currentTopCategoryId,
            concurrency: 3,
            onFileProgress: (i, p, extra) => {
              const itemId = newItems[i].id
              updateItem(itemId, {
                overallProgress: Math.min(60, Math.round(p * 0.6)), // OBS 阶段上限 60%
                multipart: extra?.multipart,
                partNumber: extra?.partNumber,
                totalParts: extra?.totalParts,
                speed: extra?.speed,
              })
              updateStage(itemId, 'obs', { progress: p, status: 'processing' })
            },
            onFileStatus: (i, status, assetId) => {
              const itemId = newItems[i].id
              if (status === 'uploading') {
                updateItem(itemId, { status: 'uploading' })
              } else if (status === 'processing') {
                updateItem(itemId, { status: 'processing', assetId })
              } else if (status === 'done') {
                updateItem(itemId, { status: 'done', overallProgress: 100 })
                updateStage(itemId, 'obs', { status: 'done', progress: 100 })
              } else if (status === 'failed') {
                updateItem(itemId, { status: 'failed' })
              }
            },
          })

          // 通知父级（让首页刷新素材列表）
          onUploaded()
        } catch (err) {
          console.error('上传失败', err)
        }
      },
      [currentTopCategoryId, onUploaded, addItems, updateItem, updateStage, setPanelCollapsed],
    )

    // 拖拽
    const handleDragOver = (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(true)
    }
    const handleDragLeave = () => setDragging(false)

    const collectEntries = async (entries: FileSystemEntry[]): Promise<File[]> => {
      const files: File[] = []
      for (const entry of entries) {
        if (entry.isFile) {
          const file = await new Promise<File>((resolve) =>
            (entry as FileSystemFileEntry).file(resolve),
          )
          files.push(file)
        } else if (entry.isDirectory) {
          const reader = (entry as FileSystemDirectoryEntry).createReader()
          const subEntries = await new Promise<FileSystemEntry[]>((resolve) =>
            reader.readEntries(resolve),
          )
          files.push(...(await collectEntries(subEntries)))
        }
      }
      return files
    }

    const handleDrop = async (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const items = Array.from(e.dataTransfer.items || [])
      const hasEntryMethod = items.length > 0 && typeof items[0].webkitGetAsEntry === 'function'
      if (hasEntryMethod) {
        const entries = items
          .map((i) => i.webkitGetAsEntry())
          .filter(Boolean) as FileSystemEntry[]
        const files = await collectEntries(entries)
        startUpload(files)
      } else if (e.dataTransfer.files) {
        startUpload(Array.from(e.dataTransfer.files))
      }
    }

    const doneCount = items.filter((i) => i.status === 'done').length
    const failCount = items.filter((i) => i.status === 'failed').length
    const totalSize = items.reduce((s, i) => s + i.size, 0)
    const uploadedSize = items.reduce((s, i) => {
      if (i.status === 'done') return s + i.size
      if (i.status === 'uploading' && i.overallProgress > 0) return s + (i.size * i.overallProgress) / 100
      if (i.status === 'processing') return s + i.size * 0.6
      return s
    }, 0)
    const totalPercent = totalSize > 0 ? Math.round((uploadedSize / totalSize) * 100) : 0

    const uploading = items.some((i) => i.status === 'uploading')

    return (
      <>
        {/* 全局拖拽遮罩 */}
        {dragging && (
          <div
            className="fixed inset-0 z-40 bg-teal-600/20 backdrop-blur-sm flex items-center justify-center"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="p-8 rounded-2xl bg-white dark:bg-zinc-900 shadow-2xl text-center border-2 border-dashed border-teal-500">
              <div className="text-4xl mb-3">📤</div>
              <div className="text-lg font-medium">松手即可上传</div>
              <div className="text-sm text-zinc-500 mt-1">支持图片/视频/ARW，可拖拽整个文件夹</div>
            </div>
          </div>
        )}

        {/* 上传进度面板 */}
        {items.length > 0 && !panelCollapsed && (
          <div className="fixed bottom-4 right-4 w-[420px] bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-zinc-200 dark:border-zinc-800 z-30 overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
              <div>
                <span className="font-medium text-sm">
                  {uploading
                    ? '上传中...'
                    : doneCount === items.length
                      ? '上传完成'
                      : '上传结果'}
                </span>
                <span className="text-xs text-zinc-500 ml-2">
                  {doneCount}/{items.length} · {totalPercent}%
                </span>
              </div>
              <div className="flex items-center gap-2">
                {failCount > 0 && <span className="text-xs text-red-500">{failCount} 失败</span>}
                <button
                  onClick={() => navigate('/upload')}
                  className="text-zinc-400 hover:text-teal-500 text-xs px-2"
                  title="打开完整上传页"
                >
                  ↗ 详情
                </button>
                <button
                  onClick={() => setPanelCollapsed(true)}
                  className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 text-sm w-5 h-5 flex items-center justify-center rounded hover:bg-zinc-100 dark:hover:bg-zinc-800"
                  title="最小化"
                >
                  —
                </button>
              </div>
            </div>
            {/* 总进度条 */}
            <div className="h-1 bg-zinc-100 dark:bg-zinc-800">
              <div
                className="h-full bg-teal-500 transition-all duration-300"
                style={{ width: `${totalPercent}%` }}
              />
            </div>
            <div className="max-h-72 overflow-y-auto">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="px-3 py-2 border-b border-zinc-100 dark:border-zinc-800/50 last:border-0"
                >
                  <div className="flex items-center gap-2 text-sm">
                    <span
                      className={`text-xs w-4 text-center ${
                        item.status === 'done'
                          ? 'text-green-500'
                          : item.status === 'failed'
                            ? 'text-red-500'
                            : item.status === 'processing'
                              ? 'text-amber-500'
                              : 'text-teal-500'
                      }`}
                    >
                      {item.status === 'done'
                        ? '✓'
                        : item.status === 'failed'
                          ? '✗'
                          : item.status === 'processing'
                            ? '⚙'
                            : '↻'}
                    </span>
                    <span className="flex-1 truncate text-zinc-700 dark:text-zinc-300">{item.name}</span>
                    <span className="text-xs text-zinc-400 w-20 text-right">
                      {item.status === 'uploading' ? (
                        item.multipart ? (
                          <span className="flex flex-col items-end leading-tight">
                            <span>
                              {Math.round(item.overallProgress)}%
                              {item.speed ? ` · ${formatSpeed(item.speed)}` : ''}
                            </span>
                            {item.partNumber && item.totalParts && (
                              <span className="text-[10px] text-teal-500">
                                part {item.partNumber}/{item.totalParts}
                              </span>
                            )}
                          </span>
                        ) : (
                          `${Math.round(item.overallProgress)}%`
                        )
                      ) : item.status === 'done' ? (
                        formatSize(item.size)
                      ) : item.status === 'failed' ? (
                        '失败'
                      ) : item.status === 'processing' ? (
                        '后端处理'
                      ) : (
                        '等待中'
                      )}
                    </span>
                  </div>
                  {item.status !== 'done' && item.status !== 'processing' && item.status !== 'failed' && (
                    <div className="h-0.5 bg-zinc-100 dark:bg-zinc-800 mt-1.5 ml-6">
                      <div
                        className="h-full bg-teal-400 transition-all duration-200"
                        style={{ width: `${Math.max(0, item.overallProgress)}%` }}
                      />
                    </div>
                  )}
                  {item.status === 'processing' && (
                    // 处理阶段：缩略图/EXIF/AI 打标小点指示
                    <div className="flex items-center gap-1 ml-6 mt-1">
                      {(['thumbnail', 'exif', 'ai_tagging'] as const).map((stage) => {
                        const s = item.stages[stage]
                        const color =
                          s.status === 'done'
                            ? 'bg-teal-500'
                            : s.status === 'processing'
                              ? 'bg-teal-400 animate-pulse'
                              : s.status === 'failed'
                                ? 'bg-red-500'
                                : 'bg-zinc-300 dark:bg-zinc-700'
                        return (
                          <span key={stage} className={`w-1.5 h-1.5 rounded-full ${color}`} />
                        )
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 折叠状态：右下角小圆按钮 */}
        {items.length > 0 && panelCollapsed && (
          <button
            onClick={() => setPanelCollapsed(false)}
            className="fixed bottom-4 right-4 w-12 h-12 rounded-full bg-teal-600 hover:bg-teal-700 text-white shadow-lg z-30 flex items-center justify-center transition-transform hover:scale-105"
            title={`上传进度 (${doneCount}/${items.length})`}
          >
            {uploading ? (
              <div className="relative w-8 h-8">
                <svg className="w-8 h-8 -rotate-90" viewBox="0 0 32 32">
                  <circle cx="16" cy="16" r="14" fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="3" />
                  <circle
                    cx="16"
                    cy="16"
                    r="14"
                    fill="none"
                    stroke="white"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeDasharray={`${totalPercent * 0.88} 88`}
                    className="transition-all duration-300"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-xs font-medium">
                  {totalPercent}%
                </span>
              </div>
            ) : (
              <div className="relative">
                <span className="text-lg">📥</span>
                {doneCount > 0 && (
                  <span className="absolute -top-1 -right-2 w-4 h-4 bg-green-500 text-white text-[10px] rounded-full flex items-center justify-center font-medium">
                    {doneCount > 9 ? '9+' : doneCount}
                  </span>
                )}
                {failCount > 0 && (
                  <span className="absolute -bottom-1 -right-2 w-4 h-4 bg-red-500 text-white text-[10px] rounded-full flex items-center justify-center font-medium">
                    {failCount > 9 ? '!' : failCount}
                  </span>
                )}
              </div>
            )}
          </button>
        )}

        {/* 文件选择 input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,video/*,.arw,.raw,.cr2,.nef,.dng"
          className="hidden"
          onChange={(e) => {
            if (e.target.files) startUpload(Array.from(e.target.files))
            e.target.value = ''
          }}
        />
        {/* 文件夹选择 input */}
        <input
          ref={folderInputRef}
          type="file"
          multiple
          // @ts-expect-error webkitdirectory 是非标准属性
          webkitdirectory=""
          directory=""
          className="hidden"
          onChange={(e) => {
            if (e.target.files) startUpload(Array.from(e.target.files))
            e.target.value = ''
          }}
        />
      </>
    )
  },
)