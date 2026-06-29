import { useEffect, useState } from 'react';
import { BarChart3, Building2, Route } from 'lucide-react';
import FloodChart from '../components/analytics/FloodChart';
import StatisticsCard from '../components/analytics/StatisticsCard';
import { analyticsService } from '../services/analyticsService';

export default function Analytics() {
  const [roads, setRoads] = useState([]);
  const [buildings, setBuildings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [roadsRes, buildingsRes] = await Promise.all([
        analyticsService.getMostFloodedRoads(null, 10),
        analyticsService.getMostAffectedBuildings(null, 10),
      ]);
      setRoads(roadsRes.roads || []);
      setBuildings(buildingsRes.buildings || []);
    } catch (err) {
      console.error('Analytics load error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Flood Analytics</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatisticsCard title="Flooded Roads" value={roads.length} icon={Route} color="red" />
        <StatisticsCard title="Affected Buildings" value={buildings.length} icon={Building2} color="orange" />
        <StatisticsCard title="Data Source" value="Copernicus" icon={BarChart3} color="blue" />
      </div>

      <FloodChart
        data={roads.slice(0, 10).map((r) => ({ name: r.name || 'Road', worst_depth: r.worst_depth, avg_depth: r.avg_depth }))}
        title="Most Flooded Roads"
      />
    </div>
  );
}
