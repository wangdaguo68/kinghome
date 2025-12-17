-- KingBlog 数据库初始化脚本
-- 数据库：kingblog
-- 端口：3306
-- 账号：root
-- 密码：king665206

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS `kingblog` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `kingblog`;

-- 1. 创建用户表
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` VARCHAR(50) NOT NULL COMMENT '用户名',
  `password` VARCHAR(255) NOT NULL COMMENT '密码（加密存储）',
  `email` VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
  `nickname` VARCHAR(50) DEFAULT NULL COMMENT '昵称',
  `avatar` VARCHAR(255) DEFAULT NULL COMMENT '头像URL',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 2. 创建复盘记录表（核心表）
DROP TABLE IF EXISTS `posts`;
CREATE TABLE `posts` (
  `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '复盘ID',
  `user_id` INT(11) NOT NULL COMMENT '用户ID',
  `title` VARCHAR(200) NOT NULL COMMENT '标题',
  `content` TEXT NOT NULL COMMENT '复盘内容',
  `summary` TEXT DEFAULT NULL COMMENT '今日总结',
  `plan` TEXT DEFAULT NULL COMMENT '明日计划',
  `mood` VARCHAR(20) DEFAULT NULL COMMENT '心情/状态',
  `date` DATE NOT NULL COMMENT '复盘日期',
  `status` ENUM('draft', 'published') NOT NULL DEFAULT 'published' COMMENT '状态：draft-草稿，published-已发布',
  `views` INT(11) NOT NULL DEFAULT 0 COMMENT '浏览次数',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_date` (`date`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_posts_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='复盘记录表';

-- 3. 创建分类表
DROP TABLE IF EXISTS `categories`;
CREATE TABLE `categories` (
  `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '分类ID',
  `name` VARCHAR(50) NOT NULL COMMENT '分类名称',
  `description` VARCHAR(200) DEFAULT NULL COMMENT '分类描述',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分类表';

-- 4. 创建文章分类关联表
DROP TABLE IF EXISTS `post_categories`;
CREATE TABLE `post_categories` (
  `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '关联ID',
  `post_id` INT(11) NOT NULL COMMENT '复盘ID',
  `category_id` INT(11) NOT NULL COMMENT '分类ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_post_category` (`post_id`, `category_id`),
  KEY `idx_post_id` (`post_id`),
  KEY `idx_category_id` (`category_id`),
  CONSTRAINT `fk_post_categories_post_id` FOREIGN KEY (`post_id`) REFERENCES `posts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_post_categories_category_id` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文章分类关联表';

-- 5. 创建标签表
DROP TABLE IF EXISTS `tags`;
CREATE TABLE `tags` (
  `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '标签ID',
  `name` VARCHAR(30) NOT NULL COMMENT '标签名称',
  `color` VARCHAR(7) NOT NULL DEFAULT '#1890ff' COMMENT '标签颜色（十六进制）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='标签表';

-- 6. 创建文章标签关联表
DROP TABLE IF EXISTS `post_tags`;
CREATE TABLE `post_tags` (
  `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '关联ID',
  `post_id` INT(11) NOT NULL COMMENT '复盘ID',
  `tag_id` INT(11) NOT NULL COMMENT '标签ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_post_tag` (`post_id`, `tag_id`),
  KEY `idx_post_id` (`post_id`),
  KEY `idx_tag_id` (`tag_id`),
  CONSTRAINT `fk_post_tags_post_id` FOREIGN KEY (`post_id`) REFERENCES `posts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_post_tags_tag_id` FOREIGN KEY (`tag_id`) REFERENCES `tags` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文章标签关联表';

-- 插入默认用户
-- 默认用户名：admin，默认密码：admin（请在生产环境中修改）
-- 注意：这里使用明文密码，系统会自动支持bcrypt加密的密码
INSERT INTO `users` (`username`, `password`, `nickname`, `email`) VALUES
('admin', 'admin', '管理员', 'admin@example.com');

-- 插入一些示例分类
INSERT INTO `categories` (`name`, `description`) VALUES
('工作复盘', '记录工作中的思考和总结'),
('学习复盘', '记录学习过程中的收获和反思'),
('生活复盘', '记录日常生活的感悟'),
('项目复盘', '记录项目开发中的经验教训');

-- 插入一些示例标签
INSERT INTO `tags` (`name`, `color`) VALUES
('重要', '#ff4d4f'),
('待改进', '#faad14'),
('已完成', '#52c41a'),
('计划中', '#1890ff'),
('思考', '#722ed1');

