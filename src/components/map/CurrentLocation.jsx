import { Circle, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { useLocationStore } from '../../store/locationStore';

const locationIcon = L.divIcon({
  className: 'current-location-marker',
  html: '<div class="w-4 h-4 bg-blue-500 rounded-full border-3 border-white shadow-lg animate-pulse"></div>',
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

export default function CurrentLocation() {
  const { currentLocation } = useLocationStore();

  if (!currentLocation) return null;

  const position = [currentLocation.lat, currentLocation.lon];
  const accuracy = currentLocation.accuracy || 50;

  return (
    <>
      {/* Accuracy circle */}
      <Circle
        center={position}
        radius={accuracy}
        pathOptions={{
          color: '#3b82f6',
          fillColor: '#3b82f6',
          fillOpacity: 0.1,
          weight: 1,
        }}
      />

      {/* Location dot */}
      <Marker position={position} icon={locationIcon}>
        <Popup>
          <div className="text-sm">
            <p className="font-semibold">Your Location</p>
            <p>{currentLocation.lat.toFixed(5)}, {currentLocation.lon.toFixed(5)}</p>
            <p className="text-gray-500">Accuracy: {Math.round(accuracy)}m</p>
          </div>
        </Popup>
      </Marker>
    </>
  );
}
