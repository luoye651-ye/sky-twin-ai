import { test } from 'node:test'
import assert from 'node:assert/strict'
import http from 'node:http'
import { once } from 'node:events'
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { createDomesticServer } from './domestic-server.mjs'

test('domestic entry serves SPA and same-origin APIs without Sites, preserving access controls and streaming', async t => {
  const directory = mkdtempSync(path.join(os.tmpdir(), 'skytwin-cn-test-'))
  writeFileSync(path.join(directory, 'index.html'), '<html><div id="app">isolated fixture</div></html>')
  writeFileSync(path.join(directory, 'fixture.json'), JSON.stringify({ fixture: 'test-only-'.repeat(1000) }))
  let upstreamHeaders
  const fixture = http.createServer((req, res) => {
    upstreamHeaders = req.headers
    res.writeHead(200, { 'Content-Type': 'text/event-stream' })
    res.write('data: first\n\n'); setTimeout(() => res.end('data: last\n\n'), 100)
  }).listen(0, '127.0.0.1')
  await once(fixture, 'listening')
  const publicOrigin = 'https://isolated-domestic.example.test'
  const entry = await createDomesticServer({ publicOrigin, port: 0, staticRoot: directory, upstreamRequest: (options, cb) => http.request({ ...options, port: fixture.address().port }, cb) })
  t.after(() => { entry.close(); fixture.closeAllConnections(); fixture.close(); rmSync(directory, { recursive: true, force: true }) })
  const base = 'http://127.0.0.1:' + entry.server.address().port
  const headers = { Host: 'isolated-domestic.example.test', 'X-Forwarded-Proto': 'https', Origin: publicOrigin }
  // Node's fetch discards Host. Use HTTP directly to exercise the real tunnel
  // Host and forwarded-protocol boundary, including the public HTTPS check.
  const check = (url, extra = {}) => new Promise((resolve, reject) => {
    const request = http.request(base + url, { method: extra.method || 'GET', headers: { ...headers, ...extra.headers } }, reply => {
      const stream = new ReadableStream({ start(controller) { reply.on('data', value => controller.enqueue(value)); reply.on('end', () => controller.close()); reply.on('error', error => controller.error(error)) } })
      resolve(new Response(stream, { status: reply.statusCode, headers: { 'Content-Type': reply.headers['content-type'] || '' } }))
    })
    request.on('error', reject); request.end(extra.body)
  })
  assert.match(await (await check('/ai-workbench')).text(), /isolated fixture/)
  const config = await (await check('/deployment-config.js')).text()
  assert.match(config, /apiOrigin: ''/); assert.doesNotMatch(config, /chatgpt|localhost.run/)
  const asset = await fetch(base + '/fixture.json', { headers: { 'Accept-Encoding': 'gzip' } })
  assert.equal(asset.headers.get('Content-Encoding'), 'gzip')
  assert.equal((await asset.json()).fixture, 'test-only-'.repeat(1000))
  const cached = await fetch(base + '/fixture.json', { headers: { 'If-None-Match': asset.headers.get('ETag') } })
  assert.equal(cached.status, 304)
  assert.equal((await check('/java-api/sky/snapshot')).status, 401)
  assert.equal((await check('/java-api/system/user/list')).status, 404)
  assert.equal((await check('/.env')).status, 400)
  assert.equal((await check('/java-api/login', { method: 'POST', body: JSON.stringify({ username: 'admin' }), headers: { 'Content-Type': 'application/json' } })).status, 403)
  assert.equal((await check('/java-api/captchaImage', { headers: { Origin: 'https://evil.test' } })).status, 403)
  assert.equal((await check('/', { headers: { 'X-Forwarded-Proto': 'http' } })).status, 426)
  const stream = await check('/java-api/sky/stream', { headers: { Authorization: 'Bearer fixture-only', Cookie: 'never-forward=1' } })
  const reader = stream.body.getReader()
  assert.equal(new TextDecoder().decode((await reader.read()).value), 'data: first\n\n')
  assert.equal(new TextDecoder().decode((await reader.read()).value), 'data: last\n\n')
  assert.equal(upstreamHeaders.origin, 'http://127.0.0.1:5173')
  assert.equal(upstreamHeaders.cookie, undefined)
  await assert.rejects(createDomesticServer({ publicOrigin: 'http://insecure.test', port: 0, staticRoot: directory }), /HTTPS/)
})
