import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Theme } from '../../types';
import { RootState } from '../../store/store';

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
}

interface UIState {
  theme: Theme;
  toasts: Toast[];
  sidebarOpen: boolean;
  loading: {
    global: boolean;
    [key: string]: boolean;
  };
}

const initialState: UIState = {
  theme: 'system',
  toasts: [],
  sidebarOpen: false,
  loading: {
    global: false,
  },
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setTheme: (state, action: PayloadAction<Theme>) => {
      state.theme = action.payload;
      // Update document class for dark mode
      if (action.payload === 'dark') {
        document.documentElement.classList.add('dark');
      } else if (action.payload === 'light') {
        document.documentElement.classList.remove('dark');
      } else if (action.payload === 'system') {
        // Check system preference
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (prefersDark) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      }
    },
    
    addToast: (state, action: PayloadAction<Omit<Toast, 'id'>>) => {
      const id = crypto.randomUUID();
      state.toasts.push({
        id,
        ...action.payload,
        duration: action.payload.duration || 5000, // Default 5 seconds
      });
    },
    
    removeToast: (state, action: PayloadAction<string>) => {
      state.toasts = state.toasts.filter(toast => toast.id !== action.payload);
    },
    
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload;
    },
    
    setLoading: (state, action: PayloadAction<{ key: string; loading: boolean }>) => {
      const { key, loading } = action.payload;
      state.loading[key] = loading;
    },
    
    setGlobalLoading: (state, action: PayloadAction<boolean>) => {
      state.loading.global = action.payload;
    },
  },
});

// Export actions
export const {
  setTheme,
  addToast,
  removeToast,
  toggleSidebar,
  setSidebarOpen,
  setLoading,
  setGlobalLoading,
} = uiSlice.actions;

// Selectors
export const selectTheme = (state: RootState) => state.ui.theme;
export const selectToasts = (state: RootState) => state.ui.toasts;
export const selectSidebarOpen = (state: RootState) => state.ui.sidebarOpen;
export const selectLoading = (key: string) => (state: RootState) => state.ui.loading[key] || false;
export const selectGlobalLoading = (state: RootState) => state.ui.loading.global;

export default uiSlice.reducer;