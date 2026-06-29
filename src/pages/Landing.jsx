import { Link } from 'react-router-dom';
import { Droplets, MapPin, Shield, Zap, BarChart3, MessageCircle } from 'lucide-react';

export default function Landing() {
  const features = [
    { icon: MapPin, title: 'Flood-Safe Navigation', desc: 'AI-powered routes that avoid flooded roads in real-time' },
    { icon: Shield, title: 'Real-Time Monitoring', desc: 'Live GPS tracking with automatic rerouting when conditions change' },
    { icon: Zap, title: 'AI Assistant', desc: 'Ask questions about flood conditions, hospitals, shelters, and safe routes' },
    { icon: BarChart3, title: 'Analytics', desc: 'Historical flood data and infrastructure risk reports' },
    { icon: Droplets, title: 'Copernicus EMS Data', desc: 'Real flood polygons from European Emergency Management Service' },
    { icon: MessageCircle, title: 'Multi-Vehicle', desc: 'Routes optimized for cars, trucks, ambulances, and pedestrians' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-primary-50 to-white">
      {/* Hero */}
      <section className="max-w-7xl mx-auto px-4 pt-20 pb-16 text-center">
        <div className="flex items-center justify-center gap-3 mb-6">
          <Droplets className="w-12 h-12 text-primary-600" />
          <h1 className="text-5xl font-bold text-gray-900">AFDAS</h1>
        </div>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-4">
          AI Flood Disaster Assistance System
        </p>
        <p className="text-lg text-gray-500 max-w-3xl mx-auto mb-10">
          Real-time flood-aware navigation powered by Copernicus EMS data, OpenStreetMap,
          graph algorithms, and AI agents. Find the safest route during floods.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link to="/register" className="btn-primary text-lg px-8 py-3">
            Get Started
          </Link>
          <Link to="/login" className="btn-secondary text-lg px-8 py-3">
            Log In
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center text-gray-800 mb-12">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map(({ icon: Icon, title, desc }, idx) => (
            <div key={idx} className="card hover:shadow-md transition-shadow">
              <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center mb-4">
                <Icon className="w-5 h-5 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">{title}</h3>
              <p className="text-sm text-gray-500">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-primary-600 py-16 mt-16">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Emergency? Get Safe Routes Now</h2>
          <p className="text-primary-100 mb-8">
            No account needed for emergency routing. Sign up for full features.
          </p>
          <Link to="/navigate" className="inline-block px-8 py-3 bg-white text-primary-700 rounded-lg font-semibold hover:bg-gray-100 transition-colors">
            Open Navigation
          </Link>
        </div>
      </section>
    </div>
  );
}
