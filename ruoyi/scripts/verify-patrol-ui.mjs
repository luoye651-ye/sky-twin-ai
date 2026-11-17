// Real Vue/Java acceptance: random patrol list and text-free image dialog.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.SKYTWIN_PLAYWRIGHT_MODULE || 'playwright')
const base = 'http://127.0.0.1:5173', runId = process.env.SKYTWIN_PATROL_RUN
const result = { passed:false, checks:[] }
const check = name => { result.checks.push(name); console.log('PASS UI: '+name) }
let browser
try {
  try { browser = await chromium.launch({channel:'chrome',headless:true}) }
  catch { browser = await chromium.launch({headless:true}) }
  const context = await browser.newContext({viewport:{width:1720,height:1080},locale:'zh-CN'})
  await context.addCookies([{name:'Admin-Token',value:process.env.SKYTWIN_UI_ADMIN_TOKEN,url:base}])
  const page = await context.newPage(), errors = []
  page.on('pageerror',error => errors.push(error.message))
  const api = async id => {
    const response = await context.request.get(base+'/java-api/sky/patrol-evaluation/runs/'+id,{headers:{Authorization:'Bearer '+process.env.SKYTWIN_UI_ADMIN_TOKEN}})
    return (await response.json()).data
  }
  const run = await api(runId), report = run.report, count = report.rows.length
  assert(count >= 1 && count <= 132)
  const heading = '逐图检测结果（'+count+' 张）'
  await page.goto(base+'/environment?runId='+runId)
  await page.getByRole('heading',{name:heading,exact:true}).waitFor()
  assert.deepEqual(await page.locator('.result-table th').allTextContents(),['图片','检出数量','操作'])
  assert.equal(await page.locator('.result-table tbody tr').count(),Math.min(count,15))
  assert.equal(await page.locator('.source-note,.metrics,.simulation,.report-note,.image-detail,.detection-image').count(),0)
  assert(!/仿真演示：使用HAIDA|非杭州实时画面|测试图片|查准率|召回率|mAP|GPU推理|下载本次评测JSON/.test(await page.locator('body').innerText()))
  check('random count drives lean list; page explanation and all benchmark UI absent')
  await mkdir(resolve('docs/verification'),{recursive:true})
  await page.screenshot({path:resolve('docs/verification/environment-patrol-list.png')})
  if(count>15) {
    await page.locator('.pagination .btn-next').click()
    await page.waitForFunction(() => document.querySelector('.el-pager .is-active')?.textContent?.trim()==='2')
    check('random-size list pagination works')
  }
  const chosen = report.rows.find(r => r.predictionCount>0) ?? report.rows[0]
  await page.getByRole('textbox',{name:'搜索检测图片',exact:true}).fill(chosen.filename)
  assert.equal(await page.locator('.result-table tbody tr').count(),1)
  assert.equal(await page.locator('.result-table tbody tr td').nth(1).innerText(),String(chosen.predictionCount))
  const before = page.url()
  await page.getByRole('button',{name:'查看检测图 '+chosen.filename,exact:true}).click()
  const dialog = page.getByRole('dialog')
  await dialog.waitFor()
  await page.waitForFunction(() => document.querySelector('.patrol-image-dialog .detection-image')?.naturalWidth>0)
  assert.equal(page.url(),before)
  assert.equal(context.pages().length,1)
  assert.equal((await dialog.locator('.el-dialog__title').allTextContents()).join(''),'')
  assert(!/检测图 ·|HAIDA OFFLINE TEST|MODEL PREDICTIONS/.test(await dialog.innerText()))
  assert.equal(await page.locator('.patrol-workspace .detection-image').count(),0)
  await dialog.screenshot({path:resolve('docs/verification/environment-patrol-dialog.png')})
  check('same-page image modal has no visible title or header text')
  await dialog.locator('.el-dialog__headerbtn').click()
  await dialog.waitFor({state:'hidden'})
  await page.getByRole('button',{name:'查看检测图 '+chosen.filename,exact:true}).click()
  await page.waitForFunction(() => document.querySelector('.patrol-image-dialog .detection-image')?.naturalWidth>0)
  await page.keyboard.press('Escape')
  await dialog.waitFor({state:'hidden'})
  check('titleless modal closes and reopens correctly')
  await page.reload()
  await page.getByRole('heading',{name:heading,exact:true}).waitFor()
  const saved = await api(runId)
  assert.deepEqual(saved.report,report)
  assert.equal(await page.locator('.detection-image').count(),0)
  check('refresh preserves sample count and exact results, never rerandomizes history')
  await page.goto(base+'/patrol-evaluation?runId='+runId)
  await page.waitForURL('**/environment?runId='+runId)
  await page.getByRole('heading',{name:heading,exact:true}).waitFor()
  check('old entry redirect preserves random-run deep link')
  const legacyId = process.env.SKYTWIN_PATROL_LEGACY_RUN
  if(legacyId) {
    const legacy = await api(legacyId), row = legacy.report.rows.find(r=>r.id==='data15_14') ?? legacy.report.rows[0]
    await page.goto(base+'/environment?runId='+legacyId)
    await page.getByRole('heading',{name:'逐图检测结果（'+legacy.imageCount+' 张）',exact:true}).waitFor()
    await page.getByRole('textbox',{name:'搜索检测图片',exact:true}).fill(row.filename)
    await page.getByRole('button',{name:'查看检测图 '+row.filename,exact:true}).click()
    await page.waitForFunction(() => document.querySelector('.patrol-image-dialog .detection-image')?.naturalWidth>0)
    await dialog.screenshot({path:resolve('docs/verification/patrol-legacy-clean-preview.png')})
    await page.keyboard.press('Escape')
    await dialog.waitFor({state:'hidden'})
    check('historical full-run detection image also serves clean preview without changing report')
  }
  const viewer = await browser.newContext({viewport:{width:1440,height:900}})
  await viewer.addCookies([{name:'Admin-Token',value:process.env.SKYTWIN_UI_VIEWER_TOKEN,url:base}])
  const readonly = await viewer.newPage()
  await readonly.goto(base+'/environment?runId='+runId)
  await readonly.getByRole('heading',{name:heading,exact:true}).waitFor()
  assert(await readonly.getByRole('button',{name:'启动仿真巡逻',exact:true}).isDisabled())
  check('viewer cannot start random patrol')
  await page.goto(base+'/environment?runId='+runId)
  await page.getByRole('heading',{name:heading,exact:true}).waitFor()
  const started = page.waitForResponse(r=>r.url().endsWith('/patrol-evaluation/runs') && r.request().method()==='POST')
  await page.getByRole('button',{name:'启动仿真巡逻',exact:true}).click()
  const next = (await (await started).json()).data
  assert.notEqual(next.id,runId)
  assert(next.imageCount>=1 && next.imageCount<=132)
  await page.waitForURL('**/environment?runId='+next.id)
  assert(await page.getByRole('button',{name:'巡逻识别中',exact:true}).isDisabled())
  await page.getByRole('heading',{name:'逐图检测结果（'+next.imageCount+' 张）',exact:true}).waitFor({timeout:180000})
  assert.equal((await api(next.id)).report.rows.length,next.imageCount)
  result.sampleCounts = [count,next.imageCount]
  check('new patrol selects and processes its own random size; duplicate clicks disabled')
  assert.deepEqual(errors,[])
  check('no browser runtime errors')
  result.passed = true
} finally {
  await browser?.close()
  await mkdir(resolve('docs/verification'),{recursive:true})
  await writeFile(resolve('docs/verification/patrol-ui.json'),JSON.stringify(result,null,2))
}
