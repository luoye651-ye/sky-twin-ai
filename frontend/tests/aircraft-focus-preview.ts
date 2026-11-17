// Development-only integration fixture: real components/scene, no login, Java or business writes.
import { createApp, defineComponent, h, nextTick, shallowRef, useTemplateRef } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import { ElProgress } from 'element-plus'
import FleetPanel from '../src/components/business/FleetPanel.vue'
import CityViewport from '../src/components/business/CityViewport.vue'
import type { Aircraft } from '../../shared/sky'
import '../src/style.css'

const aircraft = shallowRef<Aircraft[]>([
  { id:'C-01', name:'演示货运无人机 C-01', type:'cargo', longitude:120.08, latitude:30.27, altitude:0 },
  { id:'D-01', name:'演示巡检无人机 D-01', type:'drone', longitude:120.1736, latitude:30.2116, altitude:0 },
  { id:'D-02', name:'场外仿真布点 D-02', type:'drone', longitude:121.48, latitude:31.22, altitude:0 },
  { id:'E-01', name:'演示通勤 eVTOL E-01', type:'evtol', longitude:120.25, latitude:30.175, altitude:400 },
  { id:'TERMINAL-OUT', name:'场外终端（不伪造位置）', type:'drone', longitude:121.48, latitude:31.22, altitude:100, positionSource:'simulated_terminal', positionSampledAt:'2026-10-22T12:00:00Z' },
].map(a => ({ ...a, model:'组件样例', status:'idle', battery:90, payloadCapacity:20, seats:a.type==='evtol'?4:0, speed:0 })) as Aircraft[])

const App=defineComponent({setup(){
  const viewport=useTemplateRef<InstanceType<typeof CityViewport>>('viewport')
  const selectedId=shallowRef(''), diagnostics=shallowRef(''), sceneKey=shallowRef(0)
  function locate(id:string) { selectedId.value=id; viewport.value?.focusAircraft(id) }
  return ()=>h('div',[
    h('header',{style:'padding:10px;background:#283324;display:flex;gap:12px;flex-wrap:wrap;font-size:12px'},[
      h('strong','点击定位组件样例 · 非Java实时业务数据'),
      h('button',{onClick:()=>diagnostics.value=JSON.stringify(viewport.value?.getDiagnostics())},'读取相机诊断'),
      h('button',{onClick:async()=>{sceneKey.value++; await nextTick(); locate('D-02')}},'重建并立即定位 D-02'),
      h('button',{onClick:()=>{aircraft.value=aircraft.value.map(a=>a.id==='C-01'?{...a,longitude:120.3,latitude:30.26}:a)}},'更新样例 C-01 位置'),
    ]),
    h('main',{style:'height:850px;display:grid;grid-template-columns:310px minmax(0,1fr);gap:12px;padding:12px'},[
      h(FleetPanel,{aircraft:aircraft.value,tasks:[],connected:true,selectedId:selectedId.value,onLocate:locate}),
      h(CityViewport,{key:sceneKey.value,ref:'viewport',aircraft:aircraft.value,stations:[],tasks:[],selectedAircraftId:selectedId.value}),
    ]),
    h('pre',{'data-testid':'diagnostics',style:'font-size:11px;white-space:pre-wrap'},diagnostics.value),
  ])
}})
const router=createRouter({history:createMemoryHistory(),routes:[{path:'/:pathMatch(.*)*',component:{render:()=>null}}]})
createApp(App).component('el-progress', ElProgress).use(router).mount('#app')
