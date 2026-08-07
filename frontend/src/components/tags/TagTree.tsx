import { useState, useEffect } from 'react'
import { tagApi, Tag } from '../../lib/api'
import { useFilterStore } from '../../stores/uiStore'

interface Props {
  category: string
}

function TagNode({ tag, depth }: { tag: Tag; depth: number }) {
  const [expanded, setExpanded] = useState(depth === 0)
  const selectedTagIds = useFilterStore((s) => s.selectedTagIds)
  const toggleTag = useFilterStore((s) => s.toggleTag)
  const hasChildren = tag.children && tag.children.length > 0
  const isSelected = selectedTagIds.includes(tag.id)

  return (
    <div>
      <div
        className={`flex items-center gap-1 px-2 py-1.5 rounded-md cursor-pointer text-sm group select-none ${
          isSelected
            ? 'bg-teal-600 text-white'
            : 'text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800'
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onClick={(e) => {
          e.stopPropagation()
          toggleTag(tag.id)
        }}
      >
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation()
              setExpanded(!expanded)
            }}
            className={`w-4 h-4 flex items-center justify-center text-[10px] transition-transform ${
              expanded ? 'rotate-90' : ''
            }`}
          >
            ▶
          </button>
        ) : (
          <span className="w-4" />
        )}
        <span className="flex-1 truncate">{tag.name}</span>
        {tag.asset_count > 0 && (
          <span className={`text-[10px] ${isSelected ? 'text-teal-100' : 'text-zinc-400'}`}>
            {tag.asset_count}
          </span>
        )}
      </div>
      {hasChildren && expanded && (
        <div>
          {tag.children!.map((child) => (
            <TagNode key={child.id} tag={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export function TagTree({ category }: Props) {
  const [trees, setTrees] = useState<Record<string, Tag[]>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    tagApi.tree(category || undefined)
      .then((data) => setTrees(data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [category])

  if (loading) {
    return <div className="text-xs text-zinc-400 p-3">加载标签...</div>
  }

  const categories = Object.entries(trees)
  if (categories.length === 0) {
    return <div className="text-xs text-zinc-400 p-3">暂无标签</div>
  }

  return (
    <div className="space-y-3">
      {categories.map(([cat, tags]) => (
        <div key={cat}>
          <div className="text-[10px] font-semibold uppercase text-zinc-400 px-2 py-1">
            {cat}
          </div>
          {tags.map((tag) => (
            <TagNode key={tag.id} tag={tag} depth={0} />
          ))}
        </div>
      ))}
    </div>
  )
}
