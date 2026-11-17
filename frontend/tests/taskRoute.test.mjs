import { test } from 'node:test'
import assert from 'node:assert/strict'
import * as THREE from 'three'
import { toCityPosition, fromCityPosition } from '../src/views/DigitalTwin/cityCoordinates.ts'
import { routePoint, routeSketch } from '../src/utils/taskRoute.ts'
import { createRouteDraftOverlay } from '../src/views/DigitalTwin/routeDraftOverlay.ts'
const points = [
  { longitude: 0, latitude: 0, altitude: 0, offsetSeconds: 0 },
  { longitude: 0, latitude: 0, altitude: 60, offsetSeconds: 2 },
  { longitude: 0, latitude: 10, altitude: 60, offsetSeconds: 5 },
  { longitude: 10, latitude: 10, altitude: 60, offsetSeconds: 15 },
  { longitude: 10, latitude: 0, altitude: 60, offsetSeconds: 18 },
  { longitude: 10, latitude: 0, altitude: 0, offsetSeconds: 20 },
]
test('world plane selection roundtrips WGS84 coordinates using actual projection', () => {
  const origin = { lon: 120.15, lat: 30.2, ele: 0 }
  for (const [lon, lat] of [[120.19, 30.215], [120.3, 30.3], [119.9, 29.95]]) {
    const p = toCityPosition(lon, lat, 60, origin), restored = fromCityPosition(p.x, p.z, origin)
    assert.ok(Math.abs(restored.longitude - lon) < 1e-9)
    assert.ok(Math.abs(restored.latitude - lat) < 1e-9)
  }
})
test('route-aware frame interpolation turns along legs, never cuts a corner chord', () => {
  assert.equal(routePoint([], 1), undefined)
  assert.equal(routePoint(points, -1).altitude, 0)
  assert.equal(routePoint(points, 50).altitude, 0)
  assert.equal(routePoint(points, 1).altitude, 30)
  assert.equal(routePoint(points, 6).latitude, 10)
  assert.equal(routePoint(points, 14).latitude, 10)
  assert.deepEqual(routePoint(points, 5), points[2])
})
test('sketch fixes takeoff/landing endpoints and uses shared cruise height', () => {
  const plan = { points, cruiseAltitude: 60 }
  const sketch = routeSketch(plan, [{ longitude: 4, latitude: 6 }], 0)
  assert.equal(sketch.points[0].longitude, 0)
  assert.equal(sketch.points[sketch.points.length - 1].longitude, 10)
  assert.equal(sketch.points[2].altitude, 60)
  assert.equal(sketch.selected, 0)
})
test('draft overlay has numbered markers and uses unlifted actual altitude', () => {
  const sketch = routeSketch({ points, cruiseAltitude: 60 }, [{ longitude: 4, latitude: 6 }], 0)
  const group = createRouteDraftOverlay(sketch, (x, z, y) => new THREE.Vector3(x, y, z), new THREE.Vector2(800, 600))
  assert.equal(group.getObjectByName('route-waypoint:0').position.y, 60)
  assert.equal(group.getObjectByName('route-draft-line').geometry.getAttribute('instanceEnd').getY(0), 60)
  group.traverse(n => { n.geometry?.dispose(); n.material?.dispose() })
})
