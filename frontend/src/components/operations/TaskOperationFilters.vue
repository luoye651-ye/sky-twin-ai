<script setup lang="ts">
import { taskTypes, statusLabels } from '@sky/sky'
const keyword = defineModel<string>('keyword', { required: true }), state = defineModel<string>('state', { required: true }), type = defineModel<string>('type', { required: true })
defineProps<{ busy: boolean }>(); defineEmits<{ search: [] }>()
</script>
<template><form class="filters" @submit.prevent="$emit('search')"><el-input v-model="keyword" maxlength="200" placeholder="任务标题或编号" aria-label="运营任务搜索" /><el-select v-model="state" aria-label="任务状态"><el-option label="全部状态" value="" /><el-option v-for="s in ['created','assigned','executing','completed','failed','cancelled']" :key="s" :label="statusLabels[s]" :value="s" /></el-select><el-select v-model="type" aria-label="任务类型"><el-option label="全部类型" value="" /><el-option v-for="(label, key) in taskTypes" :key="key" :label="label" :value="key" /></el-select><el-button native-type="submit" :disabled="busy">查询</el-button></form></template>
<style scoped>.filters{display:flex;gap:12px;margin-bottom:16px}.filters :deep(.el-input){max-width:280px}.filters :deep(.el-select){width:160px}</style>
