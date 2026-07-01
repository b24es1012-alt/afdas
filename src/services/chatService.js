import api from '../config/axios';

const CHAT_ENDPOINT = '/chat';

/**
 * Chat service for AI flood assistant.
 * Supports session memory via session_id for multi-turn conversations.
 */
export const chatService = {
  /**
   * Send a message to the AI flood assistant.
   * @param {string} message - User's message
   * @param {object} context - Optional context { eventId, lat, lon, sessionId }
   * @returns {Promise<{success, response, category, vehicle_type, steps_executed, session_id, routes}>}
   */
  async sendMessage(message, context = {}) {
    const res = await api.post(CHAT_ENDPOINT, {
      message,
      session_id: context.sessionId || null,
      event_id: context.eventId || null,
      lat: context.lat || null,
      lon: context.lon || null,
    });
    return res.data;
  },

  /**
   * Get session info (message count, TTL, etc.)
   * @param {string} sessionId
   */
  async getSessionInfo(sessionId) {
    const res = await api.get(`${CHAT_ENDPOINT}/session/${sessionId}`);
    return res.data;
  },

  /**
   * Get conversation history for a session.
   * @param {string} sessionId
   * @param {number} lastN - Number of recent messages to fetch
   */
  async getSessionHistory(sessionId, lastN = 20) {
    const res = await api.get(`${CHAT_ENDPOINT}/session/${sessionId}/history`, {
      params: { last_n: lastN },
    });
    return res.data;
  },

  /**
   * Clear session (reset conversation memory).
   * @param {string} sessionId
   */
  async clearSession(sessionId) {
    const res = await api.delete(`${CHAT_ENDPOINT}/session/${sessionId}`);
    return res.data;
  },
};

export default chatService;
