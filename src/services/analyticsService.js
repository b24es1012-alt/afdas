import api from '../config/axios';
import { ENDPOINTS } from '../utils/constants';

export const analyticsService = {
  async getMostFloodedRoads(eventId = null, limit = 20) {
    const params = { limit };
    if (eventId) params.event_id = eventId;
    const res = await api.get(ENDPOINTS.ANALYTICS_ROADS, { params });
    return res.data;
  },

  async getMostAffectedBuildings(buildingType = null, limit = 20) {
    const params = { limit };
    if (buildingType) params.building_type = buildingType;
    const res = await api.get(ENDPOINTS.ANALYTICS_BUILDINGS, { params });
    return res.data;
  },

  async getEventSummary(eventId) {
    const res = await api.get(`${ENDPOINTS.ANALYTICS_EVENT_SUMMARY}/${eventId}/summary`);
    return res.data;
  },

  async getInfrastructureRisk(eventId) {
    const res = await api.get(`${ENDPOINTS.ANALYTICS_INFRASTRUCTURE}/${eventId}/infrastructure-risk`);
    return res.data;
  },
};

export default analyticsService;
