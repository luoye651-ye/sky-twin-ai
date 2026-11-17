import { computed, onMounted, onScopeDispose, shallowRef, watch } from 'vue'
import { askAgent, getAgentHealth } from '../api/agent'
import type { AgentHealth, AgentMessage } from '../types/agent'
import { useImageChat } from './useImageChat'

export function useAgentChat(identity: () => string) {
  const messages = shallowRef<AgentMessage[]>([]), draft = shallowRef(''), busy = shallowRef(false)
  const imageChat=useImageChat(identity)
  const health = shallowRef<AgentHealth>({ ready: false, message: '正在连接助手…' }), checking = shallowRef(false)
  const canSend = computed(() => (imageChat.enabled.value?imageChat.ready.value:health.value.ready) && !busy.value && !!draft.value.trim() && draft.value.length <= 2000)
  let conversationId: string = crypto.randomUUID()
  let alive = true, sequence = 0, controller: AbortController | undefined, healthController: AbortController | undefined
  const update = (id: string, patch: Partial<AgentMessage>) => { messages.value = messages.value.map(item => item.id === id ? { ...item, ...patch } : item) }
  async function refreshHealth() {
    if (checking.value) return
    checking.value = true
    const current = new AbortController(); healthController = current
    const timeout = setTimeout(() => current.abort(), 10000)
    try { const value = await getAgentHealth(current.signal); if (alive) health.value = value }
    catch { if (alive) health.value = { ready: false, message: '助手未连接，请启动Agent服务后重新检测。' } }
    finally { clearTimeout(timeout); if (alive) checking.value = false }
  }
  function stop() {
    sequence++; controller?.abort(); controller = undefined; busy.value = false
    messages.value = messages.value.map(item => item.state === 'pending' ? { ...item, state: 'stopped', text: '已停止等待；已经发出的模型请求可能仍产生费用。' } : item)
  }
  function clear() { stop(); conversationId = crypto.randomUUID(); messages.value = []; draft.value = '';imageChat.clear() }
  async function send() {
    if (!canSend.value || !identity()) return
    const question = draft.value.trim(), requestId = crypto.randomUUID(), responseId = crypto.randomUUID(), ticket = ++sequence
    const current = new AbortController(); controller = current
    busy.value = true; draft.value = ''
    messages.value = [...messages.value.slice(-38),
      { id: requestId, role: 'user', state: 'complete', text: question, progress: [] },
      { id: responseId, role: 'assistant', state: 'pending', text: '', progress: [] }]
    let timedOut = false
    const timeout = setTimeout(() => { timedOut = true; current.abort() }, 110000)
    const progress: string[] = []
    try {
      if(imageChat.enabled.value){
        update(responseId,{progress:['正在将已授权图片发送至现有DeepSeek进行视觉理解…']})
        const result=await imageChat.ask(question,requestId,current.signal)
        if(alive&&ticket===sequence)update(responseId,{state:'complete',text:result.summary,vision:result})
        return
      }
      await askAgent(question, requestId, current.signal, event => {
        if (!alive || ticket !== sequence) return
        if (event.type === 'progress') { progress.push(event.message); update(responseId, { progress: progress.slice(-8) }) }
        if (event.type === 'answer') update(responseId, { state: 'complete', text: event.data.text, answer: event.data })
      }, conversationId)
    } catch (error) {
      if (alive && ticket === sequence) {
        update(responseId, { state: 'error', answer: undefined, text: timedOut ? '等待超时，请检查服务后重试；不会自动重复付费请求。' : error instanceof Error ? error.message : '本次查询未完成。' })
        if (!draft.value) draft.value = question
        void refreshHealth() // Diagnostic only; never automatically repeat a paid question.
      }
    } finally {
      clearTimeout(timeout)
      if (alive && ticket === sequence) { busy.value = false; controller = undefined }
    }
  }
  watch(identity, () => clear())
  onMounted(refreshHealth)
  onScopeDispose(() => { alive = false; sequence++; controller?.abort(); healthController?.abort() })
  return { messages, draft, busy, health, checking, canSend, send, stop, clear, refreshHealth, imageChat }
}
