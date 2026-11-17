import * as THREE from 'three'
import type { MapPoint, MapRings } from './cityRegionData.ts'

export function triangulate(rings: MapRings) {
  const vectors = rings.map(ring => ring.map(p => new THREE.Vector2(p[0], p[1])))
  return { points: rings.flat(), triangles: THREE.ShapeUtils.triangulateShape(vectors[0]!, vectors.slice(1)) }
}
export function pushSurface(output: number[], rings: MapRings, y: number) {
  const { points, triangles } = triangulate(rings)
  for (const indices of triangles) {
    // Y-up needs the reverse winding of the x,z plane.
    for (const i of [indices[0]!, indices[2]!, indices[1]!]) { const p = points[i]!; output.push(p[0], y, p[1]) }
  }
}
export function pushWalls(output: number[], rings: MapRings, height: number) {
  for (const ring of rings) for (let i = 0; i < ring.length; i++) {
    const a = ring[i]!, b = ring[(i + 1) % ring.length]!
    output.push(a[0], 0, a[1], b[0], 0, b[1], b[0], height, b[1], a[0], 0, a[1], b[0], height, b[1], a[0], height, a[1])
  }
}
export function pushRoad(output: number[], points: MapPoint[], width: number, y: number) {
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1]!, b = points[i]!, dx = b[0] - a[0], dz = b[1] - a[1], length = Math.hypot(dx, dz)
    if (length < .05) continue
    const x = -dz / length * width / 2, z = dx / length * width / 2
    output.push(a[0] + x, y, a[1] + z, b[0] + x, y, b[1] + z, b[0] - x, y, b[1] - z,
      a[0] + x, y, a[1] + z, b[0] - x, y, b[1] - z, a[0] - x, y, a[1] - z)
  }
}
export function geometry(positions: number[]) {
  const result = new THREE.BufferGeometry()
  result.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  result.computeVertexNormals(); result.computeBoundingSphere()
  return result
}
