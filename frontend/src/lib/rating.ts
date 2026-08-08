/** 星级 / 旗标 颜色定义 */

export const FLAG_COLORS = [
  { level: 1, color: '#ef4444', name: '红旗' },   // 红
  { level: 2, color: '#f97316', name: '橙旗' },   // 橙
  { level: 3, color: '#eab308', name: '黄旗' },   // 黄
  { level: 4, color: '#22c55e', name: '绿旗' },   // 绿
  { level: 5, color: '#3b82f6', name: '蓝旗' },   // 蓝
]

export function getFlagColor(level: number): string | null {
  const f = FLAG_COLORS.find((x) => x.level === level)
  return f ? f.color : null
}

/** 星级：★ 字符 */
export function renderStars(level: number): string {
  return '★'.repeat(Math.max(0, Math.min(5, level)) || 0)
}
