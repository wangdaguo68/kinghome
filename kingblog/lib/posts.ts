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
  status?: 'draft' | 'published' | 'all';
  date?: string;
  categoryId?: number;
  page?: number;
  pageSize?: number;
}

// 获取复盘（支持状态/日期/分类/分页过滤）
export async function getPosts(options: GetPostsOptions = {}) {
  const {
    status = 'published',
    date,
    categoryId,
    page = 1,
    pageSize,
  } = options;

  const conditions: string[] = [];
  const params: any[] = [];
  let join = '';

  if (status !== 'all') {
    conditions.push('p.status = ?');
    params.push(status);
  }

  if (date) {
    conditions.push('p.date = ?');
    params.push(date);
  }

  if (categoryId) {
    join = 'INNER JOIN post_categories pc ON p.id = pc.post_id';
    conditions.push('pc.category_id = ?');
    params.push(categoryId);
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

  // 计算分页（直接拼到 SQL，避免 MySQL 对 LIMIT 参数类型的限制）
  const limitClause =
    pageSize && pageSize > 0
      ? `LIMIT ${Number(pageSize)} OFFSET ${Number((page - 1) * pageSize)}`
      : '';

  const sql = `
    SELECT p.* FROM posts p
    ${join}
    ${where}
    ORDER BY p.date DESC, p.created_at DESC
    ${limitClause}
  `;

  return await query(sql, params) as Post[];
}

// 统计复盘数量（用于分页）
export async function countPosts(options: Omit<GetPostsOptions, 'page' | 'pageSize'> = {}) {
  const {
    status = 'published',
    date,
    categoryId,
  } = options;

  const conditions: string[] = [];
  const params: any[] = [];
  let join = '';

  if (status !== 'all') {
    conditions.push('p.status = ?');
    params.push(status);
  }

  if (date) {
    conditions.push('p.date = ?');
    params.push(date);
  }

  if (categoryId) {
    join = 'INNER JOIN post_categories pc ON p.id = pc.post_id';
    conditions.push('pc.category_id = ?');
    params.push(categoryId);
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

  const sql = `
    SELECT COUNT(DISTINCT p.id) as total
    FROM posts p
    ${join}
    ${where}
  `;

  const rows = await query(sql, params) as any[];
  return rows[0]?.total ?? 0;
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

// 批量删除复盘
export async function deletePosts(ids: number[]) {
  if (!ids || ids.length === 0) return 0;
  const placeholders = ids.map(() => '?').join(', ');
  const sql = `DELETE FROM posts WHERE id IN (${placeholders})`;
  await query(sql, ids);
  return ids.length;
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

