import api from '../config/axios';
import { ENDPOINTS } from '../utils/constants';

export const navigationService = {
  /**
   * Calculate flood-safe routes.
   * @param {object} params - { start_lat, start_lon, end_lat, end_lon, vehicle_type, k, place }
   */
  async calculateRoute(params) {
    const res = await api.post(ENDPOINTS.ROUTE, {
      start_lat: params.startLat,
      start_lon: params.startLon,
      end_lat: params.endLat,
      end_lon: params.endLon,
      vehicle_type: params.vehicleType || 'car',
      k: params.k || 3,
      place: params.place || 'New Delhi, India',
      event_id: params.eventId || null,
    });
    return res.data;
  },

  /**
   * Request rerouting from current position.
   */
  async reroute(params) {
    const res = await api.post(ENDPOINTS.REROUTE, {
      current_lat: params.currentLat,
      current_lon: params.currentLon,
      end_lat: params.endLat,
      end_lon: params.endLon,
      vehicle_type: params.vehicleType || 'car',
      place: params.place || 'New Delhi, India',
      event_id: params.eventId || null,
    });
    return res.data;
  },

  /**
   * Get route history.
   */
  async getHistory(limit = 20) {
    const res = await api.get(ENDPOINTS.ROUTE_HISTORY, { params: { limit } });
    return res.data;
  },
};

export default navigationService;
