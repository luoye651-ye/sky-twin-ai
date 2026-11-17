<script setup lang="ts">
import { verdictLabels, type PositionSample } from '@sky/positioning'
defineProps<{ enabled: boolean; running: boolean; sending: boolean; canOperate: boolean; receipts: PositionSample[] }>()
defineEmits<{ start: []; stop: []; send: [kind: 'normal' | 'no_fix' | 'delay' | 'jump' | 'duplicate'] }>()
</script>
<template>
  <section class="panel"><h2>2 · 电脑模拟定位终端</h2>
    <p>每次响应完成后等待1秒继续上报；模拟局部环形轨迹，初始相对高度240m（已有有效点则从该点开始）。关闭页面即停止上报，30秒无有效定位将显示离线。本JSON模拟器不上报卫星数或精度；上方NMEA面板的卫星数与HDOP也仅为仿真样例。</p>
    <div class="actions"><el-button v-if="!running" type="primary" :disabled="!enabled || sending || !canOperate" @click="$emit('start')">开始连续上报</el-button><el-button v-else @click="$emit('stop')">暂停上报</el-button>
      <el-button :disabled="!enabled || running || sending || !canOperate" @click="$emit('send', 'normal')">单次上报</el-button>
      <el-button v-for="item in ([['no_fix','模拟无定位'],['delay','模拟延迟60秒'],['jump','模拟位置突跳'],['duplicate','重试上一条']] as const)" :key="item[0]" :disabled="!enabled || running || sending || !canOperate" @click="$emit('send', item[0])">{{ item[1] }}</el-button>
    </div>
    <div class="receipts"><table><thead><tr><th>序号 / 会话</th><th>采样时间</th><th>服务端接收时间</th><th>Java 校验回执</th></tr></thead><tbody><tr v-for="r in receipts.slice(0, 12)" :key="r.id"><td>{{ r.sequenceNo }} / {{ r.sessionId.slice(0, 8) }}</td><td>{{ new Date(r.sampledAt).toLocaleTimeString() }}</td><td>{{ new Date(r.receivedAt).toLocaleTimeString() }}</td><td :class="r.accepted ? 'accepted' : 'rejected'">{{ verdictLabels[r.verdict] ?? r.verdict }}</td></tr><tr v-if="!receipts.length"><td colspan="4">尚无上报记录</td></tr></tbody></table></div>
  </section>
</template>
<style scoped>.panel { padding:18px; border:1px solid #21445b; background:#0b1d2d; }.panel h2 { margin:0; font-size:16px; }.panel p { color:#a1c1d3; font-size:12px; line-height:1.7; }.actions { display:flex; gap:8px; flex-wrap:wrap; }.actions :deep(.el-button) { margin-left:0; }.receipts { overflow:auto; margin-top:16px; }table { width:100%; border-collapse:collapse; font-size:12px; }th,td { padding:10px; text-align:left; border-bottom:1px solid #21445b; white-space:nowrap; }th { color:#9bc7df; }.accepted { color:#55dfac; }.rejected { color:#ffae80; }</style>
