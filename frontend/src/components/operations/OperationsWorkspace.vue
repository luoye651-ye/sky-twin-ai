<script setup lang="ts">
import { defineAsyncComponent, shallowRef } from 'vue'
const TaskOperationsPane = defineAsyncComponent(() => import('./TaskOperationsPane.vue'))
const ResourceOperationsPane = defineAsyncComponent(() => import('./ResourceOperationsPane.vue'))
const AnalysisHistoryPane = defineAsyncComponent(() => import('./AnalysisHistoryPane.vue'))
const CommutePane = defineAsyncComponent(() => import('./CommutePane.vue'))
const ReportCenterPane = defineAsyncComponent(() => import('./ReportCenterPane.vue'))
const active = shallowRef('tasks')
</script>
<template><section class="operations business-theme"><h1>业务运营中心 · 仿真</h1><nav><button v-for="tab in [{id:'tasks',label:'任务运营'},{id:'resources',label:'资源运维'},{id:'analyses',label:'检测历史'},{id:'commute',label:'通勤预约'},{id:'reports',label:'报告中心'}]" :key="tab.id" :class="{selected:active === tab.id}" @click="active = tab.id">{{ tab.label }}</button></nav><TaskOperationsPane v-if="active === 'tasks'" /><ResourceOperationsPane v-else-if="active === 'resources'" /><AnalysisHistoryPane v-else-if="active === 'analyses'" /><CommutePane v-else-if="active === 'commute'" /><ReportCenterPane v-else /></section></template>
<style scoped>.operations{padding:24px;min-height:100%;color:#d3e8f5}.operations nav{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}.operations button{padding:10px 18px;color:#a8cde0;background:#102a3d;border:1px solid #31546b;cursor:pointer}.operations button.selected{border-color:#50d7ef;color:#fff}.operations :deep(p){font-size:13px;line-height:1.8;color:#9ebfd2}.operations :deep(a){color:#65d4ef}.operations :deep(.el-pagination){margin:16px 0}.operations :deep(.el-alert){margin:12px 0}</style>
