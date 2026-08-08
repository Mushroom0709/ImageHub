/** 星级 / 旗标 颜色定义 */

export const FLAG_COLORS = [
  { level: 1, color: '#ef4444', name: '红旗' },   // 红（快捷键 6）
  { level: 2, color: '#f97316', name: '橙旗' },   // 橙（快捷键 7）
  { level: 3, color: '#eab308', name: '黄旗' },   // 黄（快捷键 8）
  { level: 4, color: '#22c55e', name: '绿旗' },   // 绿（快捷键 9）
]
// 快捷键映射：6-9 对应 1-4 级旗标
export const KEY_TO_FLAG: Record<string, number> = { '6': 1, '7': 2, '8': 3, '9': 4 }

export function getFlagColor(level: number): string | null {
  const f = FLAG_COLORS.find((x) => x.level === level)
  return f ? f.color : null
}

/** 星级：★ 字符 */
export function renderStars(level: number): string {
  return '★'.repeat(Math.max(0, Math.min(5, level)) || 0)
}
