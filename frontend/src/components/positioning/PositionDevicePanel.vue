<script setup lang="ts">
import { computed, reactive } from 'vue'
import type { Aircraft } from '@sky/sky'
import { connectionLabels, type PositionDevice } from '@sky/positioning'
const props = defineProps<{ devices: PositionDevice[]; aircraft: Aircraft[]; selectedId: string; busy: boolean; canManage: boolean; canOperate: boolean }>()
const emit = defineEmits<{ select: [id: string]; bind: [input: { id: string; name: string; aircraftId: string }]; mode: [enabled: boolean] }>()
const form = reactive({ id: '', name: '', aircraftId: '' })
const available = computed(() => props.aircraft.filter(a => !props.devices.some(d => d.aircraftId === a.id)))
const selected = computed(() => props.devices.find(d => d.id === props.selectedId))
</script>
<template>
  <section class="panel"><h2>1 · 绑定与启用终端</h2>
    <form v-if="canManage" class="binding" @submit.prevent="emit('bind', { ...form })">
      <label>终端编号<input v-model="form.id" required maxlength="64" pattern="[A-Za-z0-9_-]{1,64}" placeholder="例如 PC-UAV-01" /></label>
      <label>终端名称<input v-model="form.name" required maxlength="80" placeholder="电脑仿真终端" /></label>
      <label>绑定飞行器<select v-model="form.aircraftId" aria-label="绑定飞行器" required><option disabled value="">选择未绑定飞行器</option><option v-for="a in available" :key="a.id" :value="a.id">{{ a.name }}</option></select></label>
      <el-button native-type="submit" :disabled="busy || !available.length">创建绑定</el-button>
    </form>
    <div class="selection"><label>当前终端<select aria-label="当前终端" :value="selectedId" @change="emit('select', ($event.target as HTMLSelectElement).value)"><option disabled value="">请选择终端</option><option v-for="d in devices" :key="d.id" :value="d.id">{{ d.name }} · {{ d.aircraftName }}</option></select></label>
      <el-button v-if="selected" :disabled="busy || !canOperate" @click="emit('mode', !selected.enabled)">{{ selected.enabled ? '停用定位，恢复任务仿真' : '启用终端定位' }}</el-button>
    </div>
    <p v-if="selected" class="meta">{{ selected.id }} · {{ connectionLabels[selected.connectionState] }} · 来源：电脑仿真终端 · 最后有效采样：{{ selected.sampledAt ? new Date(selected.sampledAt).toLocaleString() : '暂无' }}</p>
    <p v-if="selected?.sampledAt" class="meta coordinates">WGS84 {{ selected.longitude?.toFixed(6) }}, {{ selected.latitude?.toFixed(6) }} · 相对高度 {{ selected.altitude?.toFixed(1) }} m</p>
    <p class="meta">绑定不可修改；启用需要飞行器空闲。启用后禁止任务派机与资源编辑；停用恢复原任务仿真位置，不把遥测视为任务完成。</p>
  </section>
</template>
<style scoped>
.panel { padding:18px; border:1px solid #21445b; background:#0b1d2d; }.panel h2 { margin:0 0 16px; font-size:16px; }.binding,.selection { display:flex; flex-wrap:wrap; gap:14px; align-items:end; margin-bottom:14px; }.binding label,.selection label { display:grid; gap:7px; font-size:12px; color:#a1c1d3; }input,select { background:#102a3d; border:1px solid #31546b; color:#dcf4ff; border-radius:4px; padding:9px; min-width:180px; }.meta { color:#a1c1d3; font-size:12px; line-height:1.7; margin-bottom:0; }
</style>
