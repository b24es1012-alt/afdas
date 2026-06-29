import { Navigation, Clock, Route, AlertTriangle, Play, Square } from 'lucide-react';
import { formatDistance, formatTime } from '../../utils/helpers';

export default function RouteSummary({ route, isNavigating, onStart, onStop }) {
  if (!route) return null;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
          <Navigation className="w-5 h-5 text-primary-600" />
          Route Summary
        </h3>
        {!isNavigating ? (
          <button onClick={onStart} className="btn-primary flex items-center gap-2 text-sm">
            <Play className="w-4 h-4" />
            Start
          </button>
        ) : (
          <button onClick={onStop} className="btn-danger flex items-center gap-2 text-sm">
            <Square className="w-4 h-4" />
            Stop
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <Route className="w-5 h-5 text-gray-400 mx-auto mb-1" />
          <p className="text-lg font-bold text-gray-800">{formatDistance(route.total_distance_m)}</p>
          <p className="text-xs text-gray-500">Distance</p>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <Clock className="w-5 h-5 text-gray-400 mx-auto mb-1" />
          <p className="text-lg font-bold text-gray-800">{formatTime(route.estimated_time_s)}</p>
          <p className="text-xs text-gray-500">Est. Time</p>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <AlertTriangle className="w-5 h-5 text-gray-400 mx-auto mb-1" />
          <p className="text-lg font-bold text-gray-800">{Math.round(route.risk_score * 100)}%</p>
          <p className="text-xs text-gray-500">Risk Score</p>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <Navigation className="w-5 h-5 text-gray-400 mx-auto mb-1" />
          <p className="text-lg font-bold text-gray-800">{route.flooded_segments}</p>
          <p className="text-xs text-gray-500">Flooded Segs</p>
        </div>
      </div>
    </div>
  );
}
