# Design System — ImageHub

> 图片优先的工具型产品设计规范。UI 是画框，图片是主角。

## 1. 颜色系统

### 基础色板（Zinc 灰阶）

| Token | 浅色 | 深色 | 用途 |
|---|---|---|---|
| `--color-bg` | `#FAFAFA` | `#0A0A0A` | 页面背景 |
| `--color-surface` | `#FFFFFF` | `#141414` | 卡片/弹层表面 |
| `--color-border` | `#E4E4E7` | `#262626` | 边框/分割线 |
| `--color-text-primary` | `#18181B` | `#F4F4F5` | 主文本 |
| `--color-text-secondary` | `#71717A` | `#A1A1AA` | 次文本/辅助信息 |
| `--color-text-muted` | `#A1A1AA` | `#71717A` | 占位/禁用 |

### 品牌色（Teal）

| Token | 浅色 | 深色 | 用途 |
|---|---|---|---|
| `--color-primary` | `#0D9488` | `#2DD4BF` | 主色，按钮/选中态 |
| `--color-primary-hover` | `#0F766E` | `#14B8A6` | Hover 态 |
| `--color-primary-bg` | `#CCFBF7` | `#134E4A` | 选中背景/徽标背景 |

### 功能色

| Token | 值 | 用途 |
|---|---|---|
| `--color-star` | `#F59E0B` | 星标（通用） |
| `--color-flag-1` | `#EF4444` | 旗标 1 级（红） |
| `--color-flag-2` | `#F97316` | 旗标 2 级（橙） |
| `--color-flag-3` | `#EAB308` | 旗标 3 级（黄） |
| `--color-flag-4` | `#22C55E` | 旗标 4 级（绿） |
| `--color-flag-5` | `#3B82F6` | 旗标 5 级（蓝） |
| `--color-destructive` | `#DC2626` | 删除/危险操作 |

## 2. 字体

```css
--font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
             "Hiragino Sans GB", "Microsoft YaHei", Inter, sans-serif;
--font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
```

- 基准字号：`14px`
- 行高：`1.5`
- 字重：常规 400，中等 500，粗体 600

### 字号阶梯

| 级别 | 字号 | 用途 |
|---|---|---|
| xs | 12px | 标签、辅助说明、时间戳 |
| sm | 13px | 次要信息、菜单 |
| base | 14px | 正文、按钮、列表 |
| lg | 16px | 小标题 |
| xl | 18px | 页面标题 |
| 2xl | 24px | 大标题 |

## 3. 间距 & 圆角

### 间距（4px 基础单位）

```
--space-1: 4px
--space-2: 8px
--space-3: 12px
--space-4: 16px
--space-6: 24px
--space-8: 32px
```

### 圆角

```
--radius-sm: 4px     按钮、标签
--radius-md: 8px     卡片、输入框
--radius-lg: 12px    弹层、大图卡片
--radius-full: 9999px  圆形头像、徽标
```

## 4. 布局

- **侧边栏宽度**：260px（展开）/ 64px（折叠图标模式）
- **顶部栏高度**：56px
- **瀑布流列数**：4-6 列自适应，列间距 12px
- **图片卡片**：宽度自适应列宽，高度按内容比例

## 5. 组件规范

### 图片卡片
- 默认：纯图，无额外 UI
- Hover：底部 24px 半透明信息条（显示标题 + 星标按钮 + 更多）
- 选中：2px 主色边框 + 4px 内边距偏移

### 标签 Chip
- 高度 24px，左右内边距 8px，圆角 4px
- 默认：灰色背景 + 深灰文字
- 选中：主色背景 + 白色文字
- 可删除标签：右侧 × 按钮

### 按钮
- 高度：sm=28px, md=32px, lg=40px
- 主按钮：主色背景 + 白字 + 8px 圆角
- 次按钮：灰底 + 深灰字 + border
- 幽灵按钮：透明背景 + hover 灰底

## 7. 动画

- 过渡时长：150ms（微交互）/ 200ms（面板展开）/ 300ms（页面切换）
- 缓动：`cubic-bezier(0.16, 1, 0.3, 1)`
- 图片加载：淡入（opacity 0→1, 200ms），用 aspect-ratio 预留空间防布局抖动
- 尊重 `prefers-reduced-motion`

## 8. UX 关键准则

### 布局稳定性
- 所有图片必须有宽高信息，用 `aspect-ratio` 预留空间，**禁止布局抖动 (CLS < 0.1)**
- skeleton 高度与真实内容比例一致
- 固定顶栏/侧栏/面板的 z-index 层级明确，不互相遮挡

### z-index 层级
```
0  — 内容
10 — 顶栏 / 侧边栏
20 — 上传进度面板 / 悬浮工具
30 — dropdown / popover
40 — sidebar drawer (mobile)
50 — modal / lightbox
60 — toast / notification
```

### 触控（移动端）
- 所有可点击区域最小 **44×44px**
- 触控目标间距至少 **8px**
- mobile-first 设计：默认移动端样式，`md:` `lg:` 往上增强
- 主内容区 `overscroll-behavior: contain`，防止误触下拉刷新

### 图片优化
- 三档缩略图 + srcset，列表用最小档
- 懒加载（IntersectionObserver）
- WebP 优先，降级 JPG

### 可访问性
- 全功能键盘可达，Tab 顺序符合视觉顺序
- 焦点环可见，不删除
- 语义化 HTML，正确的 heading 层级
- 所有图片有 alt 文本

### 进度反馈
- 上传/采集等异步操作必须显示实时进度
- 每个步骤有状态指示（排队中/处理中/完成/失败）
- 失败项提供重试

## 9. 暗黑模式

- 所有颜色 token 自动切换
- 图片在深色模式下自动加 1px 浅色边框（防止纯白图和背景融合）
- 阴影减弱，用边框区分层级

## 10. 图标

- 使用 Lucide 图标库（线性风格，统一 24px 网格）
- 按钮内图标 16px，导航图标 20px
- 不用 emoji 当图标
