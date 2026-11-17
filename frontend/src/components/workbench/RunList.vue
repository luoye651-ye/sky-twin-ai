<script setup lang="ts">
import type { WorkbenchRun } from '../../types/workbench'
defineProps<{ rows: WorkbenchRun[]; selectedId: string; page: number; total: number }>()
defineEmits<{ select: [id: string]; page: [value: number] }>()
</script>
<template><aside class="run-list"><h2>我的持久化运行</h2><button v-for="run in rows" :key="run.id" :class="{ selected: run.id === selectedId }" @click="$emit('select',run.id)"><strong>{{ run.kind === 'evaluation' ? '对照评测' : run.input.question }}</strong><span>{{ run.status }} · {{ run.input.mode ?? run.input.evaluation_mode }}</span><small>{{ new Date(run.created*1000).toLocaleString() }} · {{ run.id }}</small></button><p v-if="!rows.length">暂无运行记录。可以先运行独立样例。</p><el-pagination :current-page="page" :page-size="20" :total="total" layout="prev, pager, next" @current-change="$emit('page',$event)" /></aside></template>
<style scoped>.run-list{min-width:0}.run-list button{display:grid;gap:7px;padding:12px;margin-bottom:8px;background:#102537;border:1px solid #31546b;color:#d3e8f5;width:100%;text-align:left;cursor:pointer}.run-list button.selected{border-color:#50d7ef}.run-list strong{font-size:13px}.run-list span,.run-list small{font-size:11px;color:#9ebfd2;overflow-wrap:anywhere}</style>
