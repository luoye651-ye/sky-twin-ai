import { test } from 'node:test'
import assert from 'node:assert/strict'
import * as THREE from 'three'
import { createCityAppearance } from '../src/views/DigitalTwin/cityAppearance.ts'

test('GLTFLoader-sanitized building names receive facades; source mode restores originals', () => {
  const model = new THREE.Group()
  const building = new THREE.Group()
  building.name = THREE.PropertyBinding.sanitizeNodeName('Building w522150754')
  building.userData.osmTags = { building: 'apartments', height: '160' }
  const original = new THREE.MeshStandardMaterial({ color: 0xffe68c })
  original.name = 'Plaster002'
  const geometry = new THREE.BoxGeometry(30, 160, 20)
  const wall = new THREE.Mesh(geometry, original)
  wall.position.y = 80
  building.add(wall); model.add(building)
  const before = new THREE.Box3().setFromObject(model)
  const appearance = createCityAppearance(model)
  assert.notEqual(wall.material, original)
  assert.equal(wall.material.customProgramCacheKey(), 'skytwin-facade-v1')
  assert.equal(wall.geometry, geometry)
  assert.deepEqual(new THREE.Box3().setFromObject(model), before)
  appearance.setMode('source')
  assert.equal(wall.material, original)
  assert.equal(appearance.details.visible, false)
  appearance.setMode('day')
  assert.notEqual(wall.material, original)
  appearance.dispose()
  assert.equal(wall.material, original)
  appearance.details.traverse(node => { if (node instanceof THREE.Mesh) { node.geometry.dispose(); node.material.dispose(); if (node instanceof THREE.InstancedMesh) node.dispose() } })
  original.dispose(); geometry.dispose()
})
