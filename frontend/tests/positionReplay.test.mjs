import { test } from 'node:test'
import assert from 'node:assert/strict'
import * as THREE from 'three'
import { replayPoint, continuous, simulatedPosition } from '../src/utils/positionReplay.ts'
import { createPositionOverlay } from '../src/views/DigitalTwin/positionOverlay.ts'
const a = { id: 1, sessionId: 'session-a', sampledAt: '2026-10-19T00:00:00Z', longitude: 120, latitude: 30, altitude: 20, accepted: true }
const b = { ...a, id: 2, sampledAt: '2026-10-19T00:00:02Z', longitude: 122, latitude: 32, altitude: 60 }
const start = Date.parse(a.sampledAt)
test('replay has no point for empty input and clamps endpoints', () => {
  assert.equal(replayPoint([], start), undefined)
  assert.equal(replayPoint([a, b], start - 1000).longitude, 120)
  assert.equal(replayPoint([a, b], start + 99999).longitude, 122)
})
test('replay interpolates using sampled time and unlifted altitude', () => {
  assert.deepEqual(replayPoint([a, b], start + 1000), { longitude: 121, latitude: 31, altitude: 40, held: false })
})
test('sessions, reverse time and outage gaps cannot be interpolated', () => {
  for (const modified of [{ ...b, sessionId: 'new' }, { ...b, sampledAt: '2026-10-19T00:00:06Z' }, { ...b, sampledAt: a.sampledAt }]) assert.equal(continuous(a, modified), false)
  assert.equal(replayPoint([a, { ...b, sessionId: 'new' }], start + 1000).longitude, 120)
  assert.equal(replayPoint([a, { ...b, sampledAt: '2026-10-19T00:00:06Z' }], start + 3000).held, true)
})
test('generator starts at origin and stays within local bounded demonstration loop', () => {
  const origin = { longitude: 120.19, latitude: 30.215, altitude: 240 }
  assert.deepEqual(simulatedPosition(origin, 0), origin)
  for (let seconds = 0; seconds < 600; seconds++) {
    const p = simulatedPosition(origin, seconds)
    assert.ok(Math.abs(p.longitude - origin.longitude) <= .000801)
    assert.ok(p.altitude >= 220 && p.altitude <= 260)
  }
})
test('map track keeps actual altitude and splits outages, sessions and rejected points', () => {
  const group = createPositionOverlay([a, b, { ...a, id: 3, sessionId: 'new', sampledAt: '2026-10-19T00:00:03Z' }, { ...b, id: 4, sessionId: 'new', sampledAt: '2026-10-19T00:00:04Z' }, { ...b, id: 5, accepted: false }], (x, z, y) => new THREE.Vector3(x, y, z), new THREE.Vector2(800, 600))
  assert.equal(group.children.length, 2)
  assert.equal(group.children[0].geometry.getAttribute('instanceStart').getY(0), 20)
  assert.equal(group.children[0].material.depthTest, false)
  group.traverse(node => { node.geometry?.dispose(); node.material?.dispose() })
})
