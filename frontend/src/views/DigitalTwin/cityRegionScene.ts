import * as THREE from 'three'
import { facadeMaterial, type CityAppearance } from './cityAppearance.ts'
import type { CityRegion, MapRings } from './cityRegionData.ts'
import { geometry, pushRoad, pushSurface, pushWalls, triangulate } from './cityRegionGeometry.ts'
import { createCityTraffic } from './cityTraffic.ts'
import { toCityPosition } from './cityCoordinates.ts'

/** Metre geometry batched by 2km cell/material; scene owner releases all GPU resources. */
export async function createRegionScene(data: CityRegion, signal: AbortSignal) {
  const model = new THREE.Group(), details = new THREE.Group()
  model.name = data.title
  const night = { value: 1 }, time = { value: 0 }
  const walls = [facadeMaterial(0x6b7987, 0x24415b, night), facadeMaterial(0x9d9d94, 0x354954, night), facadeMaterial(0x3e596b, 0x20435b, night)]
  walls.forEach(m => { m.side = THREE.DoubleSide })
  const roof = new THREE.MeshStandardMaterial({ color: 0x8b969c, roughness: .8, side: THREE.DoubleSide })
  const source = new THREE.MeshStandardMaterial({ color: 0xa2adb1, roughness: 1, side: THREE.DoubleSide })
  const materials: Record<string, THREE.Material> = {
    roof, wall0: walls[0]!, wall1: walls[1]!, wall2: walls[2]!,
    green: new THREE.MeshStandardMaterial({ color: 0x45694c, roughness: 1, side: THREE.DoubleSide }),
    residential: new THREE.MeshStandardMaterial({ color: 0x65756f, roughness: 1, side: THREE.DoubleSide }),
    commercial: new THREE.MeshStandardMaterial({ color: 0x738082, roughness: 1, side: THREE.DoubleSide }),
    industrial: new THREE.MeshStandardMaterial({ color: 0x6b7475, roughness: 1, side: THREE.DoubleSide }),
    retail: new THREE.MeshStandardMaterial({ color: 0x7a7d72, roughness: 1, side: THREE.DoubleSide }),
    road: new THREE.MeshStandardMaterial({ color: 0x3e4953, roughness: .9, side: THREE.DoubleSide }),
    path: new THREE.MeshStandardMaterial({ color: 0x9a9b85, roughness: .95, side: THREE.DoubleSide }),
    markings: new THREE.MeshBasicMaterial({ color: 0xc4c1a8, side: THREE.DoubleSide }),
  }
  const water = new THREE.MeshStandardMaterial({ color: 0x236c83, roughness: .25, metalness: .45, side: THREE.DoubleSide })
  water.onBeforeCompile = shader => {
    shader.uniforms.regionTime = time
    shader.vertexShader = shader.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 regionWater;')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nregionWater = (modelMatrix * vec4(transformed, 1.0)).xyz;')
    shader.fragmentShader = shader.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 regionWater;\nuniform float regionTime;')
      .replace('#include <normal_fragment_maps>', '#include <normal_fragment_maps>\nnormal = normalize(normal + vec3(sin(regionWater.x*.14 + regionWater.z*.19 + regionTime*.8)*.035, cos(regionWater.z*.17-regionTime*.6)*.025, 0.0));')
  }
  water.customProgramCacheKey = () => 'skytwin-region-water-v1'
  materials.water = water
  for (const [kind, material] of Object.entries(materials)) {
    if (material instanceof THREE.MeshStandardMaterial || material instanceof THREE.MeshBasicMaterial) {
      if (!/wall|roof/.test(kind)) { material.polygonOffset = true; material.polygonOffsetFactor = kind === 'markings' ? -5 : kind === 'road' || kind === 'path' ? -4 : kind === 'water' ? -3 : kind === 'green' ? -2 : -1; material.polygonOffsetUnits = material.polygonOffsetFactor }
    }
  }
  const min = toCityPosition(data.bbox[0], data.bbox[1], 0, data.origin), max = toCityPosition(data.bbox[2], data.bbox[3], 0, data.origin)
  const span = Math.max(max.x - min.x, min.z - max.z)
  const batchCellSize = span > 35000 ? 6000 : 2000
  const batches = new Map<string, { kind: string; positions: number[] }>()
  function batch(kind: string, rings: MapRings) {
    const p = rings[0]![0]!, key = `${Math.floor(p[0] / batchCellSize)},${Math.floor(p[1] / batchCellSize)},${kind}`
    let entry = batches.get(key)
    if (!entry) { entry = { kind, positions: [] }; batches.set(key, entry) }
    return entry.positions
  }
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(max.x - min.x, min.z - max.z), new THREE.MeshStandardMaterial({ color: 0x607567, roughness: 1 }))
  ground.rotation.x = -Math.PI / 2; ground.position.set((min.x + max.x) / 2, -.2, (min.z + max.z) / 2); model.add(ground)
  for (const area of data.areas) pushSurface(batch(area.kind, area.rings), area.rings, area.kind === 'water' ? .12 : .04)
  const roofs: THREE.Vector3[] = []
  for (let i = 0; i < data.buildings.length; i++) {
    if (signal.aborted) {
      ground.geometry.dispose(); ground.material.dispose()
      new Set([...Object.values(materials), source]).forEach(m => m.dispose())
      throw new DOMException('Aborted', 'AbortError')
    }
    const b = data.buildings[i]!
    pushSurface(batch('roof', b.rings), b.rings, b.height)
    const style = Number(b.id.replace(/\D/g, '').slice(-4)) % 3
    pushWalls(batch(`wall${style}`, b.rings), b.rings, b.height)
    if (b.height >= 40 && roofs.length < 1500) {
      const { points, triangles } = triangulate(b.rings), t = triangles[0]
      if (t) roofs.push(new THREE.Vector3(t.reduce((sum, j) => sum + points[j]![0], 0) / 3, b.height + 1.2, t.reduce((sum, j) => sum + points[j]![1], 0) / 3))
    }
    // Yield between CPU batches; aborted results have not created GPU resources yet.
    if (i % 250 === 249) await new Promise<void>(resolve => setTimeout(resolve, 0))
  }
  const lamps: THREE.Vector3[] = [], piers: THREE.Vector3[] = []
  let seed = 719, seenLamps = 0, seenTrees = 0
  const random = () => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 4294967296 }
  for (const road of data.roads) {
    const path = ['footway', 'cycleway'].includes(road.kind)
    pushRoad(batch(path ? 'path' : 'road', [road.points]), road.points, road.width, road.height)
    for (let i = 1; i < road.points.length; i++) {
      const a = road.points[i - 1]!, b = road.points[i]!, dx = b[0] - a[0], dz = b[1] - a[1], length = Math.hypot(dx, dz)
      if (!path && road.width >= 7) for (let d = 0; d < length; d += 18) {
        const end = Math.min(d + 5, length)
        pushRoad(batch('markings', [road.points]), [[a[0] + dx * d / length, a[1] + dz * d / length], [a[0] + dx * end / length, a[1] + dz * end / length]], .25, road.height + .035)
      }
      if (length > 80 && road.width >= 10) for (let d = 40; d < length; d += 90) {
        const p = new THREE.Vector3(a[0] + dx * d / length - dz / length * road.width / 2, road.height, a[1] + dz * d / length + dx / length * road.width / 2)
        seenLamps++
        if (lamps.length < 2400) lamps.push(p)
        else { const index = Math.floor(random() * seenLamps); if (index < 2400) lamps[index] = p }
      }
      if (road.bridge && length > 70) for (let d = 35; d < length; d += 100) piers.push(new THREE.Vector3(a[0] + dx * d / length, road.height / 2, a[1] + dz * d / length))
    }
  }
  const buildingMeshes: THREE.Mesh[] = []
  for (const entry of batches.values()) {
    if (!entry.positions.length) continue
    const mesh = new THREE.Mesh(geometry(entry.positions), materials[entry.kind]!)
    mesh.name = entry.kind
    if (/wall|roof/.test(entry.kind)) buildingMeshes.push(mesh)
    model.add(mesh)
  }
  const batchCount = batches.size
  // Float32BufferAttribute owns copies; release the temporary JS number arrays.
  batches.clear()
  function instances(geo: THREE.BufferGeometry, mat: THREE.Material, positions: THREE.Vector3[], offset: number) {
    const mesh = new THREE.InstancedMesh(geo, mat, positions.length), dummy = new THREE.Object3D()
    positions.forEach((p, i) => { dummy.position.copy(p); dummy.position.y += offset; dummy.updateMatrix(); mesh.setMatrixAt(i, dummy.matrix) })
    details.add(mesh)
    return mesh
  }
  instances(new THREE.BoxGeometry(3.6, 2.4, 3), new THREE.MeshStandardMaterial({ color: 0xb0b9b9, roughness: .6 }), roofs, 0)
  instances(new THREE.BoxGeometry(4, 16, 4), new THREE.MeshStandardMaterial({ color: 0xa0acae, roughness: .8 }), piers, 0)
  const trees: THREE.Vector3[] = []
  for (const area of data.areas.filter(a => a.kind === 'green')) {
    const { points, triangles } = triangulate(area.rings)
    for (const t of triangles) {
      const a = points[t[0]!]!, b = points[t[1]!]!, c = points[t[2]!]!
      const size = Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
      for (let i = 0; i < Math.min(80, Math.floor(size / 350)); i++) {
        const u = Math.sqrt(random()), v = random()
        const p = new THREE.Vector3(a[0] * (1 - u) + b[0] * u * (1 - v) + c[0] * u * v, 0, a[1] * (1 - u) + b[1] * u * (1 - v) + c[1] * u * v)
        seenTrees++
        if (trees.length < 8000) trees.push(p)
        else { const index = Math.floor(random() * seenTrees); if (index < 8000) trees[index] = p }
      }
    }
  }
  instances(new THREE.CylinderGeometry(.35, .5, 7, 5), new THREE.MeshStandardMaterial({ color: 0x554a3c }), trees, 3.5)
  const canopy = instances(new THREE.IcosahedronGeometry(4.5, 1), new THREE.MeshStandardMaterial({ color: 0x63875a, roughness: .9 }), trees, 8)
  trees.forEach((_, i) => canopy.setColorAt(i, new THREE.Color().setHSL(.28 + random() * .08, .25, .22 + random() * .12)))
  instances(new THREE.CylinderGeometry(.2, .3, 9, 5), new THREE.MeshStandardMaterial({ color: 0x74848a, roughness: .6 }), lamps, 4.5)
  const glow = instances(new THREE.SphereGeometry(.7, 5, 4), new THREE.MeshBasicMaterial({ color: new THREE.Color(3, 2.1, .9), toneMapped: false }), lamps, 9)
  const traffic = createCityTraffic(data.roads)
  details.add(traffic.group)
  for (const polygon of data.districtBoundary) {
    const positions = [...polygon[0]!, polygon[0]![0]!].map(p => new THREE.Vector3(p[0], .7, p[1]))
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(positions), new THREE.LineDashedMaterial({ color: 0x39a6af, dashSize: 50, gapSize: 30, transparent: true, opacity: .55 }))
    line.computeLineDistances(); model.add(line)
  }
  model.add(details)
  let trafficVisible = true
  function setMode(mode: CityAppearance) {
    night.value = mode === 'dusk' ? 1 : 0
    details.visible = mode !== 'source'
    glow.visible = mode === 'dusk'
    buildingMeshes.forEach(mesh => { mesh.material = mode === 'source' ? source : materials[mesh.name]! })
    traffic.group.visible = trafficVisible
  }
  setMode('dusk')
  // Attach otherwise-unused source material to the release traversal without drawing it.
  const resource = new THREE.Mesh(new THREE.BufferGeometry(), source); resource.visible = false; model.add(resource)
  return {
    model, details, setMode,
    animate: (elapsed: number) => { time.value = elapsed; if (trafficVisible) traffic.animate(elapsed) },
    setTraffic: (visible: boolean) => { trafficVisible = visible; traffic.group.visible = visible },
    // Restore all styled materials so traversal also releases them after source mode.
    dispose: () => { setMode('day') },
    counts: { trees: trees.length, roofEquipment: roofs.length, streetLights: lamps.length, vehicles: traffic.count, buildings: data.buildings.length, batches: batchCount, batchCellSize },
  }
}
