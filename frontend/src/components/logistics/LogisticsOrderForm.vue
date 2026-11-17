<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { Station } from '@sky/sky'
import type { CreateLogisticsOrderInput } from '../../api/logistics'

// 父组件提供站点、提交状态和服务端错误。
const props = defineProps<{
  stations: Station[]
  busy: boolean
  serverError: string
}>()

// 子组件通过 save 事件，把检查后的数据交给父组件。
const emit = defineEmits<{
  save: [data: CreateLogisticsOrderInput]
}>()

const validationError = ref('')

const form = reactive({
  cargoName: '',
  // 数字输入框被清空时，可能变成 undefined。
  weight: 1 as number | undefined,
  startStationId: '',
  endStationId: '',
  deadlineMinutes: 30 as number | undefined,
  reason: ''
})

function submit() {
  // 请求尚未结束时，不再次提交。
  if (props.busy) return

  validationError.value = ''

  const cargoName = form.cargoName.trim()
  const reason = form.reason.trim()
  const weight = form.weight
  const deadlineMinutes = form.deadlineMinutes

  if (!cargoName || !reason) {
    validationError.value = '请填写货物名称和创建原因'
    return
  }

  if (
    typeof weight !== 'number' ||
    !Number.isFinite(weight) ||
    weight < 0.01 ||
    weight > 10000
  ) {
    validationError.value = '重量应为0.01～10000千克'
    return
  }

  if (
    typeof deadlineMinutes !== 'number' ||
    !Number.isInteger(deadlineMinutes) ||
    deadlineMinutes < 1 ||
    deadlineMinutes > 1440
  ) {
    validationError.value = '配送时限应为1～1440的整数分钟'
    return
  }

  if (!form.startStationId || !form.endStationId) {
    validationError.value = '请选择起点站和终点站'
    return
  }

  if (form.startStationId === form.endStationId) {
    validationError.value = '起点与终点不能相同'
    return
  }

  // 创建一份独立的请求数据，交给父组件。
  emit('save', {
    cargoName,
    weight,
    startStationId: form.startStationId,
    endStationId: form.endStationId,
    deadlineMinutes,
    reason
  })
}
</script>

<template>
  <el-form
  :model="form"
  :disabled="props.busy"
  label-width="100px"
  @submit.prevent="submit"
>
    <el-alert
        v-if="validationError || props.serverError"
        :title="validationError || props.serverError"
        type="error"
        :closable="false"
    />
    <el-form-item label="货物名称">
      <el-input
        v-model="form.cargoName"
        placeholder="例如：应急药品"
        maxlength="80"
        show-word-limit
      />
    </el-form-item>

    <el-form-item label="重量（kg）">
      <el-input-number
        v-model="form.weight"
        :min="0.01"
        :max="10000"
        :precision="2"
        :step="0.01"
      />
    </el-form-item>

    <el-form-item label="起点站">
      <el-select
        v-model="form.startStationId"
        placeholder="请选择起点站"
        style="width: 100%"
      >
        <el-option
          v-for="station in props.stations"
          :key="station.id"
          :label="station.name"
          :value="station.id"
          :disabled="station.id === form.endStationId"
        />
      </el-select>
    </el-form-item>

    <el-form-item label="终点站">
      <el-select
        v-model="form.endStationId"
        placeholder="请选择终点站"
        style="width: 100%"
      >
        <el-option
          v-for="station in props.stations"
          :key="station.id"
          :label="station.name"
          :value="station.id"
          :disabled="station.id === form.startStationId"
        />
      </el-select>
    </el-form-item>

    <el-form-item label="时限（分钟）">
      <el-input-number
        v-model="form.deadlineMinutes"
        :min="1"
        :max="1440"
        :precision="0"
      />
    </el-form-item>

    <el-form-item label="创建原因">
      <el-input
        v-model="form.reason"
        type="textarea"
        :rows="3"
        maxlength="500"
        show-word-limit
        placeholder="请填写本次配送原因"
      />
    </el-form-item>
    <el-form-item>
        <el-button
            type="primary"
            native-type="submit"
            :loading="props.busy"
            :disabled="props.busy"
        >
            提交订单
        </el-button>
    </el-form-item>
  </el-form>
</template>
