import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { parseCityRegion } from '../src/views/DigitalTwin/cityRegionData.ts'
import { toCityPosition, isInsideCity } from '../src/views/DigitalTwin/cityCoordinates.ts'
import { pushSurface, pushWalls, geometry } from '../src/views/DigitalTwin/cityRegionGeometry.ts'
import * as THREE from 'three'
import { createCityTraffic } from '../src/views/DigitalTwin/cityTraffic.ts'

const region = JSON.parse(fs.readFileSync(new URL('../public/models/hangzhou/binjiang-region.json', import.meta.url),'utf8'))
test('offline extract covers Binjiang and river banks with sourced roads, water and district boundary', () => {
  const data = parseCityRegion(region)
  assert.ok(data.buildings.length > 19000)
  assert.ok(data.roads.length > 18000)
  assert.ok(data.areas.filter(a=>a.kind==='water').length > 400)
  assert.ok(data.labels.some(l=>l.name==='复兴大桥'))
  assert.equal(data.districtBoundary.length, 1)
  assert.ok(isInsideCity(data.districtSourceBounds[0],data.districtSourceBounds[1],data.bbox))
  assert.ok(isInsideCity(data.districtSourceBounds[2],data.districtSourceBounds[3],data.bbox))
  assert.equal(data.stats.buildings, data.buildings.length)
  assert.equal(Object.values(data.stats.heightSources).reduce((a,b)=>a+b,0), data.buildings.length)
  assert.ok(data.buildings.every(b=>['height','levels','inferred'].includes(b.heightSource)))
  const a=toCityPosition(data.bbox[0],data.bbox[1],0,data.origin), b=toCityPosition(data.bbox[2],data.bbox[3],0,data.origin)
  assert.ok(b.x-a.x>17000 && a.z-b.z>16000)
  assert.ok(isInsideCity(120.21,30.204,data.bbox))
  assert.ok(!isInsideCity(121.47,31.23,data.bbox))
  assert.equal(data.source.license,'ODbL-1.0')
})
test('invalid coordinates and unsafe footprint heights fail before geometry construction', () => {
  assert.throws(()=>parseCityRegion({...region,buildings:[{...region.buildings[0],height:Infinity}]}))
  assert.throws(()=>parseCityRegion({...region,roads:[{...region.roads[0],points:[[0,0],[NaN,2]]}]}))
})
test('Y-up polygon triangulation preserves courtyard holes and metre heights', () => {
  const rings=[[[0,0],[10,0],[10,10],[0,10]],[[3,3],[3,7],[7,7],[7,3]]]
  const surface=[], walls=[]
  pushSurface(surface,rings,50); pushWalls(walls,rings,50)
  let area=0
  for(let i=0;i<surface.length;i+=9){const ax=surface[i],az=surface[i+2],bx=surface[i+3],bz=surface[i+5],cx=surface[i+6],cz=surface[i+8]; area+=Math.abs((bx-ax)*(cz-az)-(bz-az)*(cx-ax))/2}
  assert.equal(area,84)
  const mesh=geometry(surface), n=mesh.getAttribute('normal')
  assert.ok(Array.from({length:n.count},(_,i)=>n.getY(i)).every(y=>y>.99))
  mesh.computeBoundingBox(); assert.equal(mesh.boundingBox.min.y,50); assert.equal(mesh.boundingBox.max.y,50)
  assert.equal(Math.max(...walls.filter((_,i)=>i%3===1)),50)
  mesh.dispose()
})
test('simulated vehicles move along the supplied road and remain in its lanes', () => {
  const road={id:'w100',name:'fixture',kind:'primary',width:14,height:16,bridge:true,oneway:'no',points:[[0,0],[0,500]]}
  const traffic=createCityTraffic([road]), mesh=traffic.group.children[0], matrix=new THREE.Matrix4(), p=new THREE.Vector3()
  mesh.getMatrixAt(0,matrix); p.setFromMatrixPosition(matrix); const before=p.clone()
  traffic.animate(8)
  mesh.getMatrixAt(0,matrix); p.setFromMatrixPosition(matrix)
  assert.notEqual(p.z,before.z)
  assert.ok(Math.abs(p.x)<road.width/2 && p.z>=0 && p.z<=500)
  assert.ok(Math.abs(p.y-16.8)<.001)
  traffic.group.traverse(o=>{if(o instanceof THREE.Mesh){o.dispose();o.geometry.dispose();o.material.dispose()}})
})
