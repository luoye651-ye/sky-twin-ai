// Real local browser and Java endpoints, isolated cookies, no mocked business responses.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.SKYTWIN_PLAYWRIGHT_MODULE || 'playwright')
const prefix = process.env.SKYTWIN_UI_PREFIX, task = process.env.SKYTWIN_UI_TASK
assert(/^rt_[a-f0-9]+$/.test(prefix) && /^T-/.test(task))
const base = 'http://127.0.0.1:5173', url = `${base}/route-planning?taskId=${encodeURIComponent(task)}`
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
  await page.goto(url)
  await page.getByRole('heading', { name: '多航点航线规划', exact: true }).waitFor()
  await page.getByRole('button', { name: '校验草稿', exact: true }).click()
  await page.getByText('当前草稿不可执行，请调整航点', { exact: true }).waitFor()
  assert.equal(await page.getByRole('button', { name: '保存航线', exact: true }).isDisabled(), true)
  check('original straight route is blocked by real configured no-fly policy')
  await page.waitForFunction(() => !document.querySelector('.scene-message'), null, { timeout: 45000 })
  const canvas = page.locator('.city-canvas canvas')
  await page.getByRole('button', { name: '点击地图添加航点', exact: true }).click()
  await canvas.scrollIntoViewIfNeeded()
  const rect = await canvas.boundingBox()
  await canvas.click({ position: { x: rect.width * .42, y: rect.height * .58 } })
  await page.getByRole('spinbutton', { name: '航点1经度', exact: true }).waitFor()
  await canvas.click({ position: { x: rect.width * .62, y: rect.height * .62 } })
  await page.getByRole('spinbutton', { name: '航点2经度', exact: true }).waitFor()
  check('actual Three.js cruise-plane picks create two editable waypoints')
  const firstLongitude = await page.getByRole('spinbutton', { name: '航点1经度', exact: true }).inputValue()
  await page.locator('.table-wrap tbody tr').nth(0).getByRole('button', { name: '选中', exact: true }).click()
  await page.getByRole('button', { name: '点击地图移动选中航点', exact: true }).click()
  await canvas.scrollIntoViewIfNeeded()
  await canvas.click({ position: { x: rect.width * .35, y: rect.height * .68 } })
  assert.notEqual(await page.getByRole('spinbutton', { name: '航点1经度', exact: true }).inputValue(), firstLongitude)
  check('map relocation updates the selected waypoint without adding another')
  await page.locator('.table-wrap tbody tr').nth(0).getByRole('button', { name: '下移', exact: true }).click()
  await page.locator('.table-wrap tbody tr').nth(1).getByRole('button', { name: '删除', exact: true }).click()
  assert.equal(await page.locator('.table-wrap tbody tr').count(), 1)
  await page.getByRole('button', { name: '点击地图添加航点', exact: true }).click()
  await canvas.scrollIntoViewIfNeeded()
  await canvas.click({ position: { x: rect.width * .60, y: rect.height * .70 } })
  await page.getByRole('spinbutton', { name: '航点2经度', exact: true }).waitFor()
  check('waypoints support reordering, deletion and re-addition')
  for (const [index, lon] of [[1, '120.19'], [2, '120.193']]) {
    await page.getByRole('spinbutton', { name: `航点${index}经度`, exact: true }).fill(lon)
    await page.getByRole('spinbutton', { name: `航点${index}纬度`, exact: true }).fill('30.225')
  }
  await page.getByRole('textbox', { name: '航线规划原因', exact: true }).fill(prefix + '_ui_detour')
  await page.getByRole('button', { name: '校验草稿', exact: true }).click()
  await page.getByText('当前草稿通过校验，尚未保存', { exact: true }).waitFor()
  await page.getByRole('button', { name: '保存航线', exact: true }).click()
  await page.getByText('航线 v2 已保存；起飞时仍会复查空域和资源', { exact: true }).waitFor()
  check('real Java accepts the manual detour and atomically saves v2')
  await page.getByRole('button', { name: '查看版本 1', exact: true }).click()
  await page.getByText('历史版本 · 只读', { exact: true }).waitFor()
  assert.equal(await page.getByRole('button', { name: '点击地图添加航点', exact: true }).isDisabled(), true)
  await page.getByRole('button', { name: '返回当前草稿', exact: true }).click()
  await page.reload()
  await page.getByRole('spinbutton', { name: '航点2经度', exact: true }).waitFor()
  assert.equal(Number(await page.getByRole('spinbutton', { name: '航点2经度', exact: true }).inputValue()), 120.193)
  check('history is read-only and reload restores both persisted waypoints')
  await page.waitForFunction(() => !document.querySelector('.scene-message'), null, { timeout: 45000 })
  await page.getByRole('button', { name: '定位整条航线', exact: true }).click()
  await mkdir(resolve('docs/verification'), { recursive: true })
  await page.locator('.map').screenshot({ path: resolve('docs/verification/waypoint-route-map.png') })
  await page.getByRole('button', { name: '校验草稿', exact: true }).click()
  await page.getByText('当前草稿通过校验，尚未保存', { exact: true }).waitFor()
  await page.screenshot({ path: resolve('docs/verification/waypoint-route-editor.png'), fullPage: true })
  check('WebGL renders the persisted detour with actual cruise-height waypoint markers')
  const viewerContext = await browser.newContext({ viewport: { width: 1720, height: 1080 }, locale: 'zh-CN' })
  await viewerContext.addCookies([{ name: 'Admin-Token', value: process.env.SKYTWIN_UI_VIEWER_TOKEN, url: base }])
  const viewer = await viewerContext.newPage()
  await viewer.goto(url)
  await viewer.getByRole('spinbutton', { name: '航点1经度', exact: true }).waitFor()
  assert.equal(await viewer.getByRole('button', { name: '保存航线', exact: true }).isDisabled(), true)
  assert.equal(await viewer.getByRole('button', { name: '点击地图添加航点', exact: true }).isDisabled(), true)
  check('read-only viewer cannot edit or save routes')
  await viewerContext.close()
  await page.goto(base + '/digital-twin')
  await page.getByRole('heading', { name: '飞行器资源', exact: true }).waitFor()
  await page.goto(url)
  await page.getByRole('spinbutton', { name: '航点1经度', exact: true }).waitFor()
  assert.deepEqual(errors, [])
  check('navigation and scene disposal produce no uncaught browser errors')
  report.passed = true
} catch (e) { report.error = String(e); throw e }
finally { await browser?.close(); await writeFile(resolve('ruoyi/logs/routes-ui-verification.json'), JSON.stringify(report, null, 2)) }
