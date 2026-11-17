export function boundsFromPoints(a, b) {
  if (![a?.longitude,a?.latitude,b?.longitude,b?.latitude].every(Number.isFinite)) throw new Error('框选坐标无效')
  const box = { minLon: Math.min(a.longitude,b.longitude), maxLon: Math.max(a.longitude,b.longitude), minLat: Math.min(a.latitude,b.latitude), maxLat: Math.max(a.latitude,b.latitude) }
  if (box.minLon < -180 || box.maxLon > 180 || box.minLat < -90 || box.maxLat > 90 || box.minLon === box.maxLon || box.minLat === box.maxLat) throw new Error('请框选有效的矩形区域')
  return box
}
export function inBounds(point, box) { return Number.isFinite(point?.longitude) && Number.isFinite(point?.latitude) && point.longitude >= box.minLon && point.longitude <= box.maxLon && point.latitude >= box.minLat && point.latitude <= box.maxLat }
