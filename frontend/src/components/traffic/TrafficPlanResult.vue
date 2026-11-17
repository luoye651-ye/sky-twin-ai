<script setup lang="ts">
import type { TrafficConflict, TrafficPlan } from '@sky/traffic'
defineProps<{ plan?: TrafficPlan; busy: boolean; canOperate: boolean; reason: string }>()
defineEmits<{ confirm: []; focus: [hit: TrafficConflict] }>()
</script>
<template>
  <section v-if="plan" class="card"><h2>2 · {{ plan.status === 'confirmed' ? '已确认的错峰方案' : '错峰方案预览（尚未预约）' }}</h2><p>方案 {{ plan.id }} · 任务顺序优先、逐秒搜索可行时隙，非全局最优。起飞时刻为仿真 tick，不是承诺的墙钟时间；确认时从当前 tick 重算提前量，错峰量变化则拒绝。</p>
    <el-alert :title="plan.result.allowed ? '所有任务均找到可行时隙' : '存在不可执行任务，不能确认整批方案'" :type="plan.result.allowed ? 'success' : 'error'" :closable="false" />
    <div class="table-wrap"><table><thead><tr><th>任务 / 飞行器</th><th>航线版本</th><th>额外等待</th><th>起飞 tick</th><th>预计飞行</th><th>校验结果</th></tr></thead><tbody><tr v-for="s in plan.result.slots" :key="s.taskId"><td>{{ s.title }} / {{ s.aircraftId }}</td><td>v{{ s.routeRevision }}</td><td>{{ s.allowed ? `${s.delaySeconds} 秒` : '无可行时隙' }}</td><td>{{ s.allowed ? s.departureTick : '—' }}</td><td>{{ s.durationSeconds }} 秒</td><td>{{ s.problems.join('；') || '通过' }}</td></tr></tbody></table></div>
    <h3>本任务未额外错峰时的预计冲突（前序按方案安排；不是实时碰撞告警）</h3>
    <div v-for="s in plan.result.slots" :key="s.taskId"><p v-if="!s.conflicts.length">{{ s.title }}：无冲突</p><div v-for="(hit, i) in s.conflicts" :key="i" class="conflict"><span>{{ s.title }} ↔ {{ hit.otherTitle }} · tick {{ hit.entersTick.toFixed(2) }} · 高度 {{ hit.altitude.toFixed(1) }} m · 水平 {{ hit.horizontalMeters.toFixed(1) }} m / 垂直 {{ hit.verticalMeters.toFixed(1) }} m</span><el-button @click="$emit('focus', hit)">定位冲突点</el-button></div></div>
    <el-button type="primary" :disabled="busy || !canOperate || !reason.trim() || !plan.result.allowed || plan.status !== 'proposed'" @click="$emit('confirm')">确认预约并自动起飞</el-button>
  </section>
</template>
<style scoped>.card { padding:18px; border:1px solid #21445b; background:#0b1d2d; }.card h2 { font-size:17px; margin:0 0 12px; }.card h3 { font-size:14px; }.card p { color:#acc7d8; font-size:12px; line-height:1.8; }.table-wrap { overflow:auto; margin:16px 0; }table { width:100%; border-collapse:collapse; font-size:13px; }th,td { text-align:left; padding:12px; border-bottom:1px solid #21445b; }.conflict { display:flex; flex-wrap:wrap; gap:16px; align-items:center; margin:12px 0; color:#ffcf83; font-size:13px; }</style>
