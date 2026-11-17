<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Track } from '@sky/sky'
import { formatTime } from './logisticsPresentation'
const props = defineProps<{ tracks: Track[] }>()
const page = ref(1)
const points = computed(() => {
  const valid = props.tracks.filter(p => Number.isFinite(p.longitude) && Number.isFinite(p.latitude))
  if (!valid.length) return []
  const xs = valid.map(p => p.longitude), ys = valid.map(p => p.latitude)
  const minX = Math.min(...xs), minY = Math.min(...ys)
  const scale = Math.max(Math.max(...xs) - minX, Math.max(...ys) - minY, .00001)
  return valid.map(p => ({ x: 25 + (p.longitude - minX) / scale * 550, y: 195 - (p.latitude - minY) / scale * 170 }))
})
const line = computed(() => points.value.map(p => `${p.x},${p.y}`).join(' '))
const rows = computed(() => props.tracks.slice((page.value - 1) * 20, page.value * 20))
watch(() => props.tracks.length, length => { if ((page.value - 1) * 20 >= length) page.value = 1 })
</script>

<template>
  <el-empty v-if="!tracks.length" description="任务尚未起飞，暂无轨迹" :image-size="60" />
  <template v-else>
    <div class="track-summary">已保存 {{ tracks.length }} 个轨迹点 · WGS84 航迹示意（不含地图底图）</div>
    <svg class="track-chart" viewBox="0 0 600 220" role="img" aria-label="配送飞行轨迹示意">
      <path d="M25 20 V195 H580" fill="none" stroke="#24465d" />
      <polyline :points="line" fill="none" stroke="#22cfff" stroke-width="3" />
      <circle v-if="points[0]" :cx="points[0].x" :cy="points[0].y" r="6" fill="#24dfa4" />
      <circle v-if="points.length" :cx="points[points.length - 1]!.x" :cy="points[points.length - 1]!.y" r="5" fill="#ffbd55" />
      <text x="530" y="20" fill="#86a9bf" font-size="12">北 ↑</text>
    </svg>
    <el-table :data="rows" row-key="id" size="small" max-height="300">
      <el-table-column label="记录时间" min-width="175"><template #default="{row}">{{ formatTime(row.recordedTime) }}</template></el-table-column>
      <el-table-column label="经度 / 纬度" min-width="190"><template #default="{row}">{{ row.longitude.toFixed(6) }} / {{ row.latitude.toFixed(6) }}</template></el-table-column>
      <el-table-column prop="altitude" label="高度 m" width="90" />
      <el-table-column prop="speed" label="速度 m/s" width="95" />
      <el-table-column label="电量" width="85"><template #default="{row}">{{ row.battery.toFixed(1) }}%</template></el-table-column>
      <el-table-column label="进度" width="85"><template #default="{row}">{{ Math.round(row.progress) }}%</template></el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :page-size="20" :total="tracks.length" layout="prev,pager,next,total" />
  </template>
</template>

<style scoped>
.track-summary { color:#86a9bf; font-size:13px; }.track-chart { width:100%; max-height:220px; background:#061724; border-radius:8px; margin:12px 0; }
.el-pagination { margin-top:12px; }
</style>
