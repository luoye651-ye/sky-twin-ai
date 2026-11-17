<script setup lang="ts">
import { reactive } from 'vue'
defineProps<{ selected: boolean; active: boolean; playing: boolean; loading: boolean; offset: number; duration: number; at: number; speed: number; count: number; held: boolean; hasMore: boolean; error: string }>()
const emit = defineEmits<{ load: [from: string, to: string]; play: []; pause: []; exit: []; seek: [offset: number]; speed: [value: number] }>()
const local = (date: Date) => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 19)
const form = reactive({ from: local(new Date(Date.now() - 3600000)), to: local(new Date(Date.now() + 60000)) })
function load() { emit('load', new Date(form.from).toISOString(), new Date(form.to).toISOString()) }
function recent() { form.from = local(new Date(Date.now() - 3600000)); form.to = local(new Date(Date.now() + 1000)); load() }
</script>
<template>
  <section class="panel"><h2>3 · 历史定位回放（只读）</h2><form class="actions" @submit.prevent="load"><label>开始时间（本地）<input v-model="form.from" required type="datetime-local" step="1" /></label><label>结束时间（不包含）<input v-model="form.to" required type="datetime-local" step="1" /></label><el-button native-type="submit" :disabled="!selected || loading">加载轨迹</el-button><el-button :disabled="!selected || loading" @click="recent">最近一小时</el-button></form>
    <el-alert v-if="error" :title="error" type="warning" :closable="false" /><el-alert v-if="hasMore" title="超过5000点，仅加载前5000点，请缩短查询时段后查看完整轨迹。" type="warning" :closable="false" />
    <div v-if="active" class="playback"><span>{{ count }} 个有效点 · {{ new Date(at).toLocaleString() }} · {{ held ? '缺测/端点停留，不插值' : '有效点间线性插值' }}</span><input aria-label="回放进度" type="range" min="0" :max="duration" step="1" :value="offset" @input="emit('seek', Number(($event.target as HTMLInputElement).value))" /><div class="actions"><el-button :disabled="!duration" @click="playing ? emit('pause') : emit('play')">{{ playing ? '暂停回放' : '播放' }}</el-button><label>倍速<select aria-label="倍速" :value="speed" @change="emit('speed', Number(($event.target as HTMLSelectElement).value))"><option :value="1">1×</option><option :value="5">5×</option><option :value="10">10×</option></select></label><el-button @click="emit('exit')">退出回放，返回实时</el-button></div></div>
    <p>只使用服务端通过校验的记录，按原采样时间播放；跨会话或超过5秒缺测不连线、不插值。回放不发送定位请求，也不改变任务、订单或实时位置。</p>
  </section>
</template>
<style scoped>.panel { padding:18px; border:1px solid #21445b; background:#0b1d2d; }.panel h2 { margin:0 0 16px; font-size:16px; }.actions { display:flex; flex-wrap:wrap; gap:12px; align-items:end; margin-bottom:16px; }label { display:grid; gap:6px; font-size:12px; color:#a1c1d3; }input,select { color:#dcf4ff; background:#102a3d; border:1px solid #31546b; padding:8px; border-radius:4px; }.playback { display:grid; gap:14px; margin-top:16px; font-size:13px; }.playback input[type=range] { width:100%; padding:0; }.panel p { color:#a1c1d3; font-size:12px; line-height:1.7; }</style>
