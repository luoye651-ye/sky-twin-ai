<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSkyStore } from '../../stores/sky'
import { usePatrolEvaluation } from '../../composables/usePatrolEvaluation'
import PatrolControls from './PatrolControls.vue'
import PatrolResults from './PatrolResults.vue'
import PatrolImage from './PatrolImage.vue'
import type { PatrolRow } from '@sky/patrol'

const sky = useSkyStore(), route = useRoute(), router = useRouter()
const patrol = usePatrolEvaluation(typeof route.query.runId === 'string' ? route.query.runId : '')
const { config, history, detail, selectedId, busy, error } = patrol
const selectedImage = shallowRef<PatrolRow>()
const report = computed(() => detail.value?.status === 'completed' ? detail.value.report : undefined)
watch(() => report.value?.runId, () => { selectedImage.value = undefined })
watch(selectedId, id => {
  if (id && route.query.runId !== id) void router.replace({ query: { ...route.query, runId: id } })
})
watch(() => route.query.runId, id => { if (typeof id === 'string') selectedId.value = id })
</script>

<template>
  <section class="patrol-workspace business-theme">
    <div class="page-heading">
      <div><h1>环境发现</h1><p>AI水域巡逻 · 漂浮物识别</p></div>
    </div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <PatrolControls :config="config" :history="history" :selected-id="selectedId" :run="detail"
      :busy="busy" :can-operate="sky.canOperate" @start="patrol.start" @refresh="patrol.refresh"
      @select="selectedId = $event" />
    <PatrolResults v-if="report" :rows="report.rows" @select="selectedImage = $event" />
    <div v-else class="empty" role="status">
      {{ detail?.status === 'running' || detail?.status === 'queued'
        ? '巡逻识别中，完成后将显示逐图检测结果。可离开或刷新页面，运行记录会保留。'
        : '暂无检测结果，点击“启动仿真巡逻”开始识别。' }}
    </div>
    <PatrolImage v-if="report && selectedImage" :run-id="report.runId" :item="selectedImage"
      @close="selectedImage = undefined" />
  </section>
</template>

<style scoped>
.patrol-workspace { padding:24px; display:grid; gap:18px; max-width:1900px; margin:auto; }
.page-heading { margin-bottom:0; }
.empty { padding:35px; text-align:center; border:1px dashed #31546b; color:#92b7cd; line-height:1.8; }
@media(max-width:800px) { .patrol-workspace { padding:14px; } }
</style>
