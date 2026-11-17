<script setup lang="ts">
import { computed, watch } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { useFleetDispatch } from '../../composables/useFleetDispatch'
import DispatchPlanResult from '../dispatch/DispatchPlanResult.vue'

import type { AgentMapTarget } from '../../types/agent'
defineEmits<{ locate: [target: AgentMapTarget] }>()
const props = defineProps<{ planId: string }>()
const sky = useSkyStore()
const { plan, busy, error, notice, remainingSeconds, canConfirm, confirm, open } = useFleetDispatch(() => sky.refresh())
const decisions = computed(() => plan.value?.result.decisions ?? [])
watch(() => props.planId, id => { void open(id) }, { immediate: true })
</script>

<template>
  <section class="dispatch-card" aria-label="自然语言调度方案">
    <p class="dispatch-id">Java 方案：{{ planId }} · 确认只分配任务，随后到任务管理执行仿真</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <el-alert v-if="notice" :title="notice" type="success" :closable="false" />
    <el-button :loading="busy" @click="open(planId)">刷新方案状态</el-button>
    <div v-if="plan"><el-button v-for="task in decisions" :key="task.taskId" @click="$emit('locate', { kind: 'task', id: task.taskId, label: task.taskTitle })">查看航线：{{ task.taskTitle }}</el-button></div>
    <DispatchPlanResult v-if="plan" :plan="plan" :busy="busy" :can-confirm="canConfirm"
      :remaining-seconds="remainingSeconds" :can-operate="sky.canOperate" @confirm="confirm" />
  </section>
</template>

<style scoped>
.dispatch-card{margin-top:16px;overflow:auto;max-width:100%}.dispatch-id{font-size:12px;color:#91bdd0;overflow-wrap:anywhere}.dispatch-card :deep(.result){min-width:560px;margin-top:12px}
</style>
