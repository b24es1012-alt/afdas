/**
 * Format distance in meters to human-readable string.
 */
export function formatDistance(meters) {
  if (meters < 1000) {
    return `${Math.round(meters)} m`;
  }
  return `${(meters / 1000).toFixed(1)} km`;
}

/**
 * Format time in seconds to human-readable string.
 */
export function formatTime(seconds) {
  if (seconds < 60) {
    return `${Math.round(seconds)} sec`;
  }
  if (seconds < 3600) {
    return `${Math.round(seconds / 60)} min`;
  }
  const hours = Math.floor(seconds / 3600);
  const mins = Math.round((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
}

/**
 * Format risk score (0-1) to percentage string.
 */
export function formatRisk(score) {
  return `${Math.round(score * 100)}%`;
}

/**
 * Get severity level from flood depth.
 */
export function getSeverityFromDepth(depth) {
  if (depth <= 0) return 'none';
  if (depth <= 0.1) return 'low';
  if (depth <= 0.3) return 'moderate';
  if (depth <= 0.6) return 'high';
  return 'critical';
}

/**
 * Get severity color class.
 */
export function getSeverityColor(severity) {
  const colors = {
    none: 'text-green-500',
    low: 'text-yellow-500',
    moderate: 'text-orange-500',
    high: 'text-red-500',
    critical: 'text-red-900',
  };
  return colors[severity] || 'text-gray-500';
}

/**
 * Get severity background class.
 */
export function getSeverityBg(severity) {
  const colors = {
    none: 'bg-green-100 text-green-800',
    low: 'bg-yellow-100 text-yellow-800',
    moderate: 'bg-orange-100 text-orange-800',
    high: 'bg-red-100 text-red-800',
    critical: 'bg-red-900 text-white',
  };
  return colors[severity] || 'bg-gray-100 text-gray-800';
}

/**
 * Truncate text with ellipsis.
 */
export function truncate(str, maxLen = 50) {
  if (!str || str.length <= maxLen) return str;
  return str.slice(0, maxLen) + '...';
}

/**
 * Debounce function.
 */
export function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Format date to locale string.
 */
export function formatDate(date) {
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
