<script setup lang="ts">
import { nextTick, useTemplateRef, watch } from 'vue'
import type { AgentMapTarget, AgentMessage } from '../../types/agent'
import AgentDispatchCard from './AgentDispatchCard.vue'
import AgentVisionResult from './AgentVisionResult.vue'
defineEmits<{ locate: [target: AgentMapTarget] }>()
const props = defineProps<{ messages: AgentMessage[] }>()
const scroller = useTemplateRef<HTMLElement>('scroller')
watch(() => props.messages, async () => { await nextTick(); const element = scroller.value; if (element) element.scrollTop = element.scrollHeight })
</script>
<template>
  <div ref="scroller" class="conversation" role="log" aria-label="Agent对话记录" aria-live="polite">
    <div v-if="!messages.length" class="empty"><span class="empty-symbol" aria-hidden="true">✦</span><h2>用一句话，找到数据与依据</h2><p>我可以读取飞行器登记状态，也可以检索项目规则。<br>涉及执行的指令不会在聊天里直接生效。</p></div>
    <article v-for="message in messages" :key="message.id" :class="['message', message.role, message.state]">
      <div class="avatar" aria-hidden="true">{{ message.role === 'user' ? '我' : '✦' }}</div>
      <div class="message-body"><span class="speaker">{{ message.role === 'user' ? '你' : 'SkyTwin 助手' }}</span>
        <div v-if="message.state === 'pending'" class="pending"><span class="pending-dot" />正在分析问题并调用工具…</div>
        <p v-if="message.text" class="message-text">{{ message.text }}</p>
        <AgentVisionResult v-if="message.vision" :result="message.vision" />
        <div v-if="message.answer?.map_targets?.length" class="map-actions"><el-button v-for="target in message.answer.map_targets" :key="`${target.kind}-${target.id}`" @click="$emit('locate', target)">地图定位：{{ target.label }}</el-button></div>
        <AgentDispatchCard v-if="message.answer?.dispatch_plan_id" :key="message.answer.dispatch_plan_id" :plan-id="message.answer.dispatch_plan_id" @locate="$emit('locate', $event)" />
        <details v-if="message.progress.length" class="trace" :open="message.state === 'pending'"><summary>处理过程</summary><ul><li v-for="(line, index) in message.progress" :key="index">{{ line }}</li></ul></details>
        <div v-if="message.answer" class="result-meta"><span v-if="message.answer.mcp_calls">MCP 查询 {{ message.answer.mcp_calls }} 次 · 仿真登记数据</span><span v-if="message.answer.knowledge_calls">知识检索 {{ message.answer.knowledge_calls }} 次</span></div>
        <details v-if="message.answer?.sources.length" class="sources"><summary>查看回答依据（{{ message.answer.sources.length }}处）</summary><div v-for="source in message.answer.sources" :key="source.citation_id" class="source-card"><strong>[{{ source.citation_id }}] {{ source.section }}</strong><span>{{ source.source }} · 第{{ source.line_start }}～{{ source.line_end }}行</span><p v-if="source.text" class="source-excerpt">{{ source.text }}</p><span v-if="source.version">版本 {{ source.version.slice(0, 12) }}</span><small v-for="reference in source.code_references" :key="reference">实现依据：{{ reference }}</small></div></details>
      </div>
    </article>
  </div>
</template>
<style scoped>
.conversation{height:440px;min-height:300px;overflow:auto;padding:22px;scrollbar-width:thin;scrollbar-color:#30536b #0a1b2b}.empty{min-height:360px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}.empty-symbol{width:65px;height:65px;display:grid;place-items:center;font-size:40px;color:#53d8ed;background:#103344;border:1px solid #245a6c;border-radius:20px}.empty h2{color:#e4f1f8;font-size:22px;margin:22px 0 10px}.empty p{color:#87a7bd;font-size:14px;line-height:1.9}.message{display:flex;gap:13px;margin-bottom:24px}.avatar{flex:0 0 32px;height:32px;border:1px solid #245a72;border-radius:10px;background:#0f3347;color:#67deef;display:grid;place-items:center}.user .avatar{background:#1b334a;color:#b6cce4}.message-body{min-width:0;flex:1}.speaker{color:#82a4bd;font-size:12px}.message-text{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.9;font-size:14px;color:#dfedf6;margin:8px 0 4px}.user .message-text{background:#122d43;padding:12px 15px;border-radius:0 10px 10px 10px}.error .message-text{color:#ffb5a8}.stopped .message-text{color:#b3a993}.pending{display:flex;gap:9px;align-items:center;color:#72cde5;font-size:13px;margin:12px 0}.pending-dot{width:7px;height:7px;border-radius:50%;background:#40cbeb}.trace,.sources{font-size:12px;color:#94b6c9;margin-top:12px}.trace summary,.sources summary{cursor:pointer;color:#6dbfd7}.trace ul{line-height:1.9;padding-left:20px;overflow-wrap:anywhere}.result-meta{display:flex;flex-wrap:wrap;gap:15px;color:#688fa6;font-size:11px;margin-top:10px}.source-card{display:flex;flex-direction:column;gap:7px;border-left:2px solid #2a8da9;background:#0b2536;padding:12px;margin-top:10px;overflow-wrap:anywhere}.source-card strong{color:#a6d8e9}.source-card small{color:#6e9aaf;line-height:1.6}@media(max-width:650px){.conversation{padding:14px;height:430px}.empty h2{font-size:18px}}
</style>
