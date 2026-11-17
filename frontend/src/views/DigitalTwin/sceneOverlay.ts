import type { Object3D } from 'three'

/** Transfer from a snapshot because add() reparents and mutates overlay.children. */
export function moveOverlayChildren(target: Object3D, overlay: Object3D) {
  for (const child of [...overlay.children]) target.add(child)
}
