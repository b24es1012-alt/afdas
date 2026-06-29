import { useEffect, useCallback } from 'react';
import { useLocationStore } from '../store/locationStore';
import { gpsService } from '../services/gpsService';

/**
 * Hook for GPS tracking with automatic backend sync.
 */
export function useGPS(autoStart = false) {
  const {
    currentLocation,
    isTracking,
    permissionStatus,
    error,
    startTracking,
    stopTracking,
    getCurrentPosition,
  } = useLocationStore();

  // Auto-start tracking if requested
  useEffect(() => {
    if (autoStart && !isTracking) {
      startTracking();
    }
    return () => {
      // Don't stop on unmount if navigating
    };
  }, [autoStart]);

  // Sync GPS to backend when tracking
  useEffect(() => {
    if (!currentLocation || !isTracking) return;

    gpsService.sendUpdate(
      currentLocation.lat,
      currentLocation.lon,
      currentLocation.accuracy,
      currentLocation.speed,
      currentLocation.heading
    );
  }, [currentLocation, isTracking]);

  const requestPosition = useCallback(async () => {
    try {
      return await getCurrentPosition();
    } catch (err) {
      console.error('GPS error:', err);
      return null;
    }
  }, [getCurrentPosition]);

  return {
    location: currentLocation,
    isTracking,
    permissionStatus,
    error,
    startTracking,
    stopTracking,
    requestPosition,
    lat: currentLocation?.lat,
    lon: currentLocation?.lon,
  };
}

export default useGPS;
