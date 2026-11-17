import * as THREE from 'three'
import type { PositionSample } from '@sky/positioning'
import { continuous } from '../../utils/positionReplay.ts'
import { createRouteSymbol } from './citySymbols.ts'
export function createPositionOverlay(points: PositionSample[], world: (lon: number, lat: number, altitude: number) => THREE.Vector3, resolution: THREE.Vector2) {
  const group = new THREE.Group()
  let segment: THREE.Vector3[] = []
  const flush = () => {
    if (segment.length > 1) {
      const line = createRouteSymbol(segment, resolution)
      line.name = 'position-track'; line.material.color.setHex(0x6cf5be); line.material.dashed = false
      line.material.depthTest = false; line.renderOrder = 7; group.add(line)
    }
    segment = []
  }
  let previous: PositionSample | undefined
  for (const point of points) {
    if (!point.accepted) { flush(); previous = undefined; continue }
    if (previous && !continuous(previous, point)) flush()
    segment.push(world(point.longitude, point.latitude, point.altitude)); previous = point
  }
  flush(); return group
}
