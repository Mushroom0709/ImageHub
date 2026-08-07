import { useState, useEffect, useRef } from 'react'
import { useFilterStore } from '../../stores/uiStore'

interface Suggestion {
  id: string
  title: string
  file_name: string
}

interface TagSuggestion {
  id: string
  name: string
  category: string
}

export function SearchBar() {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<{ tags: TagSuggestion[]; assets: Suggestion[] }>({ tags: [], assets: [] })
  const [showSuggest, setShowSuggest] = useState(false)
  const setKeyword = useFilterStore((s) => s.setKeyword)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!query.trim()) {
      setSuggestions({ tags: [], assets: [] })
      return
    }
    // debounce 300ms
    debounceRef.current = setTimeout(async () => {
      const token = localStorage.getItem('token')
      try {
        const resp = await fetch(`/api/search/suggest?q=${encodeURIComponent(query)}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        const data = await resp.json()
        setSuggestions(data.data || { tags: [], assets: [] })
      } catch (e) {
        console.error('搜索建议失败', e)
      }
    }, 300)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [query])

  const handleSearch = () => {
    if (!query.trim()) return
    setKeyword(query.trim())
    setShowSuggest(false)
  }

  const handleSelectTag = (name: string) => {
    setQuery(name)
    setKeyword(name)
    setShowSuggest(false)
  }

  return (
    <div className="relative flex-1 max-w-md">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setShowSuggest(true) }}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          onFocus={() => query && setShowSuggest(true)}
          onBlur={() => setTimeout(() => setShowSuggest(false), 200)}
          placeholder="搜索素材、标签..."
          className="w-full px-4 py-1.5 pl-9 rounded-lg bg-zinc-100 dark:bg-zinc-800 border border-transparent focus:border-teal-500 focus:outline-none text-sm"
        />
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 text-sm">🔍</span>
      </div>

      {/* 建议下拉 */}
      {showSuggest && query.trim() && (suggestions.tags.length > 0 || suggestions.assets.length > 0) && (
        <div className="absolute top-full mt-1 w-full bg-white dark:bg-zinc-900 rounded-lg shadow-xl border border-zinc-200 dark:border-zinc-700 z-50 overflow-hidden">
          {suggestions.tags.length > 0 && (
            <div className="p-2">
              <div className="text-[10px] uppercase text-zinc-400 px-2 py-1">标签</div>
              {suggestions.tags.slice(0, 5).map((t) => (
                <button
                  key={t.id}
                  onMouseDown={() => handleSelectTag(t.name)}
                  className="w-full text-left px-2 py-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-sm flex items-center gap-2"
                >
                  <span className="text-zinc-400">#</span>
                  <span>{t.name}</span>
                  <span className="text-[10px] text-zinc-400 ml-auto">{t.category}</span>
                </button>
              ))}
            </div>
          )}
          {suggestions.assets.length > 0 && (
            <div className="p-2 border-t border-zinc-100 dark:border-zinc-800">
              <div className="text-[10px] uppercase text-zinc-400 px-2 py-1">素材</div>
              {suggestions.assets.slice(0, 5).map((a) => (
                <div key={a.id} className="px-2 py-1.5 text-sm truncate">
                  {a.title || a.file_name}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
