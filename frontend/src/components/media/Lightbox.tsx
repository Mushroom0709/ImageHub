import { useState, useEffect } from 'react'
import { Asset, Tag, assetApi, tagApi, topCategoryApi, TopCategory } from '../../lib/api'
import { ExifPanel } from '../asset/ExifPanel'
import { FLAG_COLORS } from '../../lib/rating'

interface Props {
  asset: Asset
  onClose: () => void
  onChanged?: (id: string) => void
}

export function Lightbox({ asset, onClose, onChanged }: Props) {
  const [loaded, setLoaded] = useState(false)
  const [showInfo, setShowInfo] = useState(true)
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(asset.title || '')
  const [description, setDescription] = useState(asset.description || '')
  const [starLevel, setStarLevel] = useState(asset.star_level || 0)
  const [flagLevel, setFlagLevel] = useState(asset.flag_level || 0)
  const [tags, setTags] = useState(asset.tags || [])
  const [topCategories, setTopCategories] = useState<TopCategory[]>([])
  const [topCategoryId, setTopCategoryId] = useState(asset.top_category_id || '')
  const [tagSearch, setTagSearch] = useState('')
  const [tagSuggestions, setTagSuggestions] = useState<{ id: string; name: string }[]>([])

  // 打开时设置活动素材 id（快捷键 1-5/6-0 用）
  useEffect(() => {
    window.__imagehubActiveAssetId = asset.id
    return () => { if (window.__imagehubActiveAssetId === asset.id) window.__imagehubActiveAssetId = null }
  }, [asset.id])

  useEffect(() => {
    topCategoryApi.list().then(setTopCategories).catch(() => {})
  }, [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      // 监听素材更新事件刷新
      if (e.key === 'Escape') return
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  // 监听从快捷键发出的更新
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as { id: string }
      if (detail.id === asset.id) {
        // 刷新素材数据
        assetApi.detail(asset.id).then((a) => {
          setStarLevel(a.star_level || 0)
          setFlagLevel(a.flag_level || 0)
          setTitle(a.title || '')
          setDescription(a.description || '')
          setTags(a.tags || [])
          onChanged?.(asset.id)
        }).catch(() => {})
      }
    }
    window.addEventListener('imagehub:asset-updated', handler)
    return () => window.removeEventListener('imagehub:asset-updated', handler)
  }, [asset.id, onChanged])

  const notifyChanged = () => {
    window.dispatchEvent(new CustomEvent('imagehub:asset-updated', { detail: { id: asset.id } }))
    onChanged?.(asset.id)
  }

  const saveMeta = async () => {
    try {
      await assetApi.update(asset.id, {
        title,
        description,
        star_level: starLevel,
        flag_level: flagLevel,
        ...(topCategoryId ? { top_category_id: topCategoryId } : {}),
      })
      setEditing(false)
      notifyChanged()
    } catch (e) {
      console.error('保存失败', e)
    }
  }

  const handleStar = async (lv: number) => {
    const next = starLevel === lv ? 0 : lv
    setStarLevel(next)
    try { await assetApi.update(asset.id, { star_level: next }); notifyChanged() }
    catch { setStarLevel(starLevel) }
  }

  const handleFlag = async (lv: number) => {
    const next = flagLevel === lv ? 0 : lv
    setFlagLevel(next)
    try { await assetApi.update(asset.id, { flag_level: next }); notifyChanged() }
    catch { setFlagLevel(flagLevel) }
  }

  const handleTagSearch = async (q: string) => {
    setTagSearch(q)
    if (!q.trim()) { setTagSuggestions([]); return }
    try {
      const res = await tagApi.search(q)
      setTagSuggestions(res.slice(0, 6).map((t) => ({ id: t.id, name: t.name })))
    } catch { setTagSuggestions([]) }
  }

  const addTag = async (tagId: string, tagName: string) => {
    try {
      await assetApi.addTags(asset.id, [tagId])
      const full: Tag = {
        id: tagId, name: tagName, category: 'other',
        parent_id: null, alias: [], status: 'active', sort_order: 0, asset_count: 0,
      }
      setTags([...tags, full])
      setTagSearch(''); setTagSuggestions([])
      notifyChanged()
    } catch (e) { console.error('加标签失败', e) }
  }

  const removeTag = async (tagId: string) => {
    try {
      await assetApi.removeTag(asset.id, tagId)
      setTags(tags.filter((t) => t.id !== tagId))
      notifyChanged()
    } catch (e) { console.error('删标签失败', e) }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/95 flex" onClick={onClose}>
      {/* 媒体区域（图/视频） */}
      <div
        className="flex-1 flex items-center justify-center overflow-hidden relative"
        onClick={(e) => e.stopPropagation()}
      >
        {asset.asset_type === 'video' ? (
          <video
            src={`/api/assets/${asset.id}/stream`}
            controls
            className="max-w-full max-h-full"
            poster={asset.thumb_medium}
            onError={(e) => {
              e.currentTarget.parentElement?.querySelector('.video-error')?.classList.remove('hidden')
            }}
          />
        ) : asset.thumb_raw ? (
          <img
            src={asset.thumb_raw}
            alt={asset.title || asset.file_name}
            className={`max-w-full max-h-full object-contain transition-opacity duration-300 ${
              loaded ? 'opacity-100' : 'opacity-0'
            }`}
            onLoad={() => setLoaded(true)}
          />
        ) : (
          <div className="text-zinc-500">加载中...</div>
        )}

        {/* 关闭按钮 */}
        <button
          className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
          onClick={onClose}
        >
          ✕
        </button>
      </div>

      {/* 右侧信息面板 */}
      {showInfo && (
        <div
          className="w-80 shrink-0 bg-zinc-900 border-l border-zinc-800 overflow-y-auto text-white"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div className="text-xs text-zinc-400">信息</div>
              <button
                onClick={() => setShowInfo(false)}
                className="text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {/* 标题/描述 */}
            {editing ? (
              <div className="space-y-2">
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="标题"
                  className="w-full px-2 py-1.5 rounded bg-zinc-800 text-sm focus:outline-none focus:border-teal-500 border border-transparent"
                />
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="描述"
                  rows={3}
                  className="w-full px-2 py-1.5 rounded bg-zinc-800 text-sm focus:outline-none focus:border-teal-500 border border-transparent resize-none"
                />
              </div>
            ) : (
              <div>
                <div className="font-medium text-lg truncate">{asset.title || asset.file_name}</div>
                {asset.description && <div className="text-sm text-zinc-400 mt-1">{asset.description}</div>}
              </div>
            )}

            {/* 星级 */}
            <div className="border-t border-zinc-800 pt-3">
              <div className="text-[10px] uppercase text-zinc-500 mb-1.5">星级</div>
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((lv) => (
                  <button
                    key={lv}
                    onClick={() => handleStar(lv)}
                    className={`text-lg transition-transform hover:scale-125 ${lv <= starLevel ? 'text-amber-400' : 'text-zinc-600'}`}
                  >
                    ★
                  </button>
                ))}
                <span className="ml-2 text-xs text-zinc-500">{starLevel > 0 ? `${starLevel} 星` : '未评级'}</span>
              </div>
            </div>

            {/* 旗标 */}
            <div className="border-t border-zinc-800 pt-3">
              <div className="text-[10px] uppercase text-zinc-500 mb-1.5">旗标</div>
              <div className="flex items-center gap-2">
                {FLAG_COLORS.map((f) => (
                  <button
                    key={f.level}
                    onClick={() => handleFlag(f.level)}
                    className={`w-5 h-5 rounded-full transition-transform hover:scale-125 ${flagLevel === f.level ? 'ring-2 ring-white' : ''}`}
                    style={{ backgroundColor: f.color }}
                    title={f.name}
                  />
                ))}
                <span className="ml-1 text-xs text-zinc-500">{flagLevel > 0 ? `旗标 ${flagLevel}` : '无旗标'}</span>
              </div>
            </div>

            {/* 项目归属 */}
            <div className="border-t border-zinc-800 pt-3">
              <div className="text-[10px] uppercase text-zinc-500 mb-1.5">所属项目</div>
              <select
                value={topCategoryId || ''}
                onChange={(e) => { setTopCategoryId(e.target.value); if (editing) saveMeta() }}
                className="w-full px-2 py-1.5 rounded bg-zinc-800 text-sm focus:outline-none"
              >
                <option value="">未分类</option>
                {topCategories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            {/* 标签 */}
            <div className="border-t border-zinc-800 pt-3">
              <div className="text-[10px] uppercase text-zinc-500 mb-1.5">标签</div>
              <div className="flex flex-wrap gap-1.5">
                {tags.map((tag) => (
                  <span key={tag.id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-800 text-xs">
                    {tag.name}
                    <button onClick={() => removeTag(tag.id)} className="text-zinc-500 hover:text-red-400">×</button>
                  </span>
                ))}
              </div>
              <div className="relative mt-2">
                <input
                  value={tagSearch}
                  onChange={(e) => handleTagSearch(e.target.value)}
                  placeholder="+ 添加标签"
                  className="w-full px-2 py-1.5 rounded bg-zinc-800 text-sm focus:outline-none focus:border-teal-500 border border-transparent"
                />
                {tagSuggestions.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-zinc-800 rounded-lg shadow-xl z-10">
                    {tagSuggestions.map((t) => (
                      <button
                        key={t.id}
                        onClick={() => addTag(t.id, t.name)}
                        className="w-full text-left px-3 py-1.5 text-sm hover:bg-zinc-700"
                      >
                        {t.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* 拍摄参数 */}
            <div className="border-t border-zinc-800 pt-3">
              <div className="text-[10px] uppercase text-zinc-500 mb-1">拍摄参数</div>
              <ExifPanel asset={asset} />
            </div>

            {/* 基础信息 */}
            <div className="border-t border-zinc-800 pt-3 text-xs text-zinc-500 space-y-1">
              <div>{asset.width} × {asset.height}</div>
              {asset.source_type !== 'upload' && <div>来源：{asset.source_type}</div>}
              {asset.file_size > 0 && <div>大小：{(asset.file_size / 1024 / 1024).toFixed(1)} MB</div>}
            </div>

            {/* 操作按钮 */}
            <div className="flex gap-2 pt-2">
              {editing ? (
                <>
                  <button onClick={saveMeta} className="flex-1 px-3 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-sm">保存</button>
                  <button onClick={() => setEditing(false)} className="flex-1 px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-sm">取消</button>
                </>
              ) : (
                <button onClick={() => setEditing(true)} className="flex-1 px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-sm">编辑信息</button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 信息面板开关（图片右下角） */}
      {!showInfo && (
        <button
          className="absolute bottom-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
          onClick={(e) => { e.stopPropagation(); setShowInfo(true) }}
        >
          ℹ
        </button>
      )}
    </div>
  )
}
