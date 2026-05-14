import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

// Books
export const getBooks = (params?: Record<string, any>) => api.get('/books', { params });
export const getContinueReading = (limit = 20) => api.get('/books/continue-reading', { params: { limit } });
export const getBook = (id: number) => api.get(`/books/${id}`);
export const getCategories = () => api.get('/books/categories');
export const classifyBooks = () => api.post('/books/classify');
export const deleteBook = (id: number) => api.delete(`/books/${id}`);

// Progress
export const getProgress = (bookId: number) => api.get(`/books/${bookId}/progress`);
export const updateProgress = (bookId: number, data: any) => api.put(`/books/${bookId}/progress`, data);

// Reader
export const getBookContent = (bookId: number) => api.get(`/reader/${bookId}/content`);
export const getBookToc = (bookId: number) => api.get(`/reader/${bookId}/toc`);
export const getChapter = (bookId: number, idx: number) => api.get(`/reader/${bookId}/chapter/${idx}`);
export const getPdfPage = (bookId: number, page: number) => api.get(`/reader/${bookId}/page/${page}`);

// Highlights
export const getHighlights = (bookId: number) => api.get(`/highlights/book/${bookId}`);
export const createHighlight = (data: any) => api.post('/highlights', data);
export const updateHighlight = (id: number, data: any) => api.put(`/highlights/${id}`, data);
export const deleteHighlight = (id: number) => api.delete(`/highlights/${id}`);

// Shelf
export const getShelf = (status?: string) => api.get('/shelf', { params: { status } });
export const addToShelf = (bookId: number, data: any) => api.post(`/shelf/${bookId}`, data);
export const removeFromShelf = (bookId: number) => api.delete(`/shelf/${bookId}`);

// Search
export const fulltextSearch = (q: string, page = 1) => api.get('/search/fulltext', { params: { q, page } });

// Scan
export const getScanStatus = () => api.get('/scan/status');
export const startScan = () => api.post('/scan/start');

// Chat
export const getConversations = () => api.get('/chat/conversations');
export const createConversation = (title?: string, model?: string) => api.post('/chat/conversations', null, { params: { title, model } });
export const deleteConversation = (id: number) => api.delete(`/chat/conversations/${id}`);
export const getMessages = (convId: number) => api.get(`/chat/conversations/${convId}/messages`);
export const sendMessage = (data: any) => api.post('/chat/send', data);

// Settings / LLM Providers
export const getProviders = () => api.get('/settings/providers');
export const createProvider = (data: any) => api.post('/settings/providers', data);
export const updateProvider = (id: number, data: any) => api.put(`/settings/providers/${id}`, data);
export const deleteProvider = (id: number) => api.delete(`/settings/providers/${id}`);
export const testProviderConnection = (data: any) => api.post('/settings/providers/test', data);
export const getActiveProvider = () => api.get('/settings/providers/active');
