import { useState, useEffect, useCallback } from 'react'
import { topCategoryApi, TopCategory } from '../../lib/api'
import { useFilterStore } from '../../stores/uiStore'

export function ProjectSection() {
  const [projects, setProjects] = useState<TopCategory[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const topCategoryId = useFilterStore((s) => s.topCategoryId)

  const load = useCallback(async () => {
    try {
      setProjects(await topCategoryApi.list())
    } catch (e) {
      console.error('加载项目失败', e)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleCreate = async () => {
    if (!newName.trim()) return
    try {
      await topCategoryApi.create({ name: newName.trim() })
      setNewName('')
      setShowCreate(false)
      load()
    } catch (e) {
      console.error('创建项目失败', e)
    }
  }

  const handleSelect = (id: string | null) => {
    useFilterStore.setState({ topCategoryId: id, selectedTagIds: [] })
  }

  return (
    <div className="border-b border-zinc-200 dark:border-zinc-800 p-2">
      <div className="flex items-center justify-between px-2 py-1">
        <span className="text-[10px] font-semibold uppercase text-zinc-400">
          项目
        </span>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="w-5 h-5 rounded flex items-center justify-center text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-sm"
          title="新建项目"
        >
          +
        </button>
      </div>

      {showCreate && (
        <div className="p-1 mb-1 flex gap-1">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            placeholder="项目名称，如：摄影原图"
            className="flex-1 px-2 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 text-xs focus:outline-none focus:border-teal-500 border border-transparent"
            autoFocus
          />
          <button
            onClick={handleCreate}
            className="px-2 py-1 rounded-md bg-teal-600 text-white text-xs"
          >
            建
          </button>
        </div>
      )}

      {/* 全部 */}
      <button
        onClick={() => handleSelect(null)}
        className={`w-full px-2 py-1.5 rounded-md text-sm text-left transition-colors ${
          topCategoryId === null
            ? 'bg-teal-600 text-white'
            : 'text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800'
        }`}
      >
        📁 全部
      </button>

      {/* 项目列表 */}
      {projects.map((p) => (
        <button
          key={p.id}
          onClick={() => handleSelect(p.id)}
          className={`w-full px-2 py-1.5 rounded-md text-sm text-left transition-colors flex items-center gap-1.5 ${
            topCategoryId === p.id
              ? 'bg-teal-600 text-white'
              : 'text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800'
          }`}
          title={p.description || p.name}
        >
          <span>📁</span>
          <span className="flex-1 truncate">{p.name}</span>
          {p.asset_count > 0 && (
            <span className={`text-[10px] ${topCategoryId === p.id ? 'text-teal-100' : 'text-zinc-400'}`}>
              {p.asset_count}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}
