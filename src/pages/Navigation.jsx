import React, { useState } from 'react';
import { Loader2, RotateCcw, Navigation as NavIcon, Droplets } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Polyline, Popup, useMapEvents, GeoJSON, Polygon, useMap } from 'react-leaflet';
import L from 'leaflet';
import VehicleSelector from '../components/navigation/VehicleSelector';
import { useVehicleStore } from '../store/vehicleStore';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';
const ROUTE_COLORS = ['#9B30FF', '#FF6600', '#000000'];
const originIcon = L.divIcon({ className: '', html: '<div style="background:#22c55e;width:28px;height:28px;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:12px;">A</div>', iconSize: [28, 28], iconAnchor: [14, 14] });
const destIcon = L.divIcon({ className: '', html: '<div style="background:#ef4444;width:28px;height:28px;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:12px;">B</div>', iconSize: [28, 28], iconAnchor: [14, 14] });
const cityPresets = [{ name: 'Delhi', place: 'New Delhi, India' }, { name: 'Mumbai', place: 'Mumbai, India' }, { name: 'Chennai', place: 'Chennai, India' }, { name: 'Bangalore', place: 'Bangalore, India' }, { name: 'Kolkata', place: 'Kolkata, India' }, { name: 'Hyderabad', place: 'Hyderabad, India' }];
const mapCenters = { 'New Delhi, India': [28.63, 77.22], 'Mumbai, India': [19.07, 72.87], 'Chennai, India': [13.08, 80.27], 'Bangalore, India': [12.97, 77.59], 'Kolkata, India': [22.57, 88.36], 'Hyderabad, India': [17.38, 78.49] };

// City boundaries (approximate administrative polygons)
const cityBounds = {
  'New Delhi, India': [[28.40, 76.84], [28.88, 77.35]],
  'Mumbai, India': [[18.89, 72.77], [19.27, 72.98]],
  'Chennai, India': [[12.83, 80.10], [13.23, 80.33]],
  'Bangalore, India': [[12.85, 77.45], [13.15, 77.75]],
  'Kolkata, India': [[22.45, 88.25], [22.65, 88.45]],
  'Hyderabad, India': [[17.30, 78.35], [17.50, 78.60]],
};

const cityPolygons = {
  'New Delhi, India': [
    [28.88, 77.10], [28.85, 77.28], [28.78, 77.34], [28.70, 77.33],
    [28.62, 77.35], [28.55, 77.32], [28.50, 77.25], [28.48, 77.15],
    [28.50, 77.05], [28.55, 76.95], [28.62, 76.87], [28.70, 76.84],
    [28.78, 76.87], [28.85, 76.95], [28.88, 77.10],
  ],
  'Mumbai, India': [
    [19.27, 72.82], [19.25, 72.90], [19.20, 72.95], [19.12, 72.97],
    [19.05, 72.95], [18.97, 72.92], [18.92, 72.87], [18.90, 72.82],
    [18.92, 72.78], [18.97, 72.77], [19.05, 72.78], [19.12, 72.78],
    [19.20, 72.79], [19.25, 72.80], [19.27, 72.82],
  ],
  'Chennai, India': [
    [13.23, 80.18], [13.20, 80.28], [13.15, 80.32], [13.08, 80.30],
    [13.00, 80.28], [12.92, 80.25], [12.85, 80.22], [12.83, 80.18],
    [12.85, 80.14], [12.92, 80.12], [13.00, 80.11], [13.08, 80.12],
    [13.15, 80.14], [13.20, 80.16], [13.23, 80.18],
  ],
  'Bangalore, India': [
    [13.15, 77.55], [13.12, 77.68], [13.05, 77.74], [12.97, 77.75],
    [12.90, 77.72], [12.85, 77.65], [12.85, 77.55], [12.87, 77.48],
    [12.92, 77.45], [12.97, 77.44], [13.05, 77.46], [13.10, 77.50],
    [13.15, 77.55],
  ],
  'Kolkata, India': [
    [22.65, 88.30], [22.63, 88.40], [22.58, 88.44], [22.52, 88.43],
    [22.47, 88.40], [22.45, 88.35], [22.46, 88.28], [22.50, 88.25],
    [22.55, 88.24], [22.60, 88.26], [22.63, 88.28], [22.65, 88.30],
  ],
  'Hyderabad, India': [
    [17.50, 78.42], [17.48, 78.55], [17.43, 78.59], [17.37, 78.58],
    [17.32, 78.55], [17.30, 78.48], [17.31, 78.40], [17.35, 78.36],
    [17.40, 78.35], [17.45, 78.37], [17.48, 78.40], [17.50, 78.42],
  ],
};

function MapClickHandler({ onClick }) { 
  const map = useMapEvents({ click: (e) => onClick(e.latlng) }); 
  // Fix map size calculation (prevents click offset in flex layouts)
  React.useEffect(() => {
    const timer = setInterval(() => map.invalidateSize(), 500);
    return () => clearInterval(timer);
  }, [map]);
  return null; 
}

function FitBounds({ bounds }) {
  const map = useMap();
  const [lastBounds, setLastBounds] = React.useState(null);
  React.useEffect(() => {
    if (bounds && JSON.stringify(bounds) !== JSON.stringify(lastBounds)) {
      map.fitBounds(bounds, { padding: [20, 20] });
      setLastBounds(bounds);
    }
  }, [bounds]);
  return null;
}

function FlyToGPS({ gpsCenter }) {
  const map = useMap();
  const [hasMoved, setHasMoved] = React.useState(false);
  React.useEffect(() => {
    if (gpsCenter && !hasMoved) {
      map.flyTo(gpsCenter, 13, { duration: 1.5 });
      setHasMoved(true);
    }
  }, [gpsCenter]);
  return null;
}

export default function Navigation() {
  const [originLat, setOriginLat] = useState('');
  const [originLon, setOriginLon] = useState('');
  const [originName, setOriginName] = useState('');
  const [destLat, setDestLat] = useState('');
  const [destLon, setDestLon] = useState('');
  const [destName, setDestName] = useState('');
  const [place, setPlace] = useState('New Delhi, India');
  const [routes, setRoutes] = useState([]);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(0);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState(null);
  const [selectMode, setSelectMode] = useState(null);
  const [dbFloodZones, setDbFloodZones] = useState(null);
  const [loadingFlood, setLoadingFlood] = useState(false);
  const [gpsCenter, setGpsCenter] = useState(null);
  const { selectedVehicle } = useVehicleStore();

  // Try to get GPS location for initial map center AND auto-detect city
  React.useEffect(() => {
    navigator.geolocation?.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        setGpsCenter([latitude, longitude]);

        // Reverse geocode GPS to detect user's city
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json&zoom=10`,
            { headers: { 'User-Agent': 'AFDAS/1.0' } }
          );
          const data = await res.json();
          const city = data?.address?.city || data?.address?.state_district || data?.address?.town || '';
          
          // Match against supported city presets
          const matched = cityPresets.find((c) =>
            c.place.toLowerCase().includes(city.toLowerCase()) ||
            city.toLowerCase().includes(c.name.toLowerCase())
          );

          if (matched) {
            setPlace(matched.place);
          }
          // If no match, keep default 'New Delhi, India'
        } catch (err) {
          // Geocoding failed silently — keep Delhi default
        }
      },
      () => {} // GPS denied — keep Delhi as default
    );
  }, []);

  // Search states
  const [originSearch, setOriginSearch] = useState('');
  const [destSearch, setDestSearch] = useState('');
  const [searchingOrigin, setSearchingOrigin] = useState(false);
  const [searchingDest, setSearchingDest] = useState(false);

  // Custom vehicle clearance
  const [useCustomClearance, setUseCustomClearance] = useState(false);
  const [customClearance, setCustomClearance] = useState('0.30');

  const hasOrigin = originLat !== '' && originLon !== '' && !isNaN(parseFloat(originLat)) && !isNaN(parseFloat(originLon));
  const hasDest = destLat !== '' && destLon !== '' && !isNaN(parseFloat(destLat)) && !isNaN(parseFloat(destLon));
  const getMapCenter = () => { if (hasOrigin) return [parseFloat(originLat), parseFloat(originLon)]; if (gpsCenter) return gpsCenter; return mapCenters[place] || [28.63, 77.22]; };

  const handleMapClick = (latlng) => {
    if (selectMode === 'origin') { setOriginLat(latlng.lat.toFixed(5)); setOriginLon(latlng.lng.toFixed(5)); setOriginName(`${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}`); setSelectMode(null); }
    else if (selectMode === 'destination') { setDestLat(latlng.lat.toFixed(5)); setDestLon(latlng.lng.toFixed(5)); setDestName(`${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}`); setSelectMode(null); }
  };

  const useGPS = () => { navigator.geolocation?.getCurrentPosition((pos) => { setOriginLat(pos.coords.latitude.toFixed(5)); setOriginLon(pos.coords.longitude.toFixed(5)); setOriginName('My Location'); }, () => setError('GPS denied')); };

  // Geocode: search place name → get coordinates
  const geocodePlace = async (query, type) => {
    if (!query.trim()) return;
    const isOrigin = type === 'origin';
    isOrigin ? setSearchingOrigin(true) : setSearchingDest(true);
    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=1`, { headers: { 'User-Agent': 'AFDAS/1.0' } });
      const data = await res.json();
      if (data.length > 0) {
        const { lat, lon, display_name } = data[0];
        if (isOrigin) { setOriginLat(parseFloat(lat).toFixed(5)); setOriginLon(parseFloat(lon).toFixed(5)); setOriginName(display_name.split(',').slice(0, 2).join(',')); }
        else { setDestLat(parseFloat(lat).toFixed(5)); setDestLon(parseFloat(lon).toFixed(5)); setDestName(display_name.split(',').slice(0, 2).join(',')); }
      } else { setError(`"${query}" not found. Try a more specific name.`); }
    } catch (err) { setError('Geocoding failed'); }
    finally { isOrigin ? setSearchingOrigin(false) : setSearchingDest(false); }
  };

  const loadFloodZones = async () => {
    setLoadingFlood(true);
    try { const res = await axios.get(`${API_URL}/flood/zones/geojson`); console.log('Flood data:', res.data); setDbFloodZones(res.data); }
    catch (err) { console.error('Flood load error:', err); setError('Failed to load flood zones'); }
    finally { setLoadingFlood(false); }
  };

  const handleCalculateRoute = async () => {
    if (!hasOrigin || !hasDest) { setError('Set both origin and destination'); return; }
    setIsCalculating(true); setError(null); setRoutes([]);
    try {
      const res = await axios.post(`${API_URL}/navigation/route`, { start_lat: parseFloat(originLat), start_lon: parseFloat(originLon), end_lat: parseFloat(destLat), end_lon: parseFloat(destLon), vehicle_type: selectedVehicle, k: 3, place, event_id: null, custom_clearance: useCustomClearance ? parseFloat(customClearance) : null });
      if (res.data.success && res.data.routes.length > 0) { 
        // Add origin and destination as first/last points so line connects to markers
        const fixedRoutes = res.data.routes.map(route => {
          const coords = route.coordinates || [];
          if (coords.length > 0) {
            const startPt = [parseFloat(originLat), parseFloat(originLon)];
            const endPt = [parseFloat(destLat), parseFloat(destLon)];
            return { ...route, coordinates: [startPt, ...coords, endPt] };
          }
          return route;
        });
        setRoutes(fixedRoutes); setSelectedRouteIndex(0); 
      }
      else { setError(res.data.message || 'No routes found. Try: 1) Pick points closer to roads, 2) Use a larger city area, 3) Try "truck" vehicle (higher flood tolerance)'); }
    } catch (err) { setError(err.response?.data?.detail || err.message || 'Failed'); }
    finally { setIsCalculating(false); }
  };

  return (
    <div className="p-4 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-4 flex items-center gap-2"><NavIcon className="w-6 h-6 text-primary-600" /> Flood-Safe Navigation</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="space-y-3 overflow-y-auto max-h-[85vh]">
          {/* City */}
          <div className="card p-3">
            <label className="text-xs font-semibold text-gray-600 block mb-1">CITY / AREA</label>
            <input type="text" value={place} onChange={(e) => setPlace(e.target.value)} className="input-field text-sm mb-2" placeholder="City name..." />
            <div className="flex flex-wrap gap-1">{cityPresets.map((c) => (<button key={c.name} onClick={() => setPlace(c.place)} className={`text-[10px] px-2 py-1 rounded ${place === c.place ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>{c.name}</button>))}</div>
          </div>
          {/* Origin */}
          <div className="card p-3 border-l-4 border-green-500">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-green-700">ORIGIN (A)</label>
              <div className="flex gap-2">
                <button onClick={useGPS} className="text-[10px] px-2 py-0.5 bg-blue-50 text-blue-600 rounded">GPS</button>
                <button onClick={() => setSelectMode('origin')} className={`text-[10px] px-2 py-0.5 rounded ${selectMode === 'origin' ? 'bg-green-600 text-white' : 'bg-green-50 text-green-600'}`}>{selectMode === 'origin' ? 'Clicking...' : 'Pick Map'}</button>
              </div>
            </div>
            <div className="flex gap-1 mb-2"><input type="text" value={originSearch} onChange={(e) => setOriginSearch(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && geocodePlace(originSearch, 'origin')} className="input-field text-xs py-1.5 flex-1" placeholder="Search: India Gate, AIIMS..." /><button onClick={() => geocodePlace(originSearch, 'origin')} disabled={searchingOrigin} className="text-[10px] px-2 py-1 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50">{searchingOrigin ? '...' : 'Find'}</button></div>
            <div className="grid grid-cols-2 gap-2">
              <input type="text" value={originLat} onChange={(e) => setOriginLat(e.target.value)} className="input-field text-xs py-1.5" placeholder="Latitude" />
              <input type="text" value={originLon} onChange={(e) => setOriginLon(e.target.value)} className="input-field text-xs py-1.5" placeholder="Longitude" />
            </div>
            {originName && <p className="text-[10px] text-green-600 mt-1">{originName}</p>}
          </div>
          {/* Destination */}
          <div className="card p-3 border-l-4 border-red-500">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-red-700">DESTINATION (B)</label>
              <button onClick={() => setSelectMode('destination')} className={`text-[10px] px-2 py-0.5 rounded ${selectMode === 'destination' ? 'bg-red-600 text-white' : 'bg-red-50 text-red-600'}`}>{selectMode === 'destination' ? 'Clicking...' : 'Pick Map'}</button>
            </div>
            <div className="flex gap-1 mb-2"><input type="text" value={destSearch} onChange={(e) => setDestSearch(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && geocodePlace(destSearch, 'destination')} className="input-field text-xs py-1.5 flex-1" placeholder="Search: Hospital, Station..." /><button onClick={() => geocodePlace(destSearch, 'destination')} disabled={searchingDest} className="text-[10px] px-2 py-1 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50">{searchingDest ? '...' : 'Find'}</button></div>
            <div className="grid grid-cols-2 gap-2">
              <input type="text" value={destLat} onChange={(e) => setDestLat(e.target.value)} className="input-field text-xs py-1.5" placeholder="Latitude" />
              <input type="text" value={destLon} onChange={(e) => setDestLon(e.target.value)} className="input-field text-xs py-1.5" placeholder="Longitude" />
            </div>
            {destName && <p className="text-[10px] text-red-600 mt-1">{destName}</p>}
          </div>
          {/* Vehicle */}
          <VehicleSelector />
          {/* Custom Clearance */}
          <div className="card p-3 border-l-4 border-orange-400">
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-semibold text-orange-700">CUSTOM CLEARANCE</label>
              <button onClick={() => setUseCustomClearance(!useCustomClearance)} className={`text-[10px] px-2 py-0.5 rounded ${useCustomClearance ? 'bg-orange-500 text-white' : 'bg-orange-50 text-orange-600'}`}>{useCustomClearance ? 'ON' : 'OFF'}</button>
            </div>
            {useCustomClearance && (
              <div className="mt-2">
                <label className="text-[10px] text-gray-500 block mb-1">Max water depth your vehicle can pass (meters)</label>
                <input type="text" value={customClearance} onChange={(e) => setCustomClearance(e.target.value)} className="input-field text-xs py-1.5" placeholder="e.g. 0.45" />
                <p className="text-[10px] text-gray-400 mt-1">Car: 0.30m | SUV: 0.50m | Truck: 0.70m</p>
              </div>
            )}
          </div>
          {/* Flood */}
          <div className="card p-3 border-l-4 border-blue-500">
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-semibold text-blue-700 flex items-center gap-1"><Droplets className="w-3 h-3" /> FLOOD ZONES</label>
              <button onClick={loadFloodZones} disabled={loadingFlood} className="text-[10px] px-2 py-0.5 rounded bg-blue-50 text-blue-600 hover:bg-blue-100">{loadingFlood ? 'Loading...' : 'Load from DB'}</button>
            </div>
            {dbFloodZones && dbFloodZones.features?.length > 0 && <div className="text-[10px] text-blue-600 bg-blue-50 p-1.5 rounded flex justify-between"><span>{dbFloodZones.features.length} zone(s) on map</span><button onClick={() => setDbFloodZones(null)} className="text-red-500 underline">Hide</button></div>}
            {dbFloodZones && dbFloodZones.features?.length === 0 && <p className="text-[10px] text-gray-400 mt-1">No flood zones in DB. Insert via pgAdmin.</p>}
          </div>
          {/* Calculate */}
          <button onClick={handleCalculateRoute} disabled={!hasOrigin || !hasDest || isCalculating} className="btn-primary w-full flex items-center justify-center gap-2 py-3">
            {isCalculating ? <Loader2 className="w-5 h-5 animate-spin" /> : <NavIcon className="w-5 h-5" />}
            {isCalculating ? 'Calculating...' : 'Find Safe Route'}
          </button>
          {error && <div className="bg-red-50 border border-red-200 rounded-lg p-2 text-xs text-red-700">{error}</div>}
          {routes.length > 0 && <button onClick={() => { setRoutes([]); setError(null); }} className="btn-secondary w-full text-sm"><RotateCcw className="w-4 h-4 inline mr-1" />Clear</button>}
          {routes.length > 0 && <div className="space-y-2">{routes.map((route, idx) => (<button key={idx} onClick={() => setSelectedRouteIndex(idx)} className={`w-full text-left p-3 rounded-lg border-2 text-xs ${idx === selectedRouteIndex ? 'border-purple-500 bg-purple-50' : 'border-gray-200'}`}><div className="flex justify-between"><span className="font-semibold" style={{color:ROUTE_COLORS[idx]}}>Route {idx+1}</span><span>{Math.round(route.risk_score*100)}%</span></div><div className="flex gap-3 mt-1 text-gray-600"><span>{(route.total_distance_m/1000).toFixed(1)}km</span><span>{Math.round(route.estimated_time_s/60)}min</span><span>{route.flooded_segments} flooded</span></div></button>))}</div>}
          {selectMode && <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-2 text-xs text-yellow-800 animate-pulse">Click map for <b>{selectMode}</b> <button onClick={() => setSelectMode(null)} className="ml-2 underline">Cancel</button></div>}
        </div>
        {/* Map */}
        <div className="lg:col-span-2">
          <div className="rounded-xl overflow-hidden shadow border border-gray-200 h-[600px]">
            <MapContainer center={getMapCenter()} zoom={12} className="w-full h-full" scrollWheelZoom={true}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
              <MapClickHandler onClick={handleMapClick} />
              {cityBounds[place] && <FitBounds bounds={cityBounds[place]} />}
              <FlyToGPS gpsCenter={gpsCenter} />
              {cityPolygons[place] && <Polygon positions={cityPolygons[place]} pathOptions={{color: '#6366f1', weight: 2, fillOpacity: 0.02, dashArray: '8 4'}} />}
              {hasOrigin && <Marker position={[parseFloat(originLat), parseFloat(originLon)]} icon={originIcon}><Popup><b>Origin (A)</b></Popup></Marker>}
              {hasDest && <Marker position={[parseFloat(destLat), parseFloat(destLon)]} icon={destIcon}><Popup><b>Destination (B)</b></Popup></Marker>}
              {routes.map((route, idx) => route.coordinates?.length > 0 && <Polyline key={idx} positions={route.coordinates} pathOptions={{color:ROUTE_COLORS[idx%3],weight:idx===selectedRouteIndex?6:3,opacity:idx===selectedRouteIndex?1:0.4,dashArray:idx===selectedRouteIndex?null:'8 6'}} />)}
              {dbFloodZones?.features?.length > 0 && <GeoJSON key={JSON.stringify(dbFloodZones)} data={dbFloodZones} style={(f) => ({fillColor: f.properties.max_depth > 1 ? '#ef4444' : f.properties.max_depth > 0.5 ? '#f97316' : '#3b82f6', color: '#1e40af', fillOpacity: 0.4, weight: 2})} onEachFeature={(f, layer) => layer.bindPopup(`<b>${f.properties.event_name||'Flood'}</b><br/>Depth: ${f.properties.max_depth}m<br/>Area: ${f.properties.area_km2} km2`)} />}
            </MapContainer>
          </div>
          {/* Map Legend */}
          <div className="mt-2 flex flex-wrap gap-3 text-[10px] text-gray-600 px-2">
            <span className="flex items-center gap-1"><span className="w-3 h-1 bg-[#9B30FF] rounded inline-block"></span> Best Route</span>
            <span className="flex items-center gap-1"><span className="w-3 h-1 bg-[#FF6600] rounded inline-block"></span> Alt Route</span>
            <span className="flex items-center gap-1"><span className="w-3 h-1 bg-black rounded inline-block"></span> Alt Route 2</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-500/30 border border-blue-500 rounded-sm inline-block"></span> Flood Zone</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-green-500 rounded-full inline-block border border-white"></span> Origin</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-red-500 rounded-full inline-block border border-white"></span> Destination</span>
            <span className="flex items-center gap-1"><span className="w-3 h-1 border border-indigo-400 border-dashed rounded inline-block"></span> City Boundary</span>
          </div>
          {routes[selectedRouteIndex] && <div className="mt-4 card p-4"><h3 className="text-sm font-semibold mb-2" style={{color:ROUTE_COLORS[selectedRouteIndex]}}>Route {selectedRouteIndex+1}</h3><div className="grid grid-cols-4 gap-3 text-center text-sm"><div className="bg-gray-50 p-2 rounded"><p className="font-bold">{(routes[selectedRouteIndex].total_distance_m/1000).toFixed(1)}km</p><p className="text-[10px] text-gray-500">Distance</p></div><div className="bg-gray-50 p-2 rounded"><p className="font-bold">{Math.round(routes[selectedRouteIndex].estimated_time_s/60)}min</p><p className="text-[10px] text-gray-500">Time</p></div><div className="bg-gray-50 p-2 rounded"><p className="font-bold">{Math.round(routes[selectedRouteIndex].risk_score*100)}%</p><p className="text-[10px] text-gray-500">Risk</p></div><div className="bg-gray-50 p-2 rounded"><p className="font-bold">{routes[selectedRouteIndex].flooded_segments}</p><p className="text-[10px] text-gray-500">Flooded</p></div></div></div>}
        </div>
      </div>

      {/* AI Assistant Panel */}
      <AIChatPanel gpsCenter={gpsCenter} onRouteCalculated={(aiRoutes) => {
        // When AI calculates routes, display them on the map
        if (aiRoutes && aiRoutes.length > 0) {
          setRoutes(aiRoutes);
          setSelectedRouteIndex(0);
          // Set origin/destination markers from the first/last coordinates of the best route
          const bestRoute = aiRoutes[0];
          if (bestRoute.coordinates && bestRoute.coordinates.length >= 2) {
            const startCoord = bestRoute.coordinates[0];
            const endCoord = bestRoute.coordinates[bestRoute.coordinates.length - 1];
            setOriginLat(String(startCoord[0]));
            setOriginLon(String(startCoord[1]));
            setOriginName('AI Route Start');
            setDestLat(String(endCoord[0]));
            setDestLon(String(endCoord[1]));
            setDestName('AI Route End');
          }
          setError(null);
        }
      }} />
    </div>
  );
}

function AIChatPanel({ gpsCenter, onRouteCalculated }) {
  const [open, setOpen] = React.useState(false);
  const [messages, setMessages] = React.useState([{id:'1',role:'assistant',text:'Hi! I can help with flood info, safe routes, hospitals & more. Ask me anything!'}]);
  const [input, setInput] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const messagesEndRef = React.useRef(null);

  React.useEffect(() => { messagesEndRef.current?.scrollIntoView({behavior:'smooth'}); }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg = {id: Date.now().toString(), role:'user', text: input.trim()};
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/chat`, {message: userMsg.text, lat: gpsCenter?.[0] || null, lon: gpsCenter?.[1] || null});
      
      // Check if AI response includes route data
      const hasRoutes = res.data.routes && Array.isArray(res.data.routes) && res.data.routes.length > 0;
      
      const assistantText = res.data.response || 'No response';
      setMessages(prev => [...prev, {
        id:(Date.now()+1).toString(), 
        role:'assistant', 
        text: assistantText, 
        category: res.data.category,
        hasRoutes: hasRoutes,
      }]);

      // If routes were calculated, push them to the map
      if (hasRoutes && onRouteCalculated) {
        onRouteCalculated(res.data.routes);
      }
    } catch (err) {
      setMessages(prev => [...prev, {id:(Date.now()+1).toString(), role:'assistant', text: 'Error: ' + (err.response?.data?.detail || err.message), isError: true}]);
    } finally { setLoading(false); }
  };

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="fixed bottom-6 right-6 w-14 h-14 bg-primary-600 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-primary-700 transition-all z-50 animate-bounce" title="AI Assistant">
        <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[500px] bg-white rounded-xl shadow-2xl border border-gray-200 flex flex-col z-50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-primary-50 rounded-t-xl">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-primary-600 rounded-full flex items-center justify-center"><svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5" /></svg></div>
          <div><p className="text-sm font-semibold text-gray-800">AI Flood Assistant</p><p className="text-[10px] text-gray-500">Ask about floods, routes, hospitals</p></div>
        </div>
        <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600 p-1"><svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg></button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] px-3 py-2 rounded-lg text-sm ${msg.role === 'user' ? 'bg-primary-600 text-white' : msg.isError ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-gray-100 text-gray-800'}`}>
              <p className="whitespace-pre-wrap">{msg.text}</p>
              {msg.hasRoutes && (
                <div className="mt-2 flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-700 rounded text-[10px] font-medium">
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l5.447 2.724A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" /></svg>
                  Route displayed on map
                </div>
              )}
              {msg.category && <span className="text-[9px] opacity-60 block mt-1">{msg.category}</span>}
            </div>
          </div>
        ))}
        {loading && <div className="flex gap-1 px-3 py-2"><span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" /><span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'150ms'}} /><span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'300ms'}} /></div>}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick suggestions */}
      <div className="px-3 py-1 flex gap-1 overflow-x-auto border-t border-gray-50">
        {['Safe route to hospital','Route from India Gate to AIIMS','Which areas are flooded?','Can ambulance reach me?'].map((s,i) => (
          <button key={i} onClick={() => {setInput(s); }} className="text-[9px] px-2 py-1 bg-gray-100 text-gray-600 rounded-full whitespace-nowrap hover:bg-primary-50 hover:text-primary-700 flex-shrink-0">{s}</button>
        ))}
      </div>

      {/* Input */}
      <div className="px-3 py-2 border-t border-gray-100 flex gap-2">
        <input type="text" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && sendMessage()} placeholder="Ask about floods..." className="input-field text-sm py-2 flex-1" disabled={loading} />
        <button onClick={sendMessage} disabled={!input.trim() || loading} className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"><svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg></button>
      </div>
    </div>
  );
}
