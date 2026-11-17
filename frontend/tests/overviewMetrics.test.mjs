import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildOverviewMetrics, ringSegments } from '../src/utils/overviewMetrics.ts'
import { emptySnapshot } from '../../shared/sky.ts'
import { Group } from 'three'
import { moveOverlayChildren } from '../src/views/DigitalTwin/sceneOverlay.ts'

test('empty snapshot keeps six panel datasets empty or zero without invented observations', () => {
  const data = buildOverviewMetrics(emptySnapshot())
  for (const key of ['fleet','taskKinds','taskStates','stations','severity']) assert.equal(data[key].reduce((n,x) => n+x.value,0),0)
  assert.equal(data.averageBattery,null)
  assert.deepEqual(data.battery,[])
  assert.deepEqual(data.latestEvents,[])
  assert.ok(ringSegments(data.fleet).every(x => x.percent === 0 && x.offset === 0))
})

test('all recorded task types and lifecycle states are counted independently', () => {
  const snapshot=emptySnapshot()
  snapshot.tasks=['created','assigned','executing','completed','cancelled','failed'].map((status,i)=>({id:String(i),type:['logistics','commute','environment','rescue','airspace','logistics'][i],status}))
  const data=buildOverviewMetrics(snapshot)
  assert.deepEqual(data.taskKinds.map(x=>x.value),[2,1,1,1,1])
  assert.deepEqual(data.taskStates.map(x=>x.value),[1,1,1,1,1,1])
})

test('resource status and type distributions match the source, including future unknown categories',()=>{
  const snapshot=emptySnapshot()
  snapshot.aircraft=[{id:'A',type:'cargo',status:'idle',battery:90},{id:'B',type:'drone',status:'flying',battery:20},{id:'C',type:'evtol',status:'assigned',battery:60},{id:'D',type:'future',status:'maintenance',battery:100}]
  const data=buildOverviewMetrics(snapshot)
  assert.equal(data.fleet.reduce((n,x)=>n+x.value,0),4)
  assert.equal(data.fleetTypes.reduce((n,x)=>n+x.value,0),4)
  assert.equal(data.fleet.find(x=>x.key==='maintenance').value,1)
  assert.match(data.fleetTypes.find(x=>x.key==='future').label,/其他/)
  assert.equal(data.averageBattery,67.5)
})

test('battery clamps invalid ranges, reports missing readings, and preserves real zero',()=>{
  const snapshot=emptySnapshot()
  snapshot.aircraft=[0,NaN,Infinity,-1,110].map((battery,i)=>({id:String(i),name:'机'+i,battery}))
  const data=buildOverviewMetrics(snapshot)
  assert.deepEqual(data.battery.map(x=>x.value),[0,null,null,0,100])
  assert.equal(data.averageBattery,100/3)
})

test('alerts use open records only, sort latest by ID, and do not substitute full summary',()=>{
  const snapshot=emptySnapshot()
  snapshot.events=[{id:2,status:'resolved',severity:'high'},{id:1,status:'open',severity:'low'},{id:4,status:'open',severity:'medium'},{id:5,status:'open',severity:'high'},{id:3,status:'open',severity:'high'}]
  snapshot.summary.openEvents=800
  const data=buildOverviewMetrics(snapshot)
  assert.deepEqual(data.severity.map(x=>x.value),[2,1,1])
  assert.deepEqual(data.latestEvents.map(x=>x.id),[5,4,3])
  assert.equal(snapshot.summary.openEvents,800)
})

test('station activation is independent of station type and snapshot counters remain authoritative',()=>{
  const snapshot=emptySnapshot()
  snapshot.stations=[{type:'takeoff',status:'enabled'},{type:'charging',status:'disabled'},{type:'vertiport',status:'enabled'}]
  snapshot.summary.completed=12345
  snapshot.tasks=[{id:'recent',type:'logistics',status:'completed'}]
  const data=buildOverviewMetrics(snapshot)
  assert.equal(data.enabledStations,2)
  assert.equal(data.stations.reduce((n,x)=>n+x.value,0),3)
  assert.equal(data.taskStates.find(x=>x.key==='completed').value,1)
  assert.equal(snapshot.summary.completed,12345)
})

test('ring segments are contiguous, sum to 100, and new snapshots recompute without mutating old data',()=>{
  const snapshot=emptySnapshot()
  snapshot.aircraft=[{id:'A',status:'idle',type:'drone',battery:80}]
  const before=JSON.stringify(snapshot)
  const data=buildOverviewMetrics(snapshot)
  assert.equal(JSON.stringify(snapshot),before)
  const ring=ringSegments(data.fleet)
  assert.equal(ring.reduce((n,x)=>n+x.percent,0),100)
  assert.equal(ring[1].offset,ring[0].percent)
  const changed=buildOverviewMetrics({...snapshot,aircraft:[{...snapshot.aircraft[0],status:'flying',battery:70}]})
  assert.equal(changed.fleet.find(x=>x.key==='flying').value,1)
  assert.equal(data.fleet.find(x=>x.key==='idle').value,1)
  assert.equal(changed.averageBattery,70)
})

test('empty map overlays do not call add(undefined); transfer moves every child without skipping',()=>{
  const destination=new Group(),source=new Group(),messages=[]
  const original=console.error
  console.error=(...args)=>messages.push(args)
  try {
    moveOverlayChildren(destination,source)
    const first=new Group(),second=new Group(),third=new Group()
    source.add(first,second,third)
    moveOverlayChildren(destination,source)
    assert.deepEqual(destination.children,[first,second,third])
    assert.equal(source.children.length,0)
    assert.ok(destination.children.every(x=>x.parent===destination))
    assert.equal(messages.length,0)
  } finally { console.error=original }
})
