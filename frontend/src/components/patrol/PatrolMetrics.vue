<script setup lang="ts">
import { computed } from 'vue'
import { percentage, type PatrolReport } from '@sky/patrol'
const props = defineProps<{ report: PatrolReport }>()
const cards = computed(() => [
  ['测试图片', `${props.report.imageCount} 张`], ['查准率 Precision', percentage(props.report.precision)],
  ['召回率 Recall', percentage(props.report.recall)], ['mAP50', percentage(props.report.map50)], ['mAP50–95', percentage(props.report.map5095)],
  ['GPU推理 / 张', `${props.report.speedMs.inference?.toFixed(1) ?? '—'} ms`]
])
</script>
<template><section class="metrics"><div class="cards"><article v-for="[label,value] in cards" :key="label" class="metric"><span>{{ label }}</span><strong>{{ value }}</strong></article></div><p>固定 conf ≥ 0.25 / 同类 IoU ≥ 0.50：正确检出 TP {{ report.tp }} · 误检 FP {{ report.fp }} · 漏检 FN {{ report.fn }}。总体查准率/召回率按框数汇总，不是逐图百分比平均。</p><p>mAP由Ultralytics在置信度下限0.001下计算；不等于上面固定阈值的查准率。置信度不代表准确率；“—”表示分母为0，无定义。评测用时 {{ report.evaluationSeconds.toFixed(1) }} 秒（不含图片生成）。</p></section></template>
<style scoped>.cards { display:grid; grid-template-columns:repeat(6,minmax(100px,1fr)); gap:12px; }.metric { padding:18px; border:1px solid #24465d; background:linear-gradient(130deg,#0c2e43,#0a1c2b); display:grid; gap:12px; }.metric span { color:#8eb5cb; font-size:12px; }.metric strong { color:#6ee5ef; font-size:25px; font-variant-numeric:tabular-nums; }.metrics p { color:#91adbf; font-size:12px; line-height:1.7; margin:12px 0 0; }@media(max-width:1100px){.cards{grid-template-columns:repeat(3,1fr)}}</style>
