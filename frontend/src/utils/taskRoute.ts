import type { AirspacePoint } from '@sky/airspace'
import type { RoutePlan, RouteSketch, RouteWaypoint } from '@sky/routes'
export function routePoint(points: AirspacePoint[], seconds: number): AirspacePoint | undefined {
  if (!points.length) return undefined
  if (seconds <= 0) return points[0]
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1]!, b = points[i]!
    if (seconds <= b.offsetSeconds) {
      const f = Math.max(0, Math.min(1, (seconds - a.offsetSeconds) / (b.offsetSeconds - a.offsetSeconds)))
      return { longitude: a.longitude + (b.longitude - a.longitude) * f, latitude: a.latitude + (b.latitude - a.latitude) * f, altitude: a.altitude + (b.altitude - a.altitude) * f, offsetSeconds: seconds }
    }
  }
  return points[points.length - 1]
}
export function routeSketch(plan: RoutePlan, via: RouteWaypoint[], selected: number): RouteSketch {
  const from = plan.points[0]!, to = plan.points[plan.points.length - 1]!
  return { points: [{ ...from, altitude: 0 }, { ...from, altitude: plan.cruiseAltitude }, ...via.map(p => ({ ...p, altitude: plan.cruiseAltitude })), { ...to, altitude: plan.cruiseAltitude }, { ...to, altitude: 0 }], waypoints: via, altitude: plan.cruiseAltitude, selected }
}
