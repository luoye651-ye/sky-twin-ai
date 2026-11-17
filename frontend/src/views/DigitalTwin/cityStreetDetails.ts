import * as THREE from 'three'
import { binjiangRoads } from './binjiangRoads.ts'
import { isInsideCity, toCityPosition, type CityModelManifest } from './cityCoordinates.ts'

export function createStreetDetails(model: THREE.Group, manifest: CityModelManifest) {
  const group = new THREE.Group()
  const buildings: THREE.Box3[] = []
  const roadHeights = new Map<string, number>()
  model.traverse(node => {
    if (node.userData.osmTags?.building) buildings.push(new THREE.Box3().setFromObject(node))
    if (node.userData.osmTags?.highway && node.userData.osmId) {
      const box = new THREE.Box3().setFromObject(node)
      roadHeights.set(node.userData.osmId, box.max.y)
    }
  })
  const positions: THREE.Vector3[] = []
  const directions: number[] = []
  for (const road of binjiangRoads) {
    for (let i = 1; i < road.points.length && positions.length < 180; i++) {
      const from = road.points[i - 1]!, to = road.points[i]!
      const a = toCityPosition(from[0], from[1], 0, manifest.origin), b = toCityPosition(to[0], to[1], 0, manifest.origin)
      const dx = b.x - a.x, dz = b.z - a.z, length = Math.hypot(dx, dz)
      const width = ['footway', 'cycleway', 'path'].includes(road.kind) ? 1.8 : 4.8
      for (let distance = 14; distance < length && positions.length < 180; distance += 38) {
        const t = distance / length
        if (!isInsideCity(from[0] + (to[0] - from[0]) * t, from[1] + (to[1] - from[1]) * t, manifest.bbox)) continue
        const x = a.x + dx * t - dz / length * width, z = a.z + dz * t + dx / length * width
        if (buildings.some(box => x > box.min.x - 1 && x < box.max.x + 1 && z > box.min.z - 1 && z < box.max.z + 1)) continue
        positions.push(new THREE.Vector3(x, (roadHeights.get(`w${road.id}`) ?? 0) + 0.15, z))
        directions.push(Math.atan2(-dz, dx))
      }
    }
  }
  const poleMaterial = new THREE.MeshStandardMaterial({ color: 0x5b6d76, metalness: 0.65, roughness: 0.3 })
  const poles = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.12, 0.18, 7.5, 6), poleMaterial, positions.length)
  const caps = new THREE.InstancedMesh(new THREE.BoxGeometry(1.6, 0.2, 0.8), poleMaterial, positions.length)
  const lightMaterial = new THREE.MeshBasicMaterial({ color: new THREE.Color(3.5, 2.1, 0.9), toneMapped: false })
  const lights = new THREE.InstancedMesh(new THREE.PlaneGeometry(1.3, 0.65), lightMaterial, positions.length)
  const dummy = new THREE.Object3D()
  positions.forEach((position, index) => {
    dummy.position.copy(position); dummy.position.y += 3.75; dummy.rotation.set(0, 0, 0); dummy.updateMatrix()
    poles.setMatrixAt(index, dummy.matrix)
    dummy.position.copy(position); dummy.position.y += 7.5; dummy.rotation.set(0, directions[index]!, 0); dummy.updateMatrix()
    caps.setMatrixAt(index, dummy.matrix)
    dummy.position.y -= 0.11; dummy.rotation.x = -Math.PI / 2; dummy.updateMatrix()
    lights.setMatrixAt(index, dummy.matrix)
  })
  group.add(poles, caps, lights)
  return { group, lights, count: positions.length }
}
