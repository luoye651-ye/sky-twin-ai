<script setup lang="ts">
import { defineAsyncComponent, shallowRef, watch } from 'vue'
import { isolatedDemo } from '../../utils/runtime'
import { useRoute } from 'vue-router'
import { useSkyStore } from '../../stores/sky'
import { useWorkbenchRuns } from '../../composables/useWorkbenchRuns'
import { workbenchRequest } from '../../api/workbench'
import type { RunInput, WorkbenchRun } from '../../types/workbench'
import RunComposer from './RunComposer.vue'
import RunList from './RunList.vue'
import RunInspector from './RunInspector.vue'
const KnowledgeWorkbench=defineAsyncComponent(()=>import('./KnowledgeWorkbench.vue'))
const EvaluationWorkbench=defineAsyncComponent(()=>import('./EvaluationWorkbench.vue'))
const SpatialWorkbench=defineAsyncComponent(()=>import('./SpatialWorkbench.vue'))
const sky=useSkyStore(), route=useRoute(), tab=shallowRef('runs'), suggestedQuestion=shallowRef('')
async function resetDemo(){ await runs.act(()=>workbenchRequest('/reset',{},'POST'));selectedId.value='';await runs.load() }
const tabs=[{id:'runs',label:'运行中心 / 轨迹'},{id:'knowledge',label:'领域知识库'},{id:'evaluation',label:'效果评测'},{id:'spatial',label:'地图框选 / 航线对比'}].filter(t=>!isolatedDemo||t.id!=='spatial')
const runs=useWorkbenchRuns(()=>sky.authorized?sky.username:'')
const { rows, selected, selectedId, page, total, busy, error }=runs
watch(()=>route.query.runId,id=>{if(typeof id==='string'&&/^AR-[a-f0-9]{32}$/.test(id))selectedId.value=id},{immediate:true})
async function create(input:RunInput){ tab.value='runs';await runs.act(()=>workbenchRequest<WorkbenchRun>('/runs',{request_id:crypto.randomUUID(),...input},'POST')) }
async function action(name:string,input:Record<string,unknown>){ if(!selectedId.value)return;const id=selectedId.value;await runs.act(()=>workbenchRequest<WorkbenchRun>(`/runs/${id}/${name}`,input,'POST')) }
function evaluationCreated(run:WorkbenchRun){ selectedId.value=run.id;tab.value='runs';void runs.load() }
</script>
<template><section class="workbench business-theme"><h1>AI 工程工作台</h1><p v-if="isolatedDemo" class="demo-banner">独立样例环境：不连接Java业务、不调用外部模型；运行与知识数据单独保存。<button :disabled="busy" @click="resetDemo">重置我的演示记录</button></p><p>可恢复分析 · 真实调用轨迹 · 本地知识管理 · 效果对照 · 地图与图像证据</p><nav><button v-for="t in tabs" :key="t.id" :class="{selected:tab===t.id}" @click="tab=t.id">{{ t.label }}</button><RouterLink v-if="!isolatedDemo" to="/agent-command">原自然语言助手 →</RouterLink></nav><p v-if="error" class="error" role="alert">{{ error }}</p><template v-if="tab==='runs'"><RunComposer :disabled="busy" :selected="selected" :can-operate="sky.canOperate && !isolatedDemo" :suggested-question="suggestedQuestion" :initial-analysis-id="typeof route.query.analysisId==='string'?route.query.analysisId:''" @create="create" /><div class="run-grid"><RunList :rows="rows" :selected-id="selectedId" :page="page" :total="total" @select="selectedId=$event" @page="page=$event"/><RunInspector v-if="selected" :run="selected" :disabled="busy" :can-operate="sky.canOperate && !isolatedDemo" @action="action" @ask="suggestedQuestion=$event" /><p v-else>选择一条运行查看检查点和实际调用轨迹。</p></div></template><KnowledgeWorkbench v-else-if="tab==='knowledge'"/><EvaluationWorkbench v-else-if="tab==='evaluation'" :disabled="busy" :can-operate="sky.canOperate && !isolatedDemo" @created="evaluationCreated"/><SpatialWorkbench v-else-if="!isolatedDemo" @analyze="create"/></section></template>
<style scoped>.workbench{padding:24px;color:#d3e8f5;min-height:100%}.workbench>p{color:#9ebfd2;font-size:13px}.workbench nav{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:18px 0}.workbench :deep(button){padding:8px 12px;background:#14374d;border:1px solid #365a72;color:#d3e8f5;cursor:pointer}.workbench :deep(button:disabled){opacity:.45;cursor:default}.workbench nav button.selected{border-color:#50d7ef}.workbench a{color:#65d4ef}.run-grid{display:grid;grid-template-columns:minmax(240px,310px) minmax(0,1fr);gap:18px;margin-top:20px}.error{color:#ffb2a6!important}@media(max-width:950px){.run-grid{grid-template-columns:1fr}.workbench{padding:12px}}</style>
