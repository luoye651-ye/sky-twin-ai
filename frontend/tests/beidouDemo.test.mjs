import { test } from 'node:test'
import assert from 'node:assert/strict'
import { makeBeidouDemoFrame } from '../src/utils/beidouDemo.ts'

function decodeFrame(frame) {
  const [raw,hex]=frame.gga.slice(1).split('*')
  let sum=0;for(const c of raw)sum^=c.charCodeAt(0)
  assert.equal(parseInt(hex,16),sum)
  return raw.split(',')
}
test('synthetic BeiDou GGA includes checksum, UTC date and explicit MSL baseline', () => {
  const frame=makeBeidouDemoFrame({longitude:120.19,latitude:30.215,altitude:240},'2026-10-22T23:30:45.123+08:00')
  const fields=decodeFrame(frame)
  assert.equal(fields.length,15)
  assert.deepEqual(fields.slice(0,10),['GBGGA','153045.123','3012.90000','N','12011.40000','E','1','12','0.9','252.00'])
  assert.equal(frame.utcDate,'2026-10-22');assert.equal(frame.takeoffAltitudeMsl,12)
})
test('UTC midnight, hemispheres and minute rounding cannot create invalid timestamps or 60 minutes', () => {
  const frame=makeBeidouDemoFrame({longitude:-120.9999999999,latitude:-30.9999999999,altitude:0},'2026-10-23T00:00:00+08:00')
  const fields=decodeFrame(frame)
  assert.equal(frame.utcDate,'2026-10-22');assert.equal(fields[1],'160000.000')
  assert.equal(fields[2],'3100.00000');assert.equal(fields[3],'S')
  assert.equal(fields[4],'12100.00000');assert.equal(fields[5],'W')
})
test('loss-of-fix demo remains a valid packet but carries no valid fix', () => {
  const fields=decodeFrame(makeBeidouDemoFrame({longitude:120.19,latitude:30.215,altitude:240},'2026-10-22T00:00:00Z',false))
  assert.deepEqual(fields.slice(6,9),['0','00','99.9'])
})
test('invalid generator coordinates and time fail instead of emitting NaN packets', () => {
  for(const point of [{longitude:181,latitude:30,altitude:240},{longitude:120,latitude:91,altitude:240},{longitude:120,latitude:30,altitude:NaN}]) {
    assert.throws(()=>makeBeidouDemoFrame(point,'2026-10-22T00:00:00Z'))
  }
  assert.throws(()=>makeBeidouDemoFrame({longitude:120,latitude:30,altitude:240},'invalid'))
})
