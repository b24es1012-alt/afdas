import { Bot, User, AlertCircle } from 'lucide-react';

export default function Message({ message }) {
  const isUser = message.role === 'user';
  const isError = message.isError;

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser ? 'bg-gray-200' : isError ? 'bg-red-100' : 'bg-primary-100'
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-gray-600" />
        ) : isError ? (
          <AlertCircle className="w-4 h-4 text-red-600" />
        ) : (
          <Bot className="w-4 h-4 text-primary-600" />
        )}
      </div>

      {/* Content */}
      <div
        className={`max-w-[80%] rounded-xl px-4 py-2.5 ${
          isUser
            ? 'bg-primary-600 text-white'
            : isError
            ? 'bg-red-50 text-red-800 border border-red-200'
            : 'bg-gray-100 text-gray-800'
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>

        {/* Metadata for assistant messages */}
        {!isUser && message.category && (
          <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-200/50">
            <span className="text-[10px] text-gray-500 bg-gray-200/60 px-2 py-0.5 rounded-full">
              {message.category}
            </span>
            {message.stepsExecuted > 0 && (
              <span className="text-[10px] text-gray-500">
                {message.stepsExecuted} tools used
              </span>
            )}
          </div>
        )}

        {/* Timestamp */}
        <p className={`text-[10px] mt-1 ${isUser ? 'text-white/70' : 'text-gray-400'}`}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  );
}
