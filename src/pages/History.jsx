import { useEffect, useState } from 'react';
import { Clock, MapPin, Car } from 'lucide-react';
import { navigationService } from '../services/navigationService';
import { formatDistance, formatTime, formatDate } from '../utils/helpers';

export default function History() {
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await navigationService.getHistory(20);
      setRoutes(data.routes || []);
    } catch (err) {
      console.error('History load error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Route History</h1>

      {routes.length === 0 ? (
        <div className="card text-center py-12">
          <Clock className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No route history yet</p>
          <p className="text-sm text-gray-400">Your navigation history will appear here</p>
        </div>
      ) : (
        <div className="space-y-3">
          {routes.map((route, idx) => (
            <div key={idx} className="card flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
                <MapPin className="w-5 h-5 text-primary-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-800">
                  ({route.start_lat?.toFixed(3)}, {route.start_lon?.toFixed(3)}) to ({route.end_lat?.toFixed(3)}, {route.end_lon?.toFixed(3)})
                </p>
                <div className="flex items-center gap-3 text-xs text-gray-500 mt-1">
                  <span className="flex items-center gap-1"><Car className="w-3 h-3" />{route.vehicle_type}</span>
                  <span>{formatDistance(route.total_distance_m)}</span>
                  <span>{formatTime(route.estimated_time_s)}</span>
                  <span>Risk: {Math.round(route.risk_score * 100)}%</span>
                </div>
              </div>
              <span className="text-xs text-gray-400">{formatDate(route.created_at)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
