# 阅读应用 (Reading App)

## 架构

- **前端**: React + TypeScript + Vite + Tailwind CSS v4, `D:\software\reading-app\frontend`
- **后端**: Python FastAPI + SQLAlchemy 2.0 async + aiosqlite, `D:\software\reading-app\backend`
- **数据库**: SQLite (`data/app.db`)
- **缓存目录**: `backend/app/cache/`
- **开发端口**: Vite `:5173` → API 代理到 FastAPI `:8000`

## 常用命令

```bash
# 前端开发
cd frontend && npm run dev

# 前端构建
cd frontend && npm run build

# 后端启动
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 公网分享 (serveo, 不稳定)
ssh -R 80:localhost:5173 serveo.net
```

## 前端路由 (React Router)

| 路由 | 组件 | 说明 |
|------|------|------|
| `/` | Shelf | 书架首页，48本书/页 |
| `/reader/:bookId` | Reader | 阅读器，支持 EPUB/PDF/MOBI |
| `/chat` | Chat | AI 知识库对话 |
| `/search` | Search | 全文搜索 |
| `/stats` | Stats | 阅读统计 |
| `/settings` | Settings | AI 模型配置 |

## 后端 API 路由

| 前缀 | 说明 |
|------|------|
| `/api/books` | 书架列表、分类 |
| `/api/reader` | 阅读内容、章节、PDF页面 |
| `/api/chat` | AI 对话 (RAG) |
| `/api/search` | 全文/标题搜索 |
| `/api/scan` | 书库扫描 |
| `/api/shelf` | 书架状态 CRUD |
| `/api/highlights` | 划线笔记 |
| `/api/settings` | LLM 配置 |

## UI 主题 — 书房风 (Study/Library)

- 全局暗色木纹底 `--color-bg: #2C1F0F`
- 暖金主色 `--color-primary: #C8A96E`
- 暖白纸张 `#FBF6ED` (阅读区)
- 衬线字体 (Georgia/Songti SC)
- 无 dark mode 切换 — 默认暗色

## 最近完成的性能优化 (2026-05-14)

1. **P0**: 后端 `convert_pdf_to_html` 只返回页数，不提取全文；前端 dedup content 请求
2. **P1**: 后端 5min TTL 缓存 PDF/EPUB 文件对象；前端 React.lazy 代码分割；封面缩略图 200px
3. **P2**: 数据库索引 (format/category/updated_at/highlights FK)；PDF 翻页预加载

## 关键文件

- 全局样式: `frontend/src/index.css` — CSS 变量 + 书房风组件样式
- 状态管理: `frontend/src/store.ts` — Zustand (readingTime, sidebarOpen)
- 阅读器: `frontend/src/pages/Reader.tsx` — 核心阅读页
- PDF: `frontend/src/components/PdfReader.tsx` — 服务端PNG渲染
- EPUB: `frontend/src/components/HtmlEpubReader.tsx` — iframe + iframe body
- 阅读服务: `backend/app/services/reader_service.py` — PDF/EPUB/MOBI 处理
- 书架服务: `backend/app/services/book_service.py` — 元数据提取、封面缩略图
