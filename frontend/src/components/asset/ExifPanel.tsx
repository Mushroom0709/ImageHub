import { useState } from 'react'
import { Asset } from '../../lib/api'

interface Props {
  asset: Asset
}

const EXIF_LABELS: Record<string, string> = {
  camera: '相机',
  lens: '镜头',
  aperture: '光圈',
  shutter: '快门',
  iso: 'ISO',
  focal_length: '焦距',
  focal_length_35mm: '等效焦距',
  white_balance: '白平衡',
  capture_time: '拍摄时间',
  exposure_bias: '曝光补偿',
  color_space: '色彩空间',
  flash: '闪光灯',
  gps_lat: '纬度',
  gps_lng: '经度',
}

export function ExifPanel({ asset }: Props) {
  const [expanded, setExpanded] = useState(false)
  const exif = asset.exif as Record<string, unknown> | null

  if (!exif || Object.keys(exif).length === 0) {
    return (
      <div className="text-xs text-zinc-400 px-3 py-2">
        暂无拍摄参数信息
      </div>
    )
  }

  const entries = Object.entries(exif).filter(([k]) => EXIF_LABELS[k])
  const visible = expanded ? entries : entries.slice(0, 6)

  return (
    <div className="px-3 py-2 space-y-1.5">
      {visible.map(([key, value]) => (
        <div key={key} className="flex items-center justify-between text-xs">
          <span className="text-zinc-400">{EXIF_LABELS[key] || key}</span>
          <span className="text-zinc-700 dark:text-zinc-300 font-medium truncate ml-3">
            {String(value)}
          </span>
        </div>
      ))}
      {entries.length > 6 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-teal-600 dark:text-teal-400 mt-1"
        >
          {expanded ? '收起 ▲' : `展开全部 (${entries.length}) ▼`}
        </button>
      )}
    </div>
  )
}
