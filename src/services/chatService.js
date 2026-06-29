import api from '../config/axios';
import { ENDPOINTS } from '../utils/constants';

export const chatService = {
  /**
   * Send a message to the AI flood assistant.
   * @param {string} message - User's message
   * @param {object} context - Optional context { event_id, lat, lon }
   */
  async sendMessage(message, context = {}) {
    const res = await api.post(ENDPOINTS.CHAT, {
      message,
      event_id: context.eventId || null,
      lat: context.lat || null,
      lon: context.lon || null,
    });
    return res.data;
  },
};

export default chatService;
