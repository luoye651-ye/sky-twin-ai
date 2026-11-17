<script setup lang="ts">
import type { DispatchDecision } from '@sky/dispatch'
defineProps<{ decision?: DispatchDecision }>()
defineEmits<{ close: [] }>()
</script>
<template>
  <el-dialog :model-value="!!decision" title="候选资源与评分依据" width="min(1000px, 94vw)" @close="$emit('close')">
    <template v-if="decision">
      <p>{{ decision.taskTitle }}：{{ decision.explanation }}</p>
      <el-table :data="decision.candidates" row-key="aircraftId">
        <el-table-column prop="aircraftName" label="飞行器" min-width="140" />
        <el-table-column label="结果" min-width="180"><template #default="{ row }">{{ row.eligible ? (row.aircraftId === decision.aircraftId ? '已选中' : '可用，参与全局匹配') : row.reasons.join('；') }}</template></el-table-column>
        <el-table-column label="距起点" width="100"><template #default="{ row }">{{ (row.distanceMeters / 1000).toFixed(2) }} km</template></el-table-column>
        <el-table-column prop="distanceCost" label="距离成本" width="85" />
        <el-table-column prop="batteryCost" label="电量成本" width="85" />
        <el-table-column prop="capacityCost" label="运力成本" width="85" />
        <el-table-column label="评分" width="75"><template #default="{ row }">{{ row.eligible ? row.score : '—' }}</template></el-table-column>
      </el-table>
    </template>
  </el-dialog>
</template>
