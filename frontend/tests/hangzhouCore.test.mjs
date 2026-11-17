import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { parseCityRegion } from '../src/views/DigitalTwin/cityRegionData.ts'
import { isInsideCity, toCityPosition } from '../src/views/DigitalTwin/cityCoordinates.ts'

const assetUrl = new URL('../public/models/hangzhou/hangzhou-core-region.json', import.meta.url)
const region = JSON.parse(fs.readFileSync(assetUrl, 'utf8'))
const stationCoordinates = [
  [120.1900, 30.1950], [120.3450, 30.2920], [120.0800, 30.2700],
  [120.1600, 30.2600], [120.2050, 30.1750], [120.4340, 30.2360],
]

test('Hangzhou urban-core LOD covers the six simulated stations and preserves Binjiang detail', () => {
  const data = parseCityRegion(region)
  const southwest = toCityPosition(data.bbox[0], data.bbox[1], 0, data.origin)
  const northeast = toCityPosition(data.bbox[2], data.bbox[3], 0, data.origin)
  assert.ok(northeast.x - southwest.x > 70000)
  assert.ok(southwest.z - northeast.z > 75000)
  assert.deepEqual(data.detailBbox, [120.10, 30.10, 120.28, 30.29])
  assert.ok(stationCoordinates.every(([lon, lat]) => isInsideCity(lon, lat, data.bbox)))
  assert.ok(!isInsideCity(121.4737, 31.2304, data.bbox))
  assert.ok(data.buildings.length >= 30000 && data.buildings.length <= 48000)
  assert.ok(data.roads.length >= 25000 && data.roads.length <= 36000)
  assert.ok(data.areas.length >= 5000 && data.areas.length <= 9000)
  assert.ok(data.source.lod?.includes('滨江全细节'))
  assert.equal(data.stats.buildings, data.buildings.length)
  assert.ok(data.stats.candidateCounts.roads > data.roads.length)
  assert.ok(fs.statSync(assetUrl).size < 25 * 1024 * 1024)
})

test('invalid detail bounds are rejected before scene construction', () => {
  assert.throws(() => parseCityRegion({ ...region, detailBbox: [119, 29, 121, 31] }))
})
