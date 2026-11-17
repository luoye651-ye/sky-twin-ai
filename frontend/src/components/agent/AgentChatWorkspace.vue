<script setup lang="ts">
import { shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import AgentContextMap from './AgentContextMap.vue'
import type { AgentMapTarget } from '../../types/agent'
import { useSkyStore } from '../../stores/sky'
import { useAgentChat } from '../../composables/useAgentChat'
import AgentComposer from './AgentComposer.vue'
import AgentImageAttachment from './AgentImageAttachment.vue'
import AgentConversation from './AgentConversation.vue'
const mapTarget = shallowRef<AgentMapTarget>()
const sky = useSkyStore()
const { messages, draft, busy, health, checking, canSend, send, stop, clear, refreshHealth, imageChat } = useAgentChat(() => sky.authorized ? sky.username : '')
const {enabled:imageEnabled,consent:imageConsent,preview:imagePreview,hasContext:imageContext,error:imageError,health:imageHealth}=imageChat
watch(() => messages.value.length, count => { if (!count) mapTarget.value = undefined })
const route = useRoute()
watch(() => route.query.taskId, id => {
  if (typeof id === 'string' && /^[A-Za-z0-9_-]{1,40}$/.test(id)) draft.value = `请为任务${id}生成调度方案，先预览不要执行。`
}, { immediate: true })
const examples = ['请为所有待分配的物流任务生成调度方案，先预览不要执行。', '当前有哪些空闲的巡检无人机？分别有多少电量？', '命中禁飞区后还能起飞吗？', '应急事件结案需要哪些证据？', 'AI识别漂浮物后会自动生成应急事件吗？']
</script>
<template>
  <section class="chat-workspace"><div class="chat-grid"><section class="chat-panel" aria-label="自然语言助手">
    <header class="chat-header"><div><span class="assistant-mark" aria-hidden="true">✦</span><strong>SkyTwin 自然语言助手</strong><span :class="['status', { online: health.ready }]">{{ health.ready ? '已连接' : '未就绪' }}</span></div><button type="button" :disabled="!messages.length" @click="clear">清空会话</button></header>
    <div v-if="!health.ready" class="service-notice" role="status"><span>{{ health.message }}</span><button type="button" :disabled="checking" @click="refreshHealth">{{ checking ? '检测中…' : '重新检测' }}</button></div>
    <AgentConversation :messages="messages" @locate="mapTarget = $event" /><AgentImageAttachment v-model:enabled="imageEnabled" v-model:consent="imageConsent" :preview="imagePreview" :has-context="imageContext" :busy="busy" :message="imageHealth.message" :error="imageError" @choose="imageChat.choose" @check="imageChat.check" /><AgentComposer v-model="draft" :busy="busy" :can-send="canSend" :ready="imageEnabled ? imageHealth.ready : health.ready" @send="send" @stop="stop" />
  </section><aside class="capabilities"><span class="eyebrow">ASSISTANT WORKSPACE</span><h2>先查询，再判断</h2><p class="intro">将系统状态与项目规则放到同一个对话入口，回答可查看工具过程与知识来源。</p>
    <div class="ability"><span class="ability-icon">↗</span><div><h3>业务数据 · MCP</h3><p>按当前登录账号读取飞行器状态、电量及运力。</p></div></div><div class="ability"><span class="ability-icon">≡</span><div><h3>项目知识 · RAG</h3><p>检索禁飞、限高与环境处置规则，提供来源依据。</p></div></div>
    <h3 class="example-heading">试着这样问</h3><button v-for="question in examples" :key="question" class="example" type="button" :disabled="busy || !health.ready" @click="draft = question">{{ question }} <span aria-hidden="true">↗</span></button>
    <div class="boundary"><strong>支持自然语言生成调度方案</strong><p>可查询待分配任务并生成方案，在对话中的方案卡审查后人工确认分配。不会自动起飞或结案。</p><p>保留当前会话最近三轮上下文，20分钟无活动后过期；清空或重新登录开始新会话。可说“把刚才那批任务改为紧急”，实时状态会重新查询。提问会调用DeepSeek并产生API费用，请勿输入密钥或令牌。</p></div>
  </aside></div><el-dialog :model-value="!!mapTarget" title="对话地图联动 · 仿真" width="min(1200px, 96vw)" destroy-on-close @close="mapTarget = undefined"><AgentContextMap v-if="mapTarget" :key="`${mapTarget.kind}-${mapTarget.id}`" :target="mapTarget" /></el-dialog></section>
</template>
<style scoped>
.chat-workspace{padding:22px 24px 30px}.chat-grid{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:22px;max-width:1540px;margin:0 auto}.chat-panel{min-width:0;border:1px solid #24465e;border-radius:13px;overflow:hidden;background:#091b2b;box-shadow:0 16px 50px #0002}.chat-header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:19px 22px;border-bottom:1px solid #1e3c53;background:linear-gradient(110deg,#102e44,#0b1d2e)}.chat-header>div{display:flex;align-items:center;flex-wrap:wrap;gap:10px}.chat-header strong{font-size:14px;color:#d7ecf8}.assistant-mark{font-size:24px;color:#50d4ed}.status{font-size:10px;color:#bba173;border:1px solid #6b553a;padding:3px 7px;border-radius:20px}.status.online{color:#5cdbc0;border-color:#216353;background:#123e382e}.chat-header button,.service-notice button{border:0;background:none;color:#7dafc8;cursor:pointer;white-space:nowrap;font-size:12px}.chat-header button:disabled{opacity:.4;cursor:default}.service-notice{padding:13px 20px;background:#48361333;color:#d8ba86;display:flex;gap:12px;justify-content:space-between;font-size:12px}.capabilities{padding:13px 2px;color:#96b3c7}.eyebrow{font-size:10px;letter-spacing:1.6px;color:#409fb9}.capabilities h2{font-size:23px;color:#dcebf5;font-weight:600;margin:12px 0}.intro{font-size:13px;line-height:1.9;margin-bottom:24px}.ability{display:flex;gap:12px;margin:20px 0}.ability-icon{color:#69cee1;background:#123244;border:1px solid #214b60;border-radius:8px;width:32px;height:32px;display:grid;place-items:center;flex-shrink:0}.ability h3{margin:0 0 6px;font-size:13px;color:#bcd5e5}.ability p{margin:0;font-size:12px;line-height:1.8;color:#789cb3}.example-heading{font-size:12px;color:#89b2c8;margin:28px 0 10px}.example{display:flex;align-items:center;justify-content:space-between;gap:12px;width:100%;text-align:left;border:1px solid #23465f;border-radius:8px;background:#0d2335;color:#a8c7da;padding:12px;margin:9px 0;line-height:1.6;font-size:12px;cursor:pointer}.example:hover{border-color:#328da9;color:#d3e9f7}.example:disabled{opacity:.5;cursor:default}.boundary{margin-top:24px;border-top:1px solid #203d53;padding-top:18px;font-size:11px;line-height:1.8;color:#688da6}.boundary strong{color:#adbcbb;font-weight:500}.boundary p{margin:7px 0}@media(min-height:1000px){.chat-panel :deep(.conversation){height:520px}}@media(max-width:1100px){.chat-grid{grid-template-columns:minmax(0,1fr) 250px}.chat-workspace{padding:18px}}@media(max-width:800px){.chat-grid{grid-template-columns:1fr}.capabilities{padding:8px}.chat-workspace{padding:12px}.chat-header{padding:15px}.example{max-width:none}}
</style>
