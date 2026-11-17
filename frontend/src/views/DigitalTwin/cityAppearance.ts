import * as THREE from 'three'
import type { CityModelManifest } from './cityCoordinates'
import { createStreetDetails } from './cityStreetDetails.ts'

export type CityAppearance = 'dusk' | 'day' | 'source'

function seedRandom(seed: number) {
  return () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0
    return seed / 4294967296
  }
}

function hashName(name: string) {
  let result = 17
  for (const char of name) result = Math.imul(result, 31) + char.charCodeAt(0)
  return result >>> 0
}

function isBuilding(node: THREE.Object3D) {
  // GLTFLoader sanitizes spaces to underscores. Prefer semantic tags over display names.
  return !!(node.userData.osmTags?.building || node.userData.osmTags?.['building:part']) || /^Building[ _]/.test(node.name)
}

// Surface coordinates, rather than UVs, keep floor/window dimensions consistent in metres.
export function facadeMaterial(color: number, glass: number, night: { value: number }) {
  const material = new THREE.MeshStandardMaterial({ color, roughness: 0.38, metalness: 0.35 })
  material.onBeforeCompile = shader => {
    shader.uniforms.twinNight = night
    shader.uniforms.twinGlass = { value: new THREE.Color(glass) }
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 twinPosition;\nvarying vec3 twinNormal;')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\ntwinPosition = (modelMatrix * vec4(transformed, 1.0)).xyz;\ntwinNormal = normalize(mat3(modelMatrix) * objectNormal);')
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>
        varying vec3 twinPosition;
        varying vec3 twinNormal;
        uniform float twinNight;
        uniform vec3 twinGlass;
        float twinHash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      `)
      .replace('#include <map_fragment>', `#include <map_fragment>
        float facadeAxis = abs(twinNormal.x) > abs(twinNormal.z) ? twinPosition.z : twinPosition.x;
        vec2 facadeGrid = vec2(facadeAxis / 2.9, twinPosition.y / 3.25);
        vec2 cell = fract(facadeGrid);
        vec2 aa = max(fwidth(facadeGrid) * 0.8, vec2(0.008));
        vec2 edgeLow = smoothstep(vec2(0.13, 0.19) - aa, vec2(0.13, 0.19) + aa, cell);
        vec2 edgeHigh = 1.0 - smoothstep(vec2(0.87, 0.83) - aa, vec2(0.87, 0.83) + aa, cell);
        float windowMask = edgeLow.x * edgeLow.y * edgeHigh.x * edgeHigh.y * (1.0 - step(0.5, abs(twinNormal.y)));
        float room = twinHash(floor(facadeGrid / vec2(2.0, 3.0)));
        float roomLit = step(0.90, room) * twinNight;
        vec3 litGlass = mix(vec3(0.28, 0.53, 0.7), vec3(1.0, 0.62, 0.28), step(0.96, room));
        vec3 pane = mix(twinGlass * (0.75 + room * 0.25), litGlass * 0.35, roomLit);
        diffuseColor.rgb = mix(diffuseColor.rgb, pane, windowMask);
        float floorBand = 1.0 - smoothstep(0.015, 0.055, min(cell.y, 1.0 - cell.y));
        diffuseColor.rgb *= 1.0 - floorBand * 0.22;
      `)
      .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor = mix(roughnessFactor, 0.2, windowMask);')
      .replace('#include <metalnessmap_fragment>', '#include <metalnessmap_fragment>\nmetalnessFactor = mix(metalnessFactor, 0.65, windowMask);')
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += litGlass * windowMask * roomLit * 0.65;')
  }
  material.customProgramCacheKey = () => 'skytwin-facade-v1'
  return material
}

function sampleSurface(mesh: THREE.Mesh, count: number, random: () => number) {
  const position = mesh.geometry.getAttribute('position')
  const index = mesh.geometry.getIndex()
  const triangles: { a: THREE.Vector3; b: THREE.Vector3; c: THREE.Vector3; area: number }[] = []
  let area = 0
  const edges = new THREE.Vector3(), second = new THREE.Vector3()
  for (let i = 0; i < (index?.count ?? position.count); i += 3) {
    const points = [0, 1, 2].map(offset => new THREE.Vector3().fromBufferAttribute(position, index ? index.getX(i + offset) : i + offset).applyMatrix4(mesh.matrixWorld))
    edges.subVectors(points[1]!, points[0]!).cross(second.subVectors(points[2]!, points[0]!))
    const triangleArea = edges.length() / 2
    if (triangleArea < 0.01 || Math.abs(edges.normalize().y) < 0.8) continue
    area += triangleArea
    triangles.push({ a: points[0]!, b: points[1]!, c: points[2]!, area })
  }
  const samples: THREE.Vector3[] = []
  for (let i = 0; i < count && triangles.length; i++) {
    const pick = random() * area
    const triangle = triangles.find(t => t.area >= pick)!
    const u = Math.sqrt(random()), v = random()
    samples.push(triangle.a.clone().multiplyScalar(1 - u).addScaledVector(triangle.b, u * (1 - v)).addScaledVector(triangle.c, u * v))
  }
  return { samples, area }
}

/** Procedural visual detail only: preserves the GLB geometry, transform and OSM metadata. */
export function createCityAppearance(model: THREE.Group, manifest?: CityModelManifest) {
  const details = new THREE.Group()
  details.name = 'Simulation appearance details'
  const night = { value: 1 }
  const time = { value: 0 }
  const originals = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>()
  const replacements = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>()
  const ownedMaterials = new Set<THREE.Material>()
  const clones = new Map<THREE.Material, THREE.MeshStandardMaterial>()
  const facade = [facadeMaterial(0x6b7987, 0x24415b, night), facadeMaterial(0x8c9193, 0x263c4b, night), facadeMaterial(0x344f65, 0x20435b, night)]
  facade.forEach(material => ownedMaterials.add(material))
  const roof = new THREE.MeshStandardMaterial({ color: 0x4e5a65, roughness: 0.85, metalness: 0.12 })
  ownedMaterials.add(roof)
  const paving = new THREE.MeshStandardMaterial({ color: 0x657976, roughness: 0.96 })
  ownedMaterials.add(paving)
  const water = new THREE.MeshStandardMaterial({ color: 0x1a697a, roughness: 0.24, metalness: 0.6 })
  water.onBeforeCompile = shader => {
    shader.uniforms.twinTime = time
    shader.vertexShader = shader.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 waterPosition;')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nwaterPosition = (modelMatrix * vec4(transformed, 1.0)).xyz;')
    shader.fragmentShader = shader.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 waterPosition;\nuniform float twinTime;')
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
        float rippleX = sin(waterPosition.x * 0.32 + waterPosition.z * 0.21 + twinTime * 0.65);
        float rippleZ = cos(waterPosition.z * 0.44 - waterPosition.x * 0.13 + twinTime * 0.4);
        normal = normalize(normal + vec3(rippleX * 0.1, rippleZ * 0.07, 0.0));
      `)
  }
  water.customProgramCacheKey = () => 'skytwin-water-v1'
  ownedMaterials.add(water)

  const random = seedRandom(20261011)
  const trees: THREE.Vector3[] = []
  const roofs: { position: THREE.Vector3; scale: THREE.Vector3; angle: number }[] = []
  const originalTrees: THREE.Object3D[] = []
  model.updateMatrixWorld(true)
  const bounds = new THREE.Box3().setFromObject(model)
  if (!bounds.isEmpty()) {
    const size = bounds.getSize(new THREE.Vector3())
    const base = new THREE.Mesh(new THREE.BoxGeometry(size.x + 8, 3, size.z + 8), new THREE.MeshStandardMaterial({ color: 0x334b57, roughness: 0.9 }))
    base.position.copy(bounds.getCenter(new THREE.Vector3())); base.position.y = bounds.min.y - 1.65
    base.receiveShadow = true
    details.add(base)
  }
  const street = manifest ? createStreetDetails(model, manifest) : undefined
  if (street) details.add(street.group)
  model.traverse(node => {
    if (/^Tree[ _]/.test(node.name)) {
      originalTrees.push(node)
      const bounds = new THREE.Box3().setFromObject(node)
      const center = bounds.getCenter(new THREE.Vector3()); center.y = bounds.min.y
      trees.push(center)
    }
    if (!(node instanceof THREE.Mesh)) return
    originals.set(node, node.material)
    let building: THREE.Object3D | null = node
    while (building && !isBuilding(building)) building = building.parent
    const style = building ? facade[hashName(building.name) % facade.length]! : undefined
    const convert = (original: THREE.Material) => {
      if (style) return /Roof|roof/i.test(original.name) ? roof : style
      if (node.userData.osmTags?.surface === 'osm2world:empty_terrain') return paving
      if (original.name === 'WATER') return water
      if (!(original instanceof THREE.MeshStandardMaterial)) return original
      let material = clones.get(original)
      if (!material) {
        material = original.clone()
        if (original.name === 'ASPHALT') { material.color.setHex(0x65727b); material.roughness = 0.96 }
        else if (original.name === 'GRASS') { material.color.setHex(0x417354); material.roughness = 1 }
        else if (original.name === 'EARTH') { material.color.setHex(0x7c8983); material.roughness = 1 }
        clones.set(original, material); ownedMaterials.add(material)
      }
      return material
    }
    const originalMaterials = Array.isArray(node.material) ? node.material : [node.material]
    replacements.set(node, Array.isArray(node.material) ? node.material.map(convert) : convert(node.material))
    node.castShadow = !!building
    node.receiveShadow = true
    if (originalMaterials.some(material => material.name === 'GRASS')
      && node.userData.osmTags?.surface !== 'osm2world:empty_terrain'
      && node.userData.osmTags?.leisure !== 'pitch' && !node.parent?.name.includes('Pitch')) {
      const sample = sampleSurface(node, 0, random)
      const count = Math.min(45, Math.floor(sample.area / 90))
      trees.push(...sampleSurface(node, count, random).samples)
    }
  })

  // Rooftop detail is placed inside upward roof triangles, not at potentially empty bbox centres.
  model.traverse(node => {
    if (!isBuilding(node)) return
    const bounds = new THREE.Box3().setFromObject(node)
    if (bounds.getSize(new THREE.Vector3()).y < 20) return
    let roofMesh: THREE.Mesh | undefined
    node.traverse(child => {
      if (child instanceof THREE.Mesh && (Array.isArray(child.material) ? child.material : [child.material]).some(material => /Roof|roof/i.test(material.name))) roofMesh = child
    })
    if (!roofMesh) return
    const points = sampleSurface(roofMesh, 3, random).samples
    for (const position of points) {
      if (position.y < bounds.max.y - 0.5) continue
      roofs.push({ position: position.clone().add(new THREE.Vector3(0, 1.2, 0)), scale: new THREE.Vector3(2.8, 2.4, 2.2), angle: random() * Math.PI })
    }
  })
  const equipment = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial({ color: 0x9ba5ac, roughness: 0.58, metalness: 0.5 }), roofs.length)
  const dummy = new THREE.Object3D()
  roofs.forEach((item, index) => {
    dummy.position.copy(item.position); dummy.rotation.set(0, item.angle, 0); dummy.scale.copy(item.scale); dummy.updateMatrix()
    equipment.setMatrixAt(index, dummy.matrix)
  })
  equipment.castShadow = true; equipment.receiveShadow = true
  details.add(equipment)

  // Instanced trunks and clustered crowns keep landscaping to two draw calls.
  const treePositions = trees.slice(0, 420)
  const trunks = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.18, 0.32, 1, 6), new THREE.MeshStandardMaterial({ color: 0x5b4f40, roughness: 1 }), treePositions.length)
  const crowns = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 10, 8), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.95 }), treePositions.length * 3)
  treePositions.forEach((position, index) => {
    const height = 4.5 + random() * 3.5
    dummy.rotation.set(0, 0, 0); dummy.position.copy(position).add(new THREE.Vector3(0, height / 2, 0)); dummy.scale.set(1, height, 1); dummy.updateMatrix()
    trunks.setMatrixAt(index, dummy.matrix)
    for (let i = 0; i < 3; i++) {
      const angle = i * Math.PI * 2 / 3
      dummy.position.copy(position).add(new THREE.Vector3(Math.cos(angle) * 0.8, height + (i % 2) * 0.7, Math.sin(angle) * 0.8))
      dummy.scale.set(2 + random(), 2.5 + random() * 1.4, 2 + random()); dummy.updateMatrix()
      crowns.setMatrixAt(index * 3 + i, dummy.matrix)
      crowns.setColorAt(index * 3 + i, new THREE.Color().setHSL(0.29 + random() * 0.08, 0.26, 0.19 + random() * 0.13))
    }
  })
  trunks.castShadow = crowns.castShadow = true
  crowns.receiveShadow = true
  details.add(trunks, crowns)

  let mode: CityAppearance = 'dusk'
  function setMode(value: CityAppearance) {
    mode = value
    night.value = value === 'dusk' ? 1 : 0
    details.visible = value !== 'source'
    if (street) street.lights.visible = value === 'dusk'
    originalTrees.forEach(node => { node.visible = value === 'source' })
    originals.forEach((original, mesh) => { mesh.material = value === 'source' ? original : replacements.get(mesh)! })
  }
  setMode(mode)
  return {
    details,
    setMode,
    animate: (elapsed: number) => { time.value = elapsed },
    // Details remain scene-owned; restore original GLB materials before the scene's final release.
    dispose: () => { setMode('source'); ownedMaterials.forEach(material => material.dispose()) },
    counts: { trees: treePositions.length, roofEquipment: roofs.length, streetLights: street?.count ?? 0, facadeMeshes: [...replacements.values()].filter(material => facade.includes(material as THREE.MeshStandardMaterial)).length },
  }
}
