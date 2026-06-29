import { useState } from 'react';
import { Loader2, RotateCcw } from 'lucide-react';
import MapView from '../components/map/MapView';
import SearchBox from '../components/navigation/SearchBox';
import VehicleSelector from '../components/navigation/VehicleSelector';
import RouteCard from '../components/navigation/RouteCard';
import RouteSummary from '../components/navigation/RouteSummary';
import { useRoute } from '../hooks/useRoute';
import { useFloodStatus } from '../hooks/useFloodStatus';
import { useGPS } from '../hooks/useGPS';

export default function Navigation() {
  const { location } = useGPS(true);
  const { floodZones } = useFloodStatus();
  const {
    origin, destination, routes, selectedRouteIndex, selectedRoute,
    isCalculating, isNavigating,
    setOrigin, setDestination, calculateRoute, selectRoute,
    startNavigation, stopNavigation, clearRoute,
  } = useRoute();

  const [selectMode, setSelectMode] = useState(null); // 'origin' | 'destination'

  const handleMapClick = (point) => {
    if (selectMode === 'origin') {
      setOrigin({ lat: point.lat, lon: point.lon, name: `${point.lat.toFixed(4)}, ${point.lon.toFixed(4)}` });
      setSelectMode(null);
    } else if (selectMode === 'destination') {
      setDestination({ lat: point.lat, lon: point.lon, name: `${point.lat.toFixed(4)}, ${point.lon.toFixed(4)}` });
      setSelectMode(null);
    }
  };

  const useCurrentLocation = () => {
    if (location) {
      setOrigin({ lat: location.lat, lon: location.lon, name: 'My Location' });
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Sidebar Controls */}
      <div className="space-y-4 lg:order-1">
        {/* Origin */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-sm font-medium text-gray-700">From</label>
            <div className="flex gap-2">
              <button onClick={useCurrentLocation} className="text-xs text-primary-600 hover:underline">Use GPS</button>
              <button onClick={() => setSelectMode('origin')} className="text-xs text-primary-600 hover:underline">Pick on map</button>
            </div>
          </div>
          <SearchBox
            placeholder="Start location..."
            value={origin}
            onSelect={(result) => result && setOrigin({ lat: result.lat, lon: result.lon, name: result.name })}
          />
        </div>

        {/* Destination */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-sm font-medium text-gray-700">To</label>
            <button onClick={() => setSelectMode('destination')} className="text-xs text-primary-600 hover:underline">Pick on map</button>
          </div>
          <SearchBox
            placeholder="Destination..."
            value={destination}
            onSelect={(result) => result && setDestination({ lat: result.lat, lon: result.lon, name: result.name })}
          />
        </div>

        {/* Vehicle */}
        <VehicleSelector />

        {/* Calculate button */}
        <button
          onClick={calculateRoute}
          disabled={!origin || !destination || isCalculating}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          {isCalculating ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
          {isCalculating ? 'Calculating...' : 'Find Safe Route'}
        </button>

        {routes.length > 0 && (
          <button onClick={clearRoute} className="btn-secondary w-full flex items-center justify-center gap-2">
            <RotateCcw className="w-4 h-4" />
            Clear Route
          </button>
        )}

        {/* Route alternatives */}
        {routes.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-700">Routes ({routes.length})</h3>
            {routes.map((route, idx) => (
              <RouteCard
                key={idx}
                route={route}
                index={idx}
                isSelected={idx === selectedRouteIndex}
                onSelect={selectRoute}
              />
            ))}
          </div>
        )}

        {/* Map selection mode indicator */}
        {selectMode && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
            Click on the map to set your <strong>{selectMode}</strong> point.
          </div>
        )}
      </div>

      {/* Map + Summary */}
      <div className="lg:col-span-2 space-y-4 lg:order-2">
        <MapView
          floodZones={floodZones}
          routes={routes}
          selectedRouteIndex={selectedRouteIndex}
          onMapClick={handleMapClick}
          className="h-[500px] lg:h-[600px]"
        />

        {selectedRoute && (
          <RouteSummary
            route={selectedRoute}
            isNavigating={isNavigating}
            onStart={startNavigation}
            onStop={stopNavigation}
          />
        )}
      </div>
    </div>
  );
}
