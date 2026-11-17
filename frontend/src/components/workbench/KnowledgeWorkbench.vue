<script setup lang="ts">
import { onScopeDispose, shallowRef, watch } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { workbenchRequest } from '../../api/workbench'
import type { KnowledgeDocument } from '../../types/workbench'
const sky = useSkyStore(), rows = shallowRef<KnowledgeDocument[]>([]), hits = shallowRef<{ section: string; text: string; score: number; document_version: number }[]>([])
const updating = shallowRef(''), question = shallowRef(''), busy = shallowRef(false), error = shallowRef('')
let alive = true, generation = 0, timer: ReturnType<typeof setTimeout> | undefined
async function load() { const ticket = ++generation; try { const data = await workbenchRequest<KnowledgeDocument[]>('/documents'); if (alive && ticket === generation) rows.value = data } catch (e) { if (alive && ticket === generation) error.value = String(e) } }
async function upload(event: Event) {
  const input = event.target as HTMLInputElement, file = input.files?.[0]; input.value = ''
  if (!file || busy.value) return
  if (file.size > 2*1024*1024) { error.value = '文件最多2MiB'; return }
  busy.value = true; error.value = ''
  try { const form = new FormData(); form.append('file', file); if (updating.value) form.append('document_id', updating.value); await workbenchRequest('/documents', form, 'POST'); updating.value = ''; await load() }
  catch (e) { if (alive) error.value = String(e) }
  finally { if (alive) busy.value = false }
}
async function remove(id: string) { if (busy.value) return; busy.value = true; error.value = ''; try { await workbenchRequest(`/documents/${id}`, undefined, 'DELETE'); hits.value = []; await load() } catch (e) { if (alive) error.value = String(e) } finally { if (alive) busy.value = false } }
async function search() { busy.value = true; error.value = ''; try { const data = await workbenchRequest<typeof hits.value>(`/documents/search?q=${encodeURIComponent(question.value)}`); if (alive) hits.value = data } catch (e) { if (alive) error.value = String(e) } finally { if (alive) busy.value = false } }
async function poll() { if (sky.authorized && rows.value.some(r => r.status === 'indexing')) await load(); if (alive) timer = setTimeout(poll, 2500) }
watch(() => sky.authorized ? sky.username : '', name => { generation++; rows.value = []; hits.value = []; updating.value = ''; error.value = ''; if (name) void load() }, { immediate: true })
timer = setTimeout(poll, 2500)
onScopeDispose(() => { alive = false; generation++; clearTimeout(timer) })
</script>
<template><section class="knowledge"><h2>我的领域知识库</h2><p>文档按登录账号隔离，解析及向量化在本地执行，不抓取外部链接；真实Agent分析时可能把检索片段发送给模型。支持2MiB以内UTF-8 TXT/Markdown、DOCX和文字PDF，扫描PDF需先OCR。每账号最多20份，每份最多250片段。</p><p v-if="error" role="alert">{{ error }}</p><label>新增 / 更新文档<select v-model="updating" :disabled="busy"><option value="">新增文档</option><option v-for="r in rows.filter(v => !['deleted','superseded'].includes(v.status))" :key="`${r.id}-${r.version}`" :value="r.id">更新 {{ r.name }} v{{ r.version }}</option></select><input type="file" accept=".md,.txt,.docx,.pdf" :disabled="busy || !sky.canOperate" @change="upload"></label><button :disabled="busy" @click="load">刷新索引状态</button><div class="table"><table><thead><tr><th>文档</th><th>版本</th><th>状态</th><th>片段</th><th>说明</th><th>操作</th></tr></thead><tbody><tr v-for="r in rows" :key="`${r.id}-${r.version}`"><td>{{ r.name }}<details><summary>SHA256</summary>{{ r.sha256 }}</details></td><td>{{ r.version }}</td><td>{{ r.status }}</td><td>{{ r.chunk_count }}</td><td>{{ r.error }}</td><td><button :disabled="busy || !sky.canOperate || ['deleted','superseded'].includes(r.status)" @click="remove(r.id)">删除此文档所有版本</button></td></tr></tbody></table></div><p>更新会立即停用旧版本，索引失败不会悄悄沿用旧规则；删除后不再参与新检索，既有运行的历史快照仍保留。</p><h3>本地检索试验（不调用外部模型）</h3><input v-model="question" maxlength="1000" aria-label="知识检索问题"><button :disabled="busy || !question.trim()" @click="search">检索我的文档</button><details v-for="(hit,i) in hits" :key="i" open><summary>{{ hit.section }} v{{ hit.document_version }} · 相似度 {{ hit.score }}</summary><p>{{ hit.text }}</p></details><p v-if="!hits.length">暂无检索结果；不会用无依据内容补全。</p></section></template>
<style scoped>.knowledge{padding:20px;background:#102537;border:1px solid #31546b}.knowledge p{color:#9ebfd2;line-height:1.8}.knowledge input,.knowledge select{margin:8px;padding:8px;background:#081c2a;color:#e0eff7;border:1px solid #36536b}.table{overflow:auto}table{width:100%;border-collapse:collapse}td,th{padding:10px;text-align:left;border-bottom:1px solid #31546b;font-size:13px}details{overflow-wrap:anywhere;padding:6px 0}</style>
