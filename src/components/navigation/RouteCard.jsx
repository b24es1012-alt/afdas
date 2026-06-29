import { Clock, Route, AlertTriangle, Droplets } from 'lucide-react';
import { formatDistance, formatTime, formatRisk } from '../../utils/helpers';
import settings from '../../config/settings';

export default function RouteCard({ route, index, isSelected, onSelect }) {
  const riskLevel = route.risk_score <= 0.2 ? 'low' : route.risk_score <= 0.5 ? 'moderate' : 'high';
  const routeColor = settings.routeColors[index % settings.routeColors.length];

  return (
    <button
      onClick={() => onSelect(index)}
      className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
        isSelected
          ? 'border-primary-500 bg-primary-50 shadow-sm'
          : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: routeColor }}
          />
          <span className="text-sm font-semibold text-gray-800">
            Route {index + 1}
          </span>
        </div>
        <span
          className={`badge ${
            riskLevel === 'low'
              ? 'bg-green-100 text-green-700'
              : riskLevel === 'moderate'
              ? 'bg-orange-100 text-orange-700'
              : 'bg-red-100 text-red-700'
          }`}
        >
          {formatRisk(route.risk_score)} risk
        </span>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex items-center gap-1.5 text-gray-600">
          <Route className="w-3.5 h-3.5" />
          <span>{formatDistance(route.total_distance_m)}</span>
        </div>
        <div className="flex items-center gap-1.5 text-gray-600">
          <Clock className="w-3.5 h-3.5" />
          <span>{formatTime(route.estimated_time_s)}</span>
        </div>
        <div className="flex items-center gap-1.5 text-gray-600">
          <Droplets className="w-3.5 h-3.5" />
          <span>{route.flooded_segments} flooded</span>
        </div>
        <div className="flex items-center gap-1.5 text-gray-600">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>{route.max_flood_depth.toFixed(2)}m max</span>
        </div>
      </div>
    </button>
  );
}
