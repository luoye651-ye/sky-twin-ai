import { test } from 'node:test'
import assert from 'node:assert/strict'
import http from 'node:http'
import { once } from 'node:events'
import { createGateway, routeFor } from './public-gateway.mjs'
import { createHmac } from 'node:crypto'

const site = 'https://skytwin-ai-demo.spicyangel15.chatgpt.site'
test('gateway refuses admin, files, arbitrary hosts and traversal', () => {
  for (const path of ['/system/user/list', '/java-api/system/user/list', '/.env', '/profile/test.jpg', '//evil.test/sky/a', '/java-api/sky/../system/user', '/java-api/sky/%2e%2e/system/user', '/agent-api/openapi.json', '/java-api/sky/a%5cb']) assert.equal(routeFor(path, 'GET'), null, path)
  assert.equal(routeFor('/java-api/login', 'GET'), null)
  assert.equal(routeFor('/java-api/sky/snapshot', 'GET').authenticated, true)
  assert.equal(routeFor('/agent-api/chat', 'POST').port, 8002)
})

test('gateway checks CORS and JWT before upstream and streams without buffering', async t => {
  let lastHeaders
  const fixture = http.createServer((req, res) => {
    lastHeaders = req.headers
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Set-Cookie': 'private=never-forward' })
    res.write('data: first\n\n')
    setTimeout(() => res.end('data: last\n\n'), 200)
  }).listen(0, '127.0.0.1')
  await once(fixture, 'listening')
  const gateway = createGateway({ origins: [site], port: 0, request: (options, cb) => http.request({ ...options, port: fixture.address().port }, cb) })
  await once(gateway, 'listening')
  t.after(() => { gateway.closeAllConnections(); gateway.close(); fixture.closeAllConnections(); fixture.close() })
  const url = `http://127.0.0.1:${gateway.address().port}`
  assert.equal((await fetch(url + '/java-api/sky/snapshot')).status, 401)
  assert.equal((await fetch(url + '/java-api/captchaImage', { headers: { Origin: 'https://evil.test' } })).status, 403)
  assert.equal((await fetch(url + '/java-api/system/user/list')).status, 404)
  const preflight = await fetch(url + '/agent-api/chat', { method: 'OPTIONS', headers: { Origin: site, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'authorization,content-type' } })
  assert.equal(preflight.status, 204)
  assert.equal(preflight.headers.get('Access-Control-Allow-Origin'), site)
  const response = await fetch(url + '/java-api/sky/stream', { headers: { Origin: site, Authorization: 'Bearer isolated-fixture', Cookie: 'secret=drop' } })
  assert.equal(response.headers.get('Set-Cookie'), null)
  assert.equal(response.headers.get('Access-Control-Allow-Origin'), site)
  const reader = response.body.getReader()
  assert.equal(new TextDecoder().decode((await reader.read()).value), 'data: first\n\n')
  assert.equal(new TextDecoder().decode((await reader.read()).value), 'data: last\n\n')
  assert.equal(lastHeaders.origin, 'http://127.0.0.1:5173')
  assert.equal(lastHeaders.cookie, undefined)
})

test('production tunnel requires bridge secret and signs identity challenges', async t => {
  const tunnelSecret = 'isolated-production-boundary-fixture'
  const gateway = createGateway({ origins: [site], port: 0, tunnelSecret })
  await once(gateway, 'listening')
  t.after(() => { gateway.closeAllConnections(); gateway.close() })
  const base = `http://127.0.0.1:${gateway.address().port}`
  assert.equal((await fetch(base + '/java-api/captchaImage')).status, 401)
  assert.equal((await fetch(base + '/java-api/captchaImage', { headers: { 'X-SkyTwin-Gateway': 'wrong' } })).status, 401)
  const challenge = '550e8400-e29b-41d4-a716-446655440000'
  const proof = await (await fetch(base + '/_gateway/ping?challenge=' + challenge)).json()
  assert.equal(proof.signature, createHmac('sha256', tunnelSecret).update(challenge).digest('hex'))
})
