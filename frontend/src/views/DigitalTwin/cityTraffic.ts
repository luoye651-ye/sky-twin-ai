import * as THREE from 'three'
import type { RegionRoad } from './cityRegionData.ts'

// Presentation-only population: keep GPU submissions bounded with two instanced meshes.
export const CITY_TRAFFIC_BUDGET = 6000
const VEHICLE_SPACING = 65
const MAX_VEHICLES_PER_ROAD = 16

/** Illustrative vehicles on real road centrelines; independent of Java aircraft/task state. */
export function createCityTraffic(roads: RegionRoad[]) {
  const paths = roads.filter(r => !['footway', 'cycleway', 'service'].includes(r.kind)).map(road => {
    const cumulative = [0]
    for (let i = 1; i < road.points.length; i++) cumulative.push(cumulative[i - 1]! + Math.hypot(road.points[i]![0] - road.points[i - 1]![0], road.points[i]![1] - road.points[i - 1]![1]))
    return { road, cumulative, length: cumulative[cumulative.length - 1]! }
  }).filter(path => path.length > 200).sort((a, b) => {
    // Spread the capped population over the extract instead of favouring early OSM IDs.
    const hash = (id: string) => (Math.imul(Number(id.slice(1)), 2654435761) >>> 0)
    return hash(a.road.id) - hash(b.road.id)
  })
  const agents = paths.flatMap((path, index) => Array.from({ length: Math.min(MAX_VEHICLES_PER_ROAD, Math.floor(path.length / VEHICLE_SPACING)) }, (_, i) => ({
    path, start: (i + .4) / Math.min(MAX_VEHICLES_PER_ROAD, Math.floor(path.length / VEHICLE_SPACING)) * path.length,
    speed: 7 + index % 7, reverse: path.road.oneway === '-1' || (path.road.oneway === 'no' && i % 2 === 1),
  }))).slice(0, CITY_TRAFFIC_BUDGET)
  const group = new THREE.Group()
  const body = new THREE.InstancedMesh(new THREE.BoxGeometry(2, 1.35, 4.7), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: .3, metalness: .45 }), agents.length)
  const cabin = new THREE.InstancedMesh(new THREE.BoxGeometry(1.7, .8, 2.3), new THREE.MeshStandardMaterial({ color: 0x233d4d, roughness: .2, metalness: .6 }), agents.length)
  body.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
  cabin.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
  const palette = [0xe8e9df, 0x283a45, 0x8f4141, 0x5a82a5, 0xe1bc71]
  agents.forEach((_, index) => body.setColorAt(index, new THREE.Color(palette[index % palette.length]!)))
  group.add(body, cabin)
  const dummy = new THREE.Object3D()
  function animate(time: number) {
    agents.forEach((agent, index) => {
      let distance = (agent.start + time * agent.speed) % agent.path.length
      if (agent.reverse) distance = agent.path.length - distance
      const { road, cumulative } = agent.path
      let segment = 1
      while (segment < cumulative.length - 1 && cumulative[segment]! < distance) segment++
      const a = road.points[segment - 1]!, b = road.points[segment]!, length = cumulative[segment]! - cumulative[segment - 1]!
      const t = length ? (distance - cumulative[segment - 1]!) / length : 0
      const dx = b[0] - a[0], dz = b[1] - a[1], l = Math.hypot(dx, dz) || 1
      const lane = (agent.reverse ? -1 : 1) * Math.min(road.width * .22, 2.8)
      dummy.position.set(a[0] + dx * t - dz / l * lane, road.height + .8, a[1] + dz * t + dx / l * lane)
      dummy.rotation.set(0, Math.atan2(dx, dz) + (agent.reverse ? Math.PI : 0), 0); dummy.updateMatrix(); body.setMatrixAt(index, dummy.matrix)
      dummy.position.y += .85; dummy.updateMatrix(); cabin.setMatrixAt(index, dummy.matrix)
    })
    body.instanceMatrix.needsUpdate = cabin.instanceMatrix.needsUpdate = true
  }
  animate(0)
  return { group, count: agents.length, animate }
}
