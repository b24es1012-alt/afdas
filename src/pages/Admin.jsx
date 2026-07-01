import { useEffect, useState } from 'react';
import { Shield, Database, Server, Cpu, RefreshCw, Users, CloudRain, Trash2, Play, Square, Download, AlertTriangle } from 'lucide-react';
import api from '../config/axios';

const API_URL = 'http://localhost:8000/api/v1';

export default function Admin() {
  const [activeTab, setActiveTab] = useState('floods');
  const [health, setHealth] = useState(null);

  useEffect(() => { checkHealth(); }, []);

  const checkHealth = async () => {
    try {
      // Health endpoint is at /health (no /api/v1 prefix)
      const baseUrl = import.meta.env.VITE_API_BASE_URL?.replace('/api/v1', '') || 'http://localhost:8000';
      const res = await fetch(`${baseUrl}/health`);
      const data = await res.json();
      setHealth(data);
    } catch (err) {
      setHealth({ status: 'error', error: err.message });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <Shield className="w-6 h-6 text-red-600" /> Admin Panel
        </h1>
        <div className="flex items-center gap-3">
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${health?.status === 'healthy' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            {health?.status?.toUpperCase() || 'LOADING'}
          </span>
          <button onClick={checkHealth} className="btn-secondary text-xs flex items-center gap-1">
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
        </div>
      </div>

      {/* System Health Bar */}
      <div className="grid grid-cols-3 gap-3">
        <HealthCard title="Server" status={health?.status} icon={Server} />
        <HealthCard title="PostgreSQL" status={health?.checks?.database?.status} icon={Database} />
        <HealthCard title="Redis" status={health?.checks?.redis?.status} icon={Cpu} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {[
          { id: 'floods', label: 'Flood Events', icon: CloudRain },
          { id: 'users', label: 'Users', icon: Users },
          { id: 'system', label: 'System', icon: Server },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-red-500 text-red-700'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'floods' && <FloodManagement />}
      {activeTab === 'users' && <UserManagement />}
      {activeTab === 'system' && <SystemControls health={health} onRefresh={checkHealth} />}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// FLOOD MANAGEMENT TAB
// ═══════════════════════════════════════════════════════════════════════════════

function FloodManagement() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [importForm, setImportForm] = useState({ activation_id: '', event_name: '', country: 'India', region: '' });
  const [importing, setImporting] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => { loadEvents(); }, []);

  const loadEvents = async () => {
    setLoading(true);
    try {
      const res = await api.get(`${API_URL}/flood/active`);
      setEvents(res.data || []);
    } catch (err) {
      console.error('Failed to load events:', err);
      setEvents([]);
    } finally { setLoading(false); }
  };

  const endFlood = async (eventId, eventName) => {
    if (!window.confirm(`End flood event "${eventName}"?\n\nThis will:\n- Mark it as inactive\n- Clear all cached graphs\n- Routes will no longer avoid these flooded areas`)) return;
    try {
      const res = await api.post(`${API_URL}/flood/events/${eventId}/end`, { reason: 'Admin ended via panel' });
      setMessage({ type: 'success', text: res.data.message });
      loadEvents();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to end flood' });
    }
  };

  const reactivateFlood = async (eventId, eventName) => {
    if (!window.confirm(`Reactivate flood "${eventName}"?\n\nRoutes will start avoiding flooded roads again.`)) return;
    try {
      const res = await api.post(`${API_URL}/flood/events/${eventId}/reactivate`);
      setMessage({ type: 'success', text: res.data.message });
      loadEvents();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to reactivate' });
    }
  };

  const importFlood = async (e) => {
    e.preventDefault();
    if (!importForm.activation_id.trim()) return;
    setImporting(true);
    setMessage(null);
    try {
      const res = await api.post(`${API_URL}/flood/download`, importForm);
      setMessage({ type: 'success', text: `Imported: ${res.data.message || res.data.status}. Event ID: ${res.data.event_id}` });
      setImportForm({ activation_id: '', event_name: '', country: 'India', region: '' });
      loadEvents();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Import failed' });
    } finally { setImporting(false); }
  };

  return (
    <div className="space-y-6">
      {/* Status message */}
      {message && (
        <div className={`p-3 rounded-lg text-sm ${message.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
          {message.text}
          <button onClick={() => setMessage(null)} className="ml-2 underline text-xs">dismiss</button>
        </div>
      )}

      {/* Import New Flood */}
      <div className="card p-4 border-l-4 border-blue-500">
        <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
          <Download className="w-4 h-4 text-blue-600" />
          Import Flood from Copernicus EMS
        </h3>
        <p className="text-xs text-gray-500 mb-3">
          Enter a Copernicus activation ID (e.g., EMSR838) to download flood shapefiles.
          The system also auto-polls for new activations every 5 minutes.
        </p>
        <form onSubmit={importFlood} className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input
            type="text"
            value={importForm.activation_id}
            onChange={(e) => setImportForm({ ...importForm, activation_id: e.target.value.toUpperCase() })}
            placeholder="EMSR838"
            className="input-field text-sm"
            required
          />
          <input
            type="text"
            value={importForm.event_name}
            onChange={(e) => setImportForm({ ...importForm, event_name: e.target.value })}
            placeholder="Event name (optional)"
            className="input-field text-sm"
          />
          <input
            type="text"
            value={importForm.region}
            onChange={(e) => setImportForm({ ...importForm, region: e.target.value })}
            placeholder="Region (e.g., Punjab)"
            className="input-field text-sm"
          />
          <button type="submit" disabled={importing} className="btn-primary text-sm flex items-center justify-center gap-2">
            {importing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            {importing ? 'Importing...' : 'Import'}
          </button>
        </form>
      </div>

      {/* Active Flood Events */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            <CloudRain className="w-4 h-4 text-red-500" />
            Active Flood Events ({events.length})
          </h3>
          <button onClick={loadEvents} className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1">
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-gray-500">Loading...</p>
        ) : events.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <CloudRain className="w-10 h-10 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No active flood events</p>
            <p className="text-xs mt-1">Import one above or wait for auto-discovery</p>
          </div>
        ) : (
          <div className="space-y-3">
            {events.map((event) => (
              <div key={event.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                <div>
                  <p className="font-medium text-sm text-gray-800">{event.event_name}</p>
                  <p className="text-xs text-gray-500">
                    {event.activation_id} | {event.region}, {event.country} | Since: {event.start_date?.split('T')[0] || 'Unknown'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${event.is_active ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'}`}>
                    {event.is_active ? 'ACTIVE' : 'ENDED'}
                  </span>
                  {event.is_active ? (
                    <button
                      onClick={() => endFlood(event.id, event.event_name)}
                      className="text-xs px-3 py-1.5 bg-orange-500 text-white rounded hover:bg-orange-600 flex items-center gap-1"
                    >
                      <Square className="w-3 h-3" /> End Flood
                    </button>
                  ) : (
                    <button
                      onClick={() => reactivateFlood(event.id, event.event_name)}
                      className="text-xs px-3 py-1.5 bg-green-500 text-white rounded hover:bg-green-600 flex items-center gap-1"
                    >
                      <Play className="w-3 h-3" /> Reactivate
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Auto-polling status */}
      <div className="card p-3 bg-blue-50/50 border-blue-200">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <p className="text-xs text-blue-700">
            <strong>Auto-poller active:</strong> Checking Copernicus EMS for new India flood activations every 5 minutes.
            New floods are imported automatically.
          </p>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// USER MANAGEMENT TAB
// ═══════════════════════════════════════════════════════════════════════════════

function UserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => { loadUsers(); }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const res = await api.get(`${API_URL}/auth/users`);
      setUsers(res.data.users || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load users');
    } finally { setLoading(false); }
  };

  const getRoleBadge = (role) => {
    const colors = {
      admin: 'bg-red-100 text-red-700',
      responder: 'bg-blue-100 text-blue-700',
      user: 'bg-gray-100 text-gray-600',
    };
    return (
      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${colors[role] || colors.user}`}>
        {role.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-800 flex items-center gap-2">
          <Users className="w-4 h-4" />
          Registered Users ({users.length})
        </h3>
        <button onClick={loadUsers} className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>

      {error && <div className="bg-red-50 text-red-700 p-3 rounded text-sm">{error}</div>}

      {loading ? (
        <p className="text-sm text-gray-500">Loading users...</p>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-xs">
              <tr>
                <th className="px-4 py-2 text-left">ID</th>
                <th className="px-4 py-2 text-left">Email</th>
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Role</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Last Login</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-500">{user.id}</td>
                  <td className="px-4 py-2 font-medium text-gray-800">{user.email}</td>
                  <td className="px-4 py-2 text-gray-600">{user.full_name || '-'}</td>
                  <td className="px-4 py-2">{getRoleBadge(user.role)}</td>
                  <td className="px-4 py-2">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {user.is_active ? 'ACTIVE' : 'DISABLED'}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-500 text-xs">
                    {user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {users.length === 0 && (
            <p className="text-center py-6 text-gray-400 text-sm">No users found</p>
          )}
        </div>
      )}

      <div className="card p-3 bg-yellow-50/50 border-yellow-200">
        <p className="text-xs text-yellow-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          <span>To promote a user to admin, run: <code className="bg-yellow-100 px-1 rounded">UPDATE users SET role = 'admin' WHERE email = '...';</code> in PostgreSQL.</span>
        </p>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SYSTEM CONTROLS TAB
// ═══════════════════════════════════════════════════════════════════════════════

function SystemControls({ health, onRefresh }) {
  const [clearing, setClearing] = useState(false);
  const [message, setMessage] = useState(null);

  const clearCache = async () => {
    if (!window.confirm('Clear ALL cached graphs?\n\nNext route requests will re-download road networks (slower first request).')) return;
    setClearing(true);
    try {
      // There's no dedicated cache clear endpoint, but we can call health which triggers info
      // For now we'll note this is a TODO
      setMessage({ type: 'info', text: 'Cache clear: Use Redis CLI "FLUSHDB" or end/reactivate a flood event (auto-clears cache).' });
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to clear cache' });
    } finally { setClearing(false); }
  };

  return (
    <div className="space-y-6">
      {message && (
        <div className={`p-3 rounded text-sm ${message.type === 'success' ? 'bg-green-50 text-green-700' : message.type === 'error' ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700'}`}>
          {message.text}
        </div>
      )}

      {/* System Health Details */}
      <div className="card p-4">
        <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Server className="w-4 h-4" /> System Health
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-gray-500 uppercase">Database</h4>
            <InfoRow label="Status" value={health?.checks?.database?.status || 'Unknown'} />
            <InfoRow label="PostGIS" value={health?.checks?.database?.postgis_version || 'N/A'} />
            <InfoRow label="Pool Size" value={health?.checks?.database?.pool_size || 'N/A'} />
          </div>
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-gray-500 uppercase">Redis Cache</h4>
            <InfoRow label="Status" value={health?.checks?.redis?.status || 'Unknown'} />
            <InfoRow label="Memory" value={health?.checks?.redis?.used_memory || 'N/A'} />
            <InfoRow label="Clients" value={health?.checks?.redis?.connected_clients || 'N/A'} />
          </div>
        </div>
      </div>

      {/* Cache Management */}
      <div className="card p-4">
        <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
          <Trash2 className="w-4 h-4 text-red-500" /> Cache Management
        </h3>
        <p className="text-xs text-gray-500 mb-3">
          Graph cache is automatically cleared when flood events are ended or new data is imported.
          Manual clear forces all cities to re-download on next route request.
        </p>
        <button
          onClick={clearCache}
          disabled={clearing}
          className="px-4 py-2 bg-red-500 text-white text-sm rounded hover:bg-red-600 disabled:opacity-50 flex items-center gap-2"
        >
          <Trash2 className="w-4 h-4" />
          {clearing ? 'Clearing...' : 'Clear All Graph Cache'}
        </button>
      </div>

      {/* Configuration Info */}
      <div className="card p-4">
        <h3 className="font-semibold text-gray-800 mb-3">Configuration</h3>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <InfoRow label="Copernicus Poll Interval" value="5 minutes" />
          <InfoRow label="Watch Countries" value="India" />
          <InfoRow label="Auto Import" value="Enabled" />
          <InfoRow label="Graph Cache TTL" value="24 hours" />
          <InfoRow label="Session Memory TTL" value="1 hour" />
          <InfoRow label="Rate Limit (general)" value="60 req/min" />
          <InfoRow label="Rate Limit (auth)" value="5 req/5min" />
          <InfoRow label="Login Lockout" value="5 attempts → 15 min" />
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SHARED COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

function HealthCard({ title, status, icon: Icon }) {
  const isHealthy = status === 'healthy';
  return (
    <div className={`p-3 rounded-lg border ${isHealthy ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
      <div className="flex items-center gap-2">
        <Icon className={`w-4 h-4 ${isHealthy ? 'text-green-600' : 'text-red-600'}`} />
        <span className="text-sm font-medium text-gray-700">{title}</span>
      </div>
      <p className={`text-xs mt-1 ${isHealthy ? 'text-green-600' : 'text-red-600'}`}>
        {status?.toUpperCase() || 'UNKNOWN'}
      </p>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="flex justify-between items-center py-1 border-b border-gray-50">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-700">{value}</span>
    </div>
  );
}
