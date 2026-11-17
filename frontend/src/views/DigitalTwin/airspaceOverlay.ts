import * as THREE from 'three'
import type { AirspaceCheck, AirspaceZone } from '../../../../shared/airspace'
import { createRouteSymbol } from './citySymbols.ts'

/** Scene owner releases the geometries and materials of this code-native overlay. */
export function createAirspaceOverlay(zones: AirspaceZone[], check: AirspaceCheck | undefined,
  world: (longitude: number, latitude: number, altitude?: number) => THREE.Vector3, resolution: THREE.Vector2) {
  const group = new THREE.Group()
  for (const zone of zones) {
    const lower = zone.type === 'no_fly' ? zone.minAltitude : 0
    const a = world(zone.west, zone.south, lower), b = world(zone.east, zone.north, zone.maxAltitude)
    const color = !zone.activeNow ? 0x8196a5 : zone.type === 'no_fly' ? 0xff4c61 : 0xffbb45
    const geometry = new THREE.BoxGeometry(Math.abs(b.x - a.x), Math.max(.5, b.y - a.y), Math.abs(b.z - a.z))
    const object = new THREE.Group()
    object.name = `airspace:${zone.id}`
    object.position.copy(a).add(b).multiplyScalar(.5)
    const volume = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ color, transparent: true, opacity: zone.activeNow ? .15 : .035, depthWrite: false, side: THREE.DoubleSide, toneMapped: false }))
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), new THREE.LineBasicMaterial({ color, transparent: true, opacity: zone.activeNow ? .9 : .3, toneMapped: false }))
    object.add(volume, edges); group.add(object)
  }
  if (check) {
    const route = createRouteSymbol(check.route.map(point => world(point.longitude, point.latitude, point.altitude)), resolution)
    route.name = 'airspace-check-route'; route.material.dashed = false; route.material.depthTest = false
    route.renderOrder = 5; group.add(route)
    for (const violation of check.violations) {
      const points = [violation.from, violation.to].map(point => world(point.longitude, point.latitude, point.altitude))
      const line = createRouteSymbol(points, resolution)
      line.name = 'airspace-violation'; line.material.color.setHex(0xff294d)
      line.material.linewidth = 5; line.material.dashed = false; line.material.depthTest = false
      line.renderOrder = 6; group.add(line)
    }
  }
  return group
}
