/**
 * Validate email format.
 */
export function isValidEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}

/**
 * Validate password (min 8 chars, 1 uppercase, 1 number).
 */
export function isValidPassword(password) {
  return password.length >= 8 && /[A-Z]/.test(password) && /[0-9]/.test(password);
}

/**
 * Validate coordinates.
 */
export function isValidCoordinates(lat, lon) {
  return lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
}

/**
 * Validate vehicle type.
 */
export function isValidVehicle(type) {
  const valid = ['walking', 'motorcycle', 'car', 'suv', 'ambulance', 'truck'];
  return valid.includes(type?.toLowerCase());
}

/**
 * Validate route K value (1-5).
 */
export function isValidK(k) {
  return Number.isInteger(k) && k >= 1 && k <= 5;
}
