import { create } from 'zustand'

interface UIState {
  sidebarCollapsed: boolean
  theme: 'light' | 'dark'
  toggleSidebar: () => void
  setTheme: (theme: 'light' | 'dark') => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  theme: (localStorage.getItem('theme') as 'light' | 'dark') || 'light',
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setTheme: (theme) => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('theme', theme)
    set({ theme })
  },
}))

// ===== 筛选状态 =====

export type SortOption = 'newest' | 'oldest' | 'quality' | 'likes'

interface FilterState {
  selectedTagIds: string[]
  keyword: string
  sort: SortOption
  sourceType: string | null
  starLevel: number | null
  flagLevel: number | null
  trashed: boolean
  topCategoryId: string | null
  toggleTag: (id: string) => void
  clearTags: () => void
  setKeyword: (k: string) => void
  setSort: (s: SortOption) => void
  setTopCategory: (id: string | null) => void
  reset: () => void
}

export const useFilterStore = create<FilterState>((set) => ({
  selectedTagIds: [],
  keyword: '',
  sort: 'newest',
  sourceType: null,
  starLevel: null,
  flagLevel: null,
  trashed: false,
  topCategoryId: null,
  toggleTag: (id) =>
    set((s) => ({
      selectedTagIds: s.selectedTagIds.includes(id)
        ? s.selectedTagIds.filter((t) => t !== id)
        : [...s.selectedTagIds, id],
    })),
  clearTags: () => set({ selectedTagIds: [] }),
  setKeyword: (k) => set({ keyword: k }),
  setSort: (s) => set({ sort: s }),
  setTopCategory: (id) => set({ topCategoryId: id }),
  reset: () => set({ selectedTagIds: [], keyword: '', sort: 'newest', sourceType: null, starLevel: null, flagLevel: null, trashed: false, topCategoryId: null }),
}))

// ===== 多选状态 =====

interface SelectionState {
  selectMode: boolean
  selectedIds: Set<string>
  enterSelectMode: () => void
  exitSelectMode: () => void
  toggleSelect: (id: string) => void
  selectAll: (ids: string[]) => void
  clearSelection: () => void
}

export const useSelectionStore = create<SelectionState>((set) => ({
  selectMode: false,
  selectedIds: new Set(),
  enterSelectMode: () => set({ selectMode: true }),
  exitSelectMode: () => set({ selectMode: false, selectedIds: new Set() }),
  toggleSelect: (id) =>
    set((s) => {
      const next = new Set(s.selectedIds)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return { selectedIds: next }
    }),
  selectAll: (ids) => set({ selectedIds: new Set(ids) }),
  clearSelection: () => set({ selectedIds: new Set() }),
}))
