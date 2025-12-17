# KingBlog 数据库设计文档

## 数据库概述
- 数据库名：kingblog
- 用途：个人复盘博客系统
- 字符集：utf8mb4（支持emoji和特殊字符）

## 表结构设计

### 1. users 表（用户表）
虽然是个人的博客，但为了系统扩展性，保留用户表。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INT | 用户ID | PRIMARY KEY, AUTO_INCREMENT |
| username | VARCHAR(50) | 用户名 | UNIQUE, NOT NULL |
| password | VARCHAR(255) | 密码（加密存储） | NOT NULL |
| email | VARCHAR(100) | 邮箱 | UNIQUE |
| nickname | VARCHAR(50) | 昵称 | |
| avatar | VARCHAR(255) | 头像URL | |
| created_at | DATETIME | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | 更新时间 | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP |

### 2. posts 表（复盘记录表 - 核心表）
存储每天的复盘记录。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INT | 复盘ID | PRIMARY KEY, AUTO_INCREMENT |
| user_id | INT | 用户ID | FOREIGN KEY, NOT NULL |
| title | VARCHAR(200) | 标题 | NOT NULL |
| content | TEXT | 复盘内容 | NOT NULL |
| summary | TEXT | 今日总结 | |
| plan | TEXT | 明日计划 | |
| mood | VARCHAR(20) | 心情/状态 | |
| date | DATE | 复盘日期 | NOT NULL, INDEX |
| status | ENUM('draft', 'published') | 状态 | DEFAULT 'published' |
| views | INT | 浏览次数 | DEFAULT 0 |
| created_at | DATETIME | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | 更新时间 | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP |

### 3. categories 表（分类表）
用于对复盘进行分类管理。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INT | 分类ID | PRIMARY KEY, AUTO_INCREMENT |
| name | VARCHAR(50) | 分类名称 | UNIQUE, NOT NULL |
| description | VARCHAR(200) | 分类描述 | |
| created_at | DATETIME | 创建时间 | DEFAULT CURRENT_TIMESTAMP |

### 4. post_categories 表（文章分类关联表）
多对多关系：一篇文章可以有多个分类，一个分类可以包含多篇文章。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INT | 关联ID | PRIMARY KEY, AUTO_INCREMENT |
| post_id | INT | 复盘ID | FOREIGN KEY, NOT NULL |
| category_id | INT | 分类ID | FOREIGN KEY, NOT NULL |
| created_at | DATETIME | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| UNIQUE(post_id, category_id) | | 防止重复关联 | |

### 5. tags 表（标签表）
用于给复盘添加标签。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INT | 标签ID | PRIMARY KEY, AUTO_INCREMENT |
| name | VARCHAR(30) | 标签名称 | UNIQUE, NOT NULL |
| color | VARCHAR(7) | 标签颜色（十六进制） | DEFAULT '#1890ff' |
| created_at | DATETIME | 创建时间 | DEFAULT CURRENT_TIMESTAMP |

### 6. post_tags 表（文章标签关联表）
多对多关系：一篇文章可以有多个标签，一个标签可以标记多篇文章。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INT | 关联ID | PRIMARY KEY, AUTO_INCREMENT |
| post_id | INT | 复盘ID | FOREIGN KEY, NOT NULL |
| tag_id | INT | 标签ID | FOREIGN KEY, NOT NULL |
| created_at | DATETIME | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| UNIQUE(post_id, tag_id) | | 防止重复关联 | |

## 索引设计

1. **posts表**：
   - PRIMARY KEY: id
   - INDEX: date（用于按日期查询）
   - INDEX: user_id（用于查询用户的所有复盘）
   - INDEX: status（用于筛选已发布/草稿）

2. **post_categories表**：
   - UNIQUE: (post_id, category_id)

3. **post_tags表**：
   - UNIQUE: (post_id, tag_id)

## 外键约束

- posts.user_id → users.id (ON DELETE CASCADE)
- post_categories.post_id → posts.id (ON DELETE CASCADE)
- post_categories.category_id → categories.id (ON DELETE CASCADE)
- post_tags.post_id → posts.id (ON DELETE CASCADE)
- post_tags.tag_id → tags.id (ON DELETE CASCADE)

## 设计说明

1. **核心功能**：posts表是核心，包含复盘的所有关键信息
2. **扩展性**：设计了分类和标签系统，方便后续管理和检索
3. **灵活性**：支持草稿和发布状态，可以提前写好复盘内容
4. **日期索引**：对date字段建立索引，方便按日期范围查询
5. **软删除**：可以通过status字段实现软删除，不直接删除数据

