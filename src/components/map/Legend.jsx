import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

export default function Legend() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="absolute bottom-4 left-4 z-[1000] bg-white rounded-lg shadow-lg border border-gray-200 p-3 max-w-[180px]">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-between w-full text-xs font-semibold text-gray-700 mb-1"
      >
        <span>Map Legend</span>
        {collapsed ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
      </button>

      {!collapsed && (
        <div className="space-y-1.5 text-xs text-gray-600 mt-2">
          <div className="flex items-center gap-2">
            <div className="w-4 h-1 bg-green-500 rounded" />
            <span>Safe road</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-1 bg-orange-500 rounded" />
            <span>Partially flooded</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-1 bg-red-600 rounded" />
            <span>Impassable</span>
          </div>

          <div className="border-t border-gray-100 pt-1.5 mt-1.5" />

          <div className="flex items-center gap-2">
            <div className="w-4 h-1 bg-purple-600 rounded" />
            <span>Route 1 (Best)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-1 bg-orange-500 rounded border-dashed" />
            <span>Route 2 (Alt)</span>
          </div>

          <div className="border-t border-gray-100 pt-1.5 mt-1.5" />

          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500/30 border border-blue-500 rounded-sm" />
            <span>Flood zone</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full border border-white" />
            <span>Your location</span>
          </div>
        </div>
      )}
    </div>
  );
}
