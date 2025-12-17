-- 修复admin用户
USE kingblog;

-- 删除旧的admin用户（如果存在）
DELETE FROM users WHERE username = 'admin';

-- 插入新的admin用户（密码：admin）
INSERT INTO `users` (`username`, `password`, `nickname`, `email`) VALUES
('admin', 'admin', '管理员', 'admin@example.com');

-- 验证
SELECT id, username, password, nickname FROM users WHERE username = 'admin';

