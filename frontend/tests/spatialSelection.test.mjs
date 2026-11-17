import test from 'node:test'
import assert from 'node:assert/strict'
import { boundsFromPoints, inBounds } from '../src/utils/spatialSelection.mjs'
test('selection is independent of drag direction and includes boundary stations',()=>{
  const a={longitude:120.1,latitude:30.1},b={longitude:120.3,latitude:30.4}
  assert.deepEqual(boundsFromPoints(a,b),boundsFromPoints(b,a))
  const box=boundsFromPoints(a,b)
  assert.equal(inBounds(a,box),true);assert.equal(inBounds(b,box),true)
  assert.equal(inBounds({longitude:120.5,latitude:30.2},box),false)
})
test('zero-area, non-finite and out-of-earth coordinates cannot become queries',()=>{
  const a={longitude:120,latitude:30}
  for(const b of [a,{longitude:Infinity,latitude:31},{longitude:181,latitude:31},{longitude:121,latitude:91}])assert.throws(()=>boundsFromPoints(a,b))
  assert.equal(inBounds({longitude:NaN,latitude:30},{minLon:0,maxLon:180,minLat:0,maxLat:90}),false)
})
