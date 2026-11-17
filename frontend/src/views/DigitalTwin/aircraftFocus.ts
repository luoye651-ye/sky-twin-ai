import { Vector3, type Object3D, type PerspectiveCamera } from 'three'
import type { OrbitControls } from 'three/addons/controls/OrbitControls.js'

type CameraControls = Pick<OrbitControls, 'target' | 'update' | 'enableDamping' | 'maxDistance'>

/** Focus the rendered aircraft, including visual lift/interpolation, not its raw coordinates. */
export function focusAircraftById(
  camera: PerspectiveCamera,
  controls: CameraControls,
  fleet: ReadonlyMap<string, { object: Object3D }>,
  id: string,
): boolean {
  const aircraft = fleet.get(id)
  if (!aircraft) return false
  const center = aircraft.object.getWorldPosition(new Vector3())
  if (![center.x, center.y, center.z].every(Number.isFinite)) return false

  const offset = new Vector3(-420, 420, 560)
  const distance = offset.length()
  const damping = controls.enableDamping
  try {
    // Consume any remaining drag/pan inertia before placing the new camera.
    controls.enableDamping = false
    controls.update()
    controls.target.copy(center)
    camera.position.copy(center).add(offset)
    camera.near = Math.max(1, distance / 250)
    camera.far = Math.max(camera.far, distance * 5)
    camera.updateProjectionMatrix()
    controls.maxDistance = Math.max(controls.maxDistance, distance * 3)
    controls.update()
  } finally {
    controls.enableDamping = damping
  }
  return true
}
