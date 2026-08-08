/** API 客户端 */
const BASE = '/api'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token')
  const resp = await fetch(`${BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  })
  // 401 跳转登录
  if (resp.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('请先登录')
  }
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(text || `HTTP ${resp.status}`)
  }
  const data = await resp.json()
  if (data.code !== 0) {
    throw new Error(data.message || data.detail || '请求失败')
  }
  return data.data as T
}

// ===== 类型定义 =====

export interface Tag {
  id: string
  name: string
  category: string
  parent_id: string | null
  alias: string[]
  status: string
  sort_order: number
  asset_count: number
  children?: Tag[]
}

export interface Asset {
  id: string
  title: string
  description: string
  source_type: string
  source_id: string
  source_url: string
  author_name: string
  asset_type: 'image' | 'video'
  obs_key: string
  file_name: string
  file_size: number
  width: number
  height: number
  duration: number
  phash: string
  exif: Record<string, unknown> | null
  star_level: number
  flag_level: number
  quality_score: number
  top_category_id: string | null
  created_at: string
  updated_at: string
  tags: Tag[]
  thumb_small: string
  thumb_medium: string
  thumb_raw: string
}

export interface AssetListResponse {
  items: Asset[]
  total: number
  page: number
  size: number
}

// ===== 素材 API =====

export const assetApi = {
  list: (params: Record<string, string | number | boolean | undefined>) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== '') qs.set(k, String(v))
    })
    return request<AssetListResponse>(`/assets?${qs.toString()}`)
  },
  detail: (id: string) => request<Asset>(`/assets/${id}`),
  create: (data: Record<string, unknown>) =>
    request<Asset>('/assets', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    request<Asset>(`/assets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id: string) => request(`/assets/${id}`, { method: 'DELETE' }),
  batchDelete: (ids: string[]) =>
    request('/assets/batch-delete', { method: 'POST', body: JSON.stringify(ids) }),
  batchRecover: (ids: string[]) =>
    request('/assets/batch-recover', { method: 'POST', body: JSON.stringify(ids) }),
  addTags: (id: string, tagIds: string[]) =>
    request(`/assets/${id}/tags`, { method: 'POST', body: JSON.stringify(tagIds) }),
  removeTag: (id: string, tagId: string) =>
    request(`/assets/${id}/tags/${tagId}`, { method: 'DELETE' }),
  batchTag: (assetIds: string[], addTagIds: string[], removeTagIds: string[] = []) =>
    request('/assets/batch-tag', {
      method: 'POST',
      body: JSON.stringify({ asset_ids: assetIds, add_tag_ids: addTagIds, remove_tag_ids: removeTagIds }),
    }),
}

// ===== 顶层分类（项目）API =====

export interface TopCategory {
  id: string
  name: string
  description: string
  asset_count: number
  created_at: string
}

export const topCategoryApi = {
  list: () => request<TopCategory[]>('/top-categories'),
  create: (data: { name: string; description?: string }) =>
    request<TopCategory>('/top-categories', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    request<TopCategory>(`/top-categories/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id: string) => request(`/top-categories/${id}`, { method: 'DELETE' }),
}

// ===== 标签 API =====

export const tagApi = {
  tree: (category?: string) => {
    const qs = category ? `?category=${category}` : ''
    return request<Record<string, Tag[]>>(`/tags/tree${qs}`)
  },
  search: (q: string, category?: string, limit = 10) => {
    const params = new URLSearchParams({ q, limit: String(limit) })
    if (category) params.set('category', category)
    return request<Tag[]>(`/tags/search?${params.toString()}`)
  },
  create: (data: { name: string; category: string; parent_id?: string | null; alias?: string[] }) =>
    request<Tag>('/tags', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    request<Tag>(`/tags/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id: string) => request(`/tags/${id}`, { method: 'DELETE' }),
  merge: (id: string, targetTagId: string) =>
    request(`/tags/${id}/merge`, { method: 'POST', body: JSON.stringify({ target_tag_id: targetTagId }) }),
}
