import { create } from 'zustand';

interface ReadingState {
  currentBookId: number | null;
  readingTime: number;
  setCurrentBook: (id: number | null) => void;
  addReadingTime: (seconds: number) => void;
}

export const useReadingStore = create<ReadingState>((set) => ({
  currentBookId: null,
  readingTime: 0,
  setCurrentBook: (id) => set({ currentBookId: id }),
  addReadingTime: (seconds) => set((s) => ({ readingTime: s.readingTime + seconds })),
}));

interface UIState {
  darkMode: boolean;
  sidebarOpen: boolean;
  toggleDarkMode: () => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  darkMode: false,
  sidebarOpen: true,
  toggleDarkMode: () =>
    set((s) => {
      const next = !s.darkMode;
      document.documentElement.classList.toggle('dark', next);
      return { darkMode: next };
    }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
