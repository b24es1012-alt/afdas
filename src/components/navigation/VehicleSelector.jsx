import { Car, Truck, Footprints, Bike, Ambulance } from 'lucide-react';
import { useVehicleStore } from '../../store/vehicleStore';

const vehicleIcons = {
  walking: Footprints,
  motorcycle: Bike,
  car: Car,
  suv: Truck,
  ambulance: Ambulance,
  truck: Truck,
};

export default function VehicleSelector() {
  const { selectedVehicle, vehicleProfiles, setVehicle } = useVehicleStore();

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-gray-700">Vehicle Type</label>
      <div className="grid grid-cols-3 gap-2">
        {vehicleProfiles.map((v) => {
          const Icon = vehicleIcons[v.id] || Car;
          const isActive = selectedVehicle === v.id;

          return (
            <button
              key={v.id}
              onClick={() => setVehicle(v.id)}
              className={`flex flex-col items-center gap-1 p-3 rounded-lg border-2 transition-all ${
                isActive
                  ? 'border-primary-500 bg-primary-50 text-primary-700'
                  : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="text-xs font-medium">{v.label}</span>
              <span className="text-[10px] text-gray-400">{v.maxDepth}m</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
