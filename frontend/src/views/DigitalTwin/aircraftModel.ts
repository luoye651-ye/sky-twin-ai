import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

const aircraftModelUrl = `${import.meta.env.BASE_URL}models/UAV/delivery_drone_gameready_free.glb`

export interface AircraftModelInstance {
  object: THREE.Group
  beacon: THREE.MeshBasicMaterial
  dispose: () => void
}

export interface AircraftModelAsset {
  createInstance: (large: boolean) => AircraftModelInstance
  dispose: () => void
}

function releaseTemplate(template: THREE.Object3D) {
  const geometries = new Set<THREE.BufferGeometry>()
  const materials = new Set<THREE.Material>()
  const textures = new Set<THREE.Texture>()
  const bitmaps = new Set<ImageBitmap>()
  template.traverse(child => {
    if (!(child instanceof THREE.Mesh)) return
    geometries.add(child.geometry)
    for (const material of Array.isArray(child.material) ? child.material : [child.material]) {
      materials.add(material)
      for (const value of Object.values(material)) {
        if (!(value instanceof THREE.Texture)) continue
        textures.add(value)
        if (typeof ImageBitmap !== 'undefined' && value.image instanceof ImageBitmap) bitmaps.add(value.image)
      }
    }
  })
  geometries.forEach(geometry => geometry.dispose())
  materials.forEach(material => material.dispose())
  textures.forEach(texture => texture.dispose())
  bitmaps.forEach(bitmap => bitmap.close())
}

function aborted() {
  return new DOMException('UAV 模型加载已取消', 'AbortError')
}

export async function loadAircraftModelAsset(signal: AbortSignal): Promise<AircraftModelAsset> {
  const response = await fetch(aircraftModelUrl, { signal })
  if (!response.ok) throw new Error(`UAV 模型下载失败（HTTP ${response.status}）`)
  const buffer = await response.arrayBuffer()
  if (signal.aborted) throw aborted()

  const basePath = aircraftModelUrl.slice(0, aircraftModelUrl.lastIndexOf('/') + 1)
  const gltf = await new GLTFLoader().parseAsync(buffer, basePath)
  if (signal.aborted) {
    releaseTemplate(gltf.scene)
    throw aborted()
  }

  const template = gltf.scene
  template.updateMatrixWorld(true)
  const sourceBounds = new THREE.Box3().setFromObject(template)
  const sourceSize = sourceBounds.getSize(new THREE.Vector3())
  const sourceSpan = Math.max(sourceSize.x, sourceSize.z)
  if (!Number.isFinite(sourceSpan) || sourceSpan <= 0) {
    releaseTemplate(template)
    throw new Error('UAV 模型尺寸无效')
  }

  template.traverse(child => {
    if (!(child instanceof THREE.Mesh)) return
    child.castShadow = true
    child.receiveShadow = false
  })

  let disposed = false
  function createInstance(large: boolean): AircraftModelInstance {
    if (disposed) throw new Error('UAV 模型资源已经释放')
    const object = new THREE.Group()
    const model = template.clone(true)
    // The kilometre-scale city view uses an intentionally enlarged visual symbol.
    const targetSpan = large ? 90 : 72
    model.scale.setScalar(targetSpan / sourceSpan)
    model.updateMatrixWorld(true)
    const bounds = new THREE.Box3().setFromObject(model)
    const center = bounds.getCenter(new THREE.Vector3())
    model.position.x -= center.x
    model.position.y -= bounds.min.y
    model.position.z -= center.z
    object.add(model)

    const normalizedBounds = new THREE.Box3().setFromObject(model)
    const beaconGeometry = new THREE.SphereGeometry(1.1, 10, 8)
    const beacon = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.05, 2, 2.5), toneMapped: false })
    const beaconMesh = new THREE.Mesh(beaconGeometry, beacon)
    beaconMesh.position.y = normalizedBounds.max.y + 1.8
    object.add(beaconMesh)

    let instanceDisposed = false
    return {
      object,
      beacon,
      dispose() {
        if (instanceDisposed) return
        instanceDisposed = true
        beaconGeometry.dispose()
        beacon.dispose()
        object.clear()
      },
    }
  }

  return {
    createInstance,
    dispose() {
      if (disposed) return
      disposed = true
      releaseTemplate(template)
      template.clear()
    },
  }
}

