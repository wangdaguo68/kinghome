import { query } from './db';

export interface Category {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}

// 获取所有分类
export async function getAllCategories() {
  const sql = 'SELECT * FROM categories ORDER BY name ASC';
  return await query(sql) as Category[];
}

// 根据ID获取分类
export async function getCategoryById(id: number) {
  const sql = 'SELECT * FROM categories WHERE id = ?';
  const results = await query(sql, [id]) as Category[];
  return results[0] || null;
}

// 创建分类
export async function createCategory(name: string, description?: string) {
  const sql = 'INSERT INTO categories (name, description) VALUES (?, ?)';
  const result = await query(sql, [name, description || null]) as any;
  return result.insertId;
}

// 获取复盘的所有分类
export async function getPostCategories(postId: number) {
  const sql = `
    SELECT c.* FROM categories c
    INNER JOIN post_categories pc ON c.id = pc.category_id
    WHERE pc.post_id = ?
  `;
  return await query(sql, [postId]) as Category[];
}

// 设置复盘的分类
export async function setPostCategories(postId: number, categoryIds: number[]) {
  // 先删除所有现有关联
  await query('DELETE FROM post_categories WHERE post_id = ?', [postId]);
  
  // 插入新的关联
  if (categoryIds.length > 0) {
    const values = categoryIds.map(() => '(?, ?)').join(', ');
    const sql = `INSERT INTO post_categories (post_id, category_id) VALUES ${values}`;
    const params = categoryIds.flatMap(id => [postId, id]);
    await query(sql, params);
  }
}

