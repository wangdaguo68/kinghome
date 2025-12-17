# KingBlog - 个人复盘博客系统

一个优雅简洁的个人复盘博客系统，用于记录每天的思考和成长。

## 技术栈

- **前端框架**: Next.js 14 (App Router)
- **开发语言**: TypeScript
- **样式**: Tailwind CSS
- **数据库**: MySQL
- **日期处理**: date-fns

## 功能特性

- ✨ 优雅简洁的UI设计
- 📝 创建和编辑复盘记录
- 📅 按日期查看复盘
- 🏷️ 支持心情/状态标记
- 📊 今日总结和明日计划
- 👁️ 浏览统计
- 💾 草稿和发布状态

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置数据库

首先确保MySQL服务已启动，然后执行数据库初始化脚本：

```bash
mysql -u root -p < database/init.sql
```

或者使用你提供的密码：

```bash
mysql -u root -pking665206 < database/init.sql
```

### 3. 配置环境变量

复制 `.env.local.example` 为 `.env.local`：

```bash
cp .env.local.example .env.local
```

`.env.local` 文件内容（已配置默认值）：

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=king665206
DB_NAME=kingblog
```

### 4. 启动开发服务器

```bash
npm run dev
```

打开浏览器访问 [http://localhost:3000](http://localhost:3000)

## 项目结构

```
kingblog/
├── app/                    # Next.js App Router
│   ├── api/               # API路由
│   │   └── posts/        # 复盘相关API
│   ├── posts/            # 复盘页面
│   ├── globals.css       # 全局样式
│   ├── layout.tsx        # 根布局
│   └── page.tsx          # 首页
├── components/           # React组件
│   ├── Header.tsx       # 头部导航
│   └── Footer.tsx       # 页脚
├── lib/                 # 工具库
│   ├── db.ts           # 数据库连接
│   └── posts.ts        # 复盘数据操作
├── database/            # 数据库脚本
│   └── init.sql        # 初始化SQL
└── package.json        # 项目配置
```

## 使用说明

1. **创建复盘**: 点击首页的"写复盘"按钮，填写复盘信息
2. **查看复盘**: 在首页点击任意复盘标题查看详情
3. **编辑复盘**: 在复盘详情页点击"编辑"按钮
4. **删除复盘**: 目前需要在数据库中手动删除（后续可添加删除功能）

## 数据库设计

详细设计请查看 `database_design.md` 文件。

主要表结构：
- `users`: 用户表
- `posts`: 复盘记录表（核心）
- `categories`: 分类表
- `tags`: 标签表
- `post_categories`: 文章分类关联表
- `post_tags`: 文章标签关联表

## 开发计划

- [ ] 用户认证系统
- [ ] 分类和标签管理
- [ ] 搜索功能
- [ ] 数据统计和可视化
- [ ] Markdown支持
- [ ] 图片上传

## License

MIT

