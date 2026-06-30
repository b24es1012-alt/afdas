import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { MapPin, AlertTriangle, Droplets, Building2, Navigation, Activity } from 'lucide-react';
import MapView from '../components/map/MapView';
import StatisticsCard from '../components/analytics/StatisticsCard';
import { useFloodStatus } from '../hooks/useFloodStatus';
import { useGPS } from '../hooks/useGPS';
import { getSeverityBg } from '../utils/helpers';

export default function Dashboard() {
  const { location, requestPosition } = useGPS(true);
  const { isInFloodZone, userFloodDepth, severity, activeEvents, floodZones, fetchFloodZones } = useFloodStatus();

  useEffect(() => {
    if (activeEvents.length > 0) {
      fetchFloodZones(activeEvents[0].id);
    }
  }, [activeEvents]);

  return (
    <div className="space-y-6">
      {/* Flood Warning Banner */}
      {isInFloodZone && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-red-800">You are in a flood zone!</h3>
            <p className="text-sm text-red-600 mt-1">
              Flood depth at your location: {userFloodDepth.toFixed(2)}m. Consider evacuating to higher ground.
            </p>
            <Link to="/navigate" className="inline-block mt-2 text-sm font-medium text-red-700 underline">
              Find safe route now
            </Link>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatisticsCard title="Active Floods" value={activeEvents.length} icon={Droplets} color="blue" />
        <StatisticsCard
          title="Your Status"
          value={isInFloodZone ? 'FLOODED' : 'SAFE'}
          icon={Activity}
          color={isInFloodZone ? 'red' : 'green'}
        />
        <StatisticsCard title="Flood Depth" value={`${userFloodDepth.toFixed(2)}m`} icon={Droplets} color="orange" />
        <StatisticsCard title="Severity" value={severity.toUpperCase()} icon={AlertTriangle} color={severity === 'none' ? 'green' : 'red'} />
      </div>

      {/* Map */}
      <div className="card p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Live Flood Map</h2>
          <span className={`badge ${getSeverityBg(severity)}`}>{severity}</span>
        </div>
        <MapView
          floodZones={floodZones}
          center={location ? [location.lat, location.lon] : undefined}
          zoom={location ? 15 : undefined}
          className="h-[400px]"
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link to="/navigate" className="card hover:shadow-md transition-shadow flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
            <Navigation className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-800">Navigate</h3>
            <p className="text-sm text-gray-500">Find flood-safe route</p>
          </div>
        </Link>
        <Link to="/chat" className="card hover:shadow-md transition-shadow flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
            <MapPin className="w-5 h-5 text-green-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-800">AI Assistant</h3>
            <p className="text-sm text-gray-500">Ask about flood conditions</p>
          </div>
        </Link>
        <Link to="/analytics" className="card hover:shadow-md transition-shadow flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
            <Building2 className="w-5 h-5 text-orange-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-800">Analytics</h3>
            <p className="text-sm text-gray-500">Flood impact reports</p>
          </div>
        </Link>
      </div>
    </div>
  );
}
