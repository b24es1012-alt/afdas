import { useEffect, useRef } from 'react';
import { connectSocket, disconnectSocket, getSocket } from '../config/socket';
import { useAuthStore } from '../store/authStore';
import { WS_EVENTS } from '../utils/constants';
import { toast } from 'react-toastify';

/**
 * Hook for WebSocket connection and event handling.
 */
export function useWebSocket(handlers = {}) {
  const { isAuthenticated } = useAuthStore();
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    if (!isAuthenticated) return;

    const socket = connectSocket();
    if (!socket) return;

    // Default flood alert handler
    socket.on(WS_EVENTS.FLOOD_ALERT, (data) => {
      toast.warning(`Flood Alert: ${data.title || 'New flood detected'}`, {
        autoClose: 10000,
      });
      handlersRef.current.onFloodAlert?.(data);
    });

    // Reroute needed
    socket.on(WS_EVENTS.REROUTE_NEEDED, (data) => {
      toast.info('Route update: Road conditions changed', { autoClose: 8000 });
      handlersRef.current.onRerouteNeeded?.(data);
    });

    // Road closed
    socket.on(WS_EVENTS.ROAD_CLOSED, (data) => {
      toast.error(`Road Closed: ${data.road_name || 'Nearby road'}`, {
        autoClose: 10000,
      });
      handlersRef.current.onRoadClosed?.(data);
    });

    // Route update
    socket.on(WS_EVENTS.ROUTE_UPDATE, (data) => {
      handlersRef.current.onRouteUpdate?.(data);
    });

    return () => {
      socket.off(WS_EVENTS.FLOOD_ALERT);
      socket.off(WS_EVENTS.REROUTE_NEEDED);
      socket.off(WS_EVENTS.ROAD_CLOSED);
      socket.off(WS_EVENTS.ROUTE_UPDATE);
    };
  }, [isAuthenticated]);

  // Disconnect on unmount
  useEffect(() => {
    return () => disconnectSocket();
  }, []);

  return {
    socket: getSocket(),
    isConnected: getSocket()?.connected || false,
  };
}

export default useWebSocket;
