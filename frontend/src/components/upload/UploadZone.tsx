import { forwardRef, useImperativeHandle, useRef, useState, useCallback } from 'react'
import { uploadFiles } from '../../lib/upload'
import { useUIStore } from '../../stores/uiStore'

interface UploadItem {
  id: string
  name: string
  size: number
  progress: number // 0-100, -1=失败
  status: 'waiting' | 'uploading' | 'processing' | 'done' | 'failed'
}

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

export const UploadZone = forwardRef<{ openFiles: () => void; openFolder: () => void }, Props>(
  function UploadZone({ onUploaded }, ref) {
    const [dragging, setDragging] = useState(false)
    const [items, setItems] = useState<UploadItem[]>([])
    const [showPanel, setShowPanel] = useState(false)
    const [uploading, setUploading] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)
    const folderInputRef = useRef<HTMLInputElement>(null)
    const currentTopCategoryId = useUIStore((s: any) => s.currentTopCategoryId)

    useImperativeHandle(ref, () => ({
      openFiles: () => fileInputRef.current?.click(),
      openFolder: () => folderInputRef.current?.click(),
    }))

    // 开始上传
    const startUpload = useCallback(
      async (files: File[]) => {
        const supported = files.filter((f) => isSupported(f.name))
        if (supported.length === 0) {
          alert('没有支持的图片或视频文件')
          return
        }

        const newItems: UploadItem[] = supported.map((f, i) => ({
          id: `${Date.now()}-${i}`,
          name: f.webkitRelativePath || f.name,
          size: f.size,
          progress: 0,
          status: 'waiting',
        }))
        setItems(newItems)
        setShowPanel(true)
        setUploading(true)

        try {
          await uploadFiles(supported, {
            topCategoryId: currentTopCategoryId,
            concurrency: 3,
            onFileProgress: (i, p) => {
              setItems((prev) =>
                prev.map((item, idx) => (idx === i ? { ...item, progress: p } : item)),
              )
            },
            onFileStatus: (i, status) => {
              setItems((prev) =>
                prev.map((item, idx) =>
                  idx === i
                    ? { ...item, status, progress: status === 'done' ? 100 : item.progress }
                    : item,
                ),
              )
            },
          })
          onUploaded()
        } catch (err) {
          console.error('上传失败', err)
        } finally {
          setUploading(false)
        }
      },
      [currentTopCategoryId, onUploaded],
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
      if (i.status === 'uploading' && i.progress > 0) return s + (i.size * i.progress) / 100
      return s
    }, 0)
    const totalPercent = totalSize > 0 ? Math.round((uploadedSize / totalSize) * 100) : 0

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
        {showPanel && items.length > 0 && (
          <div className="fixed bottom-4 right-4 w-96 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-zinc-200 dark:border-zinc-800 z-30 overflow-hidden">
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
                {failCount > 0 && (
                  <span className="text-xs text-red-500">{failCount} 失败</span>
                )}
                <button
                  onClick={() => setShowPanel(false)}
                  className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 text-sm"
                >
                  ✕
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
                    <span className="flex-1 truncate text-zinc-700 dark:text-zinc-300">
                      {item.name}
                    </span>
                    <span className="text-xs text-zinc-400 w-16 text-right">
                      {item.status === 'uploading'
                        ? `${item.progress}%`
                        : item.status === 'done'
                          ? formatSize(item.size)
                          : item.status === 'failed'
                            ? '失败'
                            : item.status === 'processing'
                              ? '处理中'
                              : '等待中'}
                    </span>
                  </div>
                  {/* 单文件进度条 */}
                  {item.status !== 'done' && item.status !== 'processing' && item.status !== 'failed' && (
                    <div className="h-0.5 bg-zinc-100 dark:bg-zinc-800 mt-1.5 ml-6">
                      <div
                        className="h-full bg-teal-400 transition-all duration-200"
                        style={{ width: `${Math.max(0, item.progress)}%` }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
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
