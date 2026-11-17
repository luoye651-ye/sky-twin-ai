<script setup lang="ts">
import type { DispatchHistory } from '@sky/dispatch'
defineProps<{ rows: DispatchHistory[]; busy: boolean }>()
defineEmits<{ open: [id: string]; refresh: [] }>()
</script>
<template>
  <section class="history business-theme"><div class="title-row"><h2>调度记录</h2><el-button :disabled="busy" @click="$emit('refresh')">刷新记录</el-button></div><p class="hint">保留算法版本、候选结果、确认人和派机原因；显示最近20条。</p><el-table :data="rows" row-key="id"><el-table-column prop="createdTime" label="生成时间" min-width="165" /><el-table-column prop="createdBy" label="生成人" width="100" /><el-table-column label="状态" width="110"><template #default="{ row }">{{ row.status === 'confirmed' ? '已确认' : '待确认/可过期' }}</template></el-table-column><el-table-column prop="confirmedBy" label="确认人" width="100" /><el-table-column prop="reason" label="派机原因" min-width="160" show-overflow-tooltip /><el-table-column width="100"><template #default="{ row }"><el-button link type="primary" :disabled="busy" @click="$emit('open', row.id)">查看方案</el-button></template></el-table-column></el-table></section>
</template>
<style scoped>
.history { margin-top:24px; padding:20px; border:1px solid #24465d; border-radius:8px; background:#0b2132; }.title-row { display:flex; align-items:center; justify-content:space-between; }.title-row h2 { margin:0; font-size:18px; }.hint { color:#90b4cb; font-size:12px; }
</style>
