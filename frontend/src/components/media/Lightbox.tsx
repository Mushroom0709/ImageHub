import { useState, useEffect } from 'react'
import { Asset } from '../../lib/api'
import { ExifPanel } from '../asset/ExifPanel'

interface Props {
  asset: Asset
  onClose: () => void
}

export function Lightbox({ asset, onClose }: Props) {
  const [loaded, setLoaded] = useState(false)
  const [showInfo, setShowInfo] = useState(true)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 bg-black/95 flex flex-col"
      onClick={onClose}
    >
      {/* 图片区域 */}
      <div
        className="flex-1 flex items-center justify-center overflow-hidden relative"
        onClick={(e) => e.stopPropagation()}
      >
        {asset.thumb_medium ? (
          <img
            src={asset.thumb_medium}
            alt={asset.title || asset.file_name}
            className={`max-w-full max-h-full object-contain transition-opacity duration-300 ${
              loaded ? 'opacity-100' : 'opacity-0'
            }`}
            onLoad={() => setLoaded(true)}
          />
        ) : (
          <div className="text-zinc-500">图片加载中...</div>
        )}

        {/* 关闭按钮 */}
        <button
          className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
          onClick={onClose}
        >
          ✕
        </button>

        {/* 信息面板开关 */}
        <button
          className="absolute top-4 right-16 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
          onClick={() => setShowInfo(!showInfo)}
        >
          ℹ
        </button>
      </div>

      {/* 底部信息条 */}
      {showInfo && (
        <div
          className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent text-white"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="text-sm font-medium truncate">
            {asset.title || asset.file_name || '未命名'}
          </div>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {asset.tags.map((tag) => (
              <span
                key={tag.id}
                className="px-2 py-0.5 rounded-full bg-white/15 text-xs"
              >
                {tag.name}
              </span>
            ))}
          </div>
          <div className="text-xs text-zinc-400 mt-2">
            {asset.width} × {asset.height}
            {asset.source_type !== 'upload' && ` · ${asset.source_type}`}
          </div>

          {/* 拍摄参数 */}
          <div className="mt-3 border-t border-white/10 pt-2">
            <div className="text-[10px] uppercase tracking-wide text-zinc-500 mb-1">
              拍摄参数
            </div>
            <ExifPanel asset={asset} />
          </div>
        </div>
      )}
    </div>
  )
}
