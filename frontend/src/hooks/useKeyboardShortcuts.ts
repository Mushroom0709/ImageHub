import { useEffect } from 'react'
import { useSelectionStore } from '../stores/uiStore'
import { assetApi } from '../lib/api'

/**
 * 全局快捷键
 * 空格: 预览 / 关闭
 * ← →: 翻图（由 Lightbox 处理）
 * 1-5: 设置星级（0 清除用再次按同级）
 * 6-0: 设置旗标色（6=红,7=橙,8=黄,9=绿,0=蓝）
 * F: 全屏/沉浸式
 * Esc: 退出多选 / 关闭
 * Del: 删除选中
 * Ctrl+A: 全选
 */
export function useKeyboardShortcuts(onDelete: (ids: string[]) => void) {
  useEffect(() => {
    const handler = async (e: KeyboardEvent) => {
      // 输入框聚焦时不触发
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return
      }

      const { selectMode, selectedIds, exitSelectMode } = useSelectionStore.getState()

      // Ctrl+A / Cmd+A 全选
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a') {
        e.preventDefault()
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

      // 数字键：1-5 设星级，6-9 设旗标，0 清除星标+旗标
      if (/^[0-9]$/.test(e.key) && !e.ctrlKey && !e.metaKey) {
        const num = parseInt(e.key, 10)
        const activeId = window.__imagehubActiveAssetId
        if (activeId) {
          if (num >= 1 && num <= 5) {
            e.preventDefault()
            await assetApi.update(activeId, { star_level: num })
            window.dispatchEvent(new CustomEvent('imagehub:asset-updated', { detail: { id: activeId } }))
          } else if (num >= 6 && num <= 9) {
            e.preventDefault()
            // 6=旗1红, 7=旗2橙, 8=旗3黄, 9=旗4绿
            const flagLevel = num - 5
            await assetApi.update(activeId, { flag_level: flagLevel })
            window.dispatchEvent(new CustomEvent('imagehub:asset-updated', { detail: { id: activeId } }))
          } else if (num === 0) {
            e.preventDefault()
            // 0 = 清除星标 + 清除旗标
            await assetApi.update(activeId, { star_level: 0, flag_level: 0 })
            window.dispatchEvent(new CustomEvent('imagehub:asset-updated', { detail: { id: activeId } }))
          }
        }
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onDelete])
}

// 声明全局变量类型
declare global {
  interface Window {
    __imagehubActiveAssetId: string | null
  }
}
