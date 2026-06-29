import { Routes, Route } from 'react-router-dom';

import MainLayout from '../layouts/MainLayout';
import DashboardLayout from '../layouts/DashboardLayout';
import AdminLayout from '../layouts/AdminLayout';
import PrivateRoute from './PrivateRoute';
import AdminRoute from './AdminRoute';

import Landing from '../pages/Landing';
import Login from '../pages/Login';
import Register from '../pages/Register';
import Dashboard from '../pages/Dashboard';
import Navigation from '../pages/Navigation';
import Analytics from '../pages/Analytics';
import History from '../pages/History';
import Settings from '../pages/Settings';
import Admin from '../pages/Admin';
import NotFound from '../pages/NotFound';
import ChatWindow from '../components/chat/ChatWindow';

export default function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route element={<MainLayout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      {/* Protected routes */}
      <Route element={<PrivateRoute><DashboardLayout /></PrivateRoute>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/navigate" element={<Navigation />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/history" element={<History />} />
        <Route path="/settings" element={<Settings />} />
      </Route>

      {/* Admin routes */}
      <Route element={<AdminRoute><AdminLayout /></AdminRoute>}>
        <Route path="/admin" element={<Admin />} />
      </Route>

      {/* 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

// Inline chat page wrapper
function ChatPage() {
  return (
    <div className="h-[calc(100vh-8rem)]">
      <ChatWindow />
    </div>
  );
}
