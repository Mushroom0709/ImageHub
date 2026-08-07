import { useState } from 'react'

interface Props {
  onClose: () => void
  onCollected: () => void
}

type Platform = 'xiaohongshu' | 'douyin'

const PLATFORM_HINTS: Record<Platform, string> = {
  xiaohongshu: '小红书笔记链接，如 https://www.xiaohongshu.com/explore/xxx',
  douyin: '抖音分享链接，如 https://v.douyin.com/xxx/',
}

export function CollectDialog({ onClose, onCollected }: Props) {
  const [platform, setPlatform] = useState<Platform>('xiaohongshu')
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ status: string; message?: string; success?: number; fail?: number } | null>(null)

  const handleCollect = async () => {
    if (!url.trim()) return
    setLoading(true)
    setResult(null)
    try {
      const token = localStorage.getItem('token')
      const resp = await fetch(`/api/collect/${platform}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ url: url.trim(), auto_tag: true }),
      })
      const data = await resp.json()
      const d = data.data || {}
      setResult({
        status: d.status || 'failed',
        message: d.message,
        success: d.success_count,
        fail: d.fail_count,
      })
      if (d.status === 'done') {
        onCollected()
      }
    } catch (err) {
      setResult({ status: 'failed', message: '请求失败' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center" onClick={onClose}>
      <div
        className="w-96 bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium">链接采集</h3>
          <button onClick={onClose} className="text-zinc-400 hover:text-zinc-600">✕</button>
        </div>

        {/* 平台选择 */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setPlatform('xiaohongshu')}
            className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              platform === 'xiaohongshu'
                ? 'bg-red-500 text-white'
                : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600'
            }`}
          >
            📕 小红书
          </button>
          <button
            onClick={() => setPlatform('douyin')}
            className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              platform === 'douyin'
                ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600'
            }`}
          >
            🎵 抖音
          </button>
        </div>

        {/* 链接输入 */}
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={PLATFORM_HINTS[platform]}
          className="w-full px-3 py-2 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-transparent text-sm focus:border-teal-500 focus:outline-none"
        />

        {/* 提示 */}
        <p className="text-xs text-zinc-400 mt-2">
          采集后自动下载图片/视频到 OBS，AI 自动打标签
        </p>

        {/* 结果 */}
        {result && (
          <div className={`mt-3 p-3 rounded-lg text-sm ${
            result.status === 'done'
              ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
              : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
          }`}>
            {result.status === 'done'
              ? `✅ 采集完成：成功 ${result.success || 0} 个`
              : `❌ ${result.message || '采集失败'}`}
          </div>
        )}

        {/* 按钮 */}
        <button
          onClick={handleCollect}
          disabled={loading || !url.trim()}
          className="w-full mt-4 px-4 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-medium"
        >
          {loading ? '采集中...' : '开始采集'}
        </button>
      </div>
    </div>
  )
}
