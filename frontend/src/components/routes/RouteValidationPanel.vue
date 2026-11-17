<script setup lang="ts">
import type { RouteEvaluation, RoutePlan } from '@sky/routes'
defineProps<{ result?: RouteEvaluation; current?: RoutePlan; busy: boolean; canEdit: boolean; reason: string; dirty: boolean }>()
defineEmits<{ preview: []; save: [] }>()
</script>
<template>
  <section class="panel"><h2>服务端校验与保存</h2><div v-if="current" class="metrics"><span>{{ current.revision === 0 ? '旧任务兼容直线（非历史快照）' : `查看版本 v${current.revision}` }}</span><span>水平航程 {{ current.distanceMeters.toFixed(0) }} m</span><span>仿真时长 {{ current.durationSeconds }} s</span><span>巡航高度 {{ current.cruiseAltitude }} m · 名义速度 {{ current.speed }} m/s</span></div>
    <div class="actions"><el-button :disabled="busy || !canEdit || !reason.trim()" :loading="busy" @click="$emit('preview')">校验草稿</el-button><el-button type="primary" :disabled="busy || !canEdit || !result?.allowed || !reason.trim()" @click="$emit('save')">保存航线</el-button><span>{{ dirty ? '有未保存修改' : '草稿与当前保存版本一致' }}</span></div>
    <template v-if="result"><el-alert :title="result.allowed ? (result.saved ? '航线已保存，起飞仍会再次复查' : '当前草稿通过校验，尚未保存') : '当前草稿不可执行，请调整航点'" :type="result.allowed ? 'success' : 'error'" :closable="false" /><div class="metrics"><span>候选水平航程 {{ result.plan.distanceMeters.toFixed(1) }} m</span><span>候选仿真耗时 {{ result.plan.durationSeconds }} s（10倍时间）</span><span>仿真耗电约 {{ (result.plan.durationSeconds * .08).toFixed(2) }}%</span><span>空域规则版本 {{ result.check.ruleRevision }}</span></div>
      <ul v-if="result.constraints.length"><li v-for="reason in result.constraints" :key="reason">{{ reason }}</li></ul><ul v-if="result.check.violations.length"><li v-for="(v, i) in result.check.violations" :key="i">{{ v.reason }} · {{ v.phase }} · 预计进入 {{ v.entersAt }}</li></ul>
    </template><p>保存时再次检查当前规则、配送截止时间、已分配资源及版本冲突；任一失败不覆盖原路线。耗时/电量均为仿真估计，不是实机续航评估。</p>
  </section>
</template>
<style scoped>.panel { padding:18px; background:#0b1d2d; border:1px solid #21445b; }.panel h2 { margin:0 0 16px; font-size:16px; }.metrics,.actions { display:flex; gap:18px; flex-wrap:wrap; align-items:center; margin:14px 0; }.metrics,.actions span,.panel p { font-size:12px; color:#a6bfd0; }.panel p { line-height:1.8; }.panel li { font-size:13px; color:#f3bb92; line-height:1.8; }</style>
