import { useRef, useState, useCallback } from 'react'
import { uploadFiles } from '../../lib/upload'

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
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    const fileList = Array.from(files).filter((f) =>
      /\.(jpg|jpeg|png|webp|gif|tiff|arw|mp4|mov)$/i.test(f.name),
    )
    if (fileList.length === 0) return

    const newItems: UploadItem[] = fileList.map((f) => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: f.name,
      status: 'uploading',
      progress: 0,
    }))
    setItems(newItems)
    setShowPanel(true)

    try {
      await uploadFiles(
        fileList,
        (index, percent) => {
          setItems((prev) =>
            prev.map((item, i) =>
              i === index
                ? { ...item, status: percent < 0 ? 'failed' : 'uploading', progress: percent < 0 ? 0 : percent }
                : item,
            ),
          )
        },
        (index) => {
          setItems((prev) =>
            prev.map((item, i) => (i === index ? { ...item, status: 'done', progress: 100 } : item)),
          )
        },
      )
      onUploaded()
    } catch (err) {
      console.error('上传失败', err)
    }
  }, [onUploaded])

  // 拖拽事件
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(true)
  }
  const handleDragLeave = () => setDragging(false)
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files)
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
          if (e.target.files) handleFiles(e.target.files)
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
