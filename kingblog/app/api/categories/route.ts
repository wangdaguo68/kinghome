import { NextRequest, NextResponse } from 'next/server';
import { getAllCategories, createCategory } from '@/lib/categories';

// GET - 获取所有分类
export async function GET() {
  try {
    const categories = await getAllCategories();
    return NextResponse.json({ success: true, data: categories });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// POST - 创建新分类
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, description } = body;
    
    if (!name || name.trim() === '') {
      return NextResponse.json(
        { success: false, error: '分类名称不能为空' },
        { status: 400 }
      );
    }
    
    const categoryId = await createCategory(name.trim(), description);
    return NextResponse.json({ success: true, data: { id: categoryId } });
  } catch (error: any) {
    // 处理重复分类名称的错误
    if (error.code === 'ER_DUP_ENTRY') {
      return NextResponse.json(
        { success: false, error: '分类名称已存在' },
        { status: 400 }
      );
    }
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

