<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import type { Task } from '@sky/sky'
import type { AirspaceCheck } from '@sky/airspace'
const props = defineProps<{ tasks: Task[]; result?: AirspaceCheck; busy: boolean; canOperate: boolean }>()
defineEmits<{ check: [taskId: string, departureAt?: string] }>()
const taskId = shallowRef('')
const departureAt = shallowRef('')
const tasksToCheck = computed(() => props.tasks.filter(task => ['created', 'assigned'].includes(task.status)))
const selected = computed(() => tasksToCheck.value.some(task => task.id === taskId.value))
const phases: Record<string, string> = { takeoff: '起飞', cruise: '巡航', landing: '降落' }
</script>
<template>
  <section class="panel business-theme"><h2>航线检查</h2><div class="check-form"><el-select v-model="taskId" filterable placeholder="选择待分配或已分配任务" aria-label="待检查任务" :disabled="busy || !canOperate"><el-option v-for="task in tasksToCheck" :key="task.id" :label="task.title" :value="task.id" /></el-select><el-date-picker v-model="departureAt" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="预计起飞时间（留空为现在）" aria-label="预计起飞时间" :disabled="busy || !canOperate" /><el-button type="primary" :disabled="!selected || !canOperate" :loading="busy" @click="$emit('check', taskId, departureAt)">检查航线</el-button></div><p class="hint">检查覆盖起飞、直线巡航、降落全过程及区域生效时段。实际起飞时服务器会再次检查最新规则。</p>
    <template v-if="result"><el-alert :type="result.allowed ? 'success' : 'error'" :title="result.allowed ? '本次空域检查通过' : `发现 ${result.violations.length} 个违规航段，禁止起飞`" :closable="false" /><p class="hint">{{ result.taskTitle }} · 起飞 {{ result.departureAt }} · 规则版本 {{ result.ruleRevision }} · 检查 {{ result.checkedAt }}</p><el-table v-if="result.violations.length" :data="result.violations"><el-table-column prop="zoneName" label="区域" min-width="140" /><el-table-column label="阶段" width="75"><template #default="{ row }">{{ phases[row.phase] }}</template></el-table-column><el-table-column prop="reason" label="原因" min-width="200" /><el-table-column prop="entersAt" label="预计进入时间" min-width="170" /></el-table><p class="hint">这是所示时间与规则版本的检查快照；历史结果不是当前放行凭证。</p></template>
  </section>
</template>
<style scoped>.panel { padding:18px; border:1px solid #24465d; border-radius:7px; background:#0b2132; }.panel h2 { margin:0 0 16px; font-size:17px; }.check-form { display:flex; flex-wrap:wrap; gap:12px; }.check-form :deep(.el-select) { width:280px; }.hint { color:#92b4ca; font-size:12px; line-height:1.7; }</style>
