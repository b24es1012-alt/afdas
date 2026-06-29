import { create } from 'zustand';
import { STORAGE_KEYS } from '../utils/constants';

const defaultSettings = {
  theme: 'light',
  mapStyle: 'openstreetmap',
  showFloodLayer: true,
  showRouteLayer: true,
  showAmenities: true,
  gpsTracking: true,
  notifications: true,
  soundAlerts: true,
  language: 'en',
  routeAlternatives: 3,
};

const savedSettings = JSON.parse(localStorage.getItem(STORAGE_KEYS.SETTINGS)) || {};

export const useSettingsStore = create((set, get) => ({
  // State
  ...defaultSettings,
  ...savedSettings,

  // Actions
  updateSetting: (key, value) => {
    set({ [key]: value });
    const currentSettings = { ...get() };
    // Remove functions before saving
    delete currentSettings.updateSetting;
    delete currentSettings.resetSettings;
    localStorage.setItem(STORAGE_KEYS.SETTINGS, JSON.stringify(currentSettings));
  },

  resetSettings: () => {
    localStorage.removeItem(STORAGE_KEYS.SETTINGS);
    set(defaultSettings);
  },
}));
