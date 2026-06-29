import { Droplets } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-white border-t border-gray-200 py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Droplets className="w-5 h-5 text-primary-600" />
            <span className="text-sm font-medium text-gray-700">AFDAS</span>
            <span className="text-sm text-gray-400">|</span>
            <span className="text-sm text-gray-500">AI Flood Disaster Assistance System</span>
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span>Data: Copernicus EMS + OpenStreetMap</span>
            <span className="text-gray-300">|</span>
            <span>&copy; {new Date().getFullYear()}</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
