<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Aircraft } from '@sky/sky'
import type { LogisticsAction, LogisticsActionInput, LogisticsOrder } from '../../api/logistics'
import { actionLabels, formatTime } from './logisticsPresentation'

const props = defineProps<{ action: LogisticsAction; order: LogisticsOrder; aircraft: Aircraft[]; busy: boolean; serverError: string }>()
const emit = defineEmits<{ save: [input: LogisticsActionInput]; close: [] }>()
const aircraftId = ref('')
const reason = ref('')
const validationError = ref('')
const requiredBattery = computed(() => Math.max(25, props.order.durationSeconds * .08 + 20))
const candidates = computed(() => props.aircraft.filter(a => a.type === 'cargo' && a.status === 'idle'
  && a.payloadCapacity >= props.order.weight && a.battery >= requiredBattery.value))
const canAct = computed(() => props.order.status === 'created' && (
  props.action === 'assign' ? props.order.taskStatus === 'created'
    : props.action === 'start' ? props.order.taskStatus === 'assigned'
      : props.action === 'deliver' ? props.order.taskStatus === 'completed'
        : ['created', 'assigned', 'executing'].includes(props.order.taskStatus)))
const deadlineBlocked = computed(() => ['assign', 'start'].includes(props.action)
  && Date.parse(props.order.serverTime) + props.order.durationSeconds * 1000 > Date.parse(props.order.deadlineAt))

function submit() {
  if (props.busy) return
  validationError.value = ''
  if (!canAct.value) { validationError.value = '订单状态已变化，请关闭弹窗后刷新'; return }
  if (deadlineBlocked.value) { validationError.value = '配送时限不足，请取消后重新创建订单'; return }
  const text = reason.value.trim()
  if (!text || text.length > 500) { validationError.value = '请填写1～500个字符的操作原因'; return }
  if (props.action === 'assign' && !candidates.value.some(a => a.id === aircraftId.value)) {
    validationError.value = '请选择符合载重、电量要求的空闲货运无人机'; return
  }
  emit('save', { reason: text, ...(props.action === 'assign' ? { aircraftId: aircraftId.value } : {}) })
}
</script>

<template>
  <el-dialog :model-value="true" :title="actionLabels[action]" width="560px"
    :close-on-click-modal="false" :close-on-press-escape="!busy" :show-close="!busy" @close="emit('close')">
    <p class="cargo-title">{{ order.cargoName }} · {{ order.weight }} kg</p>
    <p class="route">{{ order.startStationName }} → {{ order.endStationName }}</p>
    <el-alert v-if="validationError || serverError" :title="validationError || serverError" type="error" :closable="false" />
    <el-alert v-if="!canAct" title="订单状态已变化，当前操作不可用" type="warning" :closable="false" />
    <el-alert v-if="deadlineBlocked" title="预计仿真抵达时间超过截止时间，不能分配或起飞" type="warning" :closable="false" />
    <p v-if="action === 'assign' || action === 'start'" class="hint">
      预计仿真耗时 {{ order.durationSeconds }} 秒；截止 {{ formatTime(order.deadlineAt) }}。电量采用仿真估算规则。
    </p>
    <p v-if="action === 'deliver'" class="hint">确认本次仿真配送结果，系统将记录当前登录人和确认时间。</p>
    <el-form label-width="90px" :disabled="busy" @submit.prevent="submit">
      <el-form-item v-if="action === 'assign'" label="货运机" required>
        <el-select v-model="aircraftId" placeholder="选择空闲货运无人机" style="width:100%" aria-label="配送货运机">
          <el-option v-for="a in candidates" :key="a.id" :value="a.id"
            :label="`${a.name} · 载重 ${a.payloadCapacity} kg · 电量 ${a.battery.toFixed(0)}%`" />
        </el-select>
        <span v-if="!candidates.length" class="hint">暂无符合条件的资源，请在业务管理中维护货运机、电量和载重。</span>
      </el-form-item>
      <el-form-item label="操作原因" required>
        <el-input v-model="reason" type="textarea" :rows="3" maxlength="500" show-word-limit
          placeholder="填写调度原因或送达确认依据" aria-label="配送操作原因" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button :disabled="busy" @click="emit('close')">取消</el-button>
      <el-button :type="action === 'cancel' ? 'danger' : 'primary'" :loading="busy"
        :disabled="busy || !canAct || deadlineBlocked" @click="submit">{{ action === 'deliver' ? '确认送达' : `确认${actionLabels[action]}` }}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.cargo-title { font-size:18px; font-weight:600; }.route,.hint { color:#83a8bf; line-height:1.7; }
.hint { font-size:13px; }.el-alert { margin:12px 0; }
</style>
