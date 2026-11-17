import * as THREE from 'three'
import { Line2 } from 'three/addons/lines/Line2.js'
import { LineGeometry } from 'three/addons/lines/LineGeometry.js'
import { LineMaterial } from 'three/addons/lines/LineMaterial.js'

export function createRouteSymbol(points: THREE.Vector3[], resolution: THREE.Vector2) {
  const geometry = new LineGeometry().setPositions(points.flatMap(point => point.toArray()))
  const material = new LineMaterial({ color: 0x29d6ff, linewidth: 2.5, dashed: true, dashSize: 8, gapSize: 5, resolution, toneMapped: false })
  material.color.setRGB(0.08, 1.4, 2)
  const line = new Line2(geometry, material)
  line.computeLineDistances()
  return line
}

export function createStationSymbol(enabled: boolean) {
  const object = new THREE.Group()
  const pad = new THREE.Mesh(new THREE.CylinderGeometry(7, 7, 0.3, 32), new THREE.MeshStandardMaterial({ color: 0x223e4c, roughness: 0.7 }))
  const color = enabled ? new THREE.Color(0.06, 1.4, 1.1) : new THREE.Color(0x586675)
  const ring = new THREE.Mesh(new THREE.TorusGeometry(7.2, 0.3, 6, 40), new THREE.MeshBasicMaterial({ color, toneMapped: false }))
  ring.rotation.x = -Math.PI / 2; ring.position.y = 0.25
  object.add(pad, ring)
  return object
}
