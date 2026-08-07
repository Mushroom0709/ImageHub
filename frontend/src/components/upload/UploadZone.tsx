import { useRef, useState, useCallback } from 'react'
import { bulkImport } from '../../lib/upload'

interface UploadItem {
  id: string
  name: string
  status: 'uploading' | 'done' | 'failed'
  progress: number
}

interface Props {
  onUploaded: () => void
}

export function UploadZone({ onUploaded }: Props) {
  const [dragging, setDragging] = useState(false)
  const [items, setItems] = useState<UploadItem[]>([])
  const [showPanel, setShowPanel] = useState(false)
  const [importing, setImporting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 处理拖拽/选择（支持文件夹，通过 webkitRelativePath 识别）
  const handleDropFiles = useCallback(async (files: File[]) => {
    // 过滤支持的格式
    const supported = files.filter((f) =>
      /\.(jpg|jpeg|png|webp|gif|tiff|bmp|arw|raw|cr2|nef|dng|mp4|mov|avi|mkv)$/i.test(f.name),
    )
    if (supported.length === 0) return

    // 用批量导入（支持 ARW 大文件）
    setImporting(true)
    const newItems: UploadItem[] = supported.map((f) => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: f.webkitRelativePath || f.name,
      status: 'uploading',
      progress: 0,
    }))
    setItems(newItems)
    setShowPanel(true)

    try {
      await bulkImport(supported, (done, total) => {
        setItems((prev) => prev.map((item, i) => (i < done ? { ...item, status: 'done', progress: 100 } : item)))
      })
      setItems((prev) => prev.map((item) => ({ ...item, status: 'done', progress: 100 })))
      onUploaded()
    } catch (err) {
      console.error('导入失败', err)
      setItems((prev) => prev.map((item) => ({ ...item, status: 'failed' })))
    } finally {
      setImporting(false)
    }
  }, [onUploaded])

  // 拖拽事件（支持文件夹递归）
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(true)
  }
  const handleDragLeave = () => setDragging(false)

  const collectEntries = async (entries: FileSystemEntry[]): Promise<File[]> => {
    const files: File[] = []
    for (const entry of entries) {
      if (entry.isFile) {
        const file = await new Promise<File>((resolve) => (entry as FileSystemFileEntry).file(resolve))
        files.push(file)
      } else if (entry.isDirectory) {
        const reader = (entry as FileSystemDirectoryEntry).createReader()
        const subEntries = await new Promise<FileSystemEntry[]>((resolve) => reader.readEntries(resolve))
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
      const entries = items.map((i) => i.webkitGetAsEntry()).filter(Boolean) as FileSystemEntry[]
      const files = await collectEntries(entries)
      handleDropFiles(files)
    } else if (e.dataTransfer.files) {
      handleDropFiles(Array.from(e.dataTransfer.files))
    }
  }

  const doneCount = items.filter((i) => i.status === 'done').length
  const failCount = items.filter((i) => i.status === 'failed').length

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
            <div className="text-sm text-zinc-500 mt-1">支持图片和视频，含 ARW RAW 文件</div>
          </div>
        </div>
      )}

      {/* 上传进度面板 */}
      {showPanel && items.length > 0 && (
        <div className="fixed bottom-4 right-4 w-80 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-zinc-200 dark:border-zinc-800 z-30 overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
            <span className="font-medium text-sm">上传中</span>
            <span className="text-xs text-zinc-500">
              {doneCount}/{items.length}
              {failCount > 0 && <span className="text-red-500 ml-2">{failCount} 失败</span>}
            </span>
          </div>
          <div className="max-h-60 overflow-y-auto p-2 space-y-1.5">
            {items.map((item) => (
              <div key={item.id} className="flex items-center gap-2 text-sm">
                <span
                  className={`text-xs ${
                    item.status === 'done' ? 'text-green-500' : item.status === 'failed' ? 'text-red-500' : 'text-teal-500'
                  }`}
                >
                  {item.status === 'done' ? '✓' : item.status === 'failed' ? '✗' : '↻'}
                </span>
                <span className="flex-1 truncate text-zinc-700 dark:text-zinc-300">{item.name}</span>
                {item.status === 'uploading' && (
                  <span className="text-xs text-zinc-400">{item.progress}%</span>
                )}
              </div>
            ))}
          </div>
          <div className="h-1 bg-zinc-100 dark:bg-zinc-800">
            <div
              className="h-full bg-teal-500 transition-all"
              style={{ width: `${items.length ? (doneCount / items.length) * 100 : 0}%` }}
            />
          </div>
        </div>
      )}

      {/* 隐藏文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/*,video/*,.arw,.raw"
        className="hidden"
        onChange={(e) => {
          if (e.target.files) handleDropFiles(Array.from(e.target.files))
          e.target.value = ''
        }}
      />

      {/* 触发按钮（由外部控制） */}
      <button
        className="hidden"
        id="upload-trigger"
        onClick={() => fileInputRef.current?.click()}
      />
    </>
  )
}

/** 触发上传按钮的辅助函数 */
export function triggerUpload() {
  document.getElementById('upload-trigger')?.click()
}
