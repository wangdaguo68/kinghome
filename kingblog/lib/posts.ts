import { query } from './db';

export interface Post {
  id: number;
  user_id: number;
  title: string;
  content: string;
  summary: string | null;
  plan: string | null;
  mood: string | null;
  date: string;
  status: 'draft' | 'published';
  views: number;
  created_at: string;
  updated_at: string;
}

export interface GetPostsOptions {
  limit?: number;
  status?: 'draft' | 'published' | 'all';
  date?: string;
}

// 获取复盘（支持状态/日期过滤）
export async function getPosts(options: GetPostsOptions = {}) {
  const { limit, status = 'published', date } = options;

  const conditions: string[] = [];
  const params: any[] = [];

  if (status !== 'all') {
    conditions.push('status = ?');
    params.push(status);
  }

  if (date) {
    conditions.push('date = ?');
    params.push(date);
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

  const sql = `
    SELECT * FROM posts
    ${where}
    ORDER BY date DESC, created_at DESC
    ${limit ? `LIMIT ${limit}` : ''}
  `;

  return await query(sql, params) as Post[];
}

// 根据ID获取复盘
export async function getPostById(id: number) {
  const sql = 'SELECT * FROM posts WHERE id = ?';
  const results = await query(sql, [id]) as Post[];
  return results[0] || null;
}

// 创建复盘
export async function createPost(post: Omit<Post, 'id' | 'created_at' | 'updated_at' | 'views'>) {
  const sql = `
    INSERT INTO posts (user_id, title, content, summary, plan, mood, date, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `;
  const result = await query(sql, [
    post.user_id,
    post.title,
    post.content,
    post.summary || null,
    post.plan || null,
    post.mood || null,
    post.date,
    post.status || 'published',
  ]) as any;
  
  return result.insertId;
}

// 更新复盘
export async function updatePost(id: number, post: Partial<Post>) {
  const fields: string[] = [];
  const values: any[] = [];
  
  if (post.title !== undefined) {
    fields.push('title = ?');
    values.push(post.title);
  }
  if (post.content !== undefined) {
    fields.push('content = ?');
    values.push(post.content);
  }
  if (post.summary !== undefined) {
    fields.push('summary = ?');
    values.push(post.summary);
  }
  if (post.plan !== undefined) {
    fields.push('plan = ?');
    values.push(post.plan);
  }
  if (post.mood !== undefined) {
    fields.push('mood = ?');
    values.push(post.mood);
  }
  if (post.date !== undefined) {
    fields.push('date = ?');
    values.push(post.date);
  }
  if (post.status !== undefined) {
    fields.push('status = ?');
    values.push(post.status);
  }
  
  if (fields.length === 0) {
    return false;
  }
  
  values.push(id);
  const sql = `UPDATE posts SET ${fields.join(', ')} WHERE id = ?`;
  await query(sql, values);
  return true;
}

// 删除复盘
export async function deletePost(id: number) {
  const sql = 'DELETE FROM posts WHERE id = ?';
  await query(sql, [id]);
  return true;
}

// 增加浏览次数
export async function incrementViews(id: number) {
  const sql = 'UPDATE posts SET views = views + 1 WHERE id = ?';
  await query(sql, [id]);
}

// 获取昨天的复盘（用于创建新复盘时参考）
export async function getYesterdayPost(userId: number) {
  const sql = `
    SELECT * FROM posts 
    WHERE user_id = ? 
    AND date = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
    ORDER BY created_at DESC
    LIMIT 1
  `;
  const results = await query(sql, [userId]) as Post[];
  return results[0] || null;
}

// 获取最近一篇"日复盘"类型的复盘
export async function getLatestDailyPost(userId: number) {
  const sql = `
    SELECT p.* FROM posts p
    INNER JOIN post_categories pc ON p.id = pc.post_id
    INNER JOIN categories c ON pc.category_id = c.id
    WHERE p.user_id = ? 
    AND c.name = '日复盘'
    ORDER BY p.date DESC, p.created_at DESC
    LIMIT 1
  `;
  const results = await query(sql, [userId]) as Post[];
  return results[0] || null;
}

