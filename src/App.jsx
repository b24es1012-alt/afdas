import { BrowserRouter } from 'react-router-dom';
import AppRoutes from './routes/AppRoutes';
import ToastProvider from './components/ui/Toast';
import { useWebSocket } from './hooks/useWebSocket';

export default function App() {
  // Initialize WebSocket for real-time updates
  useWebSocket();

  return (
    <BrowserRouter>
      <AppRoutes />
      <ToastProvider />
    </BrowserRouter>
  );
}
