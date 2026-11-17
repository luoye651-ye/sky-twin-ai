<script setup lang="ts">
import { shallowRef } from 'vue'
import AgentChatWorkspace from './AgentChatWorkspace.vue'
import FleetDispatchWorkspace from '../dispatch/FleetDispatchWorkspace.vue'
const active = shallowRef<'chat' | 'dispatch'>('chat'), dispatchMounted = shallowRef(false)
function select(value: 'chat' | 'dispatch') { active.value = value; if (value === 'dispatch') dispatchMounted.value = true }
</script>
<template>
  <section class="command-workspace business-theme"><header class="command-heading"><div><span class="eyebrow">AGENT COMMAND</span><h1>Agent 指挥中心</h1><p>自然语言查询与知识辅助 · 算法调度独立确认</p></div><div class="tabs" role="tablist" aria-label="Agent指挥功能"><button id="chat-tab" type="button" role="tab" :aria-selected="active === 'chat'" aria-controls="chat-panel" :class="{ selected: active === 'chat' }" @click="select('chat')">自然语言助手</button><button id="dispatch-tab" type="button" role="tab" :aria-selected="active === 'dispatch'" aria-controls="dispatch-panel" :class="{ selected: active === 'dispatch' }" @click="select('dispatch')">算法调度</button></div></header>
    <div id="chat-panel" v-show="active === 'chat'" role="tabpanel" aria-labelledby="chat-tab"><AgentChatWorkspace /></div><div v-if="dispatchMounted" id="dispatch-panel" v-show="active === 'dispatch'" role="tabpanel" aria-labelledby="dispatch-tab"><FleetDispatchWorkspace /></div>
  </section>
</template>
<style scoped>
.command-workspace{min-height:100%;background:radial-gradient(ellipse at 40% 0,#0b273d55,transparent 65%)}.command-heading{display:flex;justify-content:space-between;align-items:center;gap:20px;padding:25px 26px 19px;border-bottom:1px solid #1b3b51}.eyebrow{color:#469fb8;letter-spacing:2px;font-size:10px}.command-heading h1{font-size:24px;color:#e2f0f8;margin:9px 0 7px;font-weight:600}.command-heading p{font-size:12px;color:#7c9fb6;margin:0}.tabs{display:flex;gap:4px;padding:4px;background:#081927;border:1px solid #203f55;border-radius:9px}.tabs button{border:0;border-radius:6px;color:#86abc2;background:transparent;padding:11px 18px;cursor:pointer;font-size:13px;white-space:nowrap}.tabs button.selected{color:#79e1ef;background:#153c51;box-shadow:inset 0 0 0 1px #275d73}.tabs button:focus-visible{outline:2px solid #54d3ea}@media(max-width:700px){.command-heading{align-items:flex-start;flex-direction:column;padding:20px}.tabs{align-self:stretch}.tabs button{flex:1;padding:10px}}
</style>
