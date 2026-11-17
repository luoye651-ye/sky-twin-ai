<script setup lang="ts">
import { statusLabels, taskTypes, type Task, type Audit } from '../../../../shared/sky'
defineProps<{ tasks:Task[]; audit:Audit[] }>()
</script>
<template>
  <div class="overview-records">
    <section class="record-panel"><header><h2>最新任务</h2><RouterLink to="/task-management">任务中心 ↗</RouterLink></header>
      <div class="table-scroll"><table><thead><tr><th>任务名称</th><th>场景</th><th>飞行器</th><th>状态</th><th>进度</th></tr></thead><tbody><tr v-for="t in tasks" :key="t.id"><td :title="t.title">{{ t.title }}</td><td>{{ taskTypes[t.type] }}</td><td>{{ t.aircraftName || '未分配' }}</td><td>{{ statusLabels[t.status] ?? t.status }}</td><td>{{ t.progress.toFixed(0) }}%</td></tr></tbody></table><p v-if="!tasks.length" class="empty">暂无任务，创建任务后显示</p></div>
    </section>
    <section class="record-panel"><header><h2>操作记录</h2><span>最近4条 · Java业务审计</span></header>
      <div class="audit-list"><article v-for="r in audit" :key="r.id"><div><strong>{{ r.action }}</strong><time>{{ r.createdTime }}</time></div><p>{{ r.actor }} · {{ r.reason }}</p></article><p v-if="!audit.length" class="empty">暂无操作记录</p></div>
    </section>
  </div>
</template>
<style scoped>
.overview-records { display:grid; grid-template-columns:1.4fr 1fr; gap:12px; margin-top:12px; }.record-panel { min-width:0; background:#07182be6; border:1px solid #22587980; border-radius:3px; padding:12px 14px; }.record-panel header { display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:8px; }.record-panel h2 { font-size:13px; color:#cce8fb; margin:0; }.record-panel a,.record-panel header>span { color:#7da9c7; font-size:10px; text-decoration:none; }.table-scroll { overflow:auto; max-height:185px; }table { width:100%; border-collapse:collapse; font-size:11px; white-space:nowrap; text-align:left; }th { color:#79a5c3; font-weight:400; padding:8px; background:#13385766; }td { color:#b1cce0; border-bottom:1px solid #224d6b55; padding:10px 8px; max-width:230px; overflow:hidden; text-overflow:ellipsis; }.audit-list { max-height:185px; overflow:auto; scrollbar-width:thin; }.audit-list article { padding:7px 0; border-bottom:1px solid #224d6b55; }.audit-list article>div { display:flex; justify-content:space-between; gap:8px; }.audit-list strong { font:11px 'Consolas',monospace; color:#66c8eb; }.audit-list time { color:#698ca7; font-size:10px; }.audit-list p { margin:5px 0 0; font-size:11px; color:#9ab6cb; overflow-wrap:anywhere; }.empty { color:#7b9db8; font-size:12px; text-align:center; padding:12px; }@media(max-width:800px) { .overview-records { grid-template-columns:1fr; } }
</style>
