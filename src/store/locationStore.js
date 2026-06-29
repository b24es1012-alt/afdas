import { create } from 'zustand';

export const useLocationStore = create((set, get) => ({
  // State
  currentLocation: null, // { lat, lon, accuracy, timestamp }
  isTracking: false,
  watchId: null,
  permissionStatus: 'prompt', // 'granted', 'denied', 'prompt'
  error: null,

  // Actions
  setCurrentLocation: (location) => set({ currentLocation: location, error: null }),

  setTracking: (isTracking) => set({ isTracking }),

  setWatchId: (watchId) => set({ watchId }),

  setPermissionStatus: (status) => set({ permissionStatus: status }),

  setError: (error) => set({ error }),

  startTracking: () => {
    if (!navigator.geolocation) {
      set({ error: 'Geolocation not supported by this browser' });
      return;
    }

    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        set({
          currentLocation: {
            lat: position.coords.latitude,
            lon: position.coords.longitude,
            accuracy: position.coords.accuracy,
            speed: position.coords.speed,
            heading: position.coords.heading,
            timestamp: position.timestamp,
          },
          isTracking: true,
          permissionStatus: 'granted',
          error: null,
        });
      },
      (err) => {
        const errorMessages = {
          1: 'Location permission denied',
          2: 'Location unavailable',
          3: 'Location request timed out',
        };
        set({
          error: errorMessages[err.code] || 'Unknown location error',
          permissionStatus: err.code === 1 ? 'denied' : get().permissionStatus,
        });
      },
      {
        enableHighAccuracy: true,
        maximumAge: 10000,
        timeout: 15000,
      }
    );

    set({ watchId, isTracking: true });
  },

  stopTracking: () => {
    const { watchId } = get();
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
    }
    set({ isTracking: false, watchId: null });
  },

  // Get current position once (Promise-based)
  getCurrentPosition: () => {
    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const location = {
            lat: position.coords.latitude,
            lon: position.coords.longitude,
            accuracy: position.coords.accuracy,
            timestamp: position.timestamp,
          };
          set({ currentLocation: location, permissionStatus: 'granted' });
          resolve(location);
        },
        (err) => {
          set({ error: err.message });
          reject(err);
        },
        { enableHighAccuracy: true, timeout: 15000 }
      );
    });
  },
}));
