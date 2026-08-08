import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useUIStore } from '../../stores/uiStore'
import { useUploadStore } from '../../stores/uploadStore'
import { SearchBar } from '../search/SearchBar'

interface Props {
  onUploadFiles?: () => void
  onUploadFolder?: () => void
  onCollectClick?: () => void
  onBack?: () => void
}

export function TopBar({ onUploadFiles, onUploadFolder, onCollectClick, onBack }: Props) {
  const theme = useUIStore((s) => s.theme)
  const setTheme = useUIStore((s) => s.setTheme)
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)
  const collapsed = useUIStore((s) => s.sidebarCollapsed)
  const items = useUploadStore((s) => s.items)
  const [uploadMenuOpen, setUploadMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const activeCount = items.filter((i) => i.status === 'uploading' || i.status === 'processing').length

  // 点击外部关闭下拉菜单
  useEffect(() => {
    if (!uploadMenuOpen) return
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setUploadMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [uploadMenuOpen])

  return (
    <header className="h-14 shrink-0 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 flex items-center px-4 gap-4 z-10">
      {/* 折叠按钮 */}
      <button
        onClick={onBack || toggleSidebar}
        className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
        title={onBack ? '返回' : collapsed ? '展开侧边栏' : '折叠侧边栏'}
      >
        {onBack ? '←' : collapsed ? '▶' : '◀'}
      </button>

      {/* Logo */}
      <div className="flex items-center gap-2">
        <span className="text-xl font-bold bg-gradient-to-r from-teal-500 to-teal-300 bg-clip-text text-transparent">
          ImageHub
        </span>
      </div>

      {/* 搜索框 */}
      <SearchBar />

      {/* 右侧操作 */}
      <div className="flex items-center gap-2 ml-auto">
        <button
          onClick={onCollectClick}
          className="px-3 py-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-sm font-medium"
        >
          🔗 采集
        </button>
        {/* 上传页链接（带活跃任务徽标） */}
        <Link
          to="/upload"
          className="relative px-3 py-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-sm font-medium"
          title="上传队列"
        >
          📤 上传页
          {activeCount > 0 && (
            <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 bg-teal-500 text-white text-[10px] rounded-full flex items-center justify-center font-medium">
              {activeCount}
            </span>
          )}
        </Link>
        {/* 上传下拉按钮 */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setUploadMenuOpen((v) => !v)}
            className="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium flex items-center gap-1"
          >
            ↑ 上传
            <span className="text-xs opacity-80">▾</span>
          </button>
          {uploadMenuOpen && (
            <div className="absolute right-0 top-full mt-1 w-36 py-1 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 shadow-xl z-50">
              <button
                onClick={() => {
                  setUploadMenuOpen(false)
                  onUploadFiles?.()
                }}
                className="w-full px-3 py-2 text-left text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 flex items-center gap-2"
              >
                <span>📄</span> 上传文件
              </button>
              <button
                onClick={() => {
                  setUploadMenuOpen(false)
                  onUploadFolder?.()
                }}
                className="w-full px-3 py-2 text-left text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 flex items-center gap-2"
              >
                <span>📁</span> 上传文件夹
              </button>
            </div>
          )}
        </div>
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
          title="切换主题"
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </div>
    </header>
  )
}
