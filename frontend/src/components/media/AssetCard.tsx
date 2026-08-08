import { useState } from 'react'
import { Asset, assetApi } from '../../lib/api'
import { useSelectionStore } from '../../stores/uiStore'
import { FLAG_COLORS, getFlagColor, renderStars } from '../../lib/rating'

interface Props {
  asset: Asset
  onClick: () => void
  selectMode: boolean
  onDelete?: (id: string) => void
}

export function AssetCard({ asset, onClick, selectMode, onDelete }: Props) {
  const [loaded, setLoaded] = useState(false)
  const [hovered, setHovered] = useState(false)
  const [showActions, setShowActions] = useState(false)
  const [starLevel, setStarLevel] = useState(asset.star_level || 0)
  const [flagLevel, setFlagLevel] = useState(asset.flag_level || 0)
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

  const handleStar = async (e: React.MouseEvent, level: number) => {
    e.stopPropagation()
    const next = starLevel === level ? 0 : level
    setStarLevel(next)
    try {
      await assetApi.update(asset.id, { star_level: next })
    } catch (err) {
      setStarLevel(starLevel)
    }
  }

  const handleFlag = async (e: React.MouseEvent, level: number) => {
    e.stopPropagation()
    const next = flagLevel === level ? 0 : level
    setFlagLevel(next)
    try {
      await assetApi.update(asset.id, { flag_level: next })
    } catch (err) {
      setFlagLevel(flagLevel)
    }
  }

  const handleClearRating = async (e: React.MouseEvent) => {
    e.stopPropagation()
    const prevStar = starLevel
    const prevFlag = flagLevel
    setStarLevel(0)
    setFlagLevel(0)
    try {
      await assetApi.update(asset.id, { star_level: 0, flag_level: 0 })
    } catch {
      setStarLevel(prevStar)
      setFlagLevel(prevFlag)
    }
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (onDelete) onDelete(asset.id)
  }

  // 根据宽高比计算 aspect-ratio（防止布局跳动）
  const ratio = asset.width && asset.height ? asset.width / asset.height : 3 / 4
  const flagColor = getFlagColor(flagLevel)

  return (
    <div
      className={`relative rounded-lg overflow-hidden bg-zinc-100 dark:bg-zinc-800 group cursor-pointer transition-all ${
        selected ? 'ring-2 ring-teal-500' : 'hover:ring-1 ring-zinc-300 dark:ring-zinc-700'
      } ${selectMode ? 'cursor-pointer' : ''}`}
      style={{ aspectRatio: String(ratio) }}
      onClick={handleClick}
      onMouseEnter={() => { setHovered(true); setShowActions(true) }}
      onMouseLeave={() => { setHovered(false); setShowActions(false) }}
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

      {/* 旗标角标（常驻，左上） */}
      {flagColor && (
        <span
          className="absolute top-1.5 left-1.5 w-4 h-4 rounded-sm"
          style={{ backgroundColor: flagColor }}
          title={`旗标 ${flagLevel}`}
        />
      )}

      {/* 星级角标（常驻，左下） */}
      {starLevel > 0 && (
        <span className="absolute bottom-1.5 left-1.5 text-amber-400 text-[10px] drop-shadow">
          {renderStars(starLevel)}
        </span>
      )}

      {/* 选中勾 */}
      {selected && (
        <span className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-teal-500 text-white flex items-center justify-center text-xs">
          ✓
        </span>
      )}

      {/* Hover 操作区 */}
      {showActions && !selectMode && (
        <div className="absolute inset-0 bg-black/40 flex flex-col justify-between p-1.5" onClick={(e) => e.stopPropagation()}>
          {/* 星级 */}
          <div className="flex items-center gap-0.5 justify-center pt-1">
            {[1, 2, 3, 4, 5].map((lv) => (
              <button
                key={lv}
                onClick={(e) => handleStar(e, lv)}
                className={`text-sm transition-transform hover:scale-125 ${
                  lv <= starLevel ? 'text-amber-400' : 'text-white/40'
                }`}
                title={`${lv} 星`}
              >
                ★
              </button>
            ))}
          </div>

          {/* 底部：旗标 + 清除 + 删除 + 信息 */}
          <div className="flex items-center justify-between">
            {/* 旗标 4 色 + 清除 */}
            <div className="flex gap-1 items-center">
              {FLAG_COLORS.map((f) => (
                <button
                  key={f.level}
                  onClick={(e) => handleFlag(e, f.level)}
                  className={`w-4 h-4 rounded-full transition-transform hover:scale-125 ${
                    flagLevel === f.level ? 'ring-2 ring-white' : ''
                  }`}
                  style={{ backgroundColor: f.color }}
                  title={f.name}
                />
              ))}
              <button
                onClick={handleClearRating}
                className="w-4 h-4 rounded-full bg-zinc-700 hover:bg-zinc-600 text-white/80 hover:text-white text-[10px] flex items-center justify-center transition-transform hover:scale-125"
                title="清除星标和旗标 (0)"
              >
                ✕
              </button>
            </div>

            {/* 操作按钮 */}
            <div className="flex gap-1">
              <button
                onClick={(e) => e.stopPropagation()}
                className="w-6 h-6 rounded bg-white/20 text-white hover:bg-white/40 flex items-center justify-center text-xs"
                title="信息"
              >
                i
              </button>
              {onDelete && (
                <button
                  onClick={handleDelete}
                  className="w-6 h-6 rounded bg-red-500/80 text-white hover:bg-red-500 flex items-center justify-center text-xs"
                  title="删除（移入回收站）"
                >
                  🗑
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
