import { Link, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { useUploadStore, Stage } from '../stores/uploadStore'
import { UploadItem } from '../stores/uploadStore'

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

function fmtTime(ms: number): string {
  const sec = Math.floor(ms / 1000)
  if (sec < 60) return `${sec}s`
  if (sec < 3600) return `${Math.floor(sec / 60)}m ${sec % 60}s`
  return `${Math.floor(sec / 3600)}h ${Math.floor((sec % 3600) / 60)}m`
}

/** 单个 5 阶段进度环（圆环图） */
function StageRings({ item }: { item: UploadItem }) {
  const stageLabels: Record<Stage, string> = {
    obs: 'OBS',
    thumbnail: '缩略图',
    exif: 'EXIF',
    ai_tagging: 'AI 打标',
    phash: 'pHash',
  }
  const stageOrder: Stage[] = ['obs', 'thumbnail', 'exif', 'ai_tagging', 'phash']

  return (
    <div className="flex items-center gap-3">
      {stageOrder.map((stage) => {
        const s = item.stages[stage]
        const color =
          s.status === 'done'
            ? 'text-teal-500'
            : s.status === 'failed'
              ? 'text-red-500'
              : s.status === 'processing'
                ? 'text-teal-400'
                : 'text-zinc-300 dark:text-zinc-700'
        const ringBg =
          s.status === 'done'
            ? 'stroke-teal-500'
            : s.status === 'failed'
              ? 'stroke-red-500'
              : s.status === 'processing'
                ? 'stroke-teal-400'
                : 'stroke-zinc-200 dark:stroke-zinc-800'

        // obs 阶段进度是分片百分比，其他阶段固定 0/100
        const pct = stage === 'obs' ? Math.min(100, Math.max(0, s.progress)) : s.status === 'done' ? 100 : 0

        const r = 14
        const c = 2 * Math.PI * r
        const offset = c * (1 - pct / 100)

        return (
          <div key={stage} className="flex flex-col items-center gap-1">
            <div className="relative w-9 h-9">
              <svg className="w-9 h-9 -rotate-90" viewBox="0 0 36 36">
                <circle cx="18" cy="18" r={r} fill="none" className="stroke-zinc-200 dark:stroke-zinc-800" strokeWidth="2" />
                <circle
                  cx="18"
                  cy="18"
                  r={r}
                  fill="none"
                  className={ringBg}
                  strokeWidth="2"
                  strokeDasharray={c}
                  strokeDashoffset={offset}
                  strokeLinecap="round"
                  style={{ transition: 'stroke-dashoffset 0.3s ease' }}
                />
              </svg>
              <span className={`absolute inset-0 flex items-center justify-center text-[10px] font-medium ${color}`}>
                {s.status === 'done' ? '✓' : s.status === 'failed' ? '✕' : s.status === 'processing' ? '…' : '·'}
              </span>
            </div>
            <span className="text-[10px] text-zinc-500 dark:text-zinc-400">{stageLabels[stage]}</span>
          </div>
        )
      })}
    </div>
  )
}

/** 单条上传记录 */
function UploadRow({ item }: { item: UploadItem }) {
  const removeItem = useUploadStore((s) => s.removeItem)

  return (
    <tr className="border-b border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900/50">
      {/* 文件名 + 大小 */}
      <td className="px-4 py-3 align-middle">
        <div className="flex flex-col">
          <span className="text-sm font-medium truncate max-w-xs" title={item.name}>
            {item.name}
          </span>
          <span className="text-xs text-zinc-500">{formatSize(item.size)}</span>
        </div>
      </td>

      {/* 状态文字 */}
      <td className="px-4 py-3 align-middle whitespace-nowrap">
        {item.status === 'waiting' && <span className="text-xs text-zinc-500">等待中</span>}
        {item.status === 'uploading' && (
          <div className="flex flex-col text-xs">
            <span className="text-teal-500">
              {item.multipart ? `分片上传中 ${item.partNumber}/${item.totalParts}` : `OBS 上传 ${item.overallProgress}%`}
            </span>
            {item.speed ? <span className="text-zinc-500">{formatSpeed(item.speed)}</span> : null}
          </div>
        )}
        {item.status === 'processing' && (
          <div className="flex flex-col text-xs">
            <span className="text-teal-400">后端处理中</span>
            <span className="text-zinc-500">已上传至 OBS</span>
          </div>
        )}
        {item.status === 'done' && (
          <span className="text-xs text-teal-600 dark:text-teal-400 font-medium">✓ 完成</span>
        )}
        {item.status === 'failed' && (
          <span className="text-xs text-red-500 font-medium" title={item.errorMessage}>
            ✕ 失败
          </span>
        )}
      </td>

      {/* 5 阶段进度环 */}
      <td className="px-4 py-3 align-middle">
        <StageRings item={item} />
      </td>

      {/* 总进度 */}
      <td className="px-4 py-3 align-middle w-48">
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-zinc-200 dark:bg-zinc-800 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all ${
                item.status === 'failed'
                  ? 'bg-red-500'
                  : item.status === 'done'
                    ? 'bg-teal-500'
                    : 'bg-teal-400'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, item.overallProgress))}%` }}
            />
          </div>
          <span className="text-xs font-mono w-10 text-right">{Math.round(item.overallProgress)}%</span>
        </div>
      </td>

      {/* 操作 */}
      <td className="px-4 py-3 align-middle text-right">
        <button
          onClick={() => removeItem(item.id)}
          className="text-xs text-zinc-400 hover:text-red-500 px-2 py-1"
          title="从队列移除"
        >
          ✕
        </button>
      </td>
    </tr>
  )
}

export function UploadPage() {
  const navigate = useNavigate()
  const items = useUploadStore((s) => s.items)
  const clearDone = useUploadStore((s) => s.clearDone)
  const clearFailed = useUploadStore((s) => s.clearFailed)

  const doneCount = items.filter((i) => i.status === 'done').length
  const failedCount = items.filter((i) => i.status === 'failed').length
  const uploadingCount = items.filter((i) => i.status === 'uploading' || i.status === 'processing').length

  return (
    <div className="h-screen flex flex-col">
      <TopBar onBack={() => navigate('/')} />

      <div className="flex-1 overflow-y-auto bg-zinc-50 dark:bg-zinc-950">
        <div className="max-w-6xl mx-auto px-6 py-6">
          {/* 顶部统计 */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold mb-1">上传队列</h1>
              <p className="text-sm text-zinc-500">
                共 {items.length} 项 · 完成 {doneCount} · 上传中 {uploadingCount}
                {failedCount > 0 && <span className="text-red-500"> · 失败 {failedCount}</span>}
              </p>
            </div>
            <div className="flex gap-2">
              {failedCount > 0 && (
                <button
                  onClick={clearFailed}
                  className="px-3 py-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-sm"
                >
                  清除失败
                </button>
              )}
              {doneCount > 0 && (
                <button
                  onClick={clearDone}
                  className="px-3 py-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-sm"
                >
                  清除已完成
                </button>
              )}
              <Link
                to="/"
                className="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium"
              >
                返回素材库
              </Link>
            </div>
          </div>

          {/* 提示横幅 */}
          <div className="mb-4 p-3 rounded-lg bg-teal-50 dark:bg-teal-950/30 border border-teal-200 dark:border-teal-900 text-sm text-teal-700 dark:text-teal-300">
            💡 上传任务在所有页面共享：刷新页面或切换页面不会丢失进度。后端处理（缩略图/EXIF/AI 打标）通常 5-15 秒。
          </div>

          {/* 上传任务表格 */}
          {items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-zinc-400">
              <span className="text-6xl mb-4">📤</span>
              <p className="text-base font-medium">暂无上传任务</p>
              <p className="text-sm mt-1">从首页或素材页拖入文件即可开始</p>
              <Link
                to="/"
                className="mt-4 px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium"
              >
                返回首页
              </Link>
            </div>
          ) : (
            <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden">
              <table className="w-full">
                <thead className="bg-zinc-50 dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800">
                  <tr className="text-xs text-zinc-500 uppercase tracking-wide">
                    <th className="px-4 py-2 text-left font-medium">文件</th>
                    <th className="px-4 py-2 text-left font-medium">状态</th>
                    <th className="px-4 py-2 text-left font-medium">处理阶段</th>
                    <th className="px-4 py-2 text-left font-medium">总进度</th>
                    <th className="px-4 py-2 text-right font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <UploadRow key={item.id} item={item} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}