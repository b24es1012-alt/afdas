import { useState } from 'react';
import { Send } from 'lucide-react';

export default function ChatInput({ onSend, isLoading }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSend(input.trim());
    setInput('');
  };

  const suggestions = [
    'Is DHQ Hospital flooded?',
    'Find nearest safe shelter',
    'Safest route to Railway Station',
    'Can an ambulance reach me?',
  ];

  return (
    <div className="border-t border-gray-100 px-4 py-3">
      {/* Quick suggestions */}
      {!isLoading && (
        <div className="flex gap-2 mb-2 overflow-x-auto pb-1">
          {suggestions.map((s, idx) => (
            <button
              key={idx}
              onClick={() => onSend(s)}
              className="flex-shrink-0 text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full hover:bg-primary-50 hover:text-primary-700 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about flood conditions, safe routes, hospitals..."
          className="input-field text-sm"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="p-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
