// Runs only against the dedicated local app, with tokens supplied by its Python
// fixture owner. Never writes tokens to disk or touches the user's browser profile.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { writeFile, mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.SKYTWIN_PLAYWRIGHT_MODULE || 'playwright')
const base = 'http://127.0.0.1:5173'
const prefix = process.env.SKYTWIN_UI_PREFIX
assert(prefix?.startsWith('ld_') && /^ld_[a-f0-9]+$/.test(prefix))
const cargo = `${prefix}_ui_delivery`
const report = { passed: false, checks: [], interceptedErrorCase: 'One isolated browser response simulates a delivery conflict; normal flow uses real Java APIs.' }
const check = name => { report.checks.push(name); console.log('PASS UI: ' + name) }
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
async function waitFor(checker, label, ms = 15000) {
  const end = Date.now() + ms
  while (Date.now() < end) {
    if (await checker()) return
    await delay(150)
  }
  throw new Error('Timeout: ' + label)
}

let browser
try {
  try { browser = await chromium.launch({ channel: 'chrome', headless: true }) }
  catch { browser = await chromium.launch({ headless: true }) }
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 }, locale: 'zh-CN' })
  await context.addCookies([{ name: 'Admin-Token', value: process.env.SKYTWIN_UI_ADMIN_TOKEN, url: base }])
  const page = await context.newPage()
  const pageErrors = []
  page.on('pageerror', error => pageErrors.push(error.message))
  await page.goto(base + '/logistics')
  await page.getByRole('button', { name: '新建配送订单', exact: true }).waitFor()
  await page.getByRole('button', { name: '新建配送订单', exact: true }).click()
  const editor = page.getByRole('dialog', { name: '新建配送订单', exact: true })
  await editor.getByRole('button', { name: '提交订单', exact: true }).click()
  await editor.getByText('请填写货物名称和创建原因', { exact: true }).waitFor()
  check('empty form rejected in place')
  await editor.getByPlaceholder('例如：应急药品').fill(cargo)
  await editor.getByRole('spinbutton').nth(0).fill('2.5')
  await editor.locator('.el-select').nth(0).click()
  await page.getByRole('option', { name: prefix + '_station_0', exact: true }).click()
  await editor.locator('.el-select').nth(1).click()
  assert.equal(await page.getByRole('option', { name: prefix + '_station_0', exact: true }).last().getAttribute('aria-disabled'), 'true')
  await page.getByRole('option', { name: prefix + '_station_1', exact: true }).last().click()
  await editor.getByPlaceholder('请填写本次配送原因').fill(prefix + '_ui_create')
  await editor.getByRole('button', { name: '提交订单', exact: true }).click()
  await editor.waitFor({ state: 'hidden' })
  await page.getByRole('textbox', { name: '搜索配送订单' }).fill(cargo)
  const row = page.getByRole('row').filter({ hasText: cargo })
  await row.getByRole('button', { name: '分配', exact: true }).waitFor()
  check('real UI creation refreshes the order list')

  await row.getByRole('button', { name: '查看配送', exact: true }).click()
  let detail = page.getByRole('dialog', { name: '配送详情与轨迹', exact: true })
  await detail.getByRole('tab', { name: '飞行轨迹', exact: true }).click()
  await detail.getByText('任务尚未起飞，暂无轨迹', { exact: true }).waitFor()
  await detail.locator('.el-dialog__headerbtn').click()
  await detail.waitFor({ state: 'hidden' })
  check('pre-flight detail shows an empty trajectory')

  await row.getByRole('button', { name: '分配', exact: true }).click()
  let operation = page.getByRole('dialog', { name: '分配货运无人机', exact: true })
  await operation.locator('.el-select').click()
  await page.getByRole('option').filter({ hasText: prefix + '_aircraft' }).click()
  await operation.getByRole('textbox', { name: '配送操作原因' }).fill(prefix + '_ui_assign')
  await operation.getByRole('button', { name: '确认分配货运无人机', exact: true }).click()
  await operation.waitFor({ state: 'hidden' })
  await row.getByText('待起飞', { exact: true }).waitFor()
  check('order assignment uses a real dedicated cargo aircraft')

  await row.getByRole('button', { name: '执行仿真', exact: true }).click()
  operation = page.getByRole('dialog', { name: '执行仿真', exact: true })
  await operation.getByRole('textbox', { name: '配送操作原因' }).fill(prefix + '_ui_start')
  await operation.getByRole('button', { name: '确认执行仿真', exact: true }).click()
  await operation.waitFor({ state: 'hidden' })
  await row.getByText('运输中', { exact: true }).waitFor()
  await row.getByRole('button', { name: '查看配送', exact: true }).click()
  detail = page.getByRole('dialog', { name: '配送详情与轨迹', exact: true })
  await detail.getByRole('tab', { name: '飞行轨迹', exact: true }).click()
  await detail.getByRole('img', { name: '配送飞行轨迹示意' }).waitFor()
  await waitFor(async () => (await detail.innerText()).includes('已保存'), 'live trajectory')
  await detail.locator('.el-dialog__headerbtn').click()
  await detail.waitFor({ state: 'hidden' })
  await row.getByText('待确认送达', { exact: true }).waitFor({ timeout: 65000 })
  check('Java completes flight and the list automatically updates without manual refresh')

  await row.getByRole('button', { name: '确认送达', exact: true }).click()
  operation = page.getByRole('dialog', { name: '确认送达', exact: true })
  await operation.getByRole('button', { name: '确认送达', exact: true }).click()
  await operation.getByText('请填写1～500个字符的操作原因', { exact: true }).waitFor()
  const reason = prefix + '_ui_deliver'
  await operation.getByRole('textbox', { name: '配送操作原因' }).fill(reason)
  let intercepted = false
  await page.route('**/java-api/sky/logistics/orders/*/deliver', async route => {
    if (!intercepted) {
      intercepted = true
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 409, msg: 'UI验收模拟冲突，请重试' }) })
    } else await route.continue()
  })
  await operation.getByRole('button', { name: '确认送达', exact: true }).click()
  await operation.getByText('UI验收模拟冲突，请重试', { exact: true }).waitFor()
  assert.equal(await operation.getByRole('textbox', { name: '配送操作原因' }).inputValue(), reason)
  check('a simulated server error preserves the confirmation reason and dialog')
  await operation.getByRole('button', { name: '确认送达', exact: true }).click()
  await operation.waitFor({ state: 'hidden' })
  await row.getByText('已送达', { exact: true }).waitFor()
  assert.equal(await row.getByRole('button', { name: '确认送达', exact: true }).count(), 0)
  check('real delivery confirmation updates the order and removes the action')
  await page.reload()
  await page.getByRole('textbox', { name: '搜索配送订单' }).fill(cargo)
  await row.getByText('已送达', { exact: true }).waitFor()
  await row.getByRole('button', { name: '查看配送', exact: true }).click()
  detail = page.getByRole('dialog', { name: '配送详情与轨迹', exact: true })
  await detail.getByRole('tab', { name: '操作记录', exact: true }).click()
  await detail.getByText(reason, { exact: true }).waitFor()
  await detail.getByRole('tab', { name: '飞行轨迹', exact: true }).click()
  await detail.getByRole('img', { name: '配送飞行轨迹示意' }).waitFor()
  await mkdir(resolve('docs/verification'), { recursive: true })
  await page.screenshot({ path: resolve('docs/verification/logistics-delivery-detail.png'), fullPage: true })
  check('reload preserves delivery, audit and trajectory; screenshot saved')

  const viewerContext = await browser.newContext({ viewport: { width: 1600, height: 1000 }, locale: 'zh-CN' })
  await viewerContext.addCookies([{ name: 'Admin-Token', value: process.env.SKYTWIN_UI_VIEWER_TOKEN, url: base }])
  const viewer = await viewerContext.newPage()
  await viewer.goto(base + '/logistics')
  await viewer.getByRole('textbox', { name: '搜索配送订单' }).fill(prefix + '_guards')
  const viewerRow = viewer.getByRole('row').filter({ hasText: prefix + '_guards' })
  await viewerRow.getByRole('button', { name: '查看配送', exact: true }).waitFor()
  assert.equal(await viewer.getByRole('button', { name: '新建配送订单', exact: true }).count(), 0)
  assert.equal(await viewerRow.getByRole('button', { name: '分配', exact: true }).count(), 0)
  assert.equal(await viewerRow.getByRole('button', { name: '取消配送', exact: true }).count(), 0)
  await viewerRow.getByRole('button', { name: '查看配送', exact: true }).click()
  await viewer.getByRole('dialog', { name: '配送详情与轨迹', exact: true }).getByRole('heading', { name: prefix + '_guards', exact: true }).waitFor()
  check('viewer can read details but sees no creation or dispatch controls')
  await viewerContext.close()
  await page.goto(base + '/general')
  await page.goto(base + '/logistics')
  await page.getByRole('textbox', { name: '搜索配送订单' }).waitFor()
  assert.deepEqual(pageErrors, [])
  check('page changes leave no uncaught Vue errors')
  report.passed = true
} catch (error) {
  report.error = String(error)
  throw error
} finally {
  await browser?.close()
  await writeFile(resolve('ruoyi/logs/logistics-ui-verification.json'), JSON.stringify(report, null, 2))
}
