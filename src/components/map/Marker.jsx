import { Marker as LeafletMarker, Popup } from 'react-leaflet';
import L from 'leaflet';

const defaultIcon = L.divIcon({
  className: 'custom-marker',
  html: '<div class="w-5 h-5 bg-primary-600 rounded-full border-2 border-white shadow-lg"></div>',
  iconSize: [20, 20],
  iconAnchor: [10, 10],
});

const icons = {
  default: defaultIcon,
  hospital: L.divIcon({
    className: 'custom-marker',
    html: '<div class="w-6 h-6 bg-red-500 rounded-full border-2 border-white shadow-lg flex items-center justify-center"><span class="text-white text-xs">H</span></div>',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  }),
  shelter: L.divIcon({
    className: 'custom-marker',
    html: '<div class="w-6 h-6 bg-green-500 rounded-full border-2 border-white shadow-lg flex items-center justify-center"><span class="text-white text-xs">S</span></div>',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  }),
  school: L.divIcon({
    className: 'custom-marker',
    html: '<div class="w-6 h-6 bg-yellow-500 rounded-full border-2 border-white shadow-lg flex items-center justify-center"><span class="text-white text-xs">E</span></div>',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  }),
};

export default function CustomMarker({ position, type = 'default', label, children }) {
  const icon = icons[type] || icons.default;

  return (
    <LeafletMarker position={position} icon={icon}>
      {(label || children) && (
        <Popup>
          {label && <span className="text-sm font-medium">{label}</span>}
          {children}
        </Popup>
      )}
    </LeafletMarker>
  );
}
