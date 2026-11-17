<script setup lang="ts">
import type { AirspaceZone } from '@sky/airspace'
defineProps<{ zones: AirspaceZone[]; busy: boolean; canManage: boolean }>()
defineEmits<{ edit: [zone: AirspaceZone]; focus: [id: string]; create: [] }>()
</script>
<template>
  <section class="panel business-theme"><div class="title-row"><h2>区域规则</h2><el-button v-if="canManage" type="primary" :disabled="busy" @click="$emit('create')">新建区域</el-button></div><el-table :data="zones" row-key="id"><el-table-column prop="name" label="名称" min-width="140" /><el-table-column label="类型" width="85"><template #default="{ row }">{{ row.type === 'no_fly' ? '禁飞区' : '限高区' }}</template></el-table-column><el-table-column label="高度 m" width="100"><template #default="{ row }">{{ row.type === 'no_fly' ? `${row.minAltitude}～${row.maxAltitude}` : `≤ ${row.maxAltitude}` }}</template></el-table-column><el-table-column label="当前状态" width="100"><template #default="{ row }">{{ !row.enabled ? '停用' : row.activeNow ? '生效中' : '生效时段外' }}</template></el-table-column><el-table-column label="生效时段" min-width="210"><template #default="{ row }">{{ row.startsAt || '不限开始' }} ～ {{ row.endsAt || '长期' }}</template></el-table-column><el-table-column label="操作" width="130"><template #default="{ row }"><el-button link type="primary" @click="$emit('focus', row.id)">定位</el-button><el-button v-if="canManage" link type="primary" :disabled="busy" @click="$emit('edit', row)">编辑</el-button></template></el-table-column></el-table></section>
</template>
<style scoped>.panel { padding:18px; background:#0b2132; border:1px solid #24465d; border-radius:7px; }.title-row { display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; }.title-row h2 { font-size:17px; margin:0; }</style>
