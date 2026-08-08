import { useState, useEffect } from 'react'
import { assetApi, topCategoryApi, tagApi, TopCategory, Tag } from '../../lib/api'

/** 批量操作弹窗：星/旗/项目/标签/导出 */
export type BatchActionType = 'star' | 'flag' | 'move' | 'tag' | 'export'

interface Props {
  type: BatchActionType
  ids: string[]
  onClose: () => void
  onDone: () => void
}

// 旗标颜色映射（与 AssetCard 保持一致：1红/2橙/3黄/4绿/5蓝）
const FLAG_COLORS: Record<number, { name: string; color: string }> = {
  1: { name: '红', color: '#ef4444' },
  2: { name: '橙', color: '#f97316' },
  3: { name: '黄', color: '#eab308' },
  4: { name: '绿', color: '#22c55e' },
  5: { name: '蓝', color: '#3b82f6' },
}

const TITLE: Record<BatchActionType, string> = {
  star: '批量修改星级',
  flag: '批量修改旗标',
  move: '批量移至项目',
  tag: '批量加标签',
  export: '批量导出',
}

export function BatchActionModal({ type, ids, onClose, onDone }: Props) {
  const [busy, setBusy] = useState(false)
  const [projects, setProjects] = useState<TopCategory[]>([])
  const [tags, setTags] = useState<Tag[]>([])
  const [selectedTagIds, setSelectedTagIds] = useState<Set<string>>(new Set())
  const [exportType, setExportType] = useState<'original' | 'medium'>('original')
  const [exportResult, setExportResult] = useState<{ file_name: string; url: string }[] | null>(null)

  useEffect(() => {
    if (type === 'move') topCategoryApi.list().then(setProjects).catch(() => {})
    if (type === 'tag') {
      tagApi.tree().then((tree) => {
        const all: Tag[] = []
        Object.values(tree).forEach((list) => {
          list.forEach((t) => {
            all.push(t)
            if (t.children) all.push(...t.children)
          })
        })
        setTags(all)
      }).catch(() => {})
    }
  }, [type])

  const handleStar = async (level: number) => {
    setBusy(true)
    try {
      await assetApi.batchStar(ids, level)
      onDone()
    } finally {
      setBusy(false)
    }
  }

  const handleFlag = async (level: number) => {
    setBusy(true)
    try {
      await assetApi.batchFlag(ids, level)
      onDone()
    } finally {
      setBusy(false)
    }
  }

  const handleMove = async (projectId: string | null) => {
    setBusy(true)
    try {
      await assetApi.batchMove(ids, projectId)
      onDone()
    } finally {
      setBusy(false)
    }
  }

  const handleTag = async () => {
    if (selectedTagIds.size === 0) return
    setBusy(true)
    try {
      await assetApi.batchTag(ids, Array.from(selectedTagIds))
      onDone()
    } finally {
      setBusy(false)
    }
  }

  const handleExport = async () => {
    setBusy(true)
    try {
      const data = await assetApi.batchExport(ids, exportType)
      setExportResult(data.items.map((i) => ({ file_name: i.file_name, url: i.url })))
    } finally {
      setBusy(false)
    }
  }

  const copyAllUrls = () => {
    if (!exportResult) return
    navigator.clipboard.writeText(exportResult.map((r) => r.url).join('\n'))
  }

  return (
    <div className="fixed inset-0 z-[60] bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-zinc-900 rounded-xl shadow-2xl w-full max-w-md max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <h3 className="font-semibold">
            {TITLE[type]} <span className="text-sm font-normal text-zinc-400">({ids.length} 项)</span>
          </h3>
          <button onClick={onClose} className="text-zinc-400 hover:text-zinc-600 text-lg leading-none">✕</button>
        </div>

        <div className="p-5">
          {busy && <div className="text-sm text-teal-500 mb-3">处理中...</div>}

          {/* 星级选择 */}
          {type === 'star' && (
            <div className="space-y-2">
              {[5, 4, 3, 2, 1].map((lv) => (
                <button
                  key={lv}
                  disabled={busy}
                  onClick={() => handleStar(lv)}
                  className="w-full px-4 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:border-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 text-left"
                >
                  <span className="text-amber-500">{'★'.repeat(lv)}</span>
                  <span className="text-zinc-300 dark:text-zinc-600">{'★'.repeat(5 - lv)}</span>
                  <span className="ml-2 text-sm text-zinc-500">{lv} 星</span>
                </button>
              ))}
              <button
                disabled={busy}
                onClick={() => handleStar(0)}
                className="w-full px-4 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:border-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 text-sm text-zinc-500"
              >
                清除星级
              </button>
            </div>
          )}

          {/* 旗标选择 */}
          {type === 'flag' && (
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(FLAG_COLORS).map(([lv, info]) => (
                <button
                  key={lv}
                  disabled={busy}
                  onClick={() => handleFlag(Number(lv))}
                  className="px-4 py-3 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800 flex items-center gap-2"
                >
                  <span className="w-4 h-4 rounded-full" style={{ backgroundColor: info.color }} />
                  <span className="text-sm">{info.name}旗</span>
                </button>
              ))}
              <button
                disabled={busy}
                onClick={() => handleFlag(0)}
                className="px-4 py-3 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:bg-red-50 dark:hover:bg-red-900/20 text-sm text-zinc-500"
              >
                清除旗标
              </button>
            </div>
          )}

          {/* 项目选择 */}
          {type === 'move' && (
            <div className="space-y-2">
              {projects.map((p) => (
                <button
                  key={p.id}
                  disabled={busy}
                  onClick={() => handleMove(p.id)}
                  className="w-full px-4 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:border-teal-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 text-left text-sm"
                >
                  📁 {p.name}
                  {p.asset_count > 0 && <span className="ml-2 text-xs text-zinc-400">{p.asset_count} 个素材</span>}
                </button>
              ))}
              <button
                disabled={busy}
                onClick={() => handleMove(null)}
                className="w-full px-4 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:border-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 text-sm text-zinc-500"
              >
                移出所有项目（归入全局）
              </button>
            </div>
          )}

          {/* 标签多选 */}
          {type === 'tag' && (
            <div>
              <div className="flex flex-wrap gap-2 max-h-64 overflow-y-auto mb-4">
                {tags.map((t) => (
                  <button
                    key={t.id}
                    onClick={() =>
                      setSelectedTagIds((prev) => {
                        const next = new Set(prev)
                        if (next.has(t.id)) next.delete(t.id)
                        else next.add(t.id)
                        return next
                      })
                    }
                    className={`px-2.5 py-1 rounded-full text-xs border transition-colors ${
                      selectedTagIds.has(t.id)
                        ? 'bg-teal-500 text-white border-teal-500'
                        : 'border-zinc-300 dark:border-zinc-600 hover:border-teal-400'
                    }`}
                  >
                    {t.name}
                  </button>
                ))}
                {tags.length === 0 && <div className="text-sm text-zinc-400">暂无可选标签</div>}
              </div>
              <button
                disabled={busy || selectedTagIds.size === 0}
                onClick={handleTag}
                className="w-full py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 disabled:opacity-40 text-white text-sm font-medium"
              >
                给 {ids.length} 个素材加 {selectedTagIds.size} 个标签
              </button>
            </div>
          )}

          {/* 导出 */}
          {type === 'export' && !exportResult && (
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="radio" checked={exportType === 'original'} onChange={() => setExportType('original')} />
                导出原文件（原图/原视频）
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="radio" checked={exportType === 'medium'} onChange={() => setExportType('medium')} />
                导出中等缩略图（1200px，更快）
              </label>
              <button
                disabled={busy}
                onClick={handleExport}
                className="w-full py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium"
              >
                生成下载链接（24 小时有效）
              </button>
            </div>
          )}

          {/* 导出结果 */}
          {type === 'export' && exportResult && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-zinc-500">共 {exportResult.length} 个下载链接</span>
                <button onClick={copyAllUrls} className="text-xs px-2 py-1 rounded bg-teal-500 text-white hover:bg-teal-600">
                  复制全部链接
                </button>
              </div>
              <div className="space-y-1 max-h-64 overflow-y-auto text-xs">
                {exportResult.map((r, i) => (
                  <a key={i} href={r.url} target="_blank" rel="noreferrer" className="block truncate text-teal-600 dark:text-teal-400 hover:underline" title={r.url}>
                    {r.file_name}
                  </a>
                ))}
              </div>
              <button onClick={onDone} className="w-full mt-4 py-2 rounded-lg border border-zinc-300 dark:border-zinc-600 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-800">
                完成
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
