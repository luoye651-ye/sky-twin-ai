// Isolated browser acceptance: all business/chat responses are explicit test fixtures.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.SKYTWIN_PLAYWRIGHT_MODULE || 'playwright')
const artifact = fileURLToPath(new URL('../../docs/verification/', import.meta.url))
const base = 'http://127.0.0.1:5173', checks = [], requests = [], errors = [], businessWrites = []
const report = { passed:false, mode:'isolated mocked Java/chat APIs; no real token or paid model', checks }
const check = label => { checks.push(label); console.log('PASS UI: '+label) }
const snapshot = { aircraft:[],stations:[],tasks:[],airspaceZones:[],events:[],reports:[],audit:[],summary:{aircraft:0,executing:0,completed:0,openEvents:0},simulation:{enabled:true,timeScale:10,coordinateSystem:'WGS84',realFlight:false} }
const answer = {text:'【界面验收样例，非模型现场回答】\n最新应急侦察必须完成，并具备事件点附近轨迹与不同于发现图的处置后图片。[K1]',tool_messages:1,mcp_calls:0,aircraft_count:null,knowledge_calls:1,sources:[{citation_id:'K1',source:'agent/knowledge/response.md',section:'结案条件与处置后证据',line_start:21,line_end:26,code_references:['EnvironmentService.java：close']} ]}
let browser, mode='answer', ready=true, release=()=>{}, arrived=()=>{}
try {
  try { browser=await chromium.launch({channel:'chrome',headless:true}) } catch { browser=await chromium.launch({headless:true}) }
  const context=await browser.newContext({viewport:{width:1720,height:1080},locale:'zh-CN'})
  await context.addCookies([{name:'Admin-Token',value:'isolated-ui-fixture-token',url:base}])
  await context.route('**/java-api/**',async route=>{
    const request=route.request(), path=new URL(request.url()).pathname
    if(request.method()!=='GET') businessWrites.push(path)
    if(path.endsWith('/getInfo')) return route.fulfill({json:{code:200,user:{userName:'UI验收样例'},permissions:['sky:read']}})
    if(path.endsWith('/sky/snapshot')) return route.fulfill({json:{code:200,data:snapshot}})
    if(path.endsWith('/sky/stream')) return route.fulfill({contentType:'text/event-stream',body:'data: '+JSON.stringify(snapshot)+'\n\n'})
    return route.fulfill({json:{code:200,data:[]}})
  })
  await context.route('**/agent-api/**',async route=>{
    if(route.request().url().endsWith('/health')) return route.fulfill({json:{ready,message:ready?'测试服务已就绪':'测试服务未就绪'},status:ready?200:503})
    const request=route.request(), body=request.postDataJSON()
    assert.deepEqual(Object.keys(body).sort(),['question','request_id'])
    assert.match(body.request_id,/^[\da-f-]{36}$/i)
    assert.equal((await request.allHeaders()).authorization,'Bearer isolated-ui-fixture-token')
    requests.push(body); arrived()
    const selected=mode
    if(selected==='hold') await new Promise(resolve=>{release=resolve})
    try {
      if(selected==='error') return await route.fulfill({status:401,json:{detail:'测试：登录已失效，请重新登录。'}})
      if(selected==='incomplete') return await route.fulfill({contentType:'application/x-ndjson',body:'{"type":"progress","message":"测试处理中"}\n'})
      const value=selected==='xss'?{...answer,text:'<img src=x onerror="window.__agentXss=true"> [K1]'}:answer
      return await route.fulfill({contentType:'application/x-ndjson',body:JSON.stringify({type:'progress',message:'[知识完成] 找到1段验收样例证据'})+'\n'+JSON.stringify({type:'answer',data:value})+'\n'})
    } catch { /* An aborted isolated route is expected in cancellation checks. */ }
  })
  const page=await context.newPage()
  page.on('pageerror',error=>errors.push(error.message))
  await page.goto(base+'/agent-command')
  await page.getByRole('heading',{name:'Agent 指挥中心',exact:true}).waitFor()
  const input=page.getByRole('textbox',{name:'向助手提问',exact:true}), send=page.getByRole('button',{name:/发送问题/})
  await input.waitFor({state:'visible'})
  await page.getByText('已连接',{exact:true}).waitFor()
  assert.equal(await page.getByRole('tab',{name:'自然语言助手',exact:true}).getAttribute('aria-selected'),'true')
  assert(await send.isDisabled())
  check('Agent指挥 defaults to read-only chat; blank submission disabled')
  await page.getByRole('button',{name:'应急事件结案需要哪些证据？',exact:false}).click()
  assert.equal(await input.inputValue(),'应急事件结案需要哪些证据？')
  assert.equal(requests.length,0)
  check('suggestions fill input without automatically spending model credits')
  mode='hold'
  const started=new Promise(resolve=>{arrived=resolve})
  await send.click(); await started
  await page.getByRole('button',{name:'停止等待',exact:true}).waitFor()
  await input.press('Enter')
  assert.equal(requests.length,1)
  release()
  await page.locator('.assistant.complete').waitFor()
  await page.locator('.sources summary').click()
  await page.getByText('agent/knowledge/response.md · 第21～26行',{exact:true}).waitFor()
  assert.equal(await page.locator('.source-card').count(),1)
  check('single submission shows reply, actual trace and expandable source metadata')
  await mkdir(artifact,{recursive:true})
  await page.screenshot({path:resolve(artifact,'agent-chat-window.png'),fullPage:true})
  await page.getByRole('tab',{name:'算法调度',exact:true}).click()
  await page.getByRole('heading',{name:'AI 集群调度',exact:true}).waitFor()
  assert(await page.getByText('当前为只读账号，可以查看调度记录；生成与确认方案需要调度权限。',{exact:true}).isVisible())
  await page.getByRole('tab',{name:'自然语言助手',exact:true}).click()
  assert.equal(await page.locator('.assistant.complete').count(),1)
  check('original algorithm dispatch retained; chat survives tab switching')
  await page.getByRole('button',{name:'清空会话',exact:true}).click()
  assert.equal(await page.locator('.message').count(),0)
  mode='error'; await input.fill('读取飞机'); await send.click()
  await page.getByText('测试：登录已失效，请重新登录。',{exact:true}).waitFor()
  assert.equal(await input.inputValue(),'读取飞机')
  check('auth error is visible and preserves the question; no automatic retry')
  mode='incomplete'; await send.click()
  await page.getByText('助手连接提前结束，未收到完整答复。',{exact:true}).waitFor()
  check('incomplete response is not displayed as successful answer')
  mode='hold'
  const waiting=new Promise(resolve=>{arrived=resolve})
  await send.click(); await waiting
  await page.getByRole('button',{name:'停止等待',exact:true}).click()
  await page.getByText('已停止等待；已经发出的模型请求可能仍产生费用。',{exact:true}).waitFor()
  release()
  assert.equal(await page.locator('.assistant.complete').count(),0)
  check('stop aborts waiting and ignores late responses')
  mode='xss'; await input.fill('测试内容转义'); await send.click()
  await page.getByText('<img src=x onerror="window.__agentXss=true"> [K1]',{exact:true}).waitFor()
  assert.equal(await page.locator('.message-body img').count(),0)
  assert.equal(await page.evaluate(()=>window.__agentXss),undefined)
  check('model text is escaped, not rendered as executable HTML')
  await page.getByRole('button',{name:'清空会话',exact:true}).click()
  ready=false; await page.reload()
  await page.getByText('测试服务未就绪',{exact:true}).waitFor()
  assert(await input.isDisabled())
  ready=true; await page.getByRole('button',{name:'重新检测',exact:true}).click()
  await page.getByText('已连接',{exact:true}).waitFor()
  assert(await input.isEnabled())
  check('unavailable service disables sending and can reconnect explicitly')
  await input.fill('输入法测试')
  const before=requests.length
  await input.dispatchEvent('keydown',{key:'Enter',isComposing:true,bubbles:true})
  await input.press('Shift+Enter')
  assert.equal(requests.length,before)
  check('IME enter and Shift+Enter do not submit requests')
  await page.setViewportSize({width:390,height:844})
  const bounds=await page.locator('.chat-panel').boundingBox()
  assert(bounds.width<=390)
  await page.screenshot({path:resolve(artifact,'agent-chat-mobile.png'),fullPage:true})
  check('chat layout fits a narrow viewport')
  assert.deepEqual(businessWrites,[])
  assert.deepEqual(errors,[])
  check('no business writes and no browser runtime errors')
  report.passed=true
} finally {
  release(); await browser?.close()
  await mkdir(artifact,{recursive:true})
  await writeFile(resolve(artifact,'agent-chat-ui.json'),JSON.stringify(report,null,2))
}
