import { useCallback, useState, useRef } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { Sidebar } from '../components/layout/Sidebar'
import { MasonryGrid } from '../components/media/MasonryGrid'
import { UploadZone } from '../components/upload/UploadZone'
import { CollectDialog } from '../components/collect/CollectDialog'
import { SelectionToolbar } from '../components/media/SelectionToolbar'
import { MobileNav } from '../components/layout/MobileNav'

export function HomePage() {
  const [refreshKey, setRefreshKey] = useState(0)
  const [showCollect, setShowCollect] = useState(false)
  const uploadZoneRef = useRef<{ openFiles: () => void; openFolder: () => void } | null>(null)

  const handleUploaded = useCallback(() => {
    setRefreshKey((k) => k + 1)
  }, [])

  const handleCollected = useCallback(() => {
    setRefreshKey((k) => k + 1)
    setShowCollect(false)
  }, [])

  return (
    <div className="h-screen flex flex-col">
      {/* 全局拖拽上传 */}
      <div className="h-full flex flex-col" onDragOver={(e) => e.preventDefault()}>
        <TopBar
          onUploadFiles={() => uploadZoneRef.current?.openFiles()}
          onUploadFolder={() => uploadZoneRef.current?.openFolder()}
          onCollectClick={() => setShowCollect(true)}
        />
        <div className="flex-1 flex overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-hidden">
            <MasonryGrid refreshKey={refreshKey} />
          </main>
        </div>
      </div>

      <UploadZone ref={uploadZoneRef} onUploaded={handleUploaded} />

      <SelectionToolbar onChanged={handleUploaded} />

      {showCollect && (
        <CollectDialog
          onClose={() => setShowCollect(false)}
          onCollected={handleCollected}
        />
      )}

      {/* 移动端底部导航 */}
      <MobileNav />
    </div>
  )
}
