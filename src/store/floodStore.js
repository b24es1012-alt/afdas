import { create } from 'zustand';

export const useFloodStore = create((set, get) => ({
  // State
  activeEvents: [], // Active flood events from backend
  currentEventId: null,
  floodZones: [], // GeoJSON flood polygons for map display
  isInFloodZone: false, // Is user currently inside a flood zone
  userFloodDepth: 0,
  isLoading: false,
  lastChecked: null,
  error: null,

  // Actions
  setActiveEvents: (events) => set({ activeEvents: events }),

  setCurrentEvent: (eventId) => set({ currentEventId: eventId }),

  setFloodZones: (zones) => set({ floodZones: zones }),

  setUserFloodStatus: (isFlooded, depth = 0) =>
    set({
      isInFloodZone: isFlooded,
      userFloodDepth: depth,
      lastChecked: new Date().toISOString(),
    }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  clearError: () => set({ error: null }),

  // Computed
  hasActiveFlood: () => get().activeEvents.length > 0,

  getCurrentEvent: () => {
    const { activeEvents, currentEventId } = get();
    return activeEvents.find((e) => e.id === currentEventId) || activeEvents[0] || null;
  },

  getSeverity: () => {
    const depth = get().userFloodDepth;
    if (depth <= 0) return 'none';
    if (depth <= 0.1) return 'low';
    if (depth <= 0.3) return 'moderate';
    if (depth <= 0.6) return 'high';
    return 'critical';
  },
}));
