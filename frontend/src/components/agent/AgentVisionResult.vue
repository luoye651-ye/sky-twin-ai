<script setup lang="ts">
import type { VisionChatResult } from '../../types/visionChat'
defineProps<{result:VisionChatResult}>()
</script>
<template><section class="vision-result"><strong>DeepSeek 实际图片输入 · {{ result.model }}</strong><p>候选观察 {{ result.observations.length }} 项；这不是YOLO框数或已确认业务事件。</p><ol><li v-for="(item,i) in result.observations" :key="i"><b>{{ item.label }} · {{ item.certainty }}</b><p>位置：{{ item.location }}<br>{{ item.description }}</p></li></ol><p v-for="(item,i) in result.limitations" :key="i">复核提示：{{ item }}</p><small>图片 {{ result.image_width }}×{{ result.image_height }} · SHA256 {{ result.image_sha256 }}</small><RouterLink :to="{path:'/ai-workbench',query:{runId:result.run_id}}">查看运行及用量：{{ result.run_id }}</RouterLink></section></template>
<style scoped>.vision-result{margin-top:12px;padding:12px;border:1px solid #31546b;color:#c8e4f4}.vision-result p{font-size:12px;line-height:1.8;color:#98bdd3}.vision-result small{display:block;overflow-wrap:anywhere;font-size:11px}.vision-result a{display:block;margin-top:8px;font-size:12px;color:#65d4ef}</style>
