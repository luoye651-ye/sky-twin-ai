import type { PositionSample } from '@sky/positioning'
export type PositionPoint = Pick<PositionSample, 'longitude' | 'latitude' | 'altitude'>
export function simulatedPosition(origin: PositionPoint, seconds: number): PositionPoint {
  return { longitude: origin.longitude + .0008 * Math.sin(seconds / 12), latitude: origin.latitude + .0006 * (1 - Math.cos(seconds / 12)), altitude: origin.altitude + 20 * Math.sin(seconds / 20) }
}
/** Never interpolate across device sessions or a positioning outage. */
export function continuous(a: PositionSample, b: PositionSample) {
  const delta = Date.parse(b.sampledAt) - Date.parse(a.sampledAt)
  return a.sessionId === b.sessionId && delta > 0 && delta <= 5000
}
export function replayPoint(points: PositionSample[], at: number): (PositionPoint & { held: boolean }) | undefined {
  if (!points.length) return undefined
  const index = points.findIndex(point => Date.parse(point.sampledAt) > at)
  const a = points[index < 0 ? points.length - 1 : Math.max(0, index - 1)]!
  const b = index > 0 ? points[index] : undefined
  if (!b || !continuous(a, b)) return { longitude: a.longitude, latitude: a.latitude, altitude: a.altitude, held: at > Date.parse(a.sampledAt) }
  const p = Math.max(0, Math.min(1, (at - Date.parse(a.sampledAt)) / (Date.parse(b.sampledAt) - Date.parse(a.sampledAt))))
  return { longitude: a.longitude + (b.longitude - a.longitude) * p, latitude: a.latitude + (b.latitude - a.latitude) * p, altitude: a.altitude + (b.altitude - a.altitude) * p, held: false }
}
