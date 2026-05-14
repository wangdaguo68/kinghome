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
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
