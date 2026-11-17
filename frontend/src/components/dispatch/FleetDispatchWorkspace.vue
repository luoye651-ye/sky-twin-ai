<script setup lang="ts">
import { useSkyStore } from '../../stores/sky'
import { useFleetDispatch } from '../../composables/useFleetDispatch'
import DispatchTaskPicker from './DispatchTaskPicker.vue'
import DispatchPlanResult from './DispatchPlanResult.vue'
import DispatchHistory from './DispatchHistory.vue'
const sky = useSkyStore()
const { plan, history, busy, error, notice, remainingSeconds, canConfirm, generate, confirm, open, loadHistory } = useFleetDispatch(() => sky.refresh())
</script>
<template>
  <section class="workspace business-theme">
    <div class="page-heading"><div><span class="eyebrow">FLEET INTELLIGENCE</span><h1>AI 集群调度</h1><p>多机多任务约束优化 · 可解释评分 · 人工确认批量派机</p></div><RouterLink to="/task-management">创建任务 / 执行仿真 →</RouterLink></div>
    <el-alert v-if="!sky.canOperate" title="当前为只读账号，可以查看调度记录；生成与确认方案需要调度权限。" type="info" :closable="false" />
    <el-alert v-if="error" :title="error" type="error" :closable="false" /><el-alert v-if="notice" :title="notice" type="success" :closable="false" />
    <div class="workflow"><DispatchTaskPicker :tasks="sky.snapshot.tasks" :aircraft="sky.snapshot.aircraft" :busy="busy" :can-operate="sky.canOperate" @generate="generate" /><DispatchPlanResult v-if="plan" :plan="plan" :busy="busy" :can-confirm="canConfirm" :remaining-seconds="remainingSeconds" :can-operate="sky.canOperate" @confirm="confirm" /><div v-else class="intro"><span class="intro-icon">⇄</span><h2>让有限资源服务更多任务</h2><p>选择任务与机队后，系统对所有可行组合进行全局匹配，输出推荐方案及顺序就近派机基线。</p><ol><li>校验机型、载重、座位、电量、物流时限和区域规则</li><li>联合优化任务覆盖、优先级和成本</li><li>复查禁飞/限高区，确认后原子批量分配</li></ol><p class="hint">当前采用最小费用最大匹配优化算法，无需外部模型密钥；自然语言助手也可生成同一类方案，并在方案卡人工确认。</p></div></div>
    <DispatchHistory :rows="history" :busy="busy" @open="open" @refresh="loadHistory" />
  </section>
</template>
<style scoped>
.workspace { min-height:100%; padding:24px; }.page-heading a { color:#58d4ff; font-size:13px; text-decoration:none; }.workflow { display:grid; grid-template-columns:minmax(360px,.9fr) minmax(560px,1.3fr); gap:20px; margin-top:20px; align-items:start; }.intro { padding:40px; background:linear-gradient(135deg,#102d43,#091b2b); border:1px solid #28516b; border-radius:8px; min-height:450px; }.intro-icon { display:inline-block; font-size:60px; color:#55d7eb; }.intro h2 { font-size:22px; }.intro p,.intro li { color:#9cbfd3; font-size:14px; line-height:2; }.intro .hint { font-size:12px; }.workspace :deep(.el-alert) { margin:12px 0; }@media(max-width:1200px) { .workflow { grid-template-columns:1fr; } }
</style>
