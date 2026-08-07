import { useSelectionStore } from '../../stores/uiStore'
import { assetApi } from '../../lib/api'

interface Props {
  onChanged: () => void
}

export function SelectionToolbar({ onChanged }: Props) {
  const selectMode = useSelectionStore((s) => s.selectMode)
  const selectedIds = useSelectionStore((s) => s.selectedIds)
  const exitSelectMode = useSelectionStore((s) => s.exitSelectMode)
  const clearSelection = useSelectionStore((s) => s.clearSelection)

  if (!selectMode || selectedIds.size === 0) return null

  const ids = Array.from(selectedIds)

  const handleStar = async () => {
    for (const id of ids) {
      await assetApi.update(id, { starred: true })
    }
    onChanged()
    clearSelection()
  }

  const handleDelete = async () => {
    if (!confirm(`确定删除选中的 ${ids.length} 个素材吗？（移入回收站）`)) return
    await assetApi.batchDelete(ids)
    onChanged()
    clearSelection()
  }

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 bg-zinc-900 dark:bg-zinc-800 text-white rounded-full shadow-2xl px-5 py-2.5 flex items-center gap-4">
      <span className="text-sm font-medium text-teal-400">
        已选 {ids.length} 项
      </span>
      <div className="w-px h-5 bg-white/20" />
      <button onClick={handleStar} className="text-sm hover:text-amber-400 transition-colors">
        ⭐ 打星
      </button>
      <button onClick={handleDelete} className="text-sm hover:text-red-400 transition-colors">
        🗑 删除
      </button>
      <div className="w-px h-5 bg-white/20" />
      <button onClick={exitSelectMode} className="text-sm text-zinc-400 hover:text-white transition-colors">
        ✕ 退出
      </button>
    </div>
  )
}
