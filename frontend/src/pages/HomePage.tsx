import { useCallback, useState } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { Sidebar } from '../components/layout/Sidebar'
import { MasonryGrid } from '../components/media/MasonryGrid'
import { UploadZone, triggerUpload } from '../components/upload/UploadZone'
import { CollectDialog } from '../components/collect/CollectDialog'
import { SelectionToolbar } from '../components/media/SelectionToolbar'

export function HomePage() {
  const [refreshKey, setRefreshKey] = useState(0)
  const [showCollect, setShowCollect] = useState(false)

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
          onUploadClick={triggerUpload}
          onCollectClick={() => setShowCollect(true)}
        />
        <div className="flex-1 flex overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-hidden">
            <MasonryGrid refreshKey={refreshKey} />
          </main>
        </div>
      </div>

      <UploadZone onUploaded={handleUploaded} />

      <SelectionToolbar onChanged={handleUploaded} />

      {showCollect && (
        <CollectDialog
          onClose={() => setShowCollect(false)}
          onCollected={handleCollected}
        />
      )}
    </div>
  )
}
