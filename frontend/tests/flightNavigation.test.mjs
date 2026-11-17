import { test } from 'node:test'
import assert from 'node:assert/strict'
import * as THREE from 'three'
import { flightNavigationDisplay, remainingFlightPoints, formatFlightDistance } from '../src/utils/flightNavigation.ts'
import { createFlightNavigationOverlay } from '../src/views/DigitalTwin/flightNavigationOverlay.ts'
import { toCityPosition } from '../src/views/DigitalTwin/cityCoordinates.ts'

const points = [
  { longitude:120.19, latitude:30.215, altitude:0, offsetSeconds:0 },
  { longitude:120.19, latitude:30.215, altitude:60, offsetSeconds:2 },
  { longitude:120.19, latitude:30.225, altitude:60, offsetSeconds:10 },
  { longitude:120.193, latitude:30.225, altitude:60, offsetSeconds:12 },
  { longitude:120.193, latitude:30.215, altitude:60, offsetSeconds:20 },
  { longitude:120.193, latitude:30.215, altitude:0, offsetSeconds:22 },
]
const navigation = {position:{longitude:120.19,latitude:30.22,altitude:60,offsetSeconds:6},remainingRouteMeters:1900,destinationDistanceMeters:620,remainingSimulationSeconds:16}
const task = {id:'nav-test',status:'executing',routePoints:points,navigation}
const tracks = [points[0],points[1],navigation.position]
const world = (x,z,y) => { const p=toCityPosition(x,z,y,{lon:120.19,lat:30.215,ele:0}); return new THREE.Vector3(p.x,p.y,p.z) }
function release(group) { group.traverse(n=>{n.geometry?.dispose();n.material?.dispose()}) }

test('only authoritative Java navigation is used; missing or invalid data is unavailable', () => {
  assert.equal(flightNavigationDisplay(undefined,[]),undefined)
  assert.equal(flightNavigationDisplay({...task,navigation:undefined},[]),undefined)
  assert.equal(flightNavigationDisplay({...task,navigation:{...navigation,remainingRouteMeters:NaN}},[]),undefined)
  assert.equal(flightNavigationDisplay({...task,routePoints:[points[0]]},[]),undefined)
  assert.equal(flightNavigationDisplay({...task,navigation:{...navigation,position:{...navigation.position,longitude:181}}},[]),undefined)
})
test('remaining route follows all later waypoints and cannot cut the detour', () => {
  const display=flightNavigationDisplay(task,tracks)
  assert.deepEqual(remainingFlightPoints(display),[navigation.position,...points.slice(2)])
  assert.equal(display.navigation.remainingRouteMeters,1900)
  assert.equal(display.navigation.destinationDistanceMeters,620)
})
test('distance formatting handles zero, meters, kilometers and unavailable values',()=>{
  assert.equal(formatFlightDistance(0),'0 m');assert.equal(formatFlightDistance(999),'999 m')
  assert.equal(formatFlightDistance(1200),'1.20 km');assert.equal(formatFlightDistance(NaN),'—')
})
test('overlay has planned/flown/remaining routes, endpoints and heading at unlifted task position',()=>{
  const group=createFlightNavigationOverlay(flightNavigationDisplay(task,tracks),world,new THREE.Vector2(800,600))
  for(const name of ['navigation-planned','navigation-flown','navigation-remaining','navigation-start','navigation-end','navigation-current','navigation-heading']) assert.ok(group.getObjectByName(name),name)
  assert.deepEqual(group.getObjectByName('navigation-current').position.toArray(),world(120.19,30.22,60).toArray())
  assert.equal(group.getObjectByName('navigation-remaining').material.color.getHex(),0xffc857)
  assert.equal(group.getObjectByName('navigation-flown').material.dashed,false)
  release(group)
})
test('no tracks means no fabricated flown-history line',()=>{
  const group=createFlightNavigationOverlay(flightNavigationDisplay(task,[]),world,new THREE.Vector2(800,600))
  assert.equal(group.getObjectByName('navigation-flown'),undefined);release(group)
})
test('out-of-range route is not relocated into model; track gaps are not connected',()=>{
  const hidden=createFlightNavigationOverlay(flightNavigationDisplay(task,tracks),world,new THREE.Vector2(1,1),()=>false)
  assert.equal(hidden.children.length,0)
  const separated=[points[0],points[1],{longitude:121,latitude:31,altitude:60},points[2],points[3]]
  const group=createFlightNavigationOverlay(flightNavigationDisplay(task,separated),world,new THREE.Vector2(1,1),x=>x<121)
  assert.equal(group.children.filter(c=>c.name==='navigation-flown').length,2);release(group)
})
test('completed task position stays its own endpoint, independently of current aircraft reuse',()=>{
  const end=points.at(-1)
  const display=flightNavigationDisplay({...task,status:'completed',navigation:{position:end,remainingRouteMeters:0,destinationDistanceMeters:0,remainingSimulationSeconds:0}},tracks)
  assert.deepEqual(remainingFlightPoints(display),[end]);assert.equal(display.navigation.remainingRouteMeters,0)
})
