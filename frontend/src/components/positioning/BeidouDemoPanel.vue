<script setup lang="ts">
import { verdictLabels, type NmeaFrame, type NmeaPositionResult } from '@sky/positioning'
defineProps<{ enabled:boolean; running:boolean; sending:boolean; canOperate:boolean; nmeaRunning:boolean; frame?:NmeaFrame; result?:NmeaPositionResult }>()
defineEmits<{ preview:[]; start:[]; stop:[]; send:[kind:'normal'|'no_fix'|'bad_checksum'] }>()
</script>
<template>
  <section class="beidou-panel" aria-label="北斗NMEA协议仿真演示">
    <div class="heading"><h2>北斗定位接入 · NMEA 协议仿真</h2><span class="badge">无硬件演示</span></div>
    <p class="explanation">电脑生成 GB/GGA 报文 → Java 校验和/度分/UTC/高度转换 → 原定位入库、地图与回放。未接收真实北斗信号；卫星数与 HDOP 为仿真字段，HDOP 不是米级精度。</p>
    <div class="actions">
      <el-button :disabled="sending || running" @click="$emit('preview')">查看报文样例</el-button>
      <el-button type="primary" :disabled="!enabled || sending || running || !canOperate" @click="$emit('send','normal')">北斗样例单次上报</el-button>
      <el-button v-if="!nmeaRunning" :disabled="!enabled || sending || running || !canOperate" @click="$emit('start')">开始北斗连续演示</el-button>
      <el-button v-else @click="$emit('stop')">暂停北斗演示</el-button>
      <el-button :disabled="!enabled || sending || running || !canOperate" @click="$emit('send','no_fix')">模拟北斗失锁</el-button>
      <el-button :disabled="!enabled || sending || running || !canOperate" @click="$emit('send','bad_checksum')">模拟校验错误</el-button>
    </div>
    <p v-if="!enabled" class="hint">先在上方选择终端并启用定位，再上报；报文样例可直接查看，不会写入业务数据。</p>
    <div v-if="frame" class="frame"><span>最近生成报文（仿真；上报按钮会生成当前 UTC 的新报文）</span><code>{{ frame.gga }}</code><small>UTC 日期 {{ frame.utcDate }} · 仿真起飞点 MSL 基准 {{ frame.takeoffAltitudeMsl }} m；GGA 本身不含日期。</small></div>
    <div v-if="result" class="decoded" aria-live="polite">
      <dl><div><dt>Java 识别</dt><dd>{{ result.decoded.constellation }} / {{ result.decoded.talker }}（仿真）</dd></div><div><dt>参与解算卫星数（仿真）</dt><dd>{{ result.decoded.satellites }}</dd></div><div><dt>HDOP（仿真，无量纲）</dt><dd>{{ result.decoded.hdop }}</dd></div><div><dt>换算后 WGS84</dt><dd>{{ result.decoded.longitude.toFixed(6) }}, {{ result.decoded.latitude.toFixed(6) }}</dd></div><div><dt>MSL → 相对起飞高度</dt><dd>{{ result.decoded.altitudeMsl.toFixed(2) }} − {{ result.decoded.takeoffAltitudeMsl }} = {{ result.decoded.relativeAltitude.toFixed(2) }} m</dd></div><div><dt>Java 持久化回执</dt><dd :class="result.receipt.accepted?'accepted':'rejected'">{{ verdictLabels[result.receipt.verdict] ?? result.receipt.verdict }} · #{{ result.receipt.id }}</dd></div></dl>
      <p class="hint">存储来源仍为 simulated_terminal。报文字头不能证明硬件或真实卫星参与；真实接入仍需设备、鉴权和实测。</p>
    </div>
  </section>
</template>
<style scoped>
.beidou-panel { padding:18px; border:1px solid #3289b0; background:linear-gradient(120deg,#0a263b,#0b1d2d); }.heading { display:flex; gap:14px; align-items:center; flex-wrap:wrap; }.heading h2 { margin:0; font-size:16px; }.badge { padding:4px 9px; color:#ffd280; background:#4b351e; border:1px solid #b38441; border-radius:4px; font-size:11px; }.explanation,.hint { color:#a1c1d3; font-size:12px; line-height:1.7; }.actions { display:flex; gap:8px; flex-wrap:wrap; }.actions :deep(.el-button) { margin-left:0; }.frame { margin-top:14px; display:grid; gap:8px; padding:12px; background:#061728; border:1px solid #21445b; font-size:12px; }.frame code { color:#6ee7cf; overflow-wrap:anywhere; }.frame small { color:#a1c1d3; }.decoded dl { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-bottom:0; }.decoded dt { color:#93b9cf; font-size:12px; }.decoded dd { margin:5px 0 0; font-size:13px; overflow-wrap:anywhere; }.accepted { color:#55dfac; }.rejected { color:#ffae80; }@media(max-width:850px) {.decoded dl { grid-template-columns:minmax(0,1fr); }}
</style>
