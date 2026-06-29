import { useCallback, useState } from 'react';
import { useNavigationStore } from '../store/navigationStore';
import { useVehicleStore } from '../store/vehicleStore';
import { navigationService } from '../services/navigationService';
import { toast } from 'react-toastify';

/**
 * Hook for route calculation and management.
 */
export function useRoute() {
  const {
    origin,
    destination,
    routes,
    selectedRouteIndex,
    isCalculating,
    isNavigating,
    setOrigin,
    setDestination,
    setRoutes,
    selectRoute,
    startNavigation,
    stopNavigation,
    setCalculating,
    setError,
    clearRoute,
    getSelectedRoute,
    addToHistory,
  } = useNavigationStore();

  const { selectedVehicle } = useVehicleStore();

  const calculateRoute = useCallback(async () => {
    if (!origin || !destination) {
      toast.error('Please set both origin and destination');
      return;
    }

    setCalculating(true);

    try {
      const result = await navigationService.calculateRoute({
        startLat: origin.lat,
        startLon: origin.lon,
        endLat: destination.lat,
        endLon: destination.lon,
        vehicleType: selectedVehicle,
        k: 3,
      });

      if (result.success && result.routes.length > 0) {
        setRoutes(result.routes);
        toast.success(`Found ${result.routes.length} route(s)`);
      } else {
        setError(result.message || 'No routes found');
        toast.error(result.message || 'No passable routes found');
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Route calculation failed';
      setError(msg);
      toast.error(msg);
    }
  }, [origin, destination, selectedVehicle]);

  const reroute = useCallback(
    async (currentLat, currentLon) => {
      if (!destination) return;

      try {
        const result = await navigationService.reroute({
          currentLat,
          currentLon,
          endLat: destination.lat,
          endLon: destination.lon,
          vehicleType: selectedVehicle,
        });

        if (result.success && result.routes.length > 0) {
          setRoutes(result.routes);
          toast.info('Route updated');
        }
      } catch (err) {
        toast.error('Rerouting failed');
      }
    },
    [destination, selectedVehicle]
  );

  return {
    origin,
    destination,
    routes,
    selectedRouteIndex,
    selectedRoute: getSelectedRoute(),
    isCalculating,
    isNavigating,
    setOrigin,
    setDestination,
    calculateRoute,
    reroute,
    selectRoute,
    startNavigation,
    stopNavigation,
    clearRoute,
  };
}

export default useRoute;
