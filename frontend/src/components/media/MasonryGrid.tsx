import { useState, useEffect, useRef, useCallback } from 'react'
import { Asset, assetApi } from '../../lib/api'
import { useFilterStore, useSelectionStore } from '../../stores/uiStore'
import { AssetCard } from './AssetCard'
import { Lightbox } from './Lightbox'
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts'

interface Props {
  refreshKey?: number
}

export function MasonryGrid({ refreshKey = 0 }: Props) {
  const [assets, setAssets] = useState<Asset[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
  const sentinelRef = useRef<HTMLDivElement>(null)

  const filter = useFilterStore()
  const selectMode = useSelectionStore((s) => s.selectMode)

  // 加载数据
  const loadPage = useCallback(async (pageNum: number, append: boolean) => {
    setLoading(true)
    try {
      const data = await assetApi.list({
        page: pageNum,
        size: 20,
        sort: filter.sort,
        tag_ids: filter.selectedTagIds.length > 0 ? filter.selectedTagIds.join(',') : '',
        keyword: filter.keyword,
        source_type: filter.sourceType || '',
        star_level: filter.starLevel === null ? '' : String(filter.starLevel),
        flag_level: filter.flagLevel || '',
        trashed: filter.trashed ? 'true' : '',
        top_category_id: filter.topCategoryId || '',
      })
      setTotal(data.total)
      setAssets((prev) => (append ? [...prev, ...data.items] : data.items))
    } catch (err) {
      console.error('加载素材失败', err)
    } finally {
      setLoading(false)
      setInitialLoading(false)
    }
  }, [filter.sort, filter.selectedTagIds, filter.keyword, filter.sourceType, filter.starLevel, filter.flagLevel, filter.trashed, filter.topCategoryId])

  // 筛选条件变化时重新加载
  useEffect(() => {
    setPage(1)
    setAssets([])
    setInitialLoading(true)
    loadPage(1, false)
  }, [filter.selectedTagIds, filter.keyword, filter.sort, filter.sourceType, filter.starLevel, filter.flagLevel, filter.trashed, filter.topCategoryId, refreshKey, loadPage])

  // 无限滚动
  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !loading && assets.length < total) {
          const next = page + 1
          setPage(next)
          loadPage(next, true)
        }
      },
      { rootMargin: '600px' },
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [sentinelRef.current, loading, assets.length, total, page, loadPage])

  // Lightbox 键盘导航
  useEffect(() => {
    if (lightboxIndex === null) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') {
        setLightboxIndex((i) => (i === null || i >= assets.length - 1 ? 0 : i + 1))
      } else if (e.key === 'ArrowLeft') {
        setLightboxIndex((i) => (i === null || i <= 0 ? assets.length - 1 : i - 1))
      } else if (e.key === 'Escape') {
        setLightboxIndex(null)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [lightboxIndex, assets.length])

  // 快捷键：全选/批量打星
  useKeyboardShortcuts(async (ids) => {
    await assetApi.batchDelete(ids)
    useSelectionStore.getState().exitSelectMode()
    loadPage(1, false)
  })

  useEffect(() => {
    const handleSelectAll = () => {
      const { selectMode, enterSelectMode, selectAll } = useSelectionStore.getState()
      if (!selectMode) enterSelectMode()
      selectAll(assets.map((a) => a.id))
    }
    const handleStarSelected = async () => {
      const { selectedIds, clearSelection } = useSelectionStore.getState()
      const ids = Array.from(selectedIds)
      for (const id of ids) {
        await assetApi.update(id, { star_level: 3 })
      }
      clearSelection()
      loadPage(1, false)
    }
    window.addEventListener('imagehub:select-all', handleSelectAll)
    window.addEventListener('imagehub:star-selected', handleStarSelected)
    return () => {
      window.removeEventListener('imagehub:select-all', handleSelectAll)
      window.removeEventListener('imagehub:star-selected', handleStarSelected)
    }
  }, [assets, loadPage])

  if (initialLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 p-4">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="aspect-square bg-zinc-100 dark:bg-zinc-800 rounded-lg animate-pulse" />
        ))}
      </div>
    )
  }

  if (assets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-zinc-400">
        <div className="text-5xl mb-4">📷</div>
        <div className="text-lg">暂无素材</div>
        <div className="text-sm mt-2">上传照片或从链接采集开始</div>
      </div>
    )
  }

  const handleSingleDelete = async (id: string) => {
    if (!confirm('删除该素材？（移入回收站）')) return
    await assetApi.remove(id)
    loadPage(1, false)
  }

  return (
    <div className="h-full overflow-y-auto pb-14 md:pb-0" data-testid="masonry-scroll">
      <div className="columns-2 md:columns-3 lg:columns-4 xl:columns-5 gap-3 p-4">
        {assets.map((asset, idx) => (
          <div key={asset.id} className="mb-3 break-inside-avoid">
            <AssetCard
              asset={asset}
              onClick={() => setLightboxIndex(idx)}
              selectMode={selectMode}
              onDelete={handleSingleDelete}
            />
          </div>
        ))}
      </div>

      {/* 无限滚动哨兵 */}
      <div ref={sentinelRef} className="h-10 flex items-center justify-center text-xs text-zinc-400">
        {loading ? '加载中...' : assets.length >= total ? '已加载全部' : '继续滚动加载'}
      </div>

      {/* Lightbox */}
      {lightboxIndex !== null && assets[lightboxIndex] && (
        <Lightbox
          asset={assets[lightboxIndex]}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </div>
  )
}
