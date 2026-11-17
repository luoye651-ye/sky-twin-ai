<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import type { DispatchPlan } from '@sky/dispatch'
import DispatchCandidateDialog from './DispatchCandidateDialog.vue'
import DispatchConfirmDialog from './DispatchConfirmDialog.vue'
const props = defineProps<{ plan: DispatchPlan; busy: boolean; canConfirm: boolean; remainingSeconds: number; canOperate: boolean }>()
const emit = defineEmits<{ confirm: [reason: string] }>()
const dialog = shallowRef(false)
const selectedTask = shallowRef('')
const details = computed(() => props.plan.result.decisions.find(value => value.taskId === selectedTask.value))
const rows = computed(() => props.plan.result.decisions.map(decision => ({ ...decision, assignment: props.plan.result.assignments.find(assignment => assignment.taskId === decision.taskId) })))
const metrics = computed(() => [
  { label: '已分配任务', optimized: `${props.plan.result.optimized.assignedCount} 项`, baseline: `${props.plan.result.baseline.assignedCount} 项` },
  { label: '优先级合计', optimized: String(props.plan.result.optimized.priorityTotal), baseline: String(props.plan.result.baseline.priorityTotal) },
  { label: '距起点距离合计', optimized: `${(props.plan.result.optimized.totalDistanceMeters / 1000).toFixed(2)} km`, baseline: `${(props.plan.result.baseline.totalDistanceMeters / 1000).toFixed(2)} km` },
  { label: '综合成本（越低越好）', optimized: props.plan.result.optimized.totalCost.toFixed(2), baseline: props.plan.result.baseline.totalCost.toFixed(2) },
])
watch(() => props.plan.id, () => { selectedTask.value = ''; dialog.value = false })
watch(() => props.plan.status, value => { if (value === 'confirmed') dialog.value = false })
</script>
<template>
  <section class="result business-theme">
    <div class="title-row"><h2>2. 审查调度方案</h2><el-tag :type="plan.status === 'confirmed' ? 'success' : 'info'">{{ plan.status === 'confirmed' ? '已确认派机' : remainingSeconds ? `有效期剩余 ${remainingSeconds} 秒` : '方案已过期' }}</el-tag></div>
    <p class="hint">最小费用最大匹配 · {{ plan.result.algorithm }} · 计算耗时 {{ plan.result.calculationMs.toFixed(2) }} ms</p>
    <table class="comparison"><thead><tr><th>指标</th><th>集群优化</th><th>顺序就近派机</th></tr></thead><tbody><tr v-for="metric in metrics" :key="metric.label"><td>{{ metric.label }}</td><td>{{ metric.optimized }}</td><td>{{ metric.baseline }}</td></tr></tbody></table>
    <p class="hint">对比使用同一批任务、资源和硬约束；基线按优先级、任务ID依次选择最近可用飞行器。先比较任务数和优先级，再比较成本；单批结果不代表普遍提升。</p>
    <el-table :data="rows" row-key="taskId"><el-table-column prop="taskTitle" label="任务" min-width="155" /><el-table-column label="等级" width="70"><template #default="{ row }">{{ ['','普通','优先','紧急'][row.priority] }}</template></el-table-column><el-table-column label="推荐飞行器" min-width="145"><template #default="{ row }">{{ row.assignment?.aircraftName ?? '等待资源' }}</template></el-table-column><el-table-column label="评分" width="75"><template #default="{ row }">{{ row.assignment?.score.toFixed(1) ?? '—' }}</template></el-table-column><el-table-column label="预计余电" width="90"><template #default="{ row }">{{ row.assignment ? `${row.assignment.remainingBattery.toFixed(1)}%` : '—' }}</template></el-table-column><el-table-column label="依据" width="115"><template #default="{ row }"><el-button link type="primary" @click="selectedTask = row.taskId">候选与原因</el-button></template></el-table-column></el-table>
    <div class="confirm-row"><span class="hint">{{ plan.status === 'confirmed' ? `确认人：${plan.confirmedBy} · ${plan.confirmedAt}` : '确认后锁定资源并复查规则，任一分配失败将整批回滚。' }}</span><el-button v-if="plan.status === 'proposed' && canOperate" type="primary" :disabled="!canConfirm" @click="dialog = true">确认批量派机</el-button><RouterLink v-else-if="plan.status === 'confirmed'" to="/task-management">前往任务管理执行 →</RouterLink></div>
    <p class="hint">评分 = 100 − 距离成本（45分）− 电量成本（35分）− 运力冗余成本（20分）。距起点距离仅用于排序，未模拟调机飞行。预计耗电为每仿真秒0.08个百分点；已检查禁飞/限高区，确认与起飞时复查，两机时空冲突检测待接入。</p>
    <DispatchCandidateDialog :decision="details" @close="selectedTask = ''" />
    <DispatchConfirmDialog :open="dialog" :busy="busy" :count="plan.result.assignments.length" :can-confirm="canConfirm && canOperate" @close="dialog = false" @confirm="emit('confirm', $event)" />
  </section>
</template>
<style scoped>
.result { background:#0b2132; border:1px solid #24465d; border-radius:8px; padding:20px; }.title-row,.confirm-row { display:flex; align-items:center; justify-content:space-between; gap:16px; }.title-row h2 { font-size:18px; margin:0; }.hint { font-size:12px; color:#90b4cb; line-height:1.8; }.comparison { width:100%; border-collapse:collapse; font-size:13px; margin:18px 0; }.comparison th,.comparison td { padding:10px; text-align:left; border-bottom:1px solid #24465d; }.comparison th { color:#8cb9d3; }.comparison td:nth-child(2) { color:#64e7c2; }.confirm-row { margin-top:18px; }.confirm-row a { color:#57d6ff; }@media(max-width:900px) { .confirm-row { flex-wrap:wrap; } }
</style>
