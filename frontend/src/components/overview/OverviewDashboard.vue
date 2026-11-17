<script setup lang="ts">
import { computed } from 'vue'
import type { Snapshot } from '../../../../shared/sky'
import { buildOverviewMetrics } from '../../utils/overviewMetrics'
import CityViewport from '../business/CityViewport.vue'
import OverviewPanel from './OverviewPanel.vue'
import OverviewRing from './OverviewRing.vue'
import OverviewBars from './OverviewBars.vue'
import OverviewBattery from './OverviewBattery.vue'
import OverviewRecords from './OverviewRecords.vue'
const props = defineProps<{ snapshot:Snapshot; connected:boolean; error:string }>()
const data = computed(() => buildOverviewMetrics(props.snapshot))
const metrics = computed(() => [
  { label:'登记飞行器', value:props.snapshot.summary.aircraft, unit:'架', detail:'当前资源总量' },
  { label:'执行中任务', value:props.snapshot.summary.executing, unit:'项', detail:'服务端当前状态' },
  { label:'累计完成', value:props.snapshot.summary.completed, unit:'项', detail:'全部已完成任务' },
  { label:'待处置告警', value:props.snapshot.summary.openEvents, unit:'条', detail:'全部未处置告警' },
])
</script>
<template>
  <section class="overview-dashboard" aria-label="低空运行总览">
    <header class="overview-heading"><div><span class="eyebrow">SKYTWIN / OPERATIONS CENTER</span><h1>城市低空运行总览</h1></div><div class="data-state" :class="{ live:connected }"><i></i>{{ connected ? 'Java实时同步' : '实时连接中断 · 保留最后快照' }}<span>WGS84 · 仿真运行</span></div></header>
    <div v-if="error || !connected" class="connection-notice" role="status">{{ error || '实时连接恢复中，图表暂显示最后一次业务快照，不代表当前实时状态。' }}</div>
    <div class="metric-strip"><article v-for="m in metrics" :key="m.label" class="metric-card"><div><span>{{ m.label }}</span><small>{{ m.detail }}</small></div><p><strong>{{ m.value }}</strong><span>{{ m.unit }}</span></p></article></div>
    <div class="overview-stage">
      <aside class="data-column left-column" aria-label="机队与任务统计">
        <OverviewPanel title="机队运行状态" index="01" subtitle="当前登记资源 · 按业务状态统计" link="/digital-twin"><OverviewRing :items="data.fleet" :total="snapshot.aircraft.length" label="登记飞行器" /><div class="fleet-types"><span v-for="item in data.fleetTypes" :key="item.key">{{ item.label }} <b>{{ item.value }}</b></span></div></OverviewPanel>
        <OverviewPanel title="机队电量监测" index="02" subtitle="Java仿真资源电量 · ≤30% 黄色提示" link="/digital-twin"><OverviewBattery :items="data.battery" :average="data.averageBattery" /></OverviewPanel>
        <OverviewPanel title="任务场景分布" index="03" :subtitle="`当前快照 ${snapshot.tasks.length} 项任务 · 最多最近500项`" link="/task-management"><OverviewBars :items="data.taskKinds" vertical /></OverviewPanel>
      </aside>
      <section class="center-scene" aria-label="杭州主城区数字孪生地图"><div class="scene-topline"><span>HANGZHOU DIGITAL TWIN</span><RouterLink to="/digital-twin">进入数字孪生 ↗</RouterLink></div><div class="scene-container"><CityViewport :aircraft="snapshot.aircraft" :stations="snapshot.stations" :tasks="snapshot.tasks" :zones="snapshot.airspaceZones" overview /></div><div class="scene-bottomline"><span>◈ {{ snapshot.stations.length }} 个站点</span><span>{{ snapshot.simulation.timeScale }}× 仿真时钟</span><span>数据来自Java业务系统</span></div></section>
      <aside class="data-column right-column" aria-label="任务与城市安全统计">
        <OverviewPanel title="任务生命周期" index="04" :subtitle="`当前快照 ${snapshot.tasks.length} 项任务 · 非全量历史完成率`" link="/task-management"><OverviewRing :items="data.taskStates" :total="snapshot.tasks.length" label="快照任务数" /></OverviewPanel>
        <OverviewPanel title="低空站点网络" index="05" :subtitle="`${data.enabledStations} 个启用 / ${snapshot.stations.length} 个登记站点`" link="/digital-twin"><OverviewBars :items="data.stations" /></OverviewPanel>
        <OverviewPanel title="告警与处置态势" index="06" subtitle="当前快照未处置告警 · 最多最近500条中统计" link="/emergency-process"><div class="alert-distribution"><span v-for="item in data.severity" :key="item.key"><i :style="{ background:item.color }"></i>{{ item.label }}<b :style="{ color:item.color }">{{ item.value }}</b></span></div><ul class="event-list"><li v-for="event in data.latestEvents" :key="event.id"><span :class="event.severity">{{ event.severity === 'high' ? '高' : event.severity === 'medium' ? '中' : '低' }}</span><div><p>{{ event.title }}</p><small>{{ event.createdTime }}</small></div></li></ul><p v-if="!data.latestEvents.length" class="clear-alerts">当前快照暂无待处置告警</p></OverviewPanel>
      </aside>
    </div>
    <OverviewRecords :tasks="data.latestTasks" :audit="data.latestAudit" />
    <footer class="data-note">统计口径：顶部指标为Java全量汇总；两侧任务与告警面板基于最近500条快照。地图飞行、定位与车流为仿真，不代表实机运行。</footer>
  </section>
</template>
<style scoped>
.overview-dashboard { padding:12px 16px 10px; color:#d5edff; background:radial-gradient(ellipse at 50% 38%,#103b6629,transparent 55%),linear-gradient(#040e1b,#061326); min-height:100%; box-sizing:border-box; }.overview-heading { display:flex; align-items:center; justify-content:space-between; min-height:48px; gap:15px; margin-bottom:10px; }.eyebrow { font:9px 'Consolas',monospace; letter-spacing:2.5px; color:#4e91b9; }.overview-heading h1 { margin:5px 0 0; font-size:21px; font-weight:600; letter-spacing:3px; text-shadow:0 0 18px #23bcff50; }.data-state { display:flex; align-items:center; gap:7px; font-size:11px; color:#ffc45b; }.data-state i { width:6px; height:6px; border-radius:50%; background:currentColor; box-shadow:0 0 8px currentColor; }.data-state.live { color:#3dddb5; }.data-state>span { color:#6d91ac; margin-left:10px; }.connection-notice { padding:9px 12px; margin-bottom:10px; border:1px solid #795f30; color:#e8c58c; font-size:12px; background:#3d2f1633; }
.metric-strip { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-bottom:12px; }.metric-card { position:relative; display:flex; justify-content:space-between; align-items:center; gap:6px; padding:12px 18px; min-width:0; border:1px solid #23557b88; background:linear-gradient(110deg,#0b2b4c,#071727); box-shadow:inset 0 2px 0 #1e67a328; border-radius:3px; }.metric-card::before { content:''; position:absolute; left:0; top:23%; height:54%; width:2px; background:#36baf9; box-shadow:0 0 9px #36baf9; }.metric-card>div { display:grid; gap:7px; }.metric-card>div>span { font-size:12px; color:#b0cde2; letter-spacing:1px; }.metric-card small { font-size:9px; color:#618ba9; }.metric-card p { margin:0; white-space:nowrap; }.metric-card strong { font:500 31px 'Bahnschrift','Consolas',sans-serif; color:#65dfff; text-shadow:0 0 15px #31bbff55; }.metric-card p>span { margin-left:7px; font-size:10px; color:#75a0bd; }
.overview-stage { display:grid; grid-template-columns:minmax(240px,.9fr) minmax(0,2.4fr) minmax(240px,.9fr); gap:12px; align-items:stretch; }.data-column { min-width:0; display:grid; grid-template-rows:repeat(3,minmax(204px,1fr)); gap:12px; }.center-scene { min-width:0; display:flex; flex-direction:column; position:relative; border:1px solid #2d85b370; background:#05182a; box-shadow:inset 0 0 35px #1461a025; overflow:hidden; }.scene-topline,.scene-bottomline { display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap; padding:10px 13px; color:#6f9dbb; font-size:10px; }.scene-topline { background:linear-gradient(90deg,#0a2d4b,#0c1e36); border-bottom:1px solid #265a7c66; letter-spacing:1.2px; }.scene-topline a { color:#85d7f4; letter-spacing:0; text-decoration:none; font-size:11px; }.scene-container { flex:1; min-height:0; position:relative; }.scene-bottomline { border-top:1px solid #265a7c66; }.fleet-types { display:flex; justify-content:space-evenly; gap:5px; color:#729eb9; font-size:9px; margin-top:2px; }.fleet-types b { color:#bce8f8; margin-left:3px; font-weight:400; }
.alert-distribution { display:flex; gap:8px; justify-content:space-between; padding:0 0 9px; border-bottom:1px solid #26557655; }.alert-distribution>span { font-size:10px; color:#92acc3; display:flex; align-items:center; gap:4px; }.alert-distribution i { width:4px; height:4px; }.alert-distribution b { font:14px 'Consolas',monospace; }.event-list { margin:0; padding:0; list-style:none; }.event-list li { display:flex; gap:7px; align-items:flex-start; padding:7px 0; border-bottom:1px solid #26557633; }.event-list li>span { background:#14435e; color:#5fd2ff; font-size:10px; padding:2px 4px; flex-shrink:0; }.event-list li>span.high { background:#ff55772b; color:#ff829c; }.event-list li>span.medium { background:#ffa72d25; color:#ffc971; }.event-list p { margin:0; font-size:11px; color:#b7d0e3; line-height:1.4; overflow-wrap:anywhere; }.event-list small { display:block; margin-top:3px; font-size:9px; color:#6588a5; }.clear-alerts { padding:22px 0 10px; text-align:center; font-size:11px; color:#73b9b6; }.data-note { text-align:center; margin-top:10px; font-size:10px; line-height:1.6; color:#688aa4; }
@media(min-width:1650px) { .data-column { grid-template-rows:repeat(3,minmax(220px,1fr)); } }
@media(max-width:1200px) { .overview-stage { grid-template-columns:minmax(220px,1fr) minmax(0,2fr); }.right-column { grid-column:1 / -1; grid-template-columns:repeat(3,minmax(0,1fr)); grid-template-rows:minmax(220px,auto); }.data-state>span { display:none; } }
@media(max-width:800px) { .overview-dashboard { padding:10px; }.overview-heading h1 { font-size:17px; }.overview-heading { align-items:flex-start; }.data-state { max-width:120px; font-size:10px; }.metric-strip { grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }.metric-card { padding:10px; }.metric-card strong { font-size:25px; }.overview-stage { display:flex; flex-direction:column; }.center-scene { order:-1; height:480px; flex:none; }.data-column,.right-column { display:grid; grid-template-columns:1fr; grid-template-rows:repeat(3,220px); }.eyebrow { letter-spacing:1px; font-size:8px; } }
</style>
