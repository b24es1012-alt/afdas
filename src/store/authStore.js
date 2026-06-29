import { create } from 'zustand';
import { STORAGE_KEYS } from '../utils/constants';

export const useAuthStore = create((set, get) => ({
  // State
  user: JSON.parse(localStorage.getItem(STORAGE_KEYS.USER)) || null,
  accessToken: localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) || null,
  refreshToken: localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN) || null,
  isAuthenticated: !!localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN),
  isLoading: false,
  error: null,

  // Actions
  setUser: (user) => {
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
    set({ user, isAuthenticated: true });
  },

  setAccessToken: (token) => {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, token);
    set({ accessToken: token, isAuthenticated: true });
  },

  setTokens: (accessToken, refreshToken) => {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
    set({ accessToken, refreshToken, isAuthenticated: true });
  },

  login: (user, accessToken, refreshToken) => {
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
    set({
      user,
      accessToken,
      refreshToken,
      isAuthenticated: true,
      error: null,
    });
  },

  logout: () => {
    localStorage.removeItem(STORAGE_KEYS.USER);
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      error: null,
    });
  },

  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),

  // Computed
  isAdmin: () => get().user?.role === 'admin',
  isResponder: () => ['admin', 'responder'].includes(get().user?.role),
}));
