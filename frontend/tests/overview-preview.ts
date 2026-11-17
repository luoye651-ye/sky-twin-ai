// Isolated visual fixture. No tokens, Java calls, stream or mutations of business data.
import { createApp, defineComponent, h, shallowRef } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import OverviewDashboard from '../src/components/overview/OverviewDashboard.vue'
import { emptySnapshot, type Snapshot } from '../../shared/sky'
import '../src/style.css'

function fixture(): Snapshot {
  const s = emptySnapshot()
  s.aircraft = [
    { id:'C-01', name:'演示货运无人机', type:'cargo', battery:96.8, status:'idle' },
    { id:'D-01', name:'演示巡检无人机一', type:'drone', battery:89.2, status:'flying' },
    { id:'D-02', name:'演示巡检无人机二', type:'drone', battery:24.5, status:'assigned' },
    { id:'E-01', name:'演示通勤eVTOL', type:'evtol', battery:100, status:'idle' },
  ].map((a,i) => ({...a,longitude:120.19+i*.003,latitude:30.215+i*.002,altitude:120+i*30,speed:0,model:'组件样例',payloadCapacity:20,seats:a.type==='evtol'?4:0})) as Snapshot['aircraft']
  s.stations = ['takeoff','logistics','charging','emergency','vertiport','vertiport'].map((type,i)=>({id:'S'+i,name:'样例站点'+i,type,longitude:120.19+i*.005,latitude:30.21+i*.002,status:i===2?'disabled':'enabled'})) as Snapshot['stations']
  s.tasks = ['created','assigned','executing','completed','completed','failed','cancelled'].map((status,i)=>({id:'T'+i,title:'组件验收任务 '+i,type:['logistics','commute','environment','rescue','airspace'][i%5],status,aircraftId:i===2?'D-01':null,aircraftName:i===2?'演示巡检无人机一':'',startStationId:'S0',endStationId:'S1',startStationName:'样例站点0',endStationName:'样例站点1',progress:i===2?45:status==='completed'?100:0,reason:'组件样例',payload:1,passengers:0,speed:20,cruiseAltitude:120,durationSeconds:600,createdBy:'fixture',createdTime:'2026-10-22 12:00:00'})) as Snapshot['tasks']
  s.events = [{id:1,taskId:'T5',aircraftId:'D-02',severity:'high',title:'组件样例：任务终止待核对',status:'open',resolution:'',resolvedBy:'',createdTime:'2026-10-22 12:00:00'},{id:2,taskId:'T1',aircraftId:'C-01',severity:'medium',title:'组件样例：电量提示',status:'open',resolution:'',resolvedBy:'',createdTime:'2026-10-22 12:05:00'}]
  s.audit = [{id:1,entityId:'T1',action:'task.create',actor:'fixture',reason:'只读组件样例，不写业务库',createdTime:'2026-10-22 12:00:00'}]
  s.summary = {aircraft:4,executing:1,completed:2,openEvents:2}
  return s
}
const App=defineComponent({setup(){
  const snapshot=shallowRef(fixture()),connected=shallowRef(true)
  return ()=>h('div',[
    h('header',{style:'padding:10px 16px;background:#283324;color:#ffe3a5;display:flex;gap:16px;align-items:center;font-size:12px;flex-wrap:wrap'},[
      h('strong','组件验收样例 · 非Java实时业务数据'),
      h('button',{onClick:()=>snapshot.value=fixture()},'样例数据'),
      h('button',{onClick:()=>snapshot.value=emptySnapshot()},'空数据'),
      h('button',{onClick:()=>connected.value=!connected.value},'切换连接状态'),
    ]),h(OverviewDashboard,{snapshot:snapshot.value,connected:connected.value,error:''})])
}})
const router=createRouter({history:createMemoryHistory(),routes:[{path:'/:pathMatch(.*)*',component:{render:()=>null}}]})
createApp(App).use(router).mount('#app')
