import { useUIStore } from '../../stores/uiStore'
import { SearchBar } from '../search/SearchBar'

interface Props {
  onUploadClick?: () => void
  onCollectClick?: () => void
  onBack?: () => void
}

export function TopBar({ onUploadClick, onCollectClick, onBack }: Props) {
  const theme = useUIStore((s) => s.theme)
  const setTheme = useUIStore((s) => s.setTheme)
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)
  const collapsed = useUIStore((s) => s.sidebarCollapsed)

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
        <button
          onClick={onUploadClick}
          className="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium"
        >
          ↑ 上传
        </button>
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
