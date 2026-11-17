import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { isInsideCity, parseCityManifest, toCityPosition } from '../src/views/DigitalTwin/cityCoordinates.ts'

const directory = new URL('../public/models/hangzhou/', import.meta.url)
const manifest = parseCityManifest(JSON.parse(readFileSync(new URL('binjiang-test-500m.manifest.json', directory), 'utf8')))
const origin = manifest.origin
const near = (value, expected, tolerance = 0.05) => assert.ok(Math.abs(value - expected) < tolerance, `${value} != ${expected}`)

test('model origin is zero horizontally and altitude keeps metre units', () => {
  const position = toCityPosition(origin.lon, origin.lat, 120, origin)
  near(position.x, 0); near(position.z, 0); near(position.y, 120)
})

test('east and north use the GLB axes and local metre distances', () => {
  const east = toCityPosition(origin.lon + 0.001, origin.lat, 0, origin)
  const north = toCityPosition(origin.lon, origin.lat + 0.001, 0, origin)
  near(east.x, 96.21, 0.1); near(east.z, 0)
  near(north.x, 0); near(north.z, -111.32, 0.1)
  assert.ok(toCityPosition(origin.lon - 0.001, origin.lat, 0, origin).x < 0)
  assert.ok(toCityPosition(origin.lon, origin.lat - 0.001, 0, origin).z > 0)
})

test('bbox includes its boundary but excludes Shanghai and invalid coordinates', () => {
  assert.equal(isInsideCity(origin.lon, origin.lat, manifest.bbox), true)
  assert.equal(isInsideCity(manifest.bbox[0], manifest.bbox[1], manifest.bbox), true)
  assert.equal(isInsideCity(manifest.bbox[2], manifest.bbox[3], manifest.bbox), true)
  assert.equal(isInsideCity(121.4737, 31.2304, manifest.bbox), false)
  assert.equal(isInsideCity(NaN, origin.lat, manifest.bbox), false)
})

test('invalid projection, origin or swapped bounds cannot align overlays', () => {
  for (const value of [null, {}, { ...manifest, projection: 'WebMercator' }, { ...manifest, origin: { ...origin, lat: 31 } }, { ...manifest, bbox: [121, 31, 120, 30] }]) {
    assert.throws(() => parseCityManifest(value))
  }
})

test('public GLB retains the exported origin and all textures are embedded', () => {
  const bytes = readFileSync(new URL('binjiang-test-500m.glb', directory))
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF')
  assert.equal(bytes.readUInt32LE(4), 2)
  assert.equal(bytes.readUInt32LE(8), bytes.length)
  const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString('utf8'))
  assert.deepEqual(json.scenes[json.scene ?? 0].extras.origin, origin)
  assert.ok(json.meshes.length > 0)
  assert.ok(json.images.length > 0)
  assert.ok(json.images.every(image => image.bufferView !== undefined && !image.uri))
  const source = readFileSync(new URL('../../assets-source/hangzhou/output/binjiang-test-500m.glb', import.meta.url))
  assert.equal(createHash('sha256').update(bytes).digest('hex'), createHash('sha256').update(source).digest('hex'))
})
