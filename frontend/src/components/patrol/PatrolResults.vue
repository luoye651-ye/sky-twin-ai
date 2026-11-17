<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import type { PatrolRow } from '@sky/patrol'
const props = defineProps<{ rows: PatrolRow[] }>()
const emit = defineEmits<{ select: [row: PatrolRow] }>()
const filter = shallowRef('all'), search = shallowRef(''), page = shallowRef(1)
const filtered = computed(() => props.rows.filter(row =>
  row.filename.toLowerCase().includes(search.value.toLowerCase()) &&
  (filter.value === 'all' || filter.value === 'detected' && row.predictionCount > 0 || filter.value === 'empty' && row.predictionCount === 0)))
const visible = computed(() => filtered.value.slice((page.value - 1) * 15, page.value * 15))
watch([filter, search, () => props.rows], () => { page.value = 1 })
</script>

<template>
  <section class="results">
    <div class="table-heading">
      <h2>逐图检测结果（{{ rows.length }} 张）</h2>
      <el-input v-model="search" placeholder="搜索图片名称" aria-label="搜索检测图片" class="search" />
      <select v-model="filter" aria-label="检测结果筛选">
        <option value="all">全部图片</option><option value="detected">有检出目标</option><option value="empty">未检出目标</option>
      </select>
    </div>
    <div class="scroll">
      <table class="result-table">
        <thead><tr><th>图片</th><th>检出数量</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in visible" :key="row.id">
            <td>{{ row.filename }}</td><td>{{ row.predictionCount }}</td>
            <td><button :aria-label="`查看检测图 ${row.filename}`" @click="emit('select', row)">查看检测图</button></td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="!filtered.length" class="empty-note">无符合条件的图片。</p>
    <el-pagination v-model:current-page="page" :page-size="15" :total="filtered.length"
      layout="prev, pager, next, total" class="pagination" />
  </section>
</template>

<style scoped>
.results { border:1px solid #24465d; background:#0b2132; padding:20px; min-width:0; }
.table-heading { display:flex; gap:14px; flex-wrap:wrap; align-items:center; }
.table-heading h2 { font-size:17px; margin:0 auto 0 0; }
.search { width:180px; }
.table-heading select { padding:8px; background:#102a3d; color:#cfe9f5; border:1px solid #31546b; }
.scroll { overflow:auto; margin-top:16px; }
.result-table { width:100%; border-collapse:collapse; font-size:12px; white-space:nowrap; }
.result-table th { background:#103048; text-align:left; color:#91c1d6; padding:13px 9px; }
.result-table td { padding:12px 9px; border-bottom:1px solid #19384e; }
.result-table button { background:transparent; border:0; color:#67d9ff; cursor:pointer; }
.pagination { margin:16px 0 0; }
.empty-note { color:#8baabd; font-size:12px; }
</style>
