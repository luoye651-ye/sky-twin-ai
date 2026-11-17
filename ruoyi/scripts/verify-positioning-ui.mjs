// Real HTTP browser acceptance in an isolated browser profile; no API mocks.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { writeFile, mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.SKYTWIN_PLAYWRIGHT_MODULE || 'playwright')
const base = 'http://127.0.0.1:5173', prefix = process.env.SKYTWIN_UI_PREFIX
assert(/^ps_[a-f0-9]+$/.test(prefix))
const report = { passed: false, checks: [], transport: 'Real local Java HTTP and SSE. No mocked API responses.' }
const check = name => { report.checks.push(name); console.log('PASS UI: ' + name) }
let browser
try {
  const options = { headless: true, args: ['--enable-unsafe-swiftshader'] }
  try { browser = await chromium.launch({ ...options, channel: 'chrome' }) }
  catch { browser = await chromium.launch(options) }
  const context = await browser.newContext({ viewport: { width: 1680, height: 1080 }, locale: 'zh-CN' })
  await context.addCookies([{ name: 'Admin-Token', value: process.env.SKYTWIN_UI_ADMIN_TOKEN, url: base }])
  const page = await context.newPage(), errors = []
  page.on('pageerror', e => errors.push(e.message))
  let writes = 0
  page.on('request', r => { if (r.method() === 'POST' && /positioning\/devices\/[^/]+\/samples/.test(r.url())) writes++ })
  await page.goto(base + '/positioning')
  await page.getByRole('heading', { name: '定位接入与轨迹回放', exact: true }).waitFor()
  await page.getByText('仿真验证版：未接北斗/GNSS硬件', { exact: false }).waitFor()
  check('page explicitly distinguishes simulation validation from real BeiDou hardware')
  await page.getByPlaceholder('例如 PC-UAV-01').fill(prefix + '_ui')
  await page.getByPlaceholder('电脑仿真终端', { exact: true }).fill(prefix + '_ui_terminal')
  await page.getByLabel('绑定飞行器', { exact: true }).selectOption(process.env.SKYTWIN_UI_AIRCRAFT)
  await page.getByRole('button', { name: '创建绑定', exact: true }).click()
  await page.getByText('终端已绑定，尚未启用定位', { exact: true }).waitFor()
  await page.getByRole('button', { name: '启用终端定位', exact: true }).click()
  await page.getByRole('button', { name: '停用定位，恢复任务仿真', exact: true }).waitFor()
  check('real UI binds fixture aircraft and enables its terminal session')
  await page.getByRole('button', { name: '开始连续上报', exact: true }).click()
  await page.waitForFunction(() => document.querySelectorAll('.receipts tbody tr .accepted').length >= 4, null, { timeout: 25000 })
  await page.getByRole('button', { name: '暂停上报', exact: true }).click()
  await page.getByRole('button', { name: '单次上报', exact: true }).waitFor({ state: 'visible' })
  await page.locator('.coordinates').waitFor()
  check('continuous reports receive persisted accepted Java receipts and coordinates')
  await page.getByRole('button', { name: '模拟无定位', exact: true }).click()
  await page.locator('.receipts').getByText('无有效定位', { exact: true }).waitFor()
  await page.getByRole('button', { name: '模拟延迟60秒', exact: true }).click()
  await page.locator('.receipts').getByText('采样延迟超过30秒', { exact: true }).waitFor()
  await page.getByRole('button', { name: '模拟位置突跳', exact: true }).click()
  await page.locator('.receipts').getByText('位置突跳', { exact: true }).waitFor()
  await page.getByRole('button', { name: '重试上一条', exact: true }).click()
  await page.getByText('相同上报重试：返回原回执，未新增记录', { exact: true }).waitFor()
  check('anomaly buttons show real server rejections and retry returns the original receipt')
  await page.waitForFunction(() => !document.querySelector('.scene-message'), null, { timeout: 45000 })
  assert.equal(await page.locator('.city-canvas canvas').count(), 1)
  await page.getByRole('button', { name: '定位当前飞行器', exact: true }).click()
  await page.locator('.aircraft-label').filter({ hasText: process.env.SKYTWIN_UI_AIRCRAFT }).waitFor({ timeout: 15000 })
  check('actual WebGL scene loads and focuses the positioned UAV')
  await page.getByRole('button', { name: '最近一小时', exact: true }).click()
  await page.getByText('历史回放 · 不影响实时状态', { exact: true }).waitFor()
  const writesBeforeReplay = writes
  await page.getByRole('button', { name: '播放', exact: true }).click()
  await page.waitForFunction(() => Number(document.querySelector('input[aria-label="回放进度"]').value) > 0)
  await page.getByRole('button', { name: '暂停回放', exact: true }).click()
  await page.getByLabel('倍速', { exact: true }).selectOption('5')
  await page.getByRole('slider', { name: '回放进度', exact: true }).fill('0')
  assert.equal(writes, writesBeforeReplay)
  check('play, pause, seek and speed controls replay persisted points without posting positions')
  await page.getByRole('button', { name: '定位当前飞行器', exact: true }).click()
  await mkdir(resolve('docs/verification'), { recursive: true })
  await page.screenshot({ path: resolve('docs/verification/positioning-live-replay.png'), fullPage: true })
  await page.getByRole('button', { name: '退出回放，返回实时', exact: true }).click()
  await page.getByText('实时定位 · 电脑仿真数据', { exact: true }).waitFor()
  await page.reload()
  await page.getByLabel('当前终端', { exact: true }).selectOption(prefix + '_ui')
  await page.locator('.coordinates').waitFor()
  check('reload restores terminal state and accepted coordinates from Java')
  await page.getByRole('button', { name: '停用定位，恢复任务仿真', exact: true }).click()
  await page.getByRole('button', { name: '启用终端定位', exact: true }).waitFor()
  check('UI can explicitly return aircraft control to task simulation')
  const readOnly = await browser.newContext({ viewport: { width: 1680, height: 1080 }, locale: 'zh-CN' })
  await readOnly.addCookies([{ name: 'Admin-Token', value: process.env.SKYTWIN_UI_VIEWER_TOKEN, url: base }])
  const viewer = await readOnly.newPage()
  await viewer.goto(base + '/positioning')
  await viewer.getByRole('heading', { name: '定位接入与轨迹回放', exact: true }).waitFor()
  assert.equal(await viewer.getByRole('button', { name: '创建绑定', exact: true }).count(), 0)
  assert.equal(await viewer.getByRole('button', { name: '单次上报', exact: true }).isDisabled(), true)
  check('viewer sees read-only positioning without binding or reporting rights')
  await page.goto(base + '/digital-twin')
  await page.getByRole('heading', { name: '飞行器资源', exact: true }).waitFor()
  assert.deepEqual(errors, [])
  check('navigation and unmount leave no uncaught Vue errors')
  report.passed = true
} catch (e) { report.error = String(e); throw e }
finally { await browser?.close(); await writeFile(resolve('ruoyi/logs/positioning-ui-verification.json'), JSON.stringify(report, null, 2)) }
