import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Droplets, MapPin, BarChart3, MessageCircle, Settings, LogOut } from 'lucide-react';
import { useState } from 'react';
import { useAuthStore } from '../../store/authStore';

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { isAuthenticated, user, logout } = useAuthStore();
  const location = useLocation();

  const navLinks = [
    { to: '/dashboard', label: 'Dashboard', icon: Droplets },
    { to: '/navigate', label: 'Navigate', icon: MapPin },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/chat', label: 'AI Chat', icon: MessageCircle },
  ];

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <Droplets className="w-8 h-8 text-primary-600" />
            <span className="text-xl font-bold text-gray-900">AFDAS</span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1">
            {isAuthenticated &&
              navLinks.map(({ to, label, icon: Icon }) => (
                <Link
                  key={to}
                  to={to}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive(to)
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              ))}
          </div>

          {/* Right side */}
          <div className="hidden md:flex items-center gap-3">
            {isAuthenticated ? (
              <>
                <Link to="/settings" className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100">
                  <Settings className="w-5 h-5" />
                </Link>
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                    <span className="text-sm font-medium text-primary-700">
                      {user?.full_name?.[0] || user?.email?.[0] || 'U'}
                    </span>
                  </div>
                  <button onClick={logout} className="p-2 text-gray-500 hover:text-red-600 rounded-lg hover:bg-red-50">
                    <LogOut className="w-5 h-5" />
                  </button>
                </div>
              </>
            ) : (
              <div className="flex gap-2">
                <Link to="/login" className="btn-secondary text-sm">Log In</Link>
                <Link to="/register" className="btn-primary text-sm">Sign Up</Link>
              </div>
            )}
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-gray-200 bg-white pb-4">
          <div className="px-4 pt-2 space-y-1">
            {isAuthenticated &&
              navLinks.map(({ to, label, icon: Icon }) => (
                <Link
                  key={to}
                  to={to}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium ${
                    isActive(to)
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {label}
                </Link>
              ))}
            {!isAuthenticated && (
              <>
                <Link to="/login" onClick={() => setMobileOpen(false)} className="block px-3 py-2.5 text-sm font-medium text-gray-600">Log In</Link>
                <Link to="/register" onClick={() => setMobileOpen(false)} className="block px-3 py-2.5 text-sm font-medium text-primary-600">Sign Up</Link>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
