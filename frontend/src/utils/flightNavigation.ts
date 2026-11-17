import type { Task, Track } from '@sky/sky'
import type { AirspacePoint } from '@sky/airspace'
import type { FlightNavigationDisplay } from '../types/flightNavigation'

export function validFlightPoint(point: { longitude: number; latitude: number; altitude: number }) {
  return Number.isFinite(point.longitude) && Math.abs(point.longitude) <= 180
    && Number.isFinite(point.latitude) && Math.abs(point.latitude) <= 90 && Number.isFinite(point.altitude)
}

/** Never substitute another aircraft's later mission position for this task's position. */
export function flightNavigationDisplay(task: Task | undefined, tracks: Track[]): FlightNavigationDisplay | undefined {
  const nav = task?.navigation, points = task?.routePoints
  if (!task || !nav || !points || points.length < 2 || !validFlightPoint(nav.position)
    || !Number.isFinite(nav.position.offsetSeconds) || !points.every(p => validFlightPoint(p) && Number.isFinite(p.offsetSeconds))
    || ![nav.remainingRouteMeters, nav.destinationDistanceMeters, nav.remainingSimulationSeconds].every(n => Number.isFinite(n) && n >= 0)) return undefined
  return { taskId: task.id, status: task.status, points, navigation: nav, tracks: tracks.filter(validFlightPoint) }
}

export function remainingFlightPoints(display: FlightNavigationDisplay): AirspacePoint[] {
  return [display.navigation.position, ...display.points.filter(p => p.offsetSeconds > display.navigation.position.offsetSeconds)]
}

export function formatFlightDistance(meters: number) {
  if (!Number.isFinite(meters) || meters < 0) return '—'
  return meters >= 1000 ? `${(meters / 1000).toFixed(2)} km` : `${Math.round(meters)} m`
}
