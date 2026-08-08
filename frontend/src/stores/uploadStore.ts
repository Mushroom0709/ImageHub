import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Stage = 'obs' | 'thumbnail' | 'exif' | 'ai_tagging' | 'phash'
export type StageStatus = 'pending' | 'processing' | 'done' | 'failed'

export interface UploadStage {
  status: StageStatus
  progress: number // 0-100（仅 obs 分片上传时实时更新）
  error?: string
  payload?: Record<string, any> // e.g. {width, height, tag_count}
}

export type ItemStatus = 'waiting' | 'uploading' | 'paused' | 'processing' | 'done' | 'failed'

export interface UploadItem {
  id: string // 本地唯一 id（与 asset_id 无关）
  name: string
  size: number
  status: ItemStatus
  // 全局进度 0-100（综合 OBS 60% + 后处理 40%）
  overallProgress: number
  // 阶段：obs 阶段记录 multipart 信息
  multipart?: boolean
  partNumber?: number
  totalParts?: number
  speed?: number // bytes/s
  // 后端处理阶段（asset_id 有值后开始）
  assetId?: string
  // 多分片断点续传：暂停时记录 batchId（localStorage mp-resume 也保留）
  batchId?: string
  // 5 阶段状态
  stages: Record<Stage, UploadStage>
  createdAt: number
  errorMessage?: string
}

interface UploadState {
  items: UploadItem[]
  panelCollapsed: boolean // 悬浮窗最小化状态
  addItems: (items: UploadItem[]) => void
  updateItem: (id: string, patch: Partial<UploadItem>) => void
  updateStage: (id: string, stage: Stage, patch: Partial<UploadStage>) => void
  removeItem: (id: string) => void
  removeItems: (ids: string[]) => void
  retryItem: (id: string) => void // 标记 failed → waiting（用于 file picker 重新上传）
  setItems: (items: UploadItem[]) => void // 用于批量重置（重试时替换原 item）
  clearDone: () => void
  clearFailed: () => void
  clearAll: () => void
  setPanelCollapsed: (v: boolean) => void
}

const initialStages = (): Record<Stage, UploadStage> => ({
  obs: { status: 'pending', progress: 0 },
  thumbnail: { status: 'pending', progress: 0 },
  exif: { status: 'pending', progress: 0 },
  ai_tagging: { status: 'pending', progress: 0 },
  phash: { status: 'pending', progress: 0 },
})

export const useUploadStore = create<UploadState>()(
  persist(
    (set) => ({
      items: [],
      panelCollapsed: false,

      addItems: (newItems) =>
        set((s) => ({
          items: [
            ...s.items,
            ...newItems.map((it) => ({
              ...it,
              stages: it.stages ?? initialStages(),
              createdAt: it.createdAt ?? Date.now(),
              overallProgress: it.overallProgress ?? 0,
            })),
          ],
        })),

      updateItem: (id, patch) =>
        set((s) => ({
          items: s.items.map((it) => (it.id === id ? { ...it, ...patch } : it)),
        })),

      updateStage: (id, stage, patch) =>
        set((s) => ({
          items: s.items.map((it) =>
            it.id === id
              ? { ...it, stages: { ...it.stages, [stage]: { ...it.stages[stage], ...patch } } }
              : it,
          ),
        })),

      removeItem: (id) =>
        set((s) => ({ items: s.items.filter((it) => it.id !== id) })),

      removeItems: (ids) =>
        set((s) => ({ items: s.items.filter((it) => !ids.includes(it.id)) })),

      retryItem: (id) =>
        set((s) => ({
          items: s.items.map((it) =>
            it.id === id
              ? {
                  ...it,
                  status: 'waiting',
                  errorMessage: undefined,
                  overallProgress: 0,
                  stages: initialStages(),
                  assetId: undefined,
                  batchId: undefined,
                }
              : it,
          ),
        })),

      setItems: (items) => set({ items }),

      clearDone: () =>
        set((s) => ({ items: s.items.filter((it) => it.status !== 'done') })),

      clearFailed: () =>
        set((s) => ({ items: s.items.filter((it) => it.status !== 'failed') })),

      clearAll: () => set({ items: [] }),

      setPanelCollapsed: (v) => set({ panelCollapsed: v }),
    }),
    {
      name: 'imagehub-upload-queue',
      version: 1,
    },
  ),
)

/** 创建一个新的上传 item */
export function newUploadItem(name: string, size: number): UploadItem {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name,
    size,
    status: 'waiting',
    overallProgress: 0,
    stages: initialStages(),
    createdAt: Date.now(),
  }
}