import { test } from 'node:test'
import assert from 'node:assert/strict'
import { consumeAgentStream, decodeAgentEvent } from '../src/utils/agentProtocol.ts'
const answer = { type:'answer', data:{ text:'中文证据[K1]', tool_messages:1, mcp_calls:0, aircraft_count:null, knowledge_calls:1, sources:[{citation_id:'K1',source:'agent/knowledge/airspace.md',section:'限高',line_start:1,line_end:5,code_references:['source.java']}] } }
function streamed(text, size = 7) {
  const bytes = new TextEncoder().encode(text)
  return new Response(new ReadableStream({start(controller) {
    for(let i=0; i<bytes.length; i+=size) controller.enqueue(bytes.slice(i,i+size))
    controller.close()
  }}))
}
test('NDJSON handles split UTF-8, progress, heartbeat and final citations', async () => {
  const events=[]
  await consumeAgentStream(streamed(JSON.stringify({type:'progress',message:'正在检索'})+'\n{"type":"heartbeat"}\n'+JSON.stringify(answer)+'\n',1),event=>events.push(event))
  assert.equal(events.at(-1).data.text,'中文证据[K1]')
  assert.equal(events.length,3)
})
test('accepts final event without trailing newline', async () => {
  const events=[]
  await consumeAgentStream(streamed(JSON.stringify(answer)),event=>events.push(event))
  assert.equal(events.length,1)
})
test('server errors and incomplete streams do not become successful answers', async () => {
  await assert.rejects(consumeAgentStream(streamed('{"type":"error","message":"登录已过期"}\n'),()=>{}),/登录已过期/)
  await assert.rejects(consumeAgentStream(streamed('{"type":"progress","message":"运行中"}\n'),()=>{}),/提前结束/)
})
test('rejects malformed schemas and forged message types', () => {
  for(const value of ['invalid','{}','{"type":"answer","data":{"text":"fake"}}','{"type":"run_code","code":"..."}']) assert.throws(()=>decodeAgentEvent(value))
  assert.throws(()=>decodeAgentEvent(JSON.stringify({...answer,data:{...answer.data,mcp_calls:-1}})))
})
test('rejects extra events after final answer and bounds oversized frames', async () => {
  await assert.rejects(consumeAgentStream(streamed(JSON.stringify(answer)+'\n'+JSON.stringify(answer)+'\n'),()=>{}),/多余数据/)
  await assert.rejects(consumeAgentStream(streamed('x'.repeat(131073),131073),()=>{}),/过大/)
})


test('dispatch cards only accept Java plan identifiers', () => {
  const data = {...answer.data, dispatch_plan_id:'DP-'+'a'.repeat(32)}
  assert.equal(decodeAgentEvent(JSON.stringify({type:'answer',data})).data.dispatch_plan_id,data.dispatch_plan_id)
  for (const id of ['forged-plan', '/sky/tasks/1/execute', 1, 'DP-'+ 'a'.repeat(33)]) {
    assert.throws(()=>decodeAgentEvent(JSON.stringify({type:'answer',data:{...data,dispatch_plan_id:id}})))
  }
})


test('map targets accept entity identifiers and reject forged kinds or oversized excerpts', () => {
  const data = {...answer.data,map_targets:[{kind:'task',id:'T-1',label:'任务'}]}
  assert.equal(decodeAgentEvent(JSON.stringify({type:'answer',data})).data.map_targets[0].id,'T-1')
  for (const target of [{kind:'command',id:'execute',label:'fake'}, {kind:'task',id:'x'.repeat(41),label:'fake'}]) {
    assert.throws(()=>decodeAgentEvent(JSON.stringify({type:'answer',data:{...data,map_targets:[target]}})))
  }
  assert.throws(()=>decodeAgentEvent(JSON.stringify({type:'answer',data:{...data,sources:[{...answer.data.sources[0],text:'x'.repeat(1001)}]}})))
})
