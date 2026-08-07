import { useState } from 'react'
import { useUIStore, useFilterStore } from '../../stores/uiStore'
import { TagTree } from '../tags/TagTree'

const CATEGORIES = [
  { key: '', label: '全部' },
  { key: 'scene', label: '场景' },
  { key: 'style', label: '风格' },
  { key: 'clothing', label: '服装' },
  { key: 'makeup', label: '妆容' },
  { key: 'pose_type', label: '姿势' },
  { key: 'composition', label: '构图' },
  { key: 'mood', label: '色调' },
  { key: 'body_focus', label: '身材' },
  { key: 'info', label: '信息' },
]

export function Sidebar() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed)
  const [category, setCategory] = useState('')
  const starred = useFilterStore((s) => s.starred)
  const trashed = useFilterStore((s) => s.trashed)

  const toggleStarred = () => {
    useFilterStore.setState({ starred: starred === true ? null : true })
  }
  const toggleTrashed = () => {
    useFilterStore.setState({ trashed: !trashed })
  }

  if (collapsed) {
    return (
      <aside className="w-16 shrink-0 border-r border-zinc-200 dark:border-zinc-800 flex flex-col items-center py-4 gap-1">
        {CATEGORIES.slice(1).map((c) => (
          <button
            key={c.key}
            onClick={() => setCategory(c.key)}
            className={`w-10 h-10 rounded-lg flex items-center justify-center text-xs transition-colors ${
              category === c.key
                ? 'bg-teal-600 text-white'
                : 'text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800'
            }`}
            title={c.label}
          >
            {c.label.charAt(0)}
          </button>
        ))}
      </aside>
    )
  }

  return (
    <aside className="w-64 shrink-0 border-r border-zinc-200 dark:border-zinc-800 flex flex-col bg-zinc-50 dark:bg-zinc-900">
      {/* 分类 Tab */}
      <div className="flex flex-wrap gap-1 p-3 border-b border-zinc-200 dark:border-zinc-800">
        {CATEGORIES.map((c) => (
          <button
            key={c.key}
            onClick={() => setCategory(c.key)}
            className={`px-2 py-1 rounded-md text-xs transition-colors ${
              category === c.key
                ? 'bg-teal-600 text-white'
                : 'text-zinc-600 hover:bg-zinc-200 dark:text-zinc-400 dark:hover:bg-zinc-800'
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {/* 快捷筛选 */}
      <div className="p-2 border-b border-zinc-200 dark:border-zinc-800 space-y-0.5">
        <QuickFilterButton
          label="⭐ 星标"
          active={starred === true}
          onClick={toggleStarred}
        />
        <QuickFilterButton
          label="🗑 回收站"
          active={trashed}
          onClick={toggleTrashed}
        />
      </div>

      {/* 标签树 */}
      <div className="flex-1 overflow-y-auto p-2">
        <TagTree category={category} />
      </div>
    </aside>
  )
}

function QuickFilterButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`w-full px-2 py-1.5 rounded-md text-sm text-left transition-colors ${
        active
          ? 'bg-teal-600 text-white'
          : 'text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800'
      }`}
    >
      {label}
    </button>
  )
}
