import { useState } from 'react'
import { Asset } from '../../lib/api'
import { useSelectionStore } from '../../stores/uiStore'

interface Props {
  asset: Asset
  onClick: () => void
  selectMode: boolean
}

export function AssetCard({ asset, onClick, selectMode }: Props) {
  const [loaded, setLoaded] = useState(false)
  const [hovered, setHovered] = useState(false)
  const toggleSelect = useSelectionStore((s) => s.toggleSelect)
  const selected = useSelectionStore((s) => s.selectedIds.has(asset.id))
  const enterSelectMode = useSelectionStore((s) => s.enterSelectMode)

  const handleClick = () => {
    if (selectMode) {
      toggleSelect(asset.id)
    } else {
      onClick()
    }
  }

  // 根据宽高比计算 aspect-ratio（防止布局跳动）
  const ratio = asset.width && asset.height ? asset.width / asset.height : 3 / 4

  return (
    <div
      className={`relative rounded-lg overflow-hidden bg-zinc-100 dark:bg-zinc-800 group cursor-pointer transition-all ${
        selected ? 'ring-2 ring-teal-500' : 'hover:ring-1 ring-zinc-300 dark:ring-zinc-700'
      } ${selectMode ? 'cursor-pointer' : ''}`}
      style={{ aspectRatio: String(ratio) }}
      onClick={handleClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      data-selected={selected || undefined}
    >
      {/* 图片 */}
      {asset.thumb_small ? (
        <img
          src={asset.thumb_small}
          alt={asset.title || asset.file_name}
          loading="lazy"
          className={`w-full h-full object-cover transition-opacity duration-200 ${
            loaded ? 'opacity-100' : 'opacity-0'
          }`}
          onLoad={() => setLoaded(true)}
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-zinc-300 dark:text-zinc-600 text-3xl">
          {asset.asset_type === 'video' ? '▶' : '🖼'}
        </div>
      )}

      {/* 视频时长角标 */}
      {asset.asset_type === 'video' && asset.duration > 0 && (
        <span className="absolute bottom-1.5 right-1.5 px-1.5 py-0.5 rounded bg-black/60 text-white text-[10px]">
          {Math.round(asset.duration)}s
        </span>
      )}

      {/* 选中勾 */}
      {selected && (
        <span className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-teal-500 text-white flex items-center justify-center text-xs">
          ✓
        </span>
      )}

      {/* Hover 操作条 */}
      {hovered && !selectMode && (
        <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/70 to-transparent flex items-center justify-between">
          <span className="text-white text-xs truncate max-w-[70%]">
            {asset.title || asset.file_name || '未命名'}
          </span>
          <div className="flex gap-1">
            <button
              className={`w-6 h-6 rounded flex items-center justify-center text-xs ${
                asset.starred ? 'bg-amber-400 text-black' : 'bg-white/20 text-white hover:bg-white/40'
              }`}
              title="星标"
            >
              ★
            </button>
            <button
              className="w-6 h-6 rounded bg-white/20 text-white hover:bg-white/40 flex items-center justify-center text-xs"
              title="更多"
            >
              ⋯
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
