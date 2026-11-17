<script setup lang="ts">
import type { WorkbenchRun } from '../../types/workbench'
defineProps<{ run: WorkbenchRun }>()
const labels: Record<string,string> = { running:'执行中', completed:'完成', interrupted:'中断', failed:'失败', pending:'待处理', cancelled:'已取消', awaiting_review:'待审查建议', awaiting_confirmation:'待确认方案', needs_reconcile:'需核对Java历史' }
function duration(start: number, end: number | null) { return end === null ? '尚未结束' : `${Math.max(0, Math.round((end-start)*1000))} ms` }
</script>
<template><section class="timeline"><h3>实际调用轨迹</h3><p>只记录真实步骤、模型/工具调用和摘要，不记录隐藏推理、原始提示或凭证。未上报Token不按0计算。</p><p v-if="run.metrics">模型调用 {{ run.metrics.model_calls }} · 工具调用 {{ run.metrics.tool_calls }} · 输入Token {{ run.metrics.input_tokens ?? '未知' }} · 输出Token {{ run.metrics.output_tokens ?? '未知' }} · 估算费用 {{ run.metrics.estimated_cost ?? '未配置单价或用量不完整' }}</p><ol><li v-for="span in run.spans" :key="span.id"><strong>{{ span.kind }} · {{ span.name }}</strong> — {{ labels[span.status] ?? span.status }} · {{ duration(span.started, span.ended) }}<p>{{ span.summary }}</p><small v-if="span.arguments && Object.keys(span.arguments).length">参数摘要 {{ JSON.stringify(span.arguments) }}</small></li></ol><p v-if="!run.spans?.length">尚无调用记录。</p></section></template>
<style scoped>.timeline{padding:16px;border:1px solid #31546b;margin:16px 0}.timeline p{color:#9ebfd2;font-size:12px;line-height:1.8}.timeline li{padding:8px 0;overflow-wrap:anywhere}</style>
