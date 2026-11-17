<script setup lang="ts">
import { trafficStatus, type TrafficState } from '@sky/traffic'
defineProps<{ state?: TrafficState; busy: boolean; canOperate: boolean; reason: string }>()
defineEmits<{ cancel: [taskId: string]; load: [id: string] }>()
</script>
<template>
  <section class="card"><h2>3 · 当前预约与执行</h2><p>取消预约只释放时隙，不取消任务；已起飞任务请在任务管理中终止。</p><div class="table-wrap"><table><thead><tr><th>任务</th><th>状态</th><th>起飞 tick / 剩余仿真秒</th><th>复核消息</th><th>操作</th></tr></thead><tbody><tr v-for="s in state?.slots ?? []" :key="s.taskId"><td>{{ s.title }}</td><td>{{ trafficStatus[s.status] ?? s.status }}</td><td>{{ s.departureTick }} / {{ s.status === 'reserved' ? Math.max(0, s.departureTick - (state?.clockTick ?? 0)) : '—' }}</td><td>{{ s.message || '—' }}</td><td><el-button :disabled="busy || !canOperate || !reason.trim() || s.status !== 'reserved'" @click="$emit('cancel', s.taskId)">取消预约</el-button></td></tr></tbody></table></div>
    <h3>方案历史</h3><div class="history"><el-button v-for="p in state?.plans ?? []" :key="p.id" :disabled="busy" @click="$emit('load', p.id)">{{ p.createdTime }} · {{ trafficStatus[p.status] ?? p.status }}</el-button></div>
  </section>
</template>
<style scoped>.card { padding:18px; border:1px solid #21445b; background:#0b1d2d; }.card h2 { font-size:17px; margin:0; }.card p { font-size:12px; color:#acc7d8; }.card h3 { font-size:14px; }.table-wrap { overflow:auto; }table { width:100%; font-size:13px; border-collapse:collapse; }td,th { padding:12px; border-bottom:1px solid #21445b; text-align:left; }.history { display:flex; flex-wrap:wrap; gap:12px; }</style>
