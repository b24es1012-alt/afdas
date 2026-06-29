import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, MapPin, BarChart3, MessageCircle,
  History, Settings, Shield, Droplets,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

const menuItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/navigate', label: 'Navigate', icon: MapPin },
  { to: '/chat', label: 'AI Assistant', icon: MessageCircle },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/history', label: 'History', icon: History },
  { to: '/settings', label: 'Settings', icon: Settings },
];

const adminItems = [
  { to: '/admin', label: 'Admin Panel', icon: Shield },
];

export default function Sidebar() {
  const location = useLocation();
  const { isAdmin } = useAuthStore();

  const isActive = (path) => location.pathname === path;

  return (
    <aside className="hidden lg:flex flex-col w-64 bg-white border-r border-gray-200 min-h-screen">
      {/* Logo */}
      <div className="p-6 border-b border-gray-100">
        <Link to="/dashboard" className="flex items-center gap-2">
          <Droplets className="w-8 h-8 text-primary-600" />
          <div>
            <h1 className="text-lg font-bold text-gray-900">AFDAS</h1>
            <p className="text-xs text-gray-500">Flood Assistance</p>
          </div>
        </Link>
      </div>

      {/* Menu */}
      <nav className="flex-1 p-4 space-y-1">
        {menuItems.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              isActive(to)
                ? 'bg-primary-50 text-primary-700 border-l-4 border-primary-600 -ml-1 pl-4'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`}
          >
            <Icon className="w-5 h-5" />
            {label}
          </Link>
        ))}

        {isAdmin() && (
          <>
            <div className="pt-4 pb-2">
              <p className="px-3 text-xs font-semibold text-gray-400 uppercase">Admin</p>
            </div>
            {adminItems.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive(to)
                    ? 'bg-red-50 text-red-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <Icon className="w-5 h-5" />
                {label}
              </Link>
            ))}
          </>
        )}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-100">
        <p className="text-xs text-gray-400 text-center">AFDAS v1.0</p>
      </div>
    </aside>
  );
}
