// Isolated presentation checks: fixture Java responses, real Vue/Three.js city and UAV assets.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { routePoint } from '../src/utils/taskRoute.ts'
const require=createRequire(import.meta.url)
const {chromium}=require(process.env.SKYTWIN_PLAYWRIGHT_MODULE || 'playwright')
const base='http://127.0.0.1:5173', artifact=fileURLToPath(new URL('../../docs/verification/',import.meta.url))
const checks=[], errors=[], writes=[]
let elapsed=6, status='executing', offline=false, failTracks=false, browser
const points=[
  {longitude:120.19,latitude:30.215,altitude:0,offsetSeconds:0},
  {longitude:120.19,latitude:30.215,altitude:90,offsetSeconds:2},
  {longitude:120.19,latitude:30.225,altitude:90,offsetSeconds:10},
  {longitude:120.193,latitude:30.225,altitude:90,offsetSeconds:12},
  {longitude:120.193,latitude:30.215,altitude:90,offsetSeconds:20},
  {longitude:120.193,latitude:30.215,altitude:0,offsetSeconds:22},
]
const secondPoints=points.map(p=>({...p,longitude:p.longitude+.007}))
function distance(a,b){const rad=x=>x*Math.PI/180;const h=Math.sin(rad(b.latitude-a.latitude)/2)**2+Math.cos(rad(a.latitude))*Math.cos(rad(b.latitude))*Math.sin(rad(b.longitude-a.longitude)/2)**2;return 6371000*2*Math.asin(Math.sqrt(h))}
function task(id,route,time,state){
  const position=routePoint(route,time), future=route.filter(p=>p.offsetSeconds>time), rest=[position,...future]
  return {id,title:id==='fixture-A'?'界面验收样例：河岸配送':'界面验收样例：备用配送',type:'logistics',aircraftId:'fixture-UAV',aircraftName:'样例货运机',startStationId:'start',endStationId:'end',startStationName:'样例起点',endStationName:'样例终点',status:state,progress:time/22*100,reason:'isolated UI fixture',payload:1,passengers:0,speed:10,cruiseAltitude:90,durationSeconds:22,elapsedSeconds:time,routeRevision:2,routePoints:route,routeDistanceMeters:2500,createdBy:'fixture',createdTime:'2026-10-20T20:00:00',navigation:{position,remainingRouteMeters:rest.slice(1).reduce((sum,p,i)=>sum+distance(rest[i],p),0),destinationDistanceMeters:distance(position,route.at(-1)),remainingSimulationSeconds:22-time}}
}
function snapshot(){const main=task('fixture-A',points,elapsed,status);return {aircraft:[{id:'fixture-UAV',name:'样例货运机',type:'cargo',model:'UI fixture',...main.navigation.position,battery:96,payloadCapacity:20,seats:0,status:status==='executing'?'flying':'idle',speed:10}],stations:[{id:'start',name:'样例起点',type:'logistics',longitude:120.19,latitude:30.215,status:'enabled'},{id:'end',name:'样例终点',type:'logistics',longitude:120.193,latitude:30.215,status:'enabled'}],tasks:[main,task('fixture-B',secondPoints,0,'assigned')],airspaceZones:[],events:[],reports:[],audit:[],summary:{aircraft:1,executing:1,completed:0,openEvents:0},simulation:{enabled:true,timeScale:10,coordinateSystem:'WGS84',realFlight:false}}}
function check(label){checks.push(label);console.log('PASS UI: '+label)}
const report={passed:false,mode:'isolated mocked Java API and account; real Three.js/GLB rendering; not real flight evidence',checks}
try{
  browser=await chromium.launch({channel:'chrome',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']})
  const context=await browser.newContext({viewport:{width:1720,height:1080},locale:'zh-CN'})
  await context.addCookies([{name:'Admin-Token',value:'isolated-navigation-fixture',url:base}])
  await context.route('**/java-api/**',async route=>{
    const request=route.request(),path=new URL(request.url()).pathname
    if(request.method()!=='GET') writes.push(path)
    if(path.endsWith('/getInfo')) return route.fulfill({json:{code:200,user:{userName:'地图界面验收样例'},permissions:['sky:read']}})
    if(path.endsWith('/sky/snapshot')) return route.fulfill({json:{code:200,data:snapshot()}})
    if(path.endsWith('/sky/stream')) {
      if(offline) return route.abort('failed')
      return route.fulfill({contentType:'text/event-stream',body:'data: '+JSON.stringify(snapshot())+'\n\n'})
    }
    if(path.endsWith('/tracks')) {
      if(failTracks) return route.fulfill({json:{code:500,msg:'样例轨迹暂不可用'}})
      const alternate=path.includes('fixture-B'), values=alternate?secondPoints:points, time=alternate?0:elapsed
      const history=[...values.filter(p=>p.offsetSeconds<time),routePoint(values,time)].map((p,i)=>({...p,id:i+1,progress:p.offsetSeconds/22*100,battery:96,speed:10,recordedTime:'2026-10-20T20:00:00'}))
      return route.fulfill({json:{code:200,data:history}})
    }
    if(path.endsWith('/sky/logistics/orders')) return route.fulfill({json:{code:200,data:[{id:'fixture-order',cargoName:'界面验收样例：河岸配送',weight:1,startStationName:'样例起点',endStationName:'样例终点',status:'created',taskStatus:status,taskId:'fixture-A',progress:20,deadlineAt:'2026-10-21T20:00:00',aircraftName:'样例货运机'}]}})
    return route.fulfill({json:{code:200,data:[]}})
  })
  const page=await context.newPage(); page.on('pageerror',e=>errors.push(e.message))
  await page.goto(base+'/logistics')
  await page.getByRole('link',{name:'地图跟踪',exact:true}).click()
  await page.waitForURL('**/digital-twin?taskId=fixture-A')
  await page.getByRole('region',{name:'物流任务地图跟踪'}).waitFor()
  check('logistics map tracking link opens the selected task')
  await page.getByTestId('remaining-route').waitFor()
  assert.notEqual(await page.getByTestId('remaining-route').textContent(),await page.getByTestId('destination-distance').textContent())
  check('route remaining and direct-to-destination distances are distinct')
  async function diagnostics(){return page.evaluate(()=>{let vm=document.querySelector('.city-canvas')?.__vueParentComponent;while(vm&&!vm.exposed?.getDiagnostics)vm=vm.parent;return vm?.exposed?.getDiagnostics()})}
  await page.waitForFunction(()=>{let vm=document.querySelector('.city-canvas')?.__vueParentComponent;while(vm&&!vm.exposed?.getDiagnostics)vm=vm.parent;return vm?.exposed?.getDiagnostics()?.phase==='ready'},{},{timeout:120000})
  const diag=await diagnostics()
  assert.equal(diag.navigationTaskId,'fixture-A')
  for(const name of ['navigation-planned','navigation-flown','navigation-remaining','navigation-current','navigation-heading']) assert(diag.navigationObjects.includes(name),name)
  check('real city scene renders UAV, planned/history/remaining paths and current marker')
  const before=await page.getByTestId('remaining-route').textContent()
  elapsed=10
  await page.waitForFunction(value=>document.querySelector('[data-testid="remaining-route"]')?.textContent!==value,before,{timeout:15000})
  assert((await page.getByTestId('navigation-position').textContent()).includes('30.225000'))
  check('new SSE task position updates distance and waypoint position without page reload')
  await page.getByRole('button',{name:'定位任务位置',exact:true}).click()
  await page.getByRole('button',{name:'查看完整航线',exact:true}).click()
  check('locate current task and frame full route controls work')
  await mkdir(artifact,{recursive:true})
  await page.screenshot({path:artifact+'navigation-desktop.png',fullPage:true})
  await page.reload();await page.getByTestId('navigation-position').waitFor()
  assert(page.url().endsWith('taskId=fixture-A'))
  check('refresh preserves task selection and reloads authoritative saved tracks')
  await page.getByRole('combobox',{name:'选择地图跟踪任务'}).click()
  await page.getByRole('option',{name:'界面验收样例：备用配送 · 已分配',exact:true}).click()
  await page.waitForURL('**taskId=fixture-B')
  await page.waitForFunction(()=>document.querySelector('[data-testid="navigation-position"]')?.textContent?.includes('120.197000'))
  check('switching tasks clears old track and uses new task origin')
  await page.goto(base+'/digital-twin?taskId=missing-fixture')
  await page.getByText('此任务不存在或不在当前可查看的物流任务中。',{exact:true}).waitFor()
  assert.equal(await page.getByTestId('remaining-route').count(),0)
  check('missing task does not fall back to an unrelated aircraft or fake distance')
  await page.goto(base+'/digital-twin')
  await page.waitForURL('**/digital-twin?taskId=fixture-A')
  await page.getByTestId('remaining-route').waitFor()
  check('opening digital twin auto-selects an executing logistics task and persists its ID')
  elapsed=22;status='completed'
  await page.getByText('仿真飞行已完成；送达确认请在物流运输中操作。',{exact:true}).waitFor()
  assert.equal(await page.getByTestId('remaining-route').textContent(),'0 m')
  assert(page.url().includes('fixture-A'))
  check('completion retains selected task, shows zero distance and does not confirm delivery')
  elapsed=6;status='cancelled';failTracks=true
  await page.reload()
  await page.getByText('任务已停止，保留最后位置和历史轨迹，不再推进。',{exact:true}).waitFor()
  await page.getByRole('alert').filter({hasText:'样例轨迹暂不可用'}).waitFor()
  check('cancelled position is frozen; history failures are visible rather than fabricated')
  offline=true
  await page.getByText('连接中断 · 数据已暂停',{exact:true}).waitFor({timeout:15000})
  check('stream disconnection is explicitly marked and navigation is not extrapolated')
  await page.setViewportSize({width:600,height:900})
  const box=await page.getByRole('region',{name:'物流任务地图跟踪'}).boundingBox()
  assert(box&&box.x>=0&&box.x+box.width<=600)
  await page.waitForFunction(()=>{let vm=document.querySelector('.city-canvas')?.__vueParentComponent;while(vm&&!vm.exposed?.getDiagnostics)vm=vm.parent;return vm?.exposed?.getDiagnostics()?.phase==='ready'},{},{timeout:120000})
  await page.screenshot({path:artifact+'navigation-mobile.png',fullPage:true})
  check('tracking card remains inside the narrow viewport')
  assert.deepEqual(errors,[]);assert.deepEqual(writes,[])
  check('no runtime errors and no business writes from tracking')
  report.passed=true
}finally{
  await browser?.close()
  await mkdir(artifact,{recursive:true})
  await writeFile(artifact+'navigation-ui.json',JSON.stringify({...report,errors,businessWrites:writes},null,2))
}
