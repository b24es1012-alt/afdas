import { create } from 'zustand';
import settings from '../config/settings';

export const useVehicleStore = create((set, get) => ({
  // State
  selectedVehicle: settings.routing.defaultVehicle, // 'car' by default
  vehicleProfiles: settings.vehicles,

  // Actions
  setVehicle: (vehicleId) => set({ selectedVehicle: vehicleId }),

  // Computed
  getProfile: () => {
    const { selectedVehicle, vehicleProfiles } = get();
    return vehicleProfiles.find((v) => v.id === selectedVehicle) || vehicleProfiles[2]; // car fallback
  },

  getMaxDepth: () => {
    const profile = get().getProfile();
    return profile?.maxDepth || 0.3;
  },

  canPassDepth: (depth) => {
    return depth <= get().getMaxDepth();
  },
}));
