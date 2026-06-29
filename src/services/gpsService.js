import { getSocket } from '../config/socket';
import { WS_EVENTS } from '../utils/constants';

export const gpsService = {
  /**
   * Send GPS update to backend via WebSocket.
   */
  sendUpdate(lat, lon, accuracy, speed, heading) {
    const socket = getSocket();
    if (!socket?.connected) return;

    socket.emit(WS_EVENTS.GPS_UPDATE, {
      latitude: lat,
      longitude: lon,
      accuracy_m: accuracy,
      speed_kmh: speed,
      bearing: heading,
      timestamp: new Date().toISOString(),
    });
  },

  /**
   * Subscribe to reroute notifications.
   */
  onRerouteNeeded(callback) {
    const socket = getSocket();
    if (!socket) return () => {};

    socket.on(WS_EVENTS.REROUTE_NEEDED, callback);
    return () => socket.off(WS_EVENTS.REROUTE_NEEDED, callback);
  },

  /**
   * Subscribe to flood alerts.
   */
  onFloodAlert(callback) {
    const socket = getSocket();
    if (!socket) return () => {};

    socket.on(WS_EVENTS.FLOOD_ALERT, callback);
    return () => socket.off(WS_EVENTS.FLOOD_ALERT, callback);
  },

  /**
   * Subscribe to road closure events.
   */
  onRoadClosed(callback) {
    const socket = getSocket();
    if (!socket) return () => {};

    socket.on(WS_EVENTS.ROAD_CLOSED, callback);
    return () => socket.off(WS_EVENTS.ROAD_CLOSED, callback);
  },
};

export default gpsService;
