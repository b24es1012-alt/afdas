import { useState, useCallback } from 'react';
import { Search, MapPin, X } from 'lucide-react';
import { debounce } from '../../utils/helpers';
import api from '../../config/axios';

export default function SearchBox({ placeholder = 'Search location...', onSelect, value }) {
  const [query, setQuery] = useState(value?.name || '');
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);

  const search = useCallback(
    debounce(async (q) => {
      if (q.length < 3) {
        setResults([]);
        return;
      }
      setIsSearching(true);
      try {
        // Use Nominatim via backend or directly
        const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}, Delhi, India&format=json&limit=5`;
        const res = await fetch(url, {
          headers: { 'User-Agent': 'AFDAS-Frontend/1.0' },
        });
        const data = await res.json();
        setResults(
          data.map((item) => ({
            name: item.display_name.split(',').slice(0, 3).join(', '),
            fullName: item.display_name,
            lat: parseFloat(item.lat),
            lon: parseFloat(item.lon),
            type: item.type,
          }))
        );
        setShowResults(true);
      } catch (err) {
        console.error('Search error:', err);
      } finally {
        setIsSearching(false);
      }
    }, 500),
    []
  );

  const handleInputChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    search(val);
  };

  const handleSelect = (result) => {
    setQuery(result.name);
    setShowResults(false);
    onSelect?.(result);
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    onSelect?.(null);
  };

  return (
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={handleInputChange}
          onFocus={() => results.length > 0 && setShowResults(true)}
          placeholder={placeholder}
          className="input-field pl-10 pr-10"
        />
        {query && (
          <button
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Dropdown results */}
      {showResults && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg border border-gray-200 shadow-lg z-50 max-h-60 overflow-y-auto">
          {results.map((result, idx) => (
            <button
              key={idx}
              onClick={() => handleSelect(result)}
              className="w-full flex items-start gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-left border-b border-gray-50 last:border-0"
            >
              <MapPin className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-gray-800">{result.name}</p>
                <p className="text-xs text-gray-500">
                  {result.lat.toFixed(4)}, {result.lon.toFixed(4)}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}

      {isSearching && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg border border-gray-200 shadow-lg p-3 z-50">
          <p className="text-sm text-gray-500 text-center">Searching...</p>
        </div>
      )}
    </div>
  );
}
