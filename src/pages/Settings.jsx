import { useSettingsStore } from '../store/settingsStore';
import { Settings as SettingsIcon, Map, Bell, Globe } from 'lucide-react';

export default function Settings() {
  const { showFloodLayer, showRouteLayer, showAmenities, gpsTracking, notifications, soundAlerts, routeAlternatives, updateSetting, resetSettings } = useSettingsStore();

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
        <SettingsIcon className="w-6 h-6" />
        Settings
      </h1>

      {/* Map Settings */}
      <div className="card">
        <h3 className="font-semibold text-gray-800 flex items-center gap-2 mb-4">
          <Map className="w-4 h-4" /> Map Settings
        </h3>
        <div className="space-y-3">
          <Toggle label="Show flood overlay" checked={showFloodLayer} onChange={(v) => updateSetting('showFloodLayer', v)} />
          <Toggle label="Show route layer" checked={showRouteLayer} onChange={(v) => updateSetting('showRouteLayer', v)} />
          <Toggle label="Show amenities (hospitals, shelters)" checked={showAmenities} onChange={(v) => updateSetting('showAmenities', v)} />
        </div>
      </div>

      {/* Navigation */}
      <div className="card">
        <h3 className="font-semibold text-gray-800 flex items-center gap-2 mb-4">
          <Globe className="w-4 h-4" /> Navigation
        </h3>
        <div className="space-y-3">
          <Toggle label="Live GPS tracking" checked={gpsTracking} onChange={(v) => updateSetting('gpsTracking', v)} />
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700">Route alternatives</span>
            <select value={routeAlternatives} onChange={(e) => updateSetting('routeAlternatives', Number(e.target.value))} className="input-field w-20 text-sm">
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
              <option value={5}>5</option>
            </select>
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="card">
        <h3 className="font-semibold text-gray-800 flex items-center gap-2 mb-4">
          <Bell className="w-4 h-4" /> Notifications
        </h3>
        <div className="space-y-3">
          <Toggle label="Push notifications" checked={notifications} onChange={(v) => updateSetting('notifications', v)} />
          <Toggle label="Sound alerts" checked={soundAlerts} onChange={(v) => updateSetting('soundAlerts', v)} />
        </div>
      </div>

      <button onClick={resetSettings} className="btn-secondary w-full">Reset to Defaults</button>
    </div>
  );
}

function Toggle({ label, checked, onChange }) {
  return (
    <label className="flex items-center justify-between cursor-pointer">
      <span className="text-sm text-gray-700">{label}</span>
      <div className={`w-10 h-5 rounded-full transition-colors ${checked ? 'bg-primary-600' : 'bg-gray-300'} relative`} onClick={() => onChange(!checked)}>
        <div className={`w-4 h-4 bg-white rounded-full shadow-sm absolute top-0.5 transition-transform ${checked ? 'translate-x-5' : 'translate-x-0.5'}`} />
      </div>
    </label>
  );
}
