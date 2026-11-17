import * as THREE from 'three'
import { createRouteSymbol } from './citySymbols.ts'
import type { FlightNavigationDisplay } from '../../types/flightNavigation'
import { remainingFlightPoints } from '../../utils/flightNavigation.ts'

export function createFlightNavigationOverlay(display: FlightNavigationDisplay,
  world: (lon: number, lat: number, altitude: number) => THREE.Vector3, resolution: THREE.Vector2,
  inside: (lon: number, lat: number) => boolean = () => true) {
  const group = new THREE.Group()
  group.name = `flight-navigation:${display.taskId}`
  // Never relocate an out-of-range route into a fake in-range route.
  if (!display.points.every(p => inside(p.longitude, p.latitude))) return group
  const vector = (p: { longitude: number; latitude: number; altitude: number }) => world(p.longitude, p.latitude, p.altitude)
  function line(name: string, points: THREE.Vector3[], color: number, dashed: boolean, width: number) {
    if (points.length < 2) return
    const symbol = createRouteSymbol(points, resolution)
    symbol.name = name; symbol.material.color.setHex(color); symbol.material.dashed = dashed
    symbol.material.linewidth = width; symbol.material.depthTest = false; symbol.material.depthWrite = false
    symbol.renderOrder = 10; group.add(symbol)
  }
  line('navigation-planned', display.points.map(vector), 0x38cfff, true, 2)
  line('navigation-remaining', remainingFlightPoints(display).map(vector), 0xffc857, true, 4)
  // Only saved Java points are flown history, never a fabricated progress curve.
  let segment: THREE.Vector3[] = []
  for (const point of display.tracks) {
    if (inside(point.longitude, point.latitude)) segment.push(vector(point))
    else { line('navigation-flown', segment, 0x33e8a5, false, 4); segment = [] }
  }
  line('navigation-flown', segment, 0x33e8a5, false, 4)
  function marker(name: string, position: THREE.Vector3, color: number, radius: number) {
    const object = new THREE.Mesh(new THREE.SphereGeometry(radius, 12, 8),
      new THREE.MeshBasicMaterial({ color, depthTest: false, depthWrite: false, toneMapped: false }))
    object.name = name; object.position.copy(position); object.renderOrder = 12; group.add(object)
  }
  marker('navigation-start', vector(display.points[0]!), 0x38cfff, 13)
  marker('navigation-end', vector(display.points[display.points.length - 1]!), 0xffc857, 17)
  const current = vector(display.navigation.position)
  marker('navigation-current', current, 0xffffff, 11)
  const ahead = remainingFlightPoints(display).map(vector).find(p => Math.hypot(p.x - current.x, p.z - current.z) > 1)
  if (ahead) {
    const direction = ahead.clone().sub(current); direction.y = 0; direction.normalize()
    const arrow = new THREE.Mesh(new THREE.ConeGeometry(14, 40, 8),
      new THREE.MeshBasicMaterial({ color: 0xffc857, depthTest: false, depthWrite: false, toneMapped: false }))
    arrow.name = 'navigation-heading'; arrow.position.copy(current).addScaledVector(direction, 40)
    arrow.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction); arrow.renderOrder = 12; group.add(arrow)
  }
  return group
}
