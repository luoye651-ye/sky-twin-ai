import * as THREE from 'three'
import type { RouteSketch } from '@sky/routes'
import { createRouteSymbol } from './citySymbols.ts'
export function createRouteDraftOverlay(sketch: RouteSketch, world: (lon: number, lat: number, altitude: number) => THREE.Vector3, resolution: THREE.Vector2) {
  const group = new THREE.Group()
  const line = createRouteSymbol(sketch.points.map(p => world(p.longitude, p.latitude, p.altitude)), resolution)
  line.name = 'route-draft-line'; line.material.color.setHex(0xffdc66); line.material.dashed = false; line.material.depthTest = false; line.renderOrder = 4; group.add(line)
  sketch.waypoints.forEach((p, index) => {
    const marker = new THREE.Mesh(new THREE.SphereGeometry(index === sketch.selected ? 18 : 12, 12, 8), new THREE.MeshBasicMaterial({ color: index === sketch.selected ? 0xffffff : 0xffdc66, depthTest: false, toneMapped: false }))
    marker.name = `route-waypoint:${index}`; marker.position.copy(world(p.longitude, p.latitude, sketch.altitude)); marker.renderOrder = 9; group.add(marker)
  })
  return group
}
