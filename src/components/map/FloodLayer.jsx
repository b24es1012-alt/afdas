import { GeoJSON } from 'react-leaflet';
import settings from '../../config/settings';

export default function FloodLayer({ zones = [] }) {
  if (zones.length === 0) return null;

  // Convert zones to GeoJSON FeatureCollection
  const geojson = {
    type: 'FeatureCollection',
    features: zones.map((zone, idx) => ({
      type: 'Feature',
      id: zone.id || idx,
      properties: {
        max_depth: zone.max_depth || 1.0,
        avg_depth: zone.avg_depth || 0.5,
        area_km2: zone.area_km2 || 0,
      },
      geometry: zone.geometry || null,
    })).filter((f) => f.geometry !== null),
  };

  if (geojson.features.length === 0) return null;

  const getColor = (depth) => {
    if (depth > 1.0) return settings.floodColors.critical;
    if (depth > 0.6) return settings.floodColors.high;
    if (depth > 0.3) return settings.floodColors.moderate;
    if (depth > 0.1) return settings.floodColors.low;
    return settings.floodColors.none;
  };

  const style = (feature) => ({
    fillColor: getColor(feature.properties.max_depth),
    color: '#2563eb',
    weight: 1,
    fillOpacity: 0.3,
    opacity: 0.6,
  });

  const onEachFeature = (feature, layer) => {
    const props = feature.properties;
    layer.bindPopup(`
      <div class="text-sm">
        <p class="font-semibold">Flood Zone</p>
        <p>Max Depth: ${props.max_depth?.toFixed(2) || 'N/A'} m</p>
        <p>Avg Depth: ${props.avg_depth?.toFixed(2) || 'N/A'} m</p>
        <p>Area: ${props.area_km2?.toFixed(3) || 'N/A'} km&sup2;</p>
      </div>
    `);
  };

  return (
    <GeoJSON key={Date.now()} data={geojson} style={style} onEachFeature={onEachFeature} />
  );
}
