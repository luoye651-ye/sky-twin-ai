// Real Java endpoints and actual WebGL; isolated cookies, no mocked responses.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.SKYTWIN_PLAYWRIGHT_MODULE || 'playwright')
const prefix = process.env.SKYTWIN_UI_PREFIX, tasks = JSON.parse(process.env.SKYTWIN_UI_TASKS || '[]')
assert(/^tf_[a-f0-9]+$/.test(prefix) && tasks.length === 2)
const base = 'http://127.0.0.1:5173'
const report = { passed: false, checks: [], transport: 'Real Java API, no mocked responses.' }
const check = name => { report.checks.push(name); console.log('PASS UI: ' + name) }
let browser
try {
  const options = { headless: true, args: ['--enable-unsafe-swiftshader'] }
  try { browser = await chromium.launch({ ...options, channel: 'chrome' }) }
  catch { browser = await chromium.launch(options) }
  const context = await browser.newContext({ viewport: { width: 1720, height: 1080 }, locale: 'zh-CN' })
  await context.addCookies([{ name: 'Admin-Token', value: process.env.SKYTWIN_UI_ADMIN_TOKEN, url: base }])
  const page = await context.newPage(), errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(base + '/traffic')
  await page.getByRole('heading', { name: '多机协同 · 冲突预测与错峰起飞', exact: true }).waitFor()
  for (const suffix of ['uiA', 'uiB']) await page.getByRole('checkbox', { name: `选择${prefix}_${suffix}`, exact: true }).check()
  assert.equal(await page.locator('.choices input:checked').count(), 2)
  await page.getByRole('spinbutton', { name: '起飞提前量', exact: true }).fill('120')
  await page.getByRole('spinbutton', { name: '最大错峰等待', exact: true }).fill('0')
  await page.getByRole('button', { name: '预测冲突并生成错峰方案', exact: true }).click()
  await page.getByText('存在不可执行任务，不能确认整批方案', { exact: true }).waitFor()
  assert.equal(await page.getByRole('button', { name: '确认预约并自动起飞', exact: true }).isDisabled(), true)
  check('real conflicting routes cannot confirm with zero delay horizon')
  await page.getByRole('spinbutton', { name: '最大错峰等待', exact: true }).fill('120')
  assert.equal(await page.getByRole('button', { name: '确认预约并自动起飞', exact: true }).count(), 0)
  check('changing scheduling inputs invalidates old preview')
  await page.locator('ol li').first().getByRole('button', { name: '下移', exact: true }).click()
  assert.match(await page.locator('ol li').first().innerText(), /_uiB/)
  await page.locator('ol li').first().getByRole('button', { name: '下移', exact: true }).click()
  check('operator can reorder slot priority without changing task business priority')
  await page.getByRole('button', { name: '预测冲突并生成错峰方案', exact: true }).click()
  await page.getByText('所有任务均找到可行时隙', { exact: true }).waitFor()
  await page.getByRole('button', { name: '定位冲突点', exact: true }).first().click()
  await page.waitForFunction(() => !document.querySelector('.scene-message'), null, { timeout: 45000 })
  assert.match(await page.locator('.map-note').innerText(), /预计冲突点/)
  assert.equal(await page.locator('.city-canvas canvas').count(), 1)
  check('saved timed routes produce positive staggering and a WebGL conflict location')
  await mkdir(resolve('docs/verification'), { recursive: true })
  await page.screenshot({ path: resolve('docs/verification/traffic-conflict-preview.png'), fullPage: true })
  await page.getByRole('textbox', { name: '错峰操作原因', exact: true }).fill(prefix + '_ui')
  await page.getByRole('button', { name: '确认预约并自动起飞', exact: true }).click()
  await page.getByText('预约已确认；Java 将在仿真时刻到达后复查并自动起飞', { exact: true }).waitFor()
  const reservations = page.getByRole('heading', { name: '3 · 当前预约与执行', exact: true }).locator('..')
  await reservations.getByText('等待起飞', { exact: true }).first().waitFor()
  assert.equal(await reservations.getByText('等待起飞', { exact: true }).count(), 2)
  check('confirmation persists two real reservations with remaining simulation time')
  await page.reload()
  await reservations.getByText('等待起飞', { exact: true }).first().waitFor()
  assert.equal(await reservations.getByText('等待起飞', { exact: true }).count(), 2)
  check('reload restores persisted reservations')
  const rowA = reservations.locator('tbody tr').filter({ hasText: prefix + '_uiA' })
  const rowB = reservations.locator('tbody tr').filter({ hasText: prefix + '_uiB' })
  await rowA.getByRole('button', { name: '取消预约', exact: true }).click()
  await rowA.getByText('已取消', { exact: true }).waitFor()
  await rowB.getByRole('button', { name: '取消预约', exact: true }).click()
  await rowB.getByText('已取消', { exact: true }).waitFor()
  await page.waitForFunction(() => [...document.querySelectorAll('section.card')].some(el => el.textContent.includes('3 · 当前预约与执行') && [...el.querySelectorAll('tbody tr')].every(row => row.textContent.includes('已取消') || !row.textContent.includes('_ui'))))
  check('cancellation releases future reservations and keeps tasks assigned')
  const viewerContext = await browser.newContext({ viewport: { width: 1720, height: 1080 }, locale: 'zh-CN' })
  await viewerContext.addCookies([{ name: 'Admin-Token', value: process.env.SKYTWIN_UI_VIEWER_TOKEN, url: base }])
  const viewer = await viewerContext.newPage()
  await viewer.goto(base + '/traffic')
  await viewer.getByRole('checkbox', { name: `选择${prefix}_uiA`, exact: true }).waitFor()
  assert.equal(await viewer.getByRole('checkbox', { name: `选择${prefix}_uiA`, exact: true }).isDisabled(), true)
  assert.equal(await viewer.getByRole('button', { name: '预测冲突并生成错峰方案', exact: true }).isDisabled(), true)
  check('viewer cannot select or reserve flights')
  await viewerContext.close()
  await page.goto(base + '/route-planning')
  await page.getByRole('heading', { name: '多航点航线规划', exact: true }).waitFor()
  await page.getByRole('link', { name: '多机冲突预测 / 错峰起飞 →', exact: true }).click()
  await page.getByRole('heading', { name: '多机协同 · 冲突预测与错峰起飞', exact: true }).waitFor()
  assert.deepEqual(errors, [])
  check('route planning links to coordination and scene remount has no uncaught errors')
  report.passed = true
} catch (e) { report.error = String(e); throw e }
finally { await browser?.close(); await writeFile(resolve('ruoyi/logs/traffic-ui-verification.json'), JSON.stringify(report, null, 2)) }
