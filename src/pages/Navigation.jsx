import { useState } from 'react';
import { Loader2, RotateCcw, MapPin, Navigation as NavIcon } from 'lucide-react';
import MapView from '../components/map/MapView';
import VehicleSelector from '../components/navigation/VehicleSelector';
import RouteCard from '../components/navigation/RouteCard';
import RouteSummary from '../components/navigation/RouteSummary';
import { useVehicleStore } from '../store/vehicleStore';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

export default function Navigation() {
  // Origin & Destination state
  const [origin, setOrigin] = useState({ lat: '', lon: '', name: '' });
  const [destination, setDestination] = useState({ lat: '', lon: '', name: '' });
  const [place, setPlace] = useState('New Delhi, India');

  // Route state
  const [routes, setRoutes] = useState([]);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(0);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState(null);

  // Map interaction
  const [selectMode, setSelectMode] = useState(null); // 'origin' | 'destination'

  const { selectedVehicle } = useVehicleStore();

  // Handle map click
  const handleMapClick = (point) => {
    if (selectMode === 'origin') {
      setOrigin({ lat: point.lat.toFixed(5), lon: point.lon.toFixed(5), name: `${point.lat.toFixed(4)}, ${point.lon.toFixed(4)}` });
      setSelectMode(null);
    } else if (selectMode === 'destination') {
      setDestination({ lat: point.lat.toFixed(5), lon: point.lon.toFixed(5), name: `${point.lat.toFixed(4)}, ${point.lon.toFixed(4)}` });
      setSelectMode(null);
    }
  };

  // Calculate route
  const handleCalculateRoute = async () => {
    if (!origin.lat || !origin.lon || !destination.lat || !destination.lon) {
      setError('Please set both origin and destination coordinates');
      return;
    }

    setIsCalculating(true);
    setError(null);
    setRoutes([]);

    try {
      const response = await axios.post(`${API_URL}/navigation/route`, {
        start_lat: parseFloat(origin.lat),
        start_lon: parseFloat(origin.lon),
        end_lat: parseFloat(destination.lat),
        end_lon: parseFloat(destination.lon),
        vehicle_type: selectedVehicle,
        k: 3,
        place: place,
        event_id: null,
      });

      if (response.data.success && response.data.routes.length > 0) {
        setRoutes(response.data.routes);
        setSelectedRouteIndex(0);
      } else {
        setError(response.data.message || 'No routes found');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Route calculation failed');
    } finally {
      setIsCalculating(false);
    }
  };

  // Clear everything
  const handleClear = () => {
    setRoutes([]);
    setSelectedRouteIndex(0);
    setError(null);
  };

  // Use GPS
  const useCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setOrigin({
            lat: pos.coords.latitude.toFixed(5),
            lon: pos.coords.longitude.toFixed(5),
            name: 'My Location',
          });
        },
        () => setError('GPS permission denied')
      );
    }
  };

  // Preset locations
  const presets = {
    'India Gate': { lat: '28.61390', lon: '77.20900' },
    'Connaught Place': { lat: '28.63150', lon: '77.21670' },
    'AIIMS Hospital': { lat: '28.56720', lon: '77.21000' },
    'Delhi Railway Stn': { lat: '28.64200', lon: '77.21950' },
    'Kashmere Gate': { lat: '28.65620', lon: '77.24100' },
    'Red Fort': { lat: '28.65620', lon: '77.24100' },
  };

  return (
    <div className="p-4 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-4 flex items-center gap-2">
        <NavIcon className="w-6 h-6 text-primary-600" />
        Flood-Safe Navigation
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sidebar Controls */}
        <div className="space-y-4">
          {/* Place (city) */}
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">City / Area</label>
            <input
              type="text"
              value={place}
              onChange={(e) => setPlace(e.target.value)}
              className="input-field"
              placeholder="e.g. New Delhi, India"
            />
          </div>

          {/* Origin */}
          <div className="card p-4">
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-semibold text-green-700 flex items-center gap-1">
                <MapPin className="w-4 h-4" /> Origin (A)
              </label>
              <div className="flex gap-2">
                <button onClick={useCurrentLocation} className="text-xs text-primary-600 hover:underline">GPS</button>
                <button onClick={() => setSelectMode('origin')} className="text-xs text-primary-600 hover:underline">Pick Map</button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 mb-2">
              <input type="number" step="any" value={origin.lat} onChange={(e) => setOrigin({...origin, lat: e.target.value})} className="input-field text-sm" placeholder="Latitude" />
              <input type="number" step="any" value={origin.lon} onChange={(e) => setOrigin({...origin, lon: e.target.value})} className="input-field text-sm" placeholder="Longitude" />
            </div>
            <div className="flex flex-wrap gap-1">
              {Object.entries(presets).slice(0, 3).map(([name, coords]) => (
                <button key={name} onClick={() => setOrigin({...coords, name})} className="text-[10px] px-2 py-1 bg-green-50 text-green-700 rounded hover:bg-green-100">
                  {name}
                </button>
              ))}
            </div>
          </div>

          {/* Destination */}
          <div className="card p-4">
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-semibold text-red-700 flex items-center gap-1">
                <MapPin className="w-4 h-4" /> Destination (B)
              </label>
              <button onClick={() => setSelectMode('destination')} className="text-xs text-primary-600 hover:underline">Pick Map</button>
            </div>
            <div className="grid grid-cols-2 gap-2 mb-2">
              <input type="number" step="any" value={destination.lat} onChange={(e) => setDestination({...destination, lat: e.target.value})} className="input-field text-sm" placeholder="Latitude" />
              <input type="number" step="any" value={destination.lon} onChange={(e) => setDestination({...destination, lon: e.target.value})} className="input-field text-sm" placeholder="Longitude" />
            </div>
            <div className="flex flex-wrap gap-1">
              {Object.entries(presets).slice(3).map(([name, coords]) => (
                <button key={name} onClick={() => setDestination({...coords, name})} className="text-[10px] px-2 py-1 bg-red-50 text-red-700 rounded hover:bg-red-100">
                  {name}
                </button>
              ))}
            </div>
          </div>

          {/* Vehicle */}
          <VehicleSelector />

          {/* Calculate button */}
          <button
            onClick={handleCalculateRoute}
            disabled={!origin.lat || !destination.lat || isCalculating}
            className="btn-primary w-full flex items-center justify-center gap-2 py-3"
          >
            {isCalculating ? <Loader2 className="w-5 h-5 animate-spin" /> : <NavIcon className="w-5 h-5" />}
            {isCalculating ? 'Calculating... (may take 1-2 min first time)' : 'Find Safe Route'}
          </button>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Clear */}
          {routes.length > 0 && (
            <button onClick={handleClear} className="btn-secondary w-full flex items-center justify-center gap-2">
              <RotateCcw className="w-4 h-4" /> Clear Routes
            </button>
          )}

          {/* Route cards */}
          {routes.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-gray-700">Found {routes.length} Route(s)</h3>
              {routes.map((route, idx) => (
                <RouteCard
                  key={idx}
                  route={route}
                  index={idx}
                  isSelected={idx === selectedRouteIndex}
                  onSelect={setSelectedRouteIndex}
                />
              ))}
            </div>
          )}

          {/* Map selection mode */}
          {selectMode && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800 animate-pulse">
              Click on the map to set <strong>{selectMode}</strong>
              <button onClick={() => setSelectMode(null)} className="ml-2 text-yellow-600 underline">Cancel</button>
            </div>
          )}
        </div>

        {/* Map + Summary */}
        <div className="lg:col-span-2 space-y-4">
          <MapView
            routes={routes}
            selectedRouteIndex={selectedRouteIndex}
            onMapClick={handleMapClick}
            center={origin.lat ? [parseFloat(origin.lat), parseFloat(origin.lon)] : [28.63, 77.22]}
            zoom={12}
            className="h-[500px] lg:h-[600px]"
          />

          {routes.length > 0 && routes[selectedRouteIndex] && (
            <RouteSummary
              route={routes[selectedRouteIndex]}
              isNavigating={false}
              onStart={() => {}}
              onStop={() => {}}
            />
          )}
        </div>
      </div>
    </div>
  );
}
