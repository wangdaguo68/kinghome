// 初始化数据
let books = JSON.parse(localStorage.getItem('books')) || ['三体', '活着', '百年孤独', '1984', '小王子'];
let menus = JSON.parse(localStorage.getItem('menus')) || ['宫保鸡丁', '麻婆豆腐', '红烧肉', '西红柿炒蛋', '鱼香肉丝'];

// 保存数据到本地
function saveData() {
    localStorage.setItem('books', JSON.stringify(books));
    localStorage.setItem('menus', JSON.stringify(menus));
}

// 标签切换
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        btn.classList.add('active');
        document.getElementById(tab).classList.add('active');
    });
});

// 随机生成书籍
function generateBook() {
    if (books.length === 0) {
        document.getElementById('book-result').textContent = '请先添加书籍';
        return;
    }
    const random = books[Math.floor(Math.random() * books.length)];
    document.getElementById('book-result').textContent = random;
}

// 随机生成菜单
function generateMenu() {
    if (menus.length === 0) {
        document.getElementById('menu-result').textContent = '请先添加菜品';
        return;
    }
    const random = menus[Math.floor(Math.random() * menus.length)];
    document.getElementById('menu-result').textContent = random;
}

// 添加书籍
function addBook() {
    const input = document.getElementById('book-input');
    const value = input.value.trim();
    if (value) {
        books.push(value);
        saveData();
        renderBooks();
        input.value = '';
    }
}

// 删除书籍
function deleteBook(index) {
    books.splice(index, 1);
    saveData();
    renderBooks();
}

// 渲染书籍列表
function renderBooks() {
    const list = document.getElementById('book-list');
    list.innerHTML = books.map((book, index) => 
        `<li>${book} <button class="btn-delete" onclick="deleteBook(${index})">删除</button></li>`
    ).join('');
}

// 添加菜品
function addMenu() {
    const input = document.getElementById('menu-input');
    const value = input.value.trim();
    if (value) {
        menus.push(value);
        saveData();
        renderMenus();
        input.value = '';
    }
}

// 删除菜品
function deleteMenu(index) {
    menus.splice(index, 1);
    saveData();
    renderMenus();
}

// 渲染菜单列表
function renderMenus() {
    const list = document.getElementById('menu-list');
    list.innerHTML = menus.map((menu, index) => 
        `<li>${menu} <button class="btn-delete" onclick="deleteMenu(${index})">删除</button></li>`
    ).join('');
}

// 页面加载时初始化
renderBooks();
renderMenus();
