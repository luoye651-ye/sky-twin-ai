export interface CityModelManifest {
  bbox: [number, number, number, number]
  origin: { lon: number; lat: number; ele: number }
  projection: 'MetricMapProjection'
}

// OSM2World MetricMapProjection + glTF exporter: east, up, south; all axes in metres.
const EARTH_CIRCUMFERENCE = 40075016.686
function mercatorY(latitude: number) {
  const sin = Math.sin(latitude * Math.PI / 180)
  return Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI) + 0.5
}

export function toCityPosition(lon: number, lat: number, altitude: number, origin: CityModelManifest['origin']) {
  const scale = EARTH_CIRCUMFERENCE * Math.cos(origin.lat * Math.PI / 180)
  return {
    x: (lon - origin.lon) / 360 * scale,
    y: altitude - origin.ele,
    z: -(mercatorY(lat) - mercatorY(origin.lat)) * scale,
  }
}
export function fromCityPosition(x: number, z: number, origin: CityModelManifest['origin']) {
  const scale = EARTH_CIRCUMFERENCE * Math.cos(origin.lat * Math.PI / 180)
  const y = mercatorY(origin.lat) - z / scale
  return { longitude: origin.lon + x / scale * 360, latitude: Math.atan(Math.sinh((y - .5) * 2 * Math.PI)) * 180 / Math.PI }
}

export function isInsideCity(lon: number, lat: number, bbox: CityModelManifest['bbox']) {
  return Number.isFinite(lon) && Number.isFinite(lat)
    && lon >= bbox[0] && lon <= bbox[2] && lat >= bbox[1] && lat <= bbox[3]
}

export function parseCityManifest(value: unknown): CityModelManifest {
  const data = value as Partial<CityModelManifest> | null
  if (!data || data.projection !== 'MetricMapProjection'
    || !Array.isArray(data.bbox) || data.bbox.length !== 4
    || !data.bbox.every(Number.isFinite)
    || data.bbox[0] >= data.bbox[2] || data.bbox[1] >= data.bbox[3]
    || data.bbox[0] < -180 || data.bbox[2] > 180 || data.bbox[1] <= -85 || data.bbox[3] >= 85
    || !data.origin || ![data.origin.lon, data.origin.lat, data.origin.ele].every(Number.isFinite)
    || !isInsideCity(data.origin.lon, data.origin.lat, data.bbox)) {
    throw new Error('模型坐标配置无效：需要 OSM2World 原点、范围和 MetricMapProjection')
  }
  return data as CityModelManifest
}
