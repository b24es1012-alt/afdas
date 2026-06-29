import { create } from 'zustand';

export const useNavigationStore = create((set, get) => ({
  // State
  origin: null, // { lat, lon, name }
  destination: null, // { lat, lon, name }
  routes: [], // Array of route results from API
  selectedRouteIndex: 0,
  isNavigating: false,
  isCalculating: false,
  currentWaypointIndex: 0,
  routeHistory: [],
  error: null,

  // Actions
  setOrigin: (origin) => set({ origin, routes: [], error: null }),

  setDestination: (destination) => set({ destination, routes: [], error: null }),

  setRoutes: (routes) =>
    set({ routes, selectedRouteIndex: 0, isCalculating: false, error: null }),

  selectRoute: (index) => set({ selectedRouteIndex: index }),

  startNavigation: () =>
    set({ isNavigating: true, currentWaypointIndex: 0 }),

  stopNavigation: () =>
    set({ isNavigating: false, currentWaypointIndex: 0 }),

  setCalculating: (isCalculating) => set({ isCalculating }),

  updateWaypointIndex: (index) => set({ currentWaypointIndex: index }),

  setError: (error) => set({ error, isCalculating: false }),

  clearError: () => set({ error: null }),

  clearRoute: () =>
    set({
      routes: [],
      selectedRouteIndex: 0,
      isNavigating: false,
      currentWaypointIndex: 0,
      error: null,
    }),

  addToHistory: (route) =>
    set((state) => ({
      routeHistory: [route, ...state.routeHistory].slice(0, 50),
    })),

  // Computed helpers
  getSelectedRoute: () => {
    const { routes, selectedRouteIndex } = get();
    return routes[selectedRouteIndex] || null;
  },

  hasRoute: () => get().routes.length > 0,

  getRouteCoordinates: () => {
    const route = get().getSelectedRoute();
    if (!route) return [];
    return route.coordinates.map(([lat, lon]) => [lat, lon]);
  },
}));
