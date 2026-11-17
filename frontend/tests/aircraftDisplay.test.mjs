import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  LOW_ALTITUDE_VISUAL_THRESHOLD,
  resolveAircraftDisplayAltitude,
} from '../src/views/DigitalTwin/aircraftDisplay.ts'

test('four grounded aircraft are lifted into stable separated display layers', () => {
  const altitudes = [0, 1, 2, 3].map(slot => resolveAircraftDisplayAltitude(0, slot))
  assert.deepEqual(altitudes.map(value => value.displayAltitude), [220, 260, 300, 340])
  assert.ok(altitudes.every(value => value.reportedAltitude === 0 && value.visualized))
})

test('real flight altitude above the visual threshold is preserved', () => {
  const altitude = resolveAircraftDisplayAltitude(LOW_ALTITUDE_VISUAL_THRESHOLD + 30, 2)
  assert.deepEqual(altitude, { displayAltitude: 150, reportedAltitude: 150, visualized: false })
})

test('invalid or negative business altitude is normalized without leaking into the scene', () => {
  assert.deepEqual(resolveAircraftDisplayAltitude(Number.NaN, 0), { displayAltitude: 220, reportedAltitude: 0, visualized: true })
  assert.deepEqual(resolveAircraftDisplayAltitude(-12, 1), { displayAltitude: 260, reportedAltitude: 0, visualized: true })
})
