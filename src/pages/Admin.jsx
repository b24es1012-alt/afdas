import { useEffect, useState } from 'react';
import { Shield, Database, Server, Cpu, RefreshCw } from 'lucide-react';
import StatisticsCard from '../components/analytics/StatisticsCard';
import api from '../config/axios';

export default function Admin() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { checkHealth(); }, []);

  const checkHealth = async () => {
    try {
      const res = await api.get('/health');
      setHealth(res.data);
    } catch (err) {
      setHealth({ status: 'error', error: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <Shield className="w-6 h-6" /> Admin Panel
        </h1>
        <button onClick={checkHealth} className="btn-secondary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatisticsCard
          title="System Status"
          value={health?.status?.toUpperCase() || 'CHECKING'}
          icon={Server}
          color={health?.status === 'healthy' ? 'green' : 'red'}
        />
        <StatisticsCard
          title="PostgreSQL"
          value={health?.checks?.database?.status?.toUpperCase() || '-'}
          icon={Database}
          color={health?.checks?.database?.status === 'healthy' ? 'green' : 'red'}
        />
        <StatisticsCard
          title="Redis"
          value={health?.checks?.redis?.status?.toUpperCase() || '-'}
          icon={Cpu}
          color={health?.checks?.redis?.status === 'healthy' ? 'green' : 'red'}
        />
      </div>

      {health?.checks?.database?.postgis_version && (
        <div className="card">
          <h3 className="font-semibold text-gray-800 mb-2">System Info</h3>
          <div className="text-sm text-gray-600 space-y-1">
            <p>PostGIS: {health.checks.database.postgis_version}</p>
            <p>Redis Memory: {health.checks.redis?.used_memory || 'N/A'}</p>
            <p>Pool Size: {health.checks.database?.pool_size || 'N/A'}</p>
          </div>
        </div>
      )}
    </div>
  );
}
