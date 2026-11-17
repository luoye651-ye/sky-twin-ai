<script setup lang="ts">
import { computed } from 'vue'
import type { PatrolConfig, PatrolRun } from '@sky/patrol'
const props = defineProps<{ config: PatrolConfig; history: PatrolRun[]; selectedId: string; run?: PatrolRun; busy: boolean; canOperate: boolean }>()
const emit = defineEmits<{ start: []; refresh: []; select: [id: string] }>()
const labels = { queued: '等待巡逻', running: '巡逻识别中', completed: '巡逻完成', failed: '巡逻中断' }
const active = computed(() => props.history.some(row => ['queued', 'running'].includes(row.status)) || !!props.run && ['queued', 'running'].includes(props.run.status))
</script>

<template>
  <section class="control-card">
    <div class="toolbar">
      <el-button type="primary" :loading="busy" :disabled="!canOperate || !config.ready || active || busy"
        @click="emit('start')">{{ active ? '巡逻识别中' : '启动仿真巡逻' }}</el-button>
      <label for="patrol-history">巡逻记录</label>
      <select id="patrol-history" aria-label="巡逻记录" :value="selectedId"
        @change="emit('select', ($event.target as HTMLSelectElement).value)">
        <option value="">请选择记录</option>
        <option v-for="item in history" :key="item.id" :value="item.id">{{ item.createdTime }} · {{ labels[item.status] }}</option>
      </select>
      <el-button :disabled="busy" @click="emit('refresh')">刷新结果</el-button>
    </div>
    <p v-if="!config.ready" class="hint">识别服务尚未就绪，请稍后重试。</p>
    <p v-if="!canOperate" class="hint">当前账号只读，可查看检测结果，不能启动巡逻。</p>
    <p v-if="run?.status === 'running' || run?.status === 'queued'" class="hint" role="status">正在处理巡逻影像，请稍候…</p>
    <el-alert v-if="run?.status === 'failed'" type="error" :closable="false" title="本次巡逻识别中断，请重新启动巡逻或联系管理员检查识别服务。" />
  </section>
</template>

<style scoped>
.control-card { padding:18px 20px; border:1px solid #24465d; background:#0b2132; }
.toolbar { display:flex; gap:14px; align-items:center; }
.toolbar label { white-space:nowrap; color:#bcd8e8; }
.toolbar select { flex:1; min-width:120px; background:#102a3d; border:1px solid #31546b; color:#e1f1fa; padding:9px; }
.hint { color:#9bbbd0; font-size:13px; line-height:1.6; }
@media(max-width:800px) { .toolbar { flex-wrap:wrap; } }
</style>
