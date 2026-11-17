import { test } from 'node:test'
import assert from 'node:assert/strict'
import { Object3D, PerspectiveCamera, Vector3 } from 'three'
import { focusAircraftById } from '../src/views/DigitalTwin/aircraftFocus.ts'

function setup() {
  const camera = new PerspectiveCamera(50, 1.5, 200, 100000)
  camera.position.set(100, 200, 300)
  const controls = { target: new Vector3(1, 2, 3), enableDamping: true, maxDistance: 5000, updates: [], update() { this.updates.push(this.enableDamping) } }
  const fleet = new Map()
  return { camera, controls, fleet }
}
function aircraft(fleet, id, position) {
  const object = new Object3D()
  object.position.fromArray(position)
  fleet.set(id, { object })
  return object
}

test('focuses the requested rendered aircraft including its visual lift without moving it', () => {
  const { camera, controls, fleet } = setup()
  const object = aircraft(fleet, 'C-01', [1200, 220, -800])
  aircraft(fleet, 'D-01', [-900, 260, 400])
  assert.equal(focusAircraftById(camera, controls, fleet, 'C-01'), true)
  assert.deepEqual(controls.target.toArray(), [1200, 220, -800])
  assert.deepEqual(camera.position.clone().sub(controls.target).toArray(), [-420, 420, 560])
  assert.deepEqual(object.position.toArray(), [1200, 220, -800])
  assert.deepEqual(fleet.get('D-01').object.position.toArray(), [-900, 260, 400])
  assert.equal(controls.enableDamping, true)
  assert.deepEqual(controls.updates, [false, false])
  assert.ok(camera.near < 5 && camera.far === 100000)
})

test('switching and clicking the same aircraft again samples its latest rendered position', () => {
  const { camera, controls, fleet } = setup()
  const object = aircraft(fleet, 'C-01', [1, 100, 2])
  aircraft(fleet, 'D-02', [500, 175, 600])
  focusAircraftById(camera, controls, fleet, 'D-02')
  assert.deepEqual(controls.target.toArray(), [500, 175, 600])
  object.position.set(100, 150, 200)
  focusAircraftById(camera, controls, fleet, 'C-01')
  assert.deepEqual(controls.target.toArray(), [100, 150, 200])
  object.position.set(200, 180, 300)
  focusAircraftById(camera, controls, fleet, 'C-01')
  assert.deepEqual(controls.target.toArray(), [200, 180, 300])
})

test('uses world coordinates if the displayed model belongs to a transformed parent', () => {
  const { camera, controls, fleet } = setup()
  const parent = new Object3D()
  parent.position.set(1000, 10, -2000)
  parent.add(aircraft(fleet, 'E-01', [30, 400, 50]))
  assert.equal(focusAircraftById(camera, controls, fleet, 'E-01'), true)
  assert.deepEqual(controls.target.toArray(), [1030, 410, -1950])
})

test('missing/hidden/outside terminal aircraft does not move the camera or fabricate a position', () => {
  const { camera, controls, fleet } = setup()
  const before = camera.position.toArray()
  assert.equal(focusAircraftById(camera, controls, fleet, 'not-rendered'), false)
  assert.deepEqual(camera.position.toArray(), before)
  assert.deepEqual(controls.target.toArray(), [1, 2, 3])
  assert.equal(controls.updates.length, 0)
})

test('invalid rendered coordinates are rejected without moving the view', () => {
  const { camera, controls, fleet } = setup()
  aircraft(fleet, 'invalid', [NaN, 10, 20])
  assert.equal(focusAircraftById(camera, controls, fleet, 'invalid'), false)
  assert.deepEqual(camera.position.toArray(), [100, 200, 300])
  assert.equal(controls.updates.length, 0)
})

test('preserves disabled damping and expands restrictive orbit/clipping limits', () => {
  const { camera, controls, fleet } = setup()
  controls.enableDamping = false
  controls.maxDistance = 50
  camera.far = 100
  aircraft(fleet, 'D-01', [0, 80, 0])
  focusAircraftById(camera, controls, fleet, 'D-01')
  assert.equal(controls.enableDamping, false)
  assert.ok(controls.maxDistance > camera.position.distanceTo(controls.target))
  assert.ok(camera.far > camera.position.distanceTo(controls.target))
})
