import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { TopBar } from '../components/layout/TopBar'

interface ReviewTag {
  id: string
  name: string
  category: string
  status: string
  confidence: number | null
  source: string
  needs_review: boolean
}

interface ReviewAsset {
  id: string
  title: string
  file_name: string
  asset_type: string
  pending_count: number
  tags: ReviewTag[]
}

export function ReviewPage() {
  const [assets, setAssets] = useState<ReviewAsset[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const navigate = useNavigate()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const resp = await fetch('/api/review/assets', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      const data = await resp.json()
      setAssets(data.data.items || [])
      setTotal(data.data.total || 0)
    } catch (e) {
      console.error('加载待审核失败', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleTagAction = async (action: 'confirm' | 'reject', tagId: string) => {
    const token = localStorage.getItem('token')
    await fetch(`/api/review/tags/${tagId}/${action}`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    load()
  }

  return (
    <div className="h-screen flex flex-col">
      <TopBar onBack={() => navigate('/')} />
      <div className="flex-1 overflow-y-auto p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">待审核素材</h2>
          <span className="text-sm text-zinc-500">共 {total} 个待审核</span>
        </div>

        {loading ? (
          <div className="text-zinc-400">加载中...</div>
        ) : assets.length === 0 ? (
          <div className="text-center text-zinc-400 py-20">
            <div className="text-5xl mb-4">✅</div>
            <div>没有待审核的素材</div>
          </div>
        ) : (
          <div className="space-y-3">
            {assets.map((asset) => (
              <div key={asset.id} className="bg-white dark:bg-zinc-900 rounded-xl p-4 border border-zinc-200 dark:border-zinc-800">
                <div className="flex items-center justify-between mb-3">
                  <div className="font-medium truncate max-w-[60%]">
                    {asset.title || asset.file_name}
                  </div>
                  <span className="text-xs px-2 py-1 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
                    {asset.pending_count} 个待确认标签
                  </span>
                </div>

                <div className="flex flex-wrap gap-2">
                  {asset.tags.map((tag) => (
                    <span
                      key={tag.id}
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs ${
                        tag.needs_review
                          ? 'bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700'
                          : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400'
                      }`}
                    >
                      <span className="text-zinc-400 text-[10px]">[{tag.category}]</span>
                      {tag.name}
                      {tag.confidence !== null && (
                        <span className="text-zinc-400">({tag.confidence})</span>
                      )}
                      {tag.needs_review && (
                        <span className="ml-1 flex gap-0.5">
                          <button
                            onClick={() => handleTagAction('confirm', tag.id)}
                            className="px-1.5 rounded bg-green-500 text-white hover:bg-green-600"
                            title="确认标签"
                          >
                            ✓
                          </button>
                          <button
                            onClick={() => handleTagAction('reject', tag.id)}
                            className="px-1.5 rounded bg-red-500 text-white hover:bg-red-600"
                            title="拒绝标签"
                          >
                            ✗
                          </button>
                        </span>
                      )}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
