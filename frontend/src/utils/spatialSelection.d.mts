export interface GeoBounds { minLon: number; maxLon: number; minLat: number; maxLat: number }
export interface GeoPoint { longitude: number; latitude: number }
export function boundsFromPoints(a: GeoPoint, b: GeoPoint): GeoBounds
export function inBounds(point: GeoPoint, box: GeoBounds): boolean
