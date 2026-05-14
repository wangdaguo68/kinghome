# Spec: 书房风整体 UI 重设计

Date: 2026-05-14 | Status: approved

## Context

当前应用视觉偏工具型，缺乏设计感。用户选择"书房/图书馆"风格全面重设计——暖木色、暖金点缀、深色沉浸。同时修复 MOBI 书籍打不开、PDF 只显示2页、键盘左右翻页无效的问题。

## Design Decisions

| 层级 | 决策 |
|---|---|
| 整体调性 | 暖木书房，深棕渐变底 `#3C2F1F`→`#2C1F0F`，暖金点缀 `#C8A96E` |
| 字体 | 标题: Songti SC/KaiTi 衬线；正文: Georgia+Songti；UI: 系统无衬线 |
| 导航栏 | 深木毛玻璃 `rgba(44,31,15,0.94)`，底部暖金分割线 |
| 书架 | 画廊式网格，暗盒镶边 `#1E1408` |
| 阅读器 | 桌面深木底 + 中间浮暖纸页 `#FBF6ED`；导航 pill 深木毛玻璃 |
| 次级页面 | 全部深色沉浸，卡片 `#2C1F0F`+边框 `#5C4A35` |
| 覆盖范围 | 全部 6 页面 + 阅读器组件 |

## Implementation

### 1. CSS 主题系统 (index.css)
- 替换现有 `@theme` 设计令牌为书房风色值
- 主背景: `#2C1F0F`，卡片: `#2C1F0F`，边框: `#5C4A35`
- 强调色: `#C8A96E` 替代微信绿 `#07c160`
- 新增 `--color-study-bg`, `--color-study-card`, `--color-study-border`, `--color-study-gold`, `--color-study-text`, `--color-study-text-dim`
- 导航栏毛玻璃效果
- 书架卡片暗盒样式 `.book-card-study`
- 阅读器桌面+书页样式 `.reader-study`

### 2. App 壳 (App.tsx)
- 导航栏深木色，活跃链接暖金下划线
- 移除 dark mode toggle（全局暗色已是默认）

### 3. 书架 (Shelf.tsx)
- 画廊式网格，卡片加暗盒镶边
- 进度条暖金色
- 继续阅读区保留，统一色调

### 4. 阅读器 (Reader.tsx + 子组件)
- **桌面+书页**: 内容区深木底，书页 `#FBF6ED` 浮起，带 box-shadow
- **导航栏/状态栏**: 深木毛玻璃
- **翻页 pill**: 深木毛玻璃圆角胶囊
- **主题**: 默认书房风，移除旧四套硬编码主题

### 5. 其余页面 (Chat/Search/Stats/Settings)
- 统一深底深卡
- 输入框暗底
- 聊天气泡暗调

### 6. Bug 修复
- **MOBI**: HtmlEpubReader 接收 format prop，MOBI 格式走纯文本渲染路径
- **PDF**: 恢复服务端 PNG 渲染方案（移除 pdfjs-dist）
- **键盘**: 左右键在 scroll 模式也触发翻页

## Verification

1. 书架首页 → 深木背景，画廊式网格，暖金点缀
2. 打开 EPUB → 桌面深底 + 暖纸页浮起，字体衬线
3. 打开 PDF → 同上外壳，图片内容居中
4. 打开 MOBI → 可正常显示文本内容
5. 键盘 ← → 翻页生效（page 和 scroll 模式均可用）
6. 搜索/AI/统计/设置 → 全部深色书房风
7. 全局导航栏 → 深木毛玻璃，暖金活跃态
