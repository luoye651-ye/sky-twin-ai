import { test } from 'node:test'
import assert from 'node:assert/strict'
import * as THREE from 'three'
import { createAirspaceOverlay } from '../src/views/DigitalTwin/airspaceOverlay.ts'

test('zone volume and red violation use business metre altitude without aircraft visual lift', () => {
  const zone = { id: 'z', type: 'no_fly', west: 0, south: 0, east: 100, north: 50, minAltitude: 20, maxAltitude: 80, activeNow: true }
  const from = { longitude: 0, latitude: 10, altitude: 60 }, to = { longitude: 100, latitude: 10, altitude: 60 }
  const check = { route: [from, to], violations: [{ from, to }] }
  const group = createAirspaceOverlay([zone], check, (x, z, y = 0) => new THREE.Vector3(x, y, z), new THREE.Vector2(800, 600))
  const volume = group.getObjectByName('airspace:z')
  const bounds = new THREE.Box3().setFromObject(volume)
  assert.equal(bounds.min.y, 20)
  assert.equal(bounds.max.y, 80)
  const line = group.getObjectByName('airspace-violation')
  assert.equal(line.material.color.getHex(), 0xff294d)
  assert.equal(line.material.depthTest, false)
  assert.equal(line.geometry.getAttribute('instanceStart').getY(0), 60)
  group.traverse(node => { node.geometry?.dispose(); if (node.material) node.material.dispose() })
})
