import { Polyline, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import settings from '../../config/settings';

const startIcon = L.divIcon({
  className: 'custom-marker',
  html: '<div class="w-6 h-6 bg-green-500 rounded-full border-2 border-white shadow-lg flex items-center justify-center"><span class="text-white text-xs font-bold">A</span></div>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

const endIcon = L.divIcon({
  className: 'custom-marker',
  html: '<div class="w-6 h-6 bg-red-500 rounded-full border-2 border-white shadow-lg flex items-center justify-center"><span class="text-white text-xs font-bold">B</span></div>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

export default function RouteLayer({ routes = [], selectedIndex = 0 }) {
  if (routes.length === 0) return null;

  return (
    <>
      {routes.map((route, idx) => {
        const coords = route.coordinates || [];
        if (coords.length === 0) return null;

        const isSelected = idx === selectedIndex;
        const color = settings.routeColors[idx % settings.routeColors.length];
        const weight = isSelected ? 6 : 4;
        const opacity = isSelected ? 1.0 : 0.5;
        const dashArray = isSelected ? null : '8 6';

        return (
          <Polyline
            key={idx}
            positions={coords}
            pathOptions={{
              color,
              weight,
              opacity,
              dashArray,
            }}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-semibold">Route {idx + 1}</p>
                <p>Distance: {(route.total_distance_m / 1000).toFixed(1)} km</p>
                <p>Time: {Math.round(route.estimated_time_s / 60)} min</p>
                <p>Risk: {Math.round(route.risk_score * 100)}%</p>
                <p>Flooded segments: {route.flooded_segments}</p>
              </div>
            </Popup>
          </Polyline>
        );
      })}

      {/* Start marker */}
      {routes[selectedIndex]?.coordinates?.[0] && (
        <Marker position={routes[selectedIndex].coordinates[0]} icon={startIcon}>
          <Popup>Start</Popup>
        </Marker>
      )}

      {/* End marker */}
      {routes[selectedIndex]?.coordinates?.length > 0 && (
        <Marker
          position={routes[selectedIndex].coordinates[routes[selectedIndex].coordinates.length - 1]}
          icon={endIcon}
        >
          <Popup>Destination</Popup>
        </Marker>
      )}
    </>
  );
}
