import { MapContainer, TileLayer, useMapEvents } from 'react-leaflet';
import settings from '../../config/settings';
import CurrentLocation from './CurrentLocation';
import FloodLayer from './FloodLayer';
import RouteLayer from './RouteLayer';
import Legend from './Legend';

export default function MapView({
  center,
  zoom,
  floodZones = [],
  routes = [],
  selectedRouteIndex = 0,
  onMapClick,
  children,
  className = 'h-[500px]',
}) {
  const mapCenter = center || settings.map.center;
  const mapZoom = zoom || settings.map.zoom;

  return (
    <div className={`relative rounded-xl overflow-hidden shadow-sm border border-gray-200 ${className}`}>
      <MapContainer
        center={mapCenter}
        zoom={mapZoom}
        maxZoom={settings.map.maxZoom}
        minZoom={settings.map.minZoom}
        className="w-full h-full z-0"
        scrollWheelZoom={true}
      >
        <TileLayer url={settings.map.tileUrl} attribution={settings.map.tileAttribution} />

        {/* Click handler */}
        {onMapClick && <MapClickHandler onClick={onMapClick} />}

        {/* Flood overlay */}
        {floodZones.length > 0 && <FloodLayer zones={floodZones} />}

        {/* Routes */}
        {routes.length > 0 && (
          <RouteLayer routes={routes} selectedIndex={selectedRouteIndex} />
        )}

        {/* Current location marker */}
        <CurrentLocation />

        {/* Custom children (extra markers, popups) */}
        {children}
      </MapContainer>

      {/* Legend overlay */}
      <Legend />
    </div>
  );
}

function MapClickHandler({ onClick }) {
  useMapEvents({
    click: (e) => {
      onClick({ lat: e.latlng.lat, lon: e.latlng.lng });
    },
  });
  return null;
}
