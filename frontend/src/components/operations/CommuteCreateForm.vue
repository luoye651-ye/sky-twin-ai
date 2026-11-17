<script setup lang="ts">
import { computed, reactive, watch, shallowRef } from 'vue'
import type { Station } from '@sky/sky'
const props = defineProps<{ stations: Station[]; disabled: boolean }>()
const emit = defineEmits<{ create: [input: { requestId: string; title: string; startStationId: string; endStationId: string; departureAt: string; seats: number; reason: string }] }>()
const form = reactive({ title: '仿真通勤班次', startStationId: '', endStationId: '', departureAt: '', seats: 4, reason: '' })
const requestId = shallowRef(crypto.randomUUID() as string)
watch(form, () => { requestId.value = crypto.randomUUID() })
const stations = computed(() => props.stations.filter(s => s.type === 'vertiport' && s.status === 'enabled'))
</script>
<template><form class="flight-form" @submit.prevent="emit('create', { ...form, departureAt: form.departureAt.length === 16 ? form.departureAt + ':00' : form.departureAt, requestId })"><fieldset :disabled="disabled"><legend>新建仿真班次</legend><label>班次名称<input v-model="form.title" maxlength="80" required></label><label>出发起降场<select v-model="form.startStationId" required><option value="">请选择</option><option v-for="s in stations" :key="s.id" :value="s.id">{{ s.name }}</option></select></label><label>到达起降场<select v-model="form.endStationId" required><option value="">请选择</option><option v-for="s in stations" :key="s.id" :value="s.id" :disabled="s.id === form.startStationId">{{ s.name }}</option></select></label><label>计划出发（项目时间 Asia/Shanghai）<input v-model="form.departureAt" type="datetime-local" required></label><label>可售座位<input v-model.number="form.seats" type="number" min="1" max="20" required></label><label>创建原因<input v-model="form.reason" maxlength="500" required></label><button type="submit">创建班次</button></fieldset></form></template>
<style scoped>fieldset{display:flex;gap:14px;flex-wrap:wrap;border:1px solid #31546b;padding:16px}label{display:grid;gap:6px;font-size:12px;color:#acc7d8}input,select{background:#102a3d;color:#e1f1fa;padding:8px;border:1px solid #31546b}button{align-self:end;padding:9px;cursor:pointer}</style>
