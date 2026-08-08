import { useState } from 'react'
import { useSelectionStore } from '../../stores/uiStore'
import { assetApi } from '../../lib/api'
import { BatchActionModal, BatchActionType } from './BatchActionModal'

interface Props {
  onChanged: () => void
}

export function SelectionToolbar({ onChanged }: Props) {
  const selectMode = useSelectionStore((s) => s.selectMode)
  const selectedIds = useSelectionStore((s) => s.selectedIds)
  const exitSelectMode = useSelectionStore((s) => s.exitSelectMode)
  const clearSelection = useSelectionStore((s) => s.clearSelection)
  const [modalType, setModalType] = useState<BatchActionType | null>(null)

  if (!selectMode || selectedIds.size === 0) return null

  const ids = Array.from(selectedIds)

  const handleDelete = async () => {
    if (!confirm(`确定删除选中的 ${ids.length} 个素材吗？（移入回收站）`)) return
    await assetApi.batchDelete(ids)
    onChanged()
    clearSelection()
  }

  const handleModalDone = () => {
    setModalType(null)
    onChanged()
    clearSelection()
  }

  const btnCls = 'text-sm hover:text-teal-400 transition-colors whitespace-nowrap'

  return (
    <>
      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 bg-zinc-900 dark:bg-zinc-800 text-white rounded-full shadow-2xl px-5 py-2.5 flex items-center gap-3 max-w-[95vw] overflow-x-auto">
        <span className="text-sm font-medium text-teal-400 whitespace-nowrap">已选 {ids.length} 项</span>
        <div className="w-px h-5 bg-white/20 shrink-0" />
        <button onClick={() => setModalType('star')} className={btnCls} title="批量修改星级">⭐ 星级</button>
        <button onClick={() => setModalType('flag')} className={btnCls} title="批量修改旗标">🚩 旗标</button>
        <button onClick={() => setModalType('tag')} className={btnCls} title="批量加标签">🏷 标签</button>
        <button onClick={() => setModalType('move')} className={btnCls} title="批量修改所属项目">📁 项目</button>
        <button onClick={() => setModalType('export')} className={btnCls} title="批量导出下载链接">📤 导出</button>
        <button onClick={handleDelete} className="text-sm hover:text-red-400 transition-colors whitespace-nowrap" title="批量删除">🗑 删除</button>
        <div className="w-px h-5 bg-white/20 shrink-0" />
        <button onClick={exitSelectMode} className="text-sm text-zinc-400 hover:text-white transition-colors whitespace-nowrap">✕ 退出</button>
      </div>

      {modalType && (
        <BatchActionModal
          type={modalType}
          ids={ids}
          onClose={() => setModalType(null)}
          onDone={handleModalDone}
        />
      )}
    </>
  )
}
