/**
 * Format coordinates for display.
 */
export function formatCoords(lat, lon, precision = 5) {
  return `${lat.toFixed(precision)}, ${lon.toFixed(precision)}`;
}

/**
 * Format flood depth with unit.
 */
export function formatDepth(meters) {
  if (meters === 0) return '0 m (Safe)';
  if (meters < 1) return `${(meters * 100).toFixed(0)} cm`;
  return `${meters.toFixed(2)} m`;
}

/**
 * Format risk score as label.
 */
export function riskLabel(score) {
  if (score <= 0) return 'No Risk';
  if (score <= 0.2) return 'Low Risk';
  if (score <= 0.5) return 'Moderate Risk';
  if (score <= 0.8) return 'High Risk';
  return 'Critical Risk';
}

/**
 * Format number with commas.
 */
export function formatNumber(num) {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * Format percentage.
 */
export function formatPercent(value, decimals = 1) {
  return `${value.toFixed(decimals)}%`;
}

/**
 * Format route summary.
 */
export function formatRouteSummary(route) {
  const distKm = (route.total_distance_m / 1000).toFixed(1);
  const timeMin = Math.round(route.estimated_time_s / 60);
  const risk = Math.round(route.risk_score * 100);
  return `${distKm} km | ${timeMin} min | Risk: ${risk}%`;
}
