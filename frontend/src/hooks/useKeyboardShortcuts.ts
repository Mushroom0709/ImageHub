import { useEffect } from 'react'
import { useSelectionStore } from '../stores/uiStore'

/**
 * 全局快捷键
 * 空格: 预览 / 关闭
 * ← →: 翻图（由 Lightbox 处理）
 * 1-5: 星标等级（MVP: 切换星标）
 * Del: 删除选中
 * Ctrl+A: 全选
 * Esc: 退出多选
 */
export function useKeyboardShortcuts(onDelete: (ids: string[]) => void) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // 输入框聚焦时不触发
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return
      }

      const { selectMode, selectedIds, exitSelectMode, selectAll } = useSelectionStore.getState()

      // Ctrl+A / Cmd+A 全选（MVP: 提示进入多选模式）
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a') {
        e.preventDefault()
        // 全选逻辑由 MasonryGrid 处理（需要知道当前加载的素材）
        window.dispatchEvent(new CustomEvent('imagehub:select-all'))
        return
      }

      // Del / Backspace 删除
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectMode && selectedIds.size > 0) {
          e.preventDefault()
          if (confirm(`删除选中的 ${selectedIds.size} 个素材？`)) {
            onDelete(Array.from(selectedIds))
          }
        }
        return
      }

      // Esc 退出多选
      if (e.key === 'Escape' && selectMode) {
        exitSelectMode()
        return
      }

      // S 切换星标（多选模式下批量打星）
      if (e.key.toLowerCase() === 's' && selectMode && selectedIds.size > 0) {
        e.preventDefault()
        window.dispatchEvent(new CustomEvent('imagehub:star-selected'))
        return
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onDelete])
}
