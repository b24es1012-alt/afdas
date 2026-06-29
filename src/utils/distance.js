const EARTH_RADIUS_KM = 6371;

/**
 * Haversine distance between two points in km.
 */
export function haversineKm(lat1, lon1, lat2, lon2) {
  const toRad = (deg) => (deg * Math.PI) / 180;

  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;

  const c = 2 * Math.asin(Math.sqrt(a));
  return EARTH_RADIUS_KM * c;
}

/**
 * Haversine distance in meters.
 */
export function haversineMeters(lat1, lon1, lat2, lon2) {
  return haversineKm(lat1, lon1, lat2, lon2) * 1000;
}

/**
 * Find nearest point from a list.
 */
export function findNearest(targetLat, targetLon, points) {
  let minDist = Infinity;
  let nearest = null;
  let nearestIdx = -1;

  points.forEach((point, idx) => {
    const dist = haversineKm(targetLat, targetLon, point.lat, point.lon);
    if (dist < minDist) {
      minDist = dist;
      nearest = point;
      nearestIdx = idx;
    }
  });

  return { point: nearest, index: nearestIdx, distanceKm: minDist };
}

/**
 * Calculate bearing between two points (degrees).
 */
export function bearing(lat1, lon1, lat2, lon2) {
  const toRad = (deg) => (deg * Math.PI) / 180;
  const toDeg = (rad) => (rad * 180) / Math.PI;

  const dLon = toRad(lon2 - lon1);
  const y = Math.sin(dLon) * Math.cos(toRad(lat2));
  const x =
    Math.cos(toRad(lat1)) * Math.sin(toRad(lat2)) -
    Math.sin(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.cos(dLon);

  return (toDeg(Math.atan2(y, x)) + 360) % 360;
}
