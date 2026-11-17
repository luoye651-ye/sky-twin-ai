import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import * as THREE from 'three'
import { createCityTraffic, CITY_TRAFFIC_BUDGET } from '../src/views/DigitalTwin/cityTraffic.ts'

const road = (id, extra = {}) => ({id, name:'fixture', kind:'primary', width:14, height:16, bridge:true, oneway:'no', points:[[0,0],[0,1040]], ...extra})
function release(traffic) {
  traffic.group.traverse(mesh => {if(mesh instanceof THREE.InstancedMesh) {mesh.dispose(); mesh.geometry.dispose(); mesh.material.dispose()}})
}
function position(mesh, index) {
  const matrix = new THREE.Matrix4()
  mesh.getMatrixAt(index, matrix)
  return new THREE.Vector3().setFromMatrixPosition(matrix)
}

test('denser population is evenly spaced, stays on both lanes and respects bridge altitude', () => {
  const traffic = createCityTraffic([road('w1')])
  try {
    assert.equal(traffic.count, 16)
    assert.equal(traffic.group.children.length, 2)
    for (const mesh of traffic.group.children) {
      assert.equal(mesh.count, 16)
      assert.equal(mesh.instanceMatrix.usage, THREE.DynamicDrawUsage)
    }
    const mesh = traffic.group.children[0]
    const before = Array.from({length:16}, (_, i) => position(mesh,i))
    assert.ok(before.some(p => p.x < 0) && before.some(p => p.x > 0))
    for (let time of [8, 1000, 100000]) {
      traffic.animate(time)
      for (let i=0; i<traffic.count; i++) {
        const p=position(mesh,i)
        assert.ok(Math.abs(p.x)<7 && p.z>=0 && p.z<=1040)
        assert.ok(Math.abs(p.y-16.8)<.001)
      }
    }
    assert.notEqual(position(mesh,0).z, before[0].z)
    // Each direction retains a 130m headway, including the looping boundary.
    for (const sign of [-1,1]) {
      const values=before.filter(p=>Math.sign(p.x)===sign).map(p=>p.z).sort((a,b)=>a-b)
      for(let i=0;i<values.length;i++) assert.ok(Math.abs(((values[(i+1)%values.length]-values[i]+1040)%1040)-130)<.001)
    }
  } finally { release(traffic) }
})

test('population is bounded and does not add per-vehicle meshes or include non-driving paths', () => {
  const traffic=createCityTraffic(Array.from({length:1000},(_,i)=>road(`w${i}`)))
  try {
    assert.equal(traffic.count,CITY_TRAFFIC_BUDGET)
    assert.equal(traffic.count,6000)
    assert.equal(traffic.group.children.length,2)
  } finally {release(traffic)}
  for(const kind of ['footway','cycleway','service']) {
    const empty=createCityTraffic([road('w1',{kind})])
    try {assert.equal(empty.count,0)} finally {release(empty)}
  }
})

test('Hangzhou city extract supports the 6000 vehicle budget with deterministic distribution', () => {
  const data=JSON.parse(fs.readFileSync(new URL('../public/models/hangzhou/hangzhou-core-region.json',import.meta.url),'utf8'))
  const traffic=createCityTraffic(data.roads), again=createCityTraffic(data.roads)
  try {
    assert.equal(traffic.count,6000)
    assert.deepEqual(traffic.group.children[0].instanceMatrix.array,again.group.children[0].instanceMatrix.array)
    assert.equal(traffic.group.children.length,2)
  } finally {release(traffic);release(again)}
})
