<script setup lang="ts">
const draft = defineModel<string>({ required: true })
defineProps<{ busy: boolean; canSend: boolean; ready: boolean }>()
const emit = defineEmits<{ send: []; stop: [] }>()
function keydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); emit('send') }
}
</script>
<template>
  <form class="composer" @submit.prevent="emit('send')">
    <label class="composer-label" for="agent-question">向助手提问</label>
    <textarea id="agent-question" v-model="draft" aria-label="向助手提问" rows="3" maxlength="2000" :disabled="!ready" placeholder="例如：为待分配的物流任务生成调度方案，先给我预览…" @keydown="keydown" />
    <div class="composer-footer"><span>Enter 发送 · Shift + Enter 换行 · {{ draft.length }}/2000</span><button v-if="busy" type="button" class="stop" @click="emit('stop')">停止等待</button><button v-else type="submit" :disabled="!canSend" class="send">发送问题 <span aria-hidden="true">↗</span></button></div>
  </form>
</template>
<style scoped>
.composer{border-top:1px solid #20425b;padding:18px 22px;background:#0b2032}.composer-label{display:block;color:#b9d4e6;font-size:12px;margin-bottom:8px}.composer textarea{box-sizing:border-box;width:100%;resize:vertical;min-height:76px;max-height:180px;border:1px solid #2a4e67;border-radius:10px;background:#081827;color:#dcecf5;padding:12px 14px;line-height:1.65;font:inherit;font-size:14px;outline:none}.composer textarea:focus{border-color:#37c4e9;box-shadow:0 0 0 2px #37c4e91a}.composer textarea:disabled{opacity:.55}.composer-footer{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:12px}.composer-footer>span{color:#7698b1;font-size:11px}.composer button{border:1px solid #257fa2;border-radius:7px;padding:10px 20px;cursor:pointer;font-weight:600}.send{background:#087fa4;color:white}.send:disabled{opacity:.4;cursor:not-allowed}.stop{background:#372c26;color:#ffc183;border-color:#74513a!important}@media(max-width:650px){.composer{padding:14px}.composer-footer>span{max-width:180px}}
</style>
