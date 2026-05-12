import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Shelf from './pages/Shelf';
import Reader from './pages/Reader';
import Chat from './pages/Chat';
import Search from './pages/Search';
import Stats from './pages/Stats';
import Settings from './pages/Settings';
import { useUIStore } from './store';

function Layout({ children }: { children: React.ReactNode }) {
  const { darkMode, toggleDarkMode } = useUIStore();
  return (
    <div className={darkMode ? 'dark' : ''} style={{ minHeight: '100vh', background: darkMode ? '#1a1a1a' : '#F6F7F9' }}>
      <header className="app-header dark:bg-gray-900/85 dark:border-gray-700">
        <div className="flex items-center gap-8">
          <span className="app-logo">📚 我的书房</span>
          <nav className="flex gap-1">
            <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>书架</NavLink>
            <NavLink to="/search" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>搜索</NavLink>
            <NavLink to="/chat" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>AI 聊天</NavLink>
            <NavLink to="/stats" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>统计</NavLink>
            <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>设置</NavLink>
          </nav>
        </div>
        <button onClick={toggleDarkMode} className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 px-3 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
          {darkMode ? '☀️' : '🌙'}
        </button>
      </header>
      <main className="page-enter">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Shelf />} />
          <Route path="/reader/:bookId" element={<Reader />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/search" element={<Search />} />
          <Route path="/stats" element={<Stats />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
