import { useEffect, useCallback } from 'react';
import { useFloodStore } from '../store/floodStore';
import { useLocationStore } from '../store/locationStore';
import api from '../config/axios';
import { ENDPOINTS } from '../utils/constants';

/**
 * Hook that checks flood status at user's current location.
 */
export function useFloodStatus() {
  const { currentLocation } = useLocationStore();
  const {
    isInFloodZone,
    userFloodDepth,
    activeEvents,
    floodZones,
    isLoading,
    setUserFloodStatus,
    setActiveEvents,
    setFloodZones,
    setLoading,
    setError,
    getSeverity,
  } = useFloodStore();

  // Fetch active flood events on mount
  useEffect(() => {
    fetchActiveEvents();
  }, []);

  // Check flood depth when location changes
  useEffect(() => {
    if (currentLocation) {
      checkFloodAtLocation(currentLocation.lat, currentLocation.lon);
    }
  }, [currentLocation?.lat, currentLocation?.lon]);

  const fetchActiveEvents = useCallback(async () => {
    try {
      const res = await api.get(ENDPOINTS.FLOOD_ACTIVE);
      setActiveEvents(res.data);
    } catch (err) {
      console.error('Failed to fetch flood events:', err);
    }
  }, []);

  const checkFloodAtLocation = useCallback(async (lat, lon) => {
    try {
      setLoading(true);
      const res = await api.post(ENDPOINTS.FLOOD_DEPTH, { lat, lon });
      setUserFloodStatus(res.data.is_flooded, res.data.depth);
    } catch (err) {
      console.error('Flood check failed:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchFloodZones = useCallback(async (eventId) => {
    try {
      const res = await api.get(ENDPOINTS.FLOOD_ZONES, {
        params: { event_id: eventId },
      });
      setFloodZones(res.data.zones || []);
    } catch (err) {
      setError('Failed to load flood zones');
    }
  }, []);

  return {
    isInFloodZone,
    userFloodDepth,
    severity: getSeverity(),
    activeEvents,
    floodZones,
    isLoading,
    checkFloodAtLocation,
    fetchActiveEvents,
    fetchFloodZones,
  };
}

export default useFloodStatus;
